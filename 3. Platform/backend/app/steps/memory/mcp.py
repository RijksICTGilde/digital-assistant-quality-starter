"""MCP step nodes for the memory chat pipeline."""

from __future__ import annotations

import os
import uuid

from loguru import logger

from app.steps.state import ChatState

MCP_PREFIX = "mcp:"


def make_triage_mcp_node():
    """Factory: returns a triage node that detects ``mcp:`` prefix."""

    async def triage_mcp(state: ChatState) -> dict:
        message = state.get("message", "")
        triage = dict(state.get("triage") or {})

        stripped = message.strip()
        if stripped.lower().startswith(MCP_PREFIX):
            query = stripped[len(MCP_PREFIX):].strip()
            triage["route"] = "mcp"
            triage["skip_llm"] = True
            triage["mcp_query"] = query
            logger.info(f"[NODE:triage_mcp] ▶ detected mcp: prefix, query={query!r}")
            return {"triage": triage}

        logger.debug("[NODE:triage_mcp] no mcp: prefix — pass-through")
        return {}

    return triage_mcp


MCP_NOT_CONFIGURED_MSG = (
    "De MCP-service is momenteel niet geconfigureerd. "
    "Probeer het later opnieuw of stel je vraag zonder het mcp: prefix."
)


def make_call_mcp_node(mcp_tool_name: str | None = None):
    """Factory: returns a node that calls the MCP server via SSE.

    The MCP server URL is read from ``MCP_SERVER_URL`` at call time.
    If it is not set, a friendly fallback message is returned.

    Parameters
    ----------
    mcp_tool_name:
        Tool to call on the MCP server.  If *None*, the first available
        tool is used.
    """

    async def call_mcp(state: ChatState) -> dict:
        triage = state.get("triage") or {}
        query = triage.get("mcp_query", "")
        exchange_id = str(uuid.uuid4())

        mcp_url = os.getenv("MCP_SERVER_URL")
        if not mcp_url:
            logger.warning("[NODE:call_mcp] MCP_SERVER_URL not set — returning fallback")
            return {
                "assistant_text": MCP_NOT_CONFIGURED_MSG,
                "exchange_id": exchange_id,
                "unique_sources": [],
                "source_ids": [],
            }

        from mcp import ClientSession
        from mcp.client.sse import sse_client

        logger.info(f"[NODE:call_mcp] ▶ connecting to {mcp_url}, query={query!r}")

        try:
            async with sse_client(mcp_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # Resolve tool name
                    tool_name = mcp_tool_name
                    if not tool_name:
                        tools_result = await session.list_tools()
                        if not tools_result.tools:
                            raise RuntimeError("MCP server has no available tools")
                        tool_name = tools_result.tools[0].name
                        logger.info(f"[NODE:call_mcp] using first available tool: {tool_name}")

                    result = await session.call_tool(tool_name, {"query": query})

                    # Extract text from result content
                    text_parts = []
                    for block in result.content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
                    assistant_text = "\n".join(text_parts) if text_parts else str(result.content)

                    logger.info(f"[NODE:call_mcp] ✓ response: {len(assistant_text)} chars")

        except Exception:
            logger.exception("[NODE:call_mcp] MCP call failed")
            assistant_text = "Sorry, de MCP-service is momenteel niet bereikbaar."

        return {
            "assistant_text": assistant_text,
            "exchange_id": exchange_id,
            "unique_sources": [],
            "source_ids": [],
        }

    return call_mcp
