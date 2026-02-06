"""LangGraph chat graph: assembles and compiles the pipeline."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

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
    make_format_mcp_node,
    make_gather_mcp_params_node,
    make_guardrail_input_node,
    make_guardrail_output_node,
    make_load_session,
    make_save_session,
    make_triage_faq_node,
    make_triage_intent_node,
    make_triage_mcp_node,
    make_triage_relevance_node,
    make_update_memory,
    make_validate_sources_node,
    make_validate_tone_node,
    should_call_llm,
    should_continue,
    should_update_memory,
)
from app.steps.state import ChatState


def build_chat_graph(
    llm: ChatOpenAI,
    enhanced_rag: Any,
    session_store: SessionStore,
    faq_service: Any = None,
):
    """Assemble and compile the LangGraph chat graph.

    Dependencies (llm, enhanced_rag, session_store, faq_service) are captured
    via closures in the node factory functions.

    Args:
        llm: The ChatOpenAI instance for LLM calls
        enhanced_rag: The EnhancedRAGSystem for knowledge retrieval
        session_store: The SessionStore for session persistence
        faq_service: Optional FAQService for FAQ matching (skips LLM for exact matches)
    """
    # Mutable containers shared between tools and graph nodes
    _state_ref: Dict[str, Any] = {}
    _captured_sources: List[Dict[str, Any]] = []

    def session_getter():
        return _state_ref.get("session", {})

    tools = create_tools(enhanced_rag, session_getter, _captured_sources)
    llm_with_tools = llm.bind_tools(tools)

    # Build node functions
    load_session = make_load_session(session_store)
    guardrail_input = make_guardrail_input_node()
    triage_mcp = make_triage_mcp_node(llm=llm)
    triage_relevance = make_triage_relevance_node()
    triage_faq = make_triage_faq_node(faq_service=faq_service)
    triage_intent = make_triage_intent_node()
    call_llm = make_call_llm(llm_with_tools)
    execute_tools = make_execute_tools_node(tools, _captured_sources)
    validate_sources = make_validate_sources_node(llm)
    validate_tone = make_validate_tone_node(llm)
    guardrail_output = make_guardrail_output_node()
    mcp_tool_name = os.getenv("MCP_TOOL_NAME") or None
    call_mcp = make_call_mcp_node(mcp_tool_name=mcp_tool_name)
    format_mcp = make_format_mcp_node(llm)
    gather_mcp_params = make_gather_mcp_params_node()
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
    graph.add_node("validate_sources", validate_sources)
    graph.add_node("validate_tone", validate_tone)
    graph.add_node("guardrail_output", guardrail_output)
    graph.add_node("update_memory", update_memory)
    graph.add_node("save_session", save_session)
    graph.add_node("format_response", format_response)
    graph.add_node("call_mcp", call_mcp)
    graph.add_node("format_mcp", format_mcp)
    graph.add_node("gather_mcp_params", gather_mcp_params)

    # Edges
    graph.add_edge(START, "load_session")

    # ── Input guardrail + triage pipeline (before LLM) ──────────
    graph.add_edge("load_session", "guardrail_input")
    graph.add_edge("guardrail_input", "triage_mcp")
    graph.add_edge("triage_mcp", "triage_relevance")
    graph.add_edge("triage_relevance", "triage_faq")
    graph.add_edge("triage_faq", "triage_intent")
    # After triage: skip LLM, route to MCP, gather params, or proceed normally
    graph.add_conditional_edges("triage_intent", should_call_llm, {
        "build_prompt": "build_prompt",
        "bundle_triage_response": "bundle_triage_response",
        "call_mcp": "call_mcp",
        "gather_mcp_params": "gather_mcp_params",
    })

    # ── LLM pipeline (normal flow) ──────────────────────────────
    graph.add_edge("build_prompt", "call_llm")
    graph.add_conditional_edges("call_llm", should_continue, {
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
    graph.add_conditional_edges("guardrail_output", should_update_memory, {
        "update_memory": "update_memory",
        "format_response": "format_response",
    })

    # ── MCP: fetch data → format with LLM → memory/response ─
    graph.add_edge("call_mcp", "format_mcp")
    graph.add_conditional_edges("format_mcp", should_update_memory, {
        "update_memory": "update_memory",
        "format_response": "format_response",
    })

    # ── MCP gather params: ask for missing info → save session → response ─
    graph.add_edge("gather_mcp_params", "save_session")

    graph.add_edge("update_memory", "save_session")
    graph.add_edge("save_session", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
