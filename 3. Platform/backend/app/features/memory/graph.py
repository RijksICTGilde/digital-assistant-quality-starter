"""LangGraph chat graph: assembles and compiles the pipeline."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from loguru import logger

from app.features.memory.session_store import SessionStore
from app.features.memory.tools import create_tools, make_execute_tools_node
from app.steps.memory import (
    _bundle_triage_response,
    _default_triage,
    build_prompt,
    bundle_sources,
    format_response,
    make_call_llm,
    make_call_mcp_node,
    make_guardrail_input_node,
    make_guardrail_output_node,
    make_load_session,
    make_save_session,
    make_triage_faq_node,
    make_triage_intent_node,
    make_triage_mcp_node,
    make_triage_relevance_node,
    make_update_memory,
    make_evaluate_answer_node,
    make_validate_sources_node,
    make_validate_tone_node,
    should_call_llm,
    should_continue,
    should_update_memory,
)
from app.steps.state import ChatState


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
    logger.info(f"[GRAPH:init] Created {len(tools)} tools for LLM:")
    for t in tools:
        logger.info(f"  - {t.name}: {t.description[:80]}...")
    llm_with_tools = llm.bind_tools(tools)
    logger.info("[GRAPH:init] Tools bound to LLM (tool calling enabled)")

    # Build node functions
    load_session = make_load_session(session_store)
    guardrail_input = make_guardrail_input_node()
    triage_mcp = make_triage_mcp_node()
    triage_relevance = make_triage_relevance_node()
    triage_faq = make_triage_faq_node()
    triage_intent = make_triage_intent_node()
    call_llm = make_call_llm(llm_with_tools)
    execute_tools = make_execute_tools_node(tools, _captured_sources)
    evaluate_answer = make_evaluate_answer_node(llm)
    validate_sources = make_validate_sources_node(llm)
    validate_tone = make_validate_tone_node(llm)
    guardrail_output = make_guardrail_output_node()
    mcp_tool_name = os.getenv("MCP_TOOL_NAME") or None
    call_mcp = make_call_mcp_node(mcp_tool_name)
    update_memory = make_update_memory(llm)
    save_session = make_save_session(session_store)

    # Wrapper for call_llm that syncs _state_ref (local mutable state)
    async def call_llm_with_sync(state: ChatState) -> dict:
        _state_ref["session"] = state.get("session", {})
        return await call_llm(state)

    # Wrapper to initialise triage state before the first guardrail/triage node
    async def guardrail_input_with_init(state: ChatState) -> dict:
        if "triage" not in state or not state.get("triage"):
            result = await guardrail_input({**state, "triage": _default_triage()})
            if "triage" not in result:
                result["triage"] = _default_triage()
            return result
        return await guardrail_input(state)

    # Build graph
    graph = StateGraph(ChatState)

    graph.add_node("load_session", load_session)
    graph.add_node("guardrail_input", guardrail_input_with_init)
    graph.add_node("triage_mcp", triage_mcp)
    graph.add_node("triage_relevance", triage_relevance)
    graph.add_node("triage_faq", triage_faq)
    graph.add_node("triage_intent", triage_intent)
    graph.add_node("bundle_triage_response", _bundle_triage_response)
    graph.add_node("build_prompt", build_prompt)
    graph.add_node("call_llm", call_llm_with_sync)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("bundle_sources", bundle_sources)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("validate_sources", validate_sources)
    graph.add_node("validate_tone", validate_tone)
    graph.add_node("guardrail_output", guardrail_output)
    graph.add_node("update_memory", update_memory)
    graph.add_node("save_session", save_session)
    graph.add_node("format_response", format_response)
    graph.add_node("call_mcp", call_mcp)

    # Edges
    graph.add_edge(START, "load_session")

    # ── Input guardrail + triage pipeline (before LLM) ──────────
    graph.add_edge("load_session", "guardrail_input")
    graph.add_edge("guardrail_input", "triage_mcp")
    graph.add_edge("triage_mcp", "triage_relevance")
    graph.add_edge("triage_relevance", "triage_faq")
    graph.add_edge("triage_faq", "triage_intent")
    # After triage: skip LLM, route to MCP, or proceed normally
    graph.add_conditional_edges("triage_intent", should_call_llm, {
        "build_prompt": "build_prompt",
        "bundle_triage_response": "bundle_triage_response",
        "call_mcp": "call_mcp",
    })

    # ── LLM pipeline (normal flow) ──────────────────────────────
    graph.add_edge("build_prompt", "call_llm")
    graph.add_conditional_edges("call_llm", should_continue, {
        "execute_tools": "execute_tools",
        "bundle_sources": "bundle_sources",
    })
    graph.add_edge("execute_tools", "call_llm")
    graph.add_edge("bundle_sources", "evaluate_answer")
    graph.add_edge("evaluate_answer", "validate_sources")
    graph.add_edge("validate_sources", "validate_tone")

    # ── Output guardrail (both paths converge here) ─────────────
    graph.add_edge("validate_tone", "guardrail_output")
    graph.add_edge("bundle_triage_response", "guardrail_output")

    # ── Memory update or straight to response ───────────────────
    graph.add_conditional_edges("guardrail_output", should_update_memory, {
        "update_memory": "update_memory",
        "format_response": "format_response",
    })

    # ── MCP bypasses validators, goes straight to memory/response ─
    graph.add_conditional_edges("call_mcp", should_update_memory, {
        "update_memory": "update_memory",
        "format_response": "format_response",
    })

    graph.add_edge("update_memory", "save_session")
    graph.add_edge("save_session", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
