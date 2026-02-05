"""LangGraph chat graph: state definition, node functions, and graph builder."""

from __future__ import annotations

import asyncio
import json
import operator
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from typing_extensions import TypedDict

from app.features.memory.models import QAIndexEntry, SessionMemory
from app.features.memory.session_store import SessionStore
from app.features.memory.tools import create_tools, make_execute_tools_node
from app.features.memory.validators import (
    _bundle_triage_response,
    _default_triage,
    make_guardrail_input_node,
    make_guardrail_output_node,
    make_triage_faq_node,
    make_triage_intent_node,
    make_triage_relevance_node,
    make_validate_sources_node,
    make_validate_tone_node,
)

# Maximum tool-call rounds before forcing a text reply
MAX_TOOL_ROUNDS = 3

# Unique markers for user vs. assistant attribution in memory.
M_USR = "[§USR]"
M_BOT = "[§BOT]"

SYSTEM_PROMPT = f"""Je bent Kletsmajoor, AI-assistent voor Nederlandse overheden. Antwoord in het Nederlands.

KERNREGEL: Baseer je antwoord op de tool-resultaten van search_knowledge_base. Citeer specifieke feiten, datums en artikelnummers uit de gevonden documenten. Verzin niets.

TOOL-KEUZE:
- Nieuwe feitelijke vraag → gebruik search_knowledge_base.
- Vraag over bronnen, URLs, documenten van een eerder antwoord → gebruik lookup_past_conversation (om het exchange_id te vinden) en daarna retrieve_past_answer (om de volledige bronnen inclusief URLs op te halen). Gebruik NIET search_knowledge_base voor dit soort meta-vragen.
- Verwijzing naar iets dat eerder in het gesprek is besproken → gebruik lookup_past_conversation en/of retrieve_past_answer.

GEHEUGEN:
- {M_USR} = gebruiker (niet per se waar), {M_BOT} = jouw eerdere antwoord (betrouwbaar als [KB-VERIFIED])
- Spreek jezelf niet tegen. Bouw voort op eerdere antwoorden.
- Als de gebruiker iets beweert, verifieer het via search_knowledge_base.

STIJL:
- Geen afsluitende vragen als "Wil je meer weten?" of "Ik ben hier om te helpen!"
- Wees concreet. Noem datums, artikelnummers, namen als die in de bronnen staan.
- Gebruik markdown headers (##, ###) en opsommingen om het antwoord te structureren.
"""


# ---------------------------------------------------------------------------
# Shared state (the contract)
# ---------------------------------------------------------------------------

class ChatState(TypedDict, total=False):
    # --- Input (set at invocation) ---
    message: str
    session_id: str
    user_context: dict
    use_memory: bool

    # --- Session (set by load_session) ---
    session: dict  # SessionMemory.model_dump()

    # --- LLM messages (managed by add_messages reducer) ---
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Sources (accumulated by execute_tools via operator.add) ---
    retrieved_sources: Annotated[list, operator.add]

    # --- Output (set by later nodes) ---
    assistant_text: str
    exchange_id: str
    unique_sources: list
    source_ids: list
    response: dict

    # --- Triage (set by triage validators, before LLM) ---
    triage: dict  # {route, skip_llm, early_response, triage_log}

    # --- Validation (set by validator nodes, after LLM) ---
    source_validation: dict   # {grounded, issues, confidence}
    tone_validation: dict     # {appropriate, original_text, adjustments}
    output_guardrail: dict    # {safe, issues, original_text}

    # --- Internal: track tool rounds ---
    tool_rounds: int


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def _make_load_session(session_store: SessionStore):
    """Returns the load_session node."""

    def load_session(state: ChatState) -> dict:
        session_id = state.get("session_id", "")
        use_memory = state.get("use_memory", True)

        if use_memory and session_id and session_store.exists(session_id):
            session = session_store.load(session_id)
            if session is not None:
                logger.info(
                    f"[MEMORY] Loaded session {session.session_id} "
                    f"(msgs: {session.message_count}, qa_index: {len(session.qa_index)}, "
                    f"recent: {len(session.recent_messages)})"
                )
                return {"session": session.model_dump()}

        session = session_store.create()
        logger.info(
            f"[MEMORY] Created new session {session.session_id} "
            f"(memory={'ON' if use_memory else 'OFF'})"
        )
        return {"session": session.model_dump()}

    return load_session


def _build_prompt(state: ChatState) -> dict:
    """Build the 3-layer system prompt + conversation messages."""
    session = state["session"]
    message = state["message"]
    user_context = state.get("user_context", {})
    use_memory = state.get("use_memory", True)

    # Build system prompt parts
    parts: List[str] = [SYSTEM_PROMPT]

    if use_memory:
        # Layer 2: session summary
        summary = session.get("summary", "")
        if summary:
            parts.append(f"\n## Sessie-samenvatting\n{summary}")

        # Layer 3: Q&A index (last 10)
        qa_index = session.get("qa_index", [])
        if qa_index:
            index_lines = []
            for entry in qa_index[-10:]:
                verified_tag = "KB-VERIFIED" if entry.get("verified", False) else "UNVERIFIED"
                source_ids = entry.get("source_ids", [])
                sources_tag = f" sources:{len(source_ids)}" if source_ids else ""
                topics = entry.get("topics", [])
                index_lines.append(
                    f"- [{entry.get('exchange_id', '')}] intent:{entry.get('user_intent', 'question')} | "
                    f"{M_USR} {entry.get('question_summary', '')} → "
                    f"{M_BOT} {entry.get('answer_summary', '')} "
                    f"[{verified_tag}]{sources_tag} (topics: {', '.join(topics)})"
                )
            parts.append("\n## Eerdere vragen in dit gesprek\n" + "\n".join(index_lines))

    # User context
    if user_context:
        ctx_str = ", ".join(f"{k}: {v}" for k, v in user_context.items() if v)
        if ctx_str:
            parts.append(f"\n## Gebruikerscontext\n{ctx_str}")

    system_content = "\n".join(parts)
    msgs: List[BaseMessage] = [SystemMessage(content=system_content)]

    # Layer 1: recent message pairs from session (server-side, last 5 pairs = 10 msgs)
    # Skip pairs where the assistant response was empty (failed turns)
    if use_memory:
        recent = session.get("recent_messages", [])[-10:]
        i = 0
        while i < len(recent):
            role = recent[i].get("role", "user")
            content = recent[i].get("content", "")
            if role == "user":
                # Check if the next message is a non-empty assistant response
                next_msg = recent[i + 1] if i + 1 < len(recent) else None
                if next_msg and next_msg.get("role") == "assistant" and next_msg.get("content", "").strip():
                    msgs.append(HumanMessage(content=content))
                    msgs.append(AIMessage(content=next_msg["content"]))
                    i += 2
                    continue
                elif next_msg and next_msg.get("role") == "assistant":
                    # Skip the entire pair — empty assistant response
                    i += 2
                    continue
            i += 1

    # Current user message
    msgs.append(HumanMessage(content=message))

    logger.info(f"[MEMORY] Built {len(msgs)} messages for LLM")
    logger.debug(f"[MEMORY] System prompt length: {len(system_content)} chars")

    return {"messages": msgs, "retrieved_sources": [], "tool_rounds": 0}


def _make_call_llm(llm: ChatOpenAI):
    """Returns the call_llm node (LLM with bound tools)."""

    async def call_llm(state: ChatState) -> dict:
        messages = state["messages"]
        tool_rounds = state.get("tool_rounds", 0)
        logger.info(f"[TOOL-LOOP] Round {tool_rounds + 1}/{MAX_TOOL_ROUNDS} — calling LLM")
        response = await llm.ainvoke(messages)
        return {"messages": [response], "tool_rounds": tool_rounds + 1}

    return call_llm


def _should_continue(state: ChatState) -> str:
    """Conditional edge: check if the last AI message has tool_calls."""
    messages = state["messages"]
    last_msg = messages[-1]
    tool_rounds = state.get("tool_rounds", 0)

    if isinstance(last_msg, AIMessage) and last_msg.tool_calls and tool_rounds < MAX_TOOL_ROUNDS:
        return "execute_tools"
    return "bundle_sources"


def _bundle_sources(state: ChatState) -> dict:
    """Deduplicate retrieved_sources and extract assistant text."""
    messages = state["messages"]

    # Find last AIMessage with text content.
    # Some models return both tool_calls and content; we accept content
    # from any AIMessage, not just those without tool_calls.
    assistant_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
            assistant_text = msg.content
            break

    if not assistant_text:
        logger.warning("[MEMORY] No text in AI messages (max tool rounds reached?), using fallback")
        assistant_text = "Ik kon geen antwoord genereren op basis van de beschikbare informatie."

    # Deduplicate sources by document_id
    seen_doc_ids: set = set()
    unique_sources: List[Dict[str, Any]] = []
    for src in state.get("retrieved_sources", []):
        doc_id = src.get("document_id", "")
        if doc_id and doc_id in seen_doc_ids:
            continue
        if doc_id:
            seen_doc_ids.add(doc_id)
        unique_sources.append(src)

    source_ids = [s.get("document_id", "") for s in unique_sources if s.get("document_id")]
    exchange_id = f"ex-{uuid.uuid4().hex[:8]}"

    logger.info(f"[MEMORY] Final answer length: {len(assistant_text)} chars, sources: {len(unique_sources)}")

    return {
        "assistant_text": assistant_text,
        "exchange_id": exchange_id,
        "unique_sources": unique_sources,
        "source_ids": source_ids,
    }


def _should_call_llm(state: ChatState) -> str:
    """Conditional edge after triage: skip LLM when triage says so."""
    triage = state.get("triage") or {}
    if triage.get("skip_llm", False):
        return "bundle_triage_response"
    return "build_prompt"


def _should_update_memory(state: ChatState) -> str:
    """Conditional edge: skip memory update when use_memory is False."""
    if state.get("use_memory", True):
        return "update_memory"
    return "format_response"


def _make_update_memory(llm: ChatOpenAI):
    """Returns the update_memory node."""

    async def _generate_qa_entry(
        question: str, answer: str, exchange_id: str, source_ids: List[str],
    ) -> QAIndexEntry:
        prompt = f"""Analyseer deze Q&A uitwisseling en maak een compacte samenvatting.

{M_USR}: {question[:500]}
{M_BOT}: {answer[:500]}

Bepaal:
- user_intent: wat deed de gebruiker?
  "question" = stelde een vraag
  "assumption" = beweerde iets / maakte een aanname
  "verified" = deelde informatie die de assistent heeft bevestigd
  "preference" = gaf een voorkeur/wens aan (bijv. "ik wil alleen X")
  "correction" = corrigeerde de assistent
- verified: heeft de assistent het antwoord gebaseerd op de kennisbank? (true/false)

Antwoord ALLEEN met valid JSON (geen markdown, geen uitleg):
{{"question_summary": "korte samenvatting vraag", "answer_summary": "korte samenvatting antwoord", "topics": ["topic1", "topic2"], "user_intent": "question", "verified": false}}"""

        response = await llm.ainvoke(
            [
                SystemMessage(content="Je maakt compacte samenvattingen. Antwoord alleen met valid JSON."),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
            max_tokens=200,
        )
        raw = response.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        return QAIndexEntry(
            exchange_id=exchange_id,
            question_summary=data.get("question_summary", question[:100]),
            answer_summary=data.get("answer_summary", answer[:100]),
            topics=data.get("topics", []),
            source_ids=source_ids or [],
            user_intent=data.get("user_intent", "question"),
            verified=data.get("verified", False),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _update_summary(current_summary: str, question: str, answer: str) -> str:
        prompt = f"""Update de sessie-samenvatting met de laatste uitwisseling.
Houd het onder 200 woorden.

BELANGRIJK: Markeer duidelijk de BRON van informatie:
- {M_USR} = uitspraken van de gebruiker (hun woorden, NIET per se waar)
- {M_BOT} = antwoorden van de assistent (gebaseerd op kennisbank)

Gebruik deze markers in de samenvatting. Voorbeeld:
"{M_USR} Gebruiker vroeg naar GDPR. {M_BOT} Assistent legde uit dat DPIA verplicht is. {M_USR} Gebruiker gaf aan alleen interesse te hebben in bewaartermijnen."

Focus op: gebruikersvoorkeuren, besluiten, en geverifieerde feiten.

Huidige samenvatting:
{current_summary or '(geen – dit is het eerste bericht)'}

Nieuwe uitwisseling:
{M_USR} {question[:300]}
{M_BOT} {answer[:300]}

Geef ALLEEN de bijgewerkte samenvatting terug, geen uitleg."""

        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="Je werkt sessie-samenvattingen bij. Maak altijd duidelijk onderscheid "
                    "tussen wat de gebruiker zei en wat de assistent antwoordde. "
                    "Antwoord alleen met de samenvatting."
                ),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
            max_tokens=300,
        )
        return response.content or current_summary

    async def update_memory(state: ChatState) -> dict:
        session = dict(state["session"])  # shallow copy
        message = state["message"]
        assistant_text = state["assistant_text"]
        exchange_id = state["exchange_id"]
        source_ids = state.get("source_ids", [])
        unique_sources = state.get("unique_sources", [])

        # Store full answer
        full_answers = dict(session.get("full_answers", {}))
        full_answers[exchange_id] = {
            "text": assistant_text,
            "sources": unique_sources,
        }
        session["full_answers"] = full_answers

        # Increment message count
        session["message_count"] = session.get("message_count", 0) + 1

        # Update recent messages (keep last 10 = 5 pairs)
        # Only store pairs where the assistant actually responded
        recent = list(session.get("recent_messages", []))
        if assistant_text.strip():
            recent.append({"role": "user", "content": message})
            recent.append({"role": "assistant", "content": assistant_text})
            session["recent_messages"] = recent[-10:]

        # Run QA entry + summary update in parallel
        try:
            results = await asyncio.gather(
                _generate_qa_entry(message, assistant_text, exchange_id, source_ids),
                _update_summary(session.get("summary", ""), message, assistant_text),
                return_exceptions=True,
            )

            # Q&A entry
            qa_index = list(session.get("qa_index", []))
            if isinstance(results[0], QAIndexEntry):
                qa_index.append(results[0].model_dump())
            else:
                logger.warning(f"QA index generation failed: {results[0]}")
                qa_index.append(QAIndexEntry(
                    exchange_id=exchange_id,
                    question_summary=message[:100],
                    answer_summary=assistant_text[:100],
                    topics=[],
                    source_ids=source_ids,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ).model_dump())
            session["qa_index"] = qa_index

            # Summary
            if isinstance(results[1], str):
                session["summary"] = results[1]
            else:
                logger.warning(f"Summary update failed: {results[1]}")

        except Exception as e:
            logger.error(f"Session memory update failed: {e}")

        return {"session": session}

    return update_memory


def _make_save_session(session_store: SessionStore):
    """Returns the save_session node."""

    def save_session(state: ChatState) -> dict:
        session_data = state["session"]
        session = SessionMemory(**session_data)
        session_store.save(session)
        logger.info(
            f"[MEMORY] Session saved (summary: {len(session.summary)} chars, "
            f"qa_index: {len(session.qa_index)} entries, "
            f"recent: {len(session.recent_messages)}, "
            f"sources: {len(state.get('unique_sources', []))})"
        )
        return {}

    return save_session


def _format_response(state: ChatState) -> dict:
    """Build the API response dict."""
    assistant_text = state.get("assistant_text", "")
    unique_sources = state.get("unique_sources", [])
    session = state["session"]

    knowledge_sources = [
        {
            "title": s.get("title", ""),
            "document_id": s.get("document_id", ""),
            "relevance_score": s.get("relevance_score", 0),
            "url": s.get("url", ""),
            "section_title": s.get("section_title", ""),
        }
        for s in unique_sources
    ]

    return {
        "response": {
            "main_answer": assistant_text,
            "response_type": "direct_answer",
            "confidence_level": "medium",
            "complexity": "moderate",
            "knowledge_sources": knowledge_sources,
            "action_items": [],
            "compliance_checks": [],
            "follow_up_suggestions": [],
            "needs_human_expert": False,
            "relevant_regulations": [],
            "processing_time_ms": 0,
            "session_id": session.get("session_id", ""),
            "validation": {
                "sources": state.get("source_validation", {}),
                "tone": state.get("tone_validation", {}),
                "output_guardrail": state.get("output_guardrail", {}),
            },
            "triage": state.get("triage", {}),
        }
    }


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_chat_graph(llm: ChatOpenAI, enhanced_rag: Any, session_store: SessionStore):
    """Assemble and compile the LangGraph chat graph.

    Dependencies (llm, enhanced_rag, session_store) are captured via closures
    in the node factory functions.
    """
    # Mutable containers shared between tools and graph nodes
    _state_ref: Dict[str, Any] = {}
    _captured_sources: List[Dict[str, Any]] = []

    def session_getter():
        return _state_ref.get("session", {})

    tools = create_tools(enhanced_rag, session_getter, _captured_sources)
    llm_with_tools = llm.bind_tools(tools)

    # Build node functions
    load_session = _make_load_session(session_store)
    guardrail_input = make_guardrail_input_node()
    triage_relevance = make_triage_relevance_node()
    triage_faq = make_triage_faq_node()
    triage_intent = make_triage_intent_node()
    call_llm = _make_call_llm(llm_with_tools)
    execute_tools = make_execute_tools_node(tools, _captured_sources)
    validate_sources = make_validate_sources_node(llm)
    validate_tone = make_validate_tone_node(llm)
    guardrail_output = make_guardrail_output_node()
    update_memory = _make_update_memory(llm)
    save_session = _make_save_session(session_store)

    # We need a wrapper for call_llm that also syncs _state_ref
    async def call_llm_with_sync(state: ChatState) -> dict:
        _state_ref["session"] = state.get("session", {})
        return await call_llm(state)

    # Wrapper to initialise triage state before the first guardrail/triage node
    async def guardrail_input_with_init(state: ChatState) -> dict:
        if "triage" not in state or not state.get("triage"):
            # Seed the triage dict so all downstream validators can read/mutate it
            result = await guardrail_input({**state, "triage": _default_triage()})
            if "triage" not in result:
                result["triage"] = _default_triage()
            return result
        return await guardrail_input(state)

    # Build graph
    graph = StateGraph(ChatState)

    graph.add_node("load_session", load_session)
    graph.add_node("guardrail_input", guardrail_input_with_init)
    graph.add_node("triage_relevance", triage_relevance)
    graph.add_node("triage_faq", triage_faq)
    graph.add_node("triage_intent", triage_intent)
    graph.add_node("bundle_triage_response", _bundle_triage_response)
    graph.add_node("build_prompt", _build_prompt)
    graph.add_node("call_llm", call_llm_with_sync)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("bundle_sources", _bundle_sources)
    graph.add_node("validate_sources", validate_sources)
    graph.add_node("validate_tone", validate_tone)
    graph.add_node("guardrail_output", guardrail_output)
    graph.add_node("update_memory", update_memory)
    graph.add_node("save_session", save_session)
    graph.add_node("format_response", _format_response)

    # Edges
    graph.add_edge(START, "load_session")

    # ── Input guardrail + triage pipeline (before LLM) ──────────
    graph.add_edge("load_session", "guardrail_input")
    graph.add_edge("guardrail_input", "triage_relevance")
    graph.add_edge("triage_relevance", "triage_faq")
    graph.add_edge("triage_faq", "triage_intent")
    # After triage: either skip LLM or proceed normally
    graph.add_conditional_edges("triage_intent", _should_call_llm, {
        "build_prompt": "build_prompt",
        "bundle_triage_response": "bundle_triage_response",
    })

    # ── LLM pipeline (normal flow) ──────────────────────────────
    graph.add_edge("build_prompt", "call_llm")
    graph.add_conditional_edges("call_llm", _should_continue, {
        "execute_tools": "execute_tools",
        "bundle_sources": "bundle_sources",
    })
    graph.add_edge("execute_tools", "call_llm")
    graph.add_edge("bundle_sources", "validate_sources")
    graph.add_edge("validate_sources", "validate_tone")

    # ── Output guardrail (both paths converge here) ─────────────
    graph.add_edge("validate_tone", "guardrail_output")
    graph.add_edge("bundle_triage_response", "guardrail_output")

    # ── Memory update or straight to response ───────────────────
    graph.add_conditional_edges("guardrail_output", _should_update_memory, {
        "update_memory": "update_memory",
        "format_response": "format_response",
    })

    graph.add_edge("update_memory", "save_session")
    graph.add_edge("save_session", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
