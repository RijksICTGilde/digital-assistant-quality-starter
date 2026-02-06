"""LLM invocation step node and conditional edges."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.steps.state import ChatState, MAX_TOOL_ROUNDS


def make_call_llm(llm: ChatOpenAI):
    """Returns the call_llm node (LLM with bound tools)."""

    async def call_llm(state: ChatState) -> dict:
        messages = state["messages"]
        tool_rounds = state.get("tool_rounds", 0)
        logger.info(f"[NODE:call_llm] ▶ round {tool_rounds + 1}/{MAX_TOOL_ROUNDS}, {len(messages)} messages in context")
        response = await llm.ainvoke(messages)
        content_len = len(response.content) if isinstance(response.content, str) else 0
        tool_names = [tc["name"] for tc in (response.tool_calls or [])]
        logger.info(
            f"[NODE:call_llm] ✓ response: {content_len} chars text, "
            f"tool_calls={tool_names if tool_names else 'none'}"
        )
        return {"messages": [response], "tool_rounds": tool_rounds + 1}

    return call_llm


def should_continue(state: ChatState) -> str:
    """Conditional edge: check if the last AI message has tool_calls."""
    messages = state["messages"]
    last_msg = messages[-1]
    tool_rounds = state.get("tool_rounds", 0)

    if isinstance(last_msg, AIMessage) and last_msg.tool_calls and tool_rounds < MAX_TOOL_ROUNDS:
        logger.info(f"[EDGE] call_llm → execute_tools (round {tool_rounds}/{MAX_TOOL_ROUNDS})")
        return "execute_tools"
    reason = "no tool_calls" if not (isinstance(last_msg, AIMessage) and last_msg.tool_calls) else f"max rounds ({MAX_TOOL_ROUNDS})"
    logger.info(f"[EDGE] call_llm → bundle_sources ({reason})")
    return "bundle_sources"


def should_call_llm(state: ChatState) -> str:
    """Conditional edge after triage: skip LLM when triage says so."""
    triage = state.get("triage") or {}
    if triage.get("skip_llm", False):
        route = triage.get("route", "")
        if route == "mcp":
            logger.info("[EDGE] triage → call_mcp")
            return "call_mcp"
        if route == "mcp_gather_params":
            logger.info("[EDGE] triage → gather_mcp_params (missing parameters)")
            return "gather_mcp_params"
        logger.info(f"[EDGE] triage → bundle_triage_response (route={route or '?'})")
        return "bundle_triage_response"
    logger.info("[EDGE] triage → build_prompt (routing to LLM)")
    return "build_prompt"
