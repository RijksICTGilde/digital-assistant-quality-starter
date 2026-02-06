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

# Parameter requirements per law type
MCP_LAW_PARAMS = {
    "zorgtoeslag": {
        "name": "zorgtoeslag",
        "required": ["inkomen"],
        "optional": ["leeftijd", "toeslagpartner"],
        "question": "Om te berekenen of je recht hebt op zorgtoeslag, heb ik de volgende gegevens nodig:\n\n"
                   "**Verplicht:**\n"
                   "- Wat is je jaarinkomen (bruto)?\n\n"
                   "**Optioneel:**\n"
                   "- Heb je een toeslagpartner? (ja/nee)\n"
                   "- Wat is je leeftijd?\n\n"
                   "Geef deze gegevens en ik bereken het voor je!",
    },
    "huurtoeslag": {
        "name": "huurtoeslag",
        "required": ["inkomen", "huur"],
        "optional": ["leeftijd", "huisgenoten"],
        "question": "Om te berekenen of je recht hebt op huurtoeslag, heb ik de volgende gegevens nodig:\n\n"
                   "**Verplicht:**\n"
                   "- Wat is je jaarinkomen (bruto)?\n"
                   "- Wat is je maandelijkse kale huur?\n\n"
                   "**Optioneel:**\n"
                   "- Wat is je leeftijd?\n"
                   "- Hoeveel huisgenoten heb je?\n\n"
                   "Geef deze gegevens en ik bereken het voor je!",
    },
    "aow": {
        "name": "AOW",
        "required": ["leeftijd"],
        "optional": ["woonsituatie"],
        "question": "Om te berekenen of je recht hebt op AOW, heb ik de volgende gegevens nodig:\n\n"
                   "**Verplicht:**\n"
                   "- Wat is je leeftijd?\n\n"
                   "**Optioneel:**\n"
                   "- Wat is je woonsituatie? (alleenstaand/samenwonend)\n\n"
                   "Geef deze gegevens en ik bereken het voor je!",
    },
    "bijstand": {
        "name": "bijstand",
        "required": ["inkomen", "vermogen"],
        "optional": ["woonsituatie", "leeftijd"],
        "question": "Om te berekenen of je recht hebt op bijstand, heb ik de volgende gegevens nodig:\n\n"
                   "**Verplicht:**\n"
                   "- Wat is je huidige inkomen?\n"
                   "- Wat is je vermogen (spaargeld, bezittingen)?\n\n"
                   "**Optioneel:**\n"
                   "- Wat is je woonsituatie? (alleenstaand/samenwonend/gezin)\n"
                   "- Wat is je leeftijd?\n\n"
                   "Geef deze gegevens en ik bereken het voor je!",
    },
}

# LLM triage prompt - decides if a question can be answered by MCP
MCP_TRIAGE_SYSTEM_PROMPT = """Je bent een classifier die bepaalt of een vraag beantwoord kan worden door de RegelRecht MCP service.

RegelRecht is een systeem met machine-uitvoerbare Nederlandse wetgeving. Het kan:
- Checken of iemand recht heeft op een regeling (zorgtoeslag, huurtoeslag, AOW, bijstand)
- Bedragen berekenen voor toeslagen
- Uitleggen welke wetten beschikbaar zijn

Vragen die WEL door MCP beantwoord kunnen worden:
- "Heb ik recht op zorgtoeslag?"
- "Kom ik in aanmerking voor huurtoeslag?"
- "Hoeveel AOW krijg ik?"
- "Wat zijn de voorwaarden voor bijstand?"
- "Welke toeslagen zijn er?"
- "Kan ik huurtoeslag krijgen met een inkomen van €25.000?"

Vragen die NIET door MCP beantwoord kunnen worden:
- Algemene vragen over de gemeente
- Vragen over afval, paspoorten, vergunningen
- Vragen over openingstijden
- Persoonlijke gesprekken of begroetingen
- Technische vragen

Antwoord ALLEEN met "JA" of "NEE" (hoofdletters, geen uitleg)."""


def _detect_law_type(query: str) -> str | None:
    """Detect which law type the query is about."""
    query_lower = query.lower()
    if "zorgtoeslag" in query_lower:
        return "zorgtoeslag"
    if "huurtoeslag" in query_lower:
        return "huurtoeslag"
    if "aow" in query_lower or "ouderdom" in query_lower:
        return "aow"
    if "bijstand" in query_lower:
        return "bijstand"
    return None


def _extract_params_from_query(query: str) -> dict:
    """Extract parameters from the query text."""
    params = {}
    query_lower = query.lower()

    # Extract income (various formats)
    income_patterns = [
        r'inkomen[^\d]*(\d+[\.,]?\d*)',
        r'verdien[^\d]*(\d+[\.,]?\d*)',
        r'(\d+[\.,]?\d*)\s*(?:euro|€)',
        r'€\s*(\d+[\.,]?\d*)',
    ]
    for pattern in income_patterns:
        match = re.search(pattern, query_lower)
        if match:
            params["inkomen"] = match.group(1).replace(',', '.')
            break

    # Extract rent
    rent_patterns = [
        r'huur[^\d]*(\d+[\.,]?\d*)',
        r'(\d+[\.,]?\d*)\s*(?:huur|per maand)',
    ]
    for pattern in rent_patterns:
        match = re.search(pattern, query_lower)
        if match:
            params["huur"] = match.group(1).replace(',', '.')
            break

    # Extract age
    age_patterns = [
        r'(\d+)\s*jaar',
        r'leeftijd[^\d]*(\d+)',
        r'ben\s*(\d+)',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, query_lower)
        if match:
            params["leeftijd"] = match.group(1)
            break

    # Detect partner status
    if any(word in query_lower for word in ["partner", "getrouwd", "samenwonend"]):
        params["toeslagpartner"] = "ja"
    elif any(word in query_lower for word in ["alleenstaand", "alleen", "single"]):
        params["toeslagpartner"] = "nee"

    # Extract vermogen/savings
    vermogen_patterns = [
        r'vermogen[^\d]*(\d+[\.,]?\d*)',
        r'spaargeld[^\d]*(\d+[\.,]?\d*)',
        r'spaar[^\d]*(\d+[\.,]?\d*)',
    ]
    for pattern in vermogen_patterns:
        match = re.search(pattern, query_lower)
        if match:
            params["vermogen"] = match.group(1).replace(',', '.')
            break

    return params


def _has_required_params(law_type: str, params: dict) -> bool:
    """Check if all required parameters for a law type are present."""
    if law_type not in MCP_LAW_PARAMS:
        return True  # Unknown law type, proceed anyway

    required = MCP_LAW_PARAMS[law_type]["required"]
    return all(param in params for param in required)


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


def make_triage_mcp_node(llm: ChatOpenAI | None = None):
    """Factory: returns a triage node that detects MCP-answerable questions.

    Detection happens in two ways:
    1. Explicit: User prefixes message with ``mcp:``
    2. Automatic: LLM classifies question as MCP-answerable (if llm is provided)

    If a question is MCP-related but lacks required parameters, it will
    ask the user for the missing information instead of calling MCP directly.

    Parameters
    ----------
    llm:
        Optional LLM for automatic classification. If None, only explicit
        ``mcp:`` prefix detection is used.
    """

    async def triage_mcp(state: ChatState) -> dict:
        message = state.get("message", "")
        triage = dict(state.get("triage") or {})
        session = state.get("session") or {}

        stripped = message.strip()

        # Check if we're continuing an MCP parameter gathering session
        pending_mcp = session.get("pending_mcp_intent")
        if pending_mcp:
            # User is providing parameters for a previous MCP question
            law_type = pending_mcp.get("law_type")
            previous_params = pending_mcp.get("params", {})

            # Extract new params from current message and merge
            new_params = _extract_params_from_query(stripped)
            merged_params = {**previous_params, **new_params}

            if _has_required_params(law_type, merged_params):
                # We have all params now, proceed to MCP
                triage["route"] = "mcp"
                triage["skip_llm"] = True
                triage["mcp_query"] = f"{law_type} met {merged_params}"
                triage["mcp_params"] = merged_params
                triage["mcp_law_type"] = law_type
                triage["clear_pending_mcp"] = True
                logger.info(f"[NODE:triage_mcp] ▶ continuing MCP with params: {merged_params}")
                return {"triage": triage}
            else:
                # Still missing params, keep asking
                triage["route"] = "mcp_gather_params"
                triage["skip_llm"] = True
                triage["mcp_law_type"] = law_type
                triage["mcp_params"] = merged_params
                logger.info(f"[NODE:triage_mcp] ▶ still missing params for {law_type}")
                return {"triage": triage}

        # 1. Explicit detection: mcp: prefix (always takes priority)
        if stripped.lower().startswith(MCP_PREFIX):
            query = stripped[len(MCP_PREFIX):].strip()
            law_type = _detect_law_type(query)
            params = _extract_params_from_query(query)

            # Check if we have the required params
            if law_type and not _has_required_params(law_type, params):
                triage["route"] = "mcp_gather_params"
                triage["skip_llm"] = True
                triage["mcp_law_type"] = law_type
                triage["mcp_params"] = params
                logger.info(f"[NODE:triage_mcp] ▶ mcp: prefix but missing params for {law_type}")
                return {"triage": triage}

            triage["route"] = "mcp"
            triage["skip_llm"] = True
            triage["mcp_query"] = query
            if law_type:
                triage["mcp_law_type"] = law_type
                triage["mcp_params"] = params
            logger.info(f"[NODE:triage_mcp] ▶ detected mcp: prefix, query={query!r}")
            return {"triage": triage}

        # 2. Automatic detection: use LLM to classify
        if llm is not None:
            try:
                messages = [
                    SystemMessage(content=MCP_TRIAGE_SYSTEM_PROMPT),
                    HumanMessage(content=f"Vraag: {stripped}")
                ]
                response = await llm.ainvoke(messages)
                answer = response.content.strip().upper()

                if answer == "JA":
                    law_type = _detect_law_type(stripped)
                    params = _extract_params_from_query(stripped)

                    # For eligibility questions, check if we have required params
                    if law_type and not _has_required_params(law_type, params):
                        triage["route"] = "mcp_gather_params"
                        triage["skip_llm"] = True
                        triage["mcp_law_type"] = law_type
                        triage["mcp_params"] = params
                        logger.info(f"[NODE:triage_mcp] ▶ MCP question but missing params for {law_type}")
                        return {"triage": triage}

                    triage["route"] = "mcp"
                    triage["skip_llm"] = True
                    triage["mcp_query"] = stripped
                    if law_type:
                        triage["mcp_law_type"] = law_type
                        triage["mcp_params"] = params
                    logger.info(f"[NODE:triage_mcp] ▶ LLM classified as MCP question: {stripped!r}")
                    return {"triage": triage}
                else:
                    logger.debug(f"[NODE:triage_mcp] LLM says not MCP: {answer}")
            except Exception as e:
                logger.warning(f"[NODE:triage_mcp] LLM classification failed: {e}")
                # Fall through to pass-through on error

        logger.debug("[NODE:triage_mcp] no MCP detection — pass-through")
        return {}

    return triage_mcp


MCP_NOT_CONFIGURED_MSG = (
    "De MCP-service is momenteel niet geconfigureerd. "
    "Probeer het later opnieuw of stel je vraag zonder het mcp: prefix."
)


def make_gather_mcp_params_node():
    """Factory: returns a node that asks for missing MCP parameters.

    This node is called when an MCP question is detected but required
    parameters are missing. It returns a friendly message asking for
    the missing information and stores the intent in the session.
    """

    async def gather_mcp_params(state: ChatState) -> dict:
        triage = state.get("triage") or {}
        law_type = triage.get("mcp_law_type")
        current_params = triage.get("mcp_params", {})
        exchange_id = str(uuid.uuid4())

        if not law_type or law_type not in MCP_LAW_PARAMS:
            # Unknown law type, shouldn't happen
            return {
                "assistant_text": "Ik kan je helpen met toeslagen berekenen. Welke toeslag wil je checken? "
                                 "(zorgtoeslag, huurtoeslag, AOW, of bijstand)",
                "exchange_id": exchange_id,
                "unique_sources": [],
                "source_ids": [],
            }

        law_config = MCP_LAW_PARAMS[law_type]
        question = law_config["question"]

        # Store the pending intent in session for follow-up
        session_update = {
            "pending_mcp_intent": {
                "law_type": law_type,
                "params": current_params,
            }
        }

        logger.info(f"[NODE:gather_mcp_params] ▶ asking for params for {law_type}, have: {current_params}")

        return {
            "assistant_text": question,
            "exchange_id": exchange_id,
            "unique_sources": [],
            "source_ids": [],
            "session_update": session_update,
        }

    return gather_mcp_params


def _build_mcp_call_from_params(law_type: str, params: dict) -> dict:
    """Build MCP call parameters from extracted params.

    This is used when parameters have been gathered through the dialogue flow.
    """
    # Map law types to MCP service/law identifiers
    law_mapping = {
        "zorgtoeslag": ("TOESLAGEN", "zorgtoeslagwet"),
        "huurtoeslag": ("TOESLAGEN", "wet_op_de_huurtoeslag"),
        "aow": ("SVB", "algemene_ouderdomswet"),
        "bijstand": ("GEMEENTE_AMSTERDAM", "participatiewet/bijstand"),
    }

    if law_type not in law_mapping:
        # Fallback to list laws
        return {
            "method": "resources/read",
            "params": {"uri": "laws://list"}
        }

    service, law = law_mapping[law_type]

    # Build parameters for the law execution
    # Map our extracted params to what the MCP expects
    mcp_params = {}

    # Convert income to cents if it looks like euros
    if "inkomen" in params:
        try:
            inkomen = float(params["inkomen"])
            # If it's a reasonable yearly income in euros, convert to cents
            if inkomen < 1000000:
                mcp_params["INKOMEN"] = int(inkomen * 100)
            else:
                mcp_params["INKOMEN"] = int(inkomen)
        except (ValueError, TypeError):
            pass

    # Convert rent
    if "huur" in params:
        try:
            huur = float(params["huur"])
            if huur < 10000:  # Looks like euros per month
                mcp_params["HUUR"] = int(huur * 100)
            else:
                mcp_params["HUUR"] = int(huur)
        except (ValueError, TypeError):
            pass

    # Add age
    if "leeftijd" in params:
        try:
            mcp_params["LEEFTIJD"] = int(params["leeftijd"])
        except (ValueError, TypeError):
            pass

    # Add partner status
    if "toeslagpartner" in params:
        mcp_params["TOESLAGPARTNER"] = params["toeslagpartner"].lower() in ("ja", "yes", "true", "1")

    # Add vermogen (savings)
    if "vermogen" in params:
        try:
            vermogen = float(params["vermogen"])
            if vermogen < 10000000:  # Looks like euros
                mcp_params["VERMOGEN"] = int(vermogen * 100)
            else:
                mcp_params["VERMOGEN"] = int(vermogen)
        except (ValueError, TypeError):
            pass

    # Use a test BSN if none provided
    mcp_params["BSN"] = params.get("bsn", "100000001")

    logger.info(f"[MCP] Built params for {law_type}: {mcp_params}")

    return {
        "method": "tools/call",
        "params": {
            "name": "check_eligibility",
            "arguments": {
                "service": service,
                "law": law,
                "parameters": mcp_params
            }
        }
    }


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
        law_type = triage.get("mcp_law_type")
        extracted_params = triage.get("mcp_params", {})
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

        logger.info(f"[NODE:call_mcp] ▶ calling {rpc_url}, query={query!r}, law_type={law_type}, params={extracted_params}")

        try:
            # Use extracted params if available, otherwise parse from query
            if law_type and extracted_params:
                call_params = _build_mcp_call_from_params(law_type, extracted_params)
            else:
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
