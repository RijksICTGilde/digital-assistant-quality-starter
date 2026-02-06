"""MCP step nodes for the memory chat pipeline."""

from __future__ import annotations

import json
import os
import re
import uuid

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.steps.state import ChatState

MCP_PREFIX = "mcp:"

# LLM formatting prompt
MCP_FORMAT_SYSTEM_PROMPT = """Je bent een vriendelijke Nederlandse overheidsassistent die resultaten van wetgevingsberekeningen uitlegt.

Je taak is om de ruwe data van RegelRecht (machine-uitvoerbare wetgeving) om te zetten naar een duidelijk, begrijpelijk antwoord in het Nederlands.

Richtlijnen:
- Schrijf in duidelijk, eenvoudig Nederlands (B1 taalniveau)
- Gebruik bullet points voor lijsten
- Bij eligibility checks: leg duidelijk uit of iemand recht heeft en waarom
- Bij bedragen: toon bedragen in euro's (deel door 100 als nodig, bijv. 183424 = €1.834,24)
- Bij wettenlijsten: groepeer logisch en geef korte beschrijvingen
- Wees vriendelijk en behulpzaam
- Eindig met een suggestie voor een vervolgvraag indien relevant

Antwoord ALLEEN met de geformatteerde uitleg, geen inleiding zoals "Hier is het antwoord"."""


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


def _parse_query(query: str) -> dict:
    """Parse natural language query into MCP tool call parameters.

    Returns a dict with 'method' and 'params' for the JSON-RPC call.
    """
    query_lower = query.lower()

    # Check for "welke wetten" / "beschikbare wetten" -> list laws
    if any(kw in query_lower for kw in ["welke wetten", "beschikbare wetten", "available laws", "lijst"]):
        return {
            "method": "resources/read",
            "params": {"uri": "laws://list"}
        }

    # Check for BSN in query for law execution
    bsn_match = re.search(r'\b(\d{9})\b', query)

    # Check for specific law mentions
    if "zorgtoeslag" in query_lower:
        bsn = bsn_match.group(1) if bsn_match else "100000001"
        return {
            "method": "tools/call",
            "params": {
                "name": "check_eligibility",
                "arguments": {
                    "service": "TOESLAGEN",
                    "law": "zorgtoeslagwet",
                    "parameters": {"BSN": bsn}
                }
            }
        }

    if "huurtoeslag" in query_lower:
        bsn = bsn_match.group(1) if bsn_match else "100000001"
        return {
            "method": "tools/call",
            "params": {
                "name": "check_eligibility",
                "arguments": {
                    "service": "TOESLAGEN",
                    "law": "wet_op_de_huurtoeslag",
                    "parameters": {"BSN": bsn}
                }
            }
        }

    if "aow" in query_lower or "ouderdom" in query_lower:
        bsn = bsn_match.group(1) if bsn_match else "100000001"
        return {
            "method": "tools/call",
            "params": {
                "name": "check_eligibility",
                "arguments": {
                    "service": "SVB",
                    "law": "algemene_ouderdomswet",
                    "parameters": {"BSN": bsn}
                }
            }
        }

    if "bijstand" in query_lower:
        bsn = bsn_match.group(1) if bsn_match else "100000001"
        return {
            "method": "tools/call",
            "params": {
                "name": "check_eligibility",
                "arguments": {
                    "service": "GEMEENTE_AMSTERDAM",
                    "law": "participatiewet/bijstand",
                    "parameters": {"BSN": bsn}
                }
            }
        }

    # Default: list available laws
    return {
        "method": "resources/read",
        "params": {"uri": "laws://list"}
    }


def _format_response(result: dict, query: str) -> str:
    """Format the MCP response into readable text."""
    if "error" in result:
        return f"❌ Fout: {result['error'].get('message', 'Onbekende fout')}"

    if "result" not in result:
        return f"❌ Onverwacht antwoord van de server: {result}"

    res = result["result"]

    # Handle both 'content' (tools) and 'contents' (resources) response formats
    content = res.get("content") or res.get("contents") or []

    # If result is directly a list or dict, use it
    if not content and isinstance(res, (list, dict)):
        content = [res] if isinstance(res, dict) else res

    if not content:
        logger.warning(f"[MCP] Empty content in response: {result}")
        return f"Geen resultaat gevonden. (Debug: {result})"

    # Extract text from content blocks
    texts = []
    for block in content:
        if isinstance(block, dict):
            # Check various text fields
            if "text" in block:
                texts.append(block["text"])
            elif "uri" in block and "text" in block.get("content", {}):
                texts.append(block["content"]["text"])
            elif "blob" in block:
                texts.append(block["blob"])
            else:
                # Fallback: serialize the block
                texts.append(json.dumps(block, ensure_ascii=False))
        elif isinstance(block, str):
            texts.append(block)

    raw_text = "\n".join(texts)

    if not raw_text.strip():
        return f"Leeg resultaat. (Debug: {result})"

    # Try to parse as JSON for better formatting
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            # List of laws
            lines = ["## 📚 Beschikbare wetten in RegelRecht\n"]
            for item in data:
                if isinstance(item, dict):
                    name = item.get("name", item.get("law", "Onbekend"))
                    service = item.get("service", "")
                    desc = item.get("description", "")
                    lines.append(f"- **{name}** ({service})")
                    if desc:
                        lines.append(f"  {desc}")
            return "\n".join(lines)
        elif isinstance(data, dict):
            # Single result - format nicely
            if "eligible" in str(data).lower() or "recht" in str(data).lower():
                eligible = data.get("eligible", data.get("is_eligible", "onbekend"))
                return f"### Resultaat\n\n**Recht op regeling:** {'✅ Ja' if eligible else '❌ Nee'}\n\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"
            return f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"
    except (json.JSONDecodeError, TypeError):
        pass

    return raw_text


def make_format_mcp_node(llm: ChatOpenAI):
    """Factory: returns a node that formats MCP responses using the LLM.

    This node takes the raw MCP response from `assistant_text` and formats it
    into a user-friendly Dutch response using the same LLM used elsewhere.
    """

    async def format_mcp(state: ChatState) -> dict:
        triage = state.get("triage") or {}
        query = triage.get("mcp_query", "")
        raw_response = state.get("assistant_text", "")

        # Skip if no MCP response or not an MCP route
        if triage.get("route") != "mcp" or not raw_response:
            return {}

        logger.info(f"[NODE:format_mcp] ▶ formatting {len(raw_response)} chars with LLM")

        try:
            messages = [
                SystemMessage(content=MCP_FORMAT_SYSTEM_PROMPT),
                HumanMessage(content=f"""Gebruikersvraag: {query}

Ruwe data van RegelRecht (machine-uitvoerbare wetgeving):
{raw_response}

Formuleer een duidelijk, vriendelijk antwoord in het Nederlands voor de burger.""")
            ]
            response = await llm.ainvoke(messages)
            formatted_text = response.content
            logger.info(f"[NODE:format_mcp] ✓ formatted: {len(formatted_text)} chars")
            return {"assistant_text": formatted_text}

        except Exception as e:
            logger.warning(f"[NODE:format_mcp] LLM formatting failed: {e}")
            # Keep original response on error
            return {}

    return format_mcp


def make_call_mcp_node(mcp_tool_name: str | None = None):
    """Factory: returns a node that calls the MCP server via JSON-RPC.

    The MCP server URL is read from ``MCP_SERVER_URL`` at call time.
    If it is not set, a friendly fallback message is returned.

    Parameters
    ----------
    llm:
        Optional LLM to format the response into readable Dutch text.
    mcp_tool_name:
        Tool to call on the MCP server. If *None*, the query is parsed
        to determine the appropriate tool.
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

        # Build RPC endpoint URL
        rpc_url = mcp_url.rstrip("/")
        if not rpc_url.endswith("/rpc"):
            rpc_url = rpc_url + "/rpc" if not rpc_url.endswith("/mcp") else rpc_url.replace("/mcp", "/mcp/rpc")

        logger.info(f"[NODE:call_mcp] ▶ calling {rpc_url}, query={query!r}")

        try:
            # Parse the query into MCP call parameters
            call_params = _parse_query(query)

            # Build JSON-RPC request
            rpc_request = {
                "jsonrpc": "2.0",
                "method": call_params["method"],
                "params": call_params["params"],
                "id": 1
            }

            logger.info(f"[NODE:call_mcp] JSON-RPC request: {rpc_request}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    rpc_url,
                    json=rpc_request,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()

            logger.info(f"[NODE:call_mcp] ✓ response received: {json.dumps(result, ensure_ascii=False)[:500]}")
            assistant_text = _format_response(result, query)

        except httpx.HTTPStatusError as e:
            logger.exception("[NODE:call_mcp] HTTP error")
            assistant_text = f"Sorry, de MCP-service gaf een fout: {e.response.status_code}"
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
