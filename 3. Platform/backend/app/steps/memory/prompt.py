"""Prompt-building step node."""

from __future__ import annotations

from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from loguru import logger

from app.steps.state import ChatState, M_BOT, M_USR

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


def build_prompt(state: ChatState) -> dict:
    """Build the 3-layer system prompt + conversation messages."""
    session = state["session"]
    message = state["message"]
    user_context = state.get("user_context", {})
    use_memory = state.get("use_memory", True)

    logger.info(f"[NODE:build_prompt] ▶ message='{message[:80]}...'" if len(message) > 80 else f"[NODE:build_prompt] ▶ message='{message}'")

    # Build system prompt parts
    parts: List[str] = [SYSTEM_PROMPT]

    if use_memory:
        # Layer 2: session summary
        summary = session.get("summary", "")
        if summary:
            parts.append(f"\n## Sessie-samenvatting\n{summary}")
            logger.debug(f"[NODE:build_prompt] Layer 2: summary ({len(summary)} chars)")

        # Layer 3: Q&A index (last 10)
        qa_index = session.get("qa_index", [])
        if qa_index:
            logger.debug(f"[NODE:build_prompt] Layer 3: qa_index ({len(qa_index)} entries, using last 10)")
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

    recent_count = len([m for m in msgs if not isinstance(m, SystemMessage)]) - 1  # exclude current user msg
    logger.info(
        f"[NODE:build_prompt] ✓ {len(msgs)} messages "
        f"(system: {len(system_content)} chars, history: {recent_count} msgs, "
        f"user_context: {bool(user_context)})"
    )

    return {"messages": msgs, "retrieved_sources": [], "tool_rounds": 0}
