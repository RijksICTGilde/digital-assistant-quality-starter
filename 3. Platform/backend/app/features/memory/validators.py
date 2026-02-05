"""Validation nodes for the LangGraph chat pipeline.

Each factory function creates a **separate graph node** that:
- Receives the full ChatState
- Returns a partial dict with only the fields it changed

These are EXAMPLE implementations. Replace the validation logic
with your own checks while keeping the same input/output contract.

Full pipeline order:

    load_session
        → guardrail_input            ← INPUT GUARDRAIL (block harmful input)
        → triage_relevance            ← TRIAGE 1 (domain relevance)
        → triage_faq                  ← TRIAGE 2 (FAQ lookup)
        → triage_intent               ← TRIAGE 3 (intent classification)
        → build_prompt → call_llm ⇄ execute_tools
        → bundle_sources
        → validate_sources            ← POST-LLM validation
        → validate_tone               ← POST-LLM validation
        → guardrail_output            ← OUTPUT GUARDRAIL (block harmful output)
        → update_memory → save_session → format_response

Triage nodes can short-circuit by setting  triage["skip_llm"] = True,
which skips the LLM and routes through bundle_triage_response instead.
Memory is always updated so conversation history stays complete.
"""

from __future__ import annotations

import json
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger


# ---------------------------------------------------------------------------
# Triage helpers
# ---------------------------------------------------------------------------

def _default_triage() -> dict:
    """Return the initial triage state dict."""
    return {
        "route": "llm",          # "llm" | "faq" | "irrelevant" | "chitchat"
        "skip_llm": False,       # True → bypass build_prompt + call_llm
        "early_response": None,  # str set when skip_llm=True
        "triage_log": [],        # human-readable log of each validator decision
    }


def _triage_already_decided(state: dict) -> bool:
    """Check whether a previous triage node already decided to skip."""
    triage = state.get("triage") or {}
    return triage.get("skip_llm", False)


# ---------------------------------------------------------------------------
# Input guardrail: is the user allowed to ask this?
# ---------------------------------------------------------------------------

def make_guardrail_input_node():
    """Factory: checks whether the user message is allowed to be processed.

    This runs BEFORE triage — it is the first line of defence.

    ── When to block ─────────────────────────────────────────────
        • Prompt-injection attempts
        • Toxic / hateful / violent content
        • PII the user shouldn't be submitting (BSN, credit card, etc.)
        • Messages that exceed length or complexity limits

    ── Example implementation ideas ──────────────────────────────
        • Regex / keyword blocklist (fast, zero cost)
        • Presidio / SpaCy NER for PII detection
        • OpenAI / Azure Content Safety moderation endpoint
        • Small classifier (e.g. Hugging Face toxic-bert)
        • LLM-as-judge with a strict system prompt

    ── State contract ────────────────────────────────────────────
        Reads:   message, triage
        Writes:  triage  (sets skip_llm + early_response when blocked)

    ── Current placeholder ───────────────────────────────────────
        Always passes through. Replace the body with your logic.
    """

    async def guardrail_input(state: dict) -> dict:
        triage = dict(state.get("triage") or _default_triage())
        message = state.get("message", "")

        # ── PLACEHOLDER: replace with your input guardrail logic ────
        #
        # Example 1: block messages containing Dutch social security numbers (BSN)
        #
        # import re
        # if re.search(r"\b\d{9}\b", message):
        #     triage["route"] = "blocked"
        #     triage["skip_llm"] = True
        #     triage["early_response"] = (
        #         "Het lijkt erop dat je een BSN-nummer hebt gedeeld. "
        #         "Deel alsjeblieft geen persoonlijke gegevens in de chat."
        #     )
        #     triage["triage_log"].append("guardrail_input: PII DETECTED → block")
        #     logger.warning("[GUARDRAIL-INPUT] PII detected, blocking message")
        #     return {"triage": triage}
        #
        # Example 2: block prompt injection attempts
        #
        # INJECTION_PATTERNS = ["ignore previous instructions", "you are now"]
        # if any(p in message.lower() for p in INJECTION_PATTERNS):
        #     triage["route"] = "blocked"
        #     triage["skip_llm"] = True
        #     triage["early_response"] = (
        #         "Ik kan dit verzoek niet verwerken."
        #     )
        #     triage["triage_log"].append("guardrail_input: INJECTION → block")
        #     logger.warning("[GUARDRAIL-INPUT] Possible prompt injection blocked")
        #     return {"triage": triage}

        triage["triage_log"].append("guardrail_input: PASS")
        logger.info("[GUARDRAIL-INPUT] Message allowed")
        return {"triage": triage}

    return guardrail_input


# ---------------------------------------------------------------------------
# Triage node 1: relevance check
# ---------------------------------------------------------------------------

def make_triage_relevance_node():
    """Factory: checks whether the user message is relevant to the domain.

    ── When to short-circuit ─────────────────────────────────────
        • Message is clearly off-topic (e.g. "what's the weather?")
        • Message is gibberish or empty
        • Message contains only greetings with no question

    ── Example implementation ideas ──────────────────────────────
        • Keyword / regex allowlist + blocklist
        • Small classifier (zero-shot or fine-tuned)
        • Embedding distance to a set of "on-topic" anchors
        • Simple LLM call with a constrained prompt

    ── Current placeholder ───────────────────────────────────────
        Always passes through. Replace the body with your logic.
    """

    async def triage_relevance(state: dict) -> dict:
        if _triage_already_decided(state):
            return {}

        triage = dict(state.get("triage") or _default_triage())
        message = state.get("message", "")

        # ── PLACEHOLDER: replace with your relevance check ──────────
        #
        # Example: reject clearly off-topic messages
        #
        # OFF_TOPIC_PATTERNS = ["what's the weather", "tell me a joke"]
        # if any(p in message.lower() for p in OFF_TOPIC_PATTERNS):
        #     triage["route"] = "irrelevant"
        #     triage["skip_llm"] = True
        #     triage["early_response"] = (
        #         "Sorry, ik kan alleen vragen beantwoorden over gemeentelijke "
        #         "onderwerpen. Kan ik je ergens anders mee helpen?"
        #     )
        #     triage["triage_log"].append("triage_relevance: OFF-TOPIC → skip")
        #     logger.info("[TRIAGE-RELEVANCE] Off-topic message, skipping LLM")
        #     return {"triage": triage}

        triage["triage_log"].append("triage_relevance: PASS")
        logger.info("[TRIAGE-RELEVANCE] Message accepted")
        return {"triage": triage}

    return triage_relevance


# ---------------------------------------------------------------------------
# Triage node 2: FAQ / known-answer lookup
# ---------------------------------------------------------------------------

def make_triage_faq_node(faq_service=None):
    """Factory: checks whether the question matches a known FAQ entry.

    Uses semantic matching with FAISS to find FAQ entries that match
    the user's question.

    ── Matching thresholds ───────────────────────────────────────
        • Score >= 0.85: Direct FAQ answer (skip LLM)
        • Score 0.70-0.85: FAQ as suggestion for LLM
        • Score < 0.70: No match, normal LLM processing

    ── State contract ────────────────────────────────────────────
        Reads:   message, triage
        Writes:  triage  (sets skip_llm + early_response when exact match)

    Args:
        faq_service: Optional FAQService instance. If None, node passes through.
    """

    async def triage_faq(state: dict) -> dict:
        if _triage_already_decided(state):
            return {}

        triage = dict(state.get("triage") or _default_triage())
        message = state.get("message", "")

        # If no FAQ service is configured, pass through
        if faq_service is None:
            triage["triage_log"].append("triage_faq: NO SERVICE")
            logger.debug("[TRIAGE-FAQ] No FAQ service configured, passing through")
            return {"triage": triage}

        # Get best FAQ match
        match, decision = faq_service.get_best_match(message)

        if decision == "exact":
            # High confidence match: return FAQ answer directly, skip LLM
            triage["route"] = "faq"
            triage["skip_llm"] = True

            # Build response with answer and related questions
            response_parts = [match.answer]

            # Add related questions as examples
            if match.related_questions:
                examples = "\n".join(f"- {q}" for q in match.related_questions[:4])
                response_parts.append(
                    f"\n\n---\n**Gerelateerde vragen die ik kan beantwoorden:**\n{examples}"
                )

            triage["early_response"] = "\n".join(response_parts)
            triage["faq_match"] = {
                "faq_id": match.faq_id,
                "category": match.category,
                "score": match.score,
            }
            # Include pre-defined sources for this FAQ
            triage["faq_sources"] = match.sources or []
            triage["triage_log"].append(
                f"triage_faq: EXACT MATCH ({match.faq_id}, score={match.score:.3f}) → skip"
            )
            logger.info(
                f"[TRIAGE-FAQ] Exact FAQ match: {match.faq_id} "
                f"(score={match.score:.3f}, sources={len(match.sources or [])}), skipping LLM"
            )
            return {"triage": triage}

        if decision == "suggest":
            # Medium confidence: pass suggestion to LLM for consideration
            triage["faq_suggestion"] = {
                "faq_id": match.faq_id,
                "category": match.category,
                "matched_question": match.matched_question,
                "suggested_answer": match.answer,
                "score": match.score,
            }
            triage["triage_log"].append(
                f"triage_faq: SUGGEST ({match.faq_id}, score={match.score:.3f})"
            )
            logger.info(
                f"[TRIAGE-FAQ] FAQ suggestion: {match.faq_id} "
                f"(score={match.score:.3f}), continuing to LLM"
            )
            return {"triage": triage}

        # No match or low confidence
        triage["triage_log"].append("triage_faq: NO MATCH")
        logger.info("[TRIAGE-FAQ] No FAQ match")
        return {"triage": triage}

    return triage_faq


# ---------------------------------------------------------------------------
# Triage node 3: intent classification
# ---------------------------------------------------------------------------

def make_triage_intent_node():
    """Factory: classifies the user's intent and makes a final routing decision.

    ── When to short-circuit ─────────────────────────────────────
        • Intent is "chitchat" — respond with a canned reply
        • Intent is "farewell" — say goodbye without LLM
        • Intent is "complaint" — route to a human agent

    ── Example implementation ideas ──────────────────────────────
        • Zero-shot classifier (e.g. Hugging Face pipeline)
        • Small LLM call: "classify this intent into one of [...]"
        • Rule-based keyword matching
        • Fine-tuned intent model

    ── Current placeholder ───────────────────────────────────────
        Always routes to the LLM. Replace the body with your logic.
    """

    async def triage_intent(state: dict) -> dict:
        if _triage_already_decided(state):
            return {}

        triage = dict(state.get("triage") or _default_triage())
        message = state.get("message", "")

        # ── PLACEHOLDER: replace with your intent classification ────
        #
        # Example: simple keyword-based intent detection
        #
        # GREETING_WORDS = {"hallo", "hey", "hoi", "goedemorgen", "goedemiddag"}
        # words = set(message.strip().lower().split())
        # if words.issubset(GREETING_WORDS | {"!", ",", "."}):
        #     triage["route"] = "chitchat"
        #     triage["skip_llm"] = True
        #     triage["early_response"] = (
        #         "Hallo! Ik ben Kletsmajoor, de AI-assistent. "
        #         "Stel gerust je vraag over gemeentelijke onderwerpen."
        #     )
        #     triage["triage_log"].append("triage_intent: CHITCHAT → skip")
        #     logger.info("[TRIAGE-INTENT] Chitchat detected, skipping LLM")
        #     return {"triage": triage}

        triage["route"] = "llm"
        triage["triage_log"].append("triage_intent: ROUTE → llm")
        logger.info("[TRIAGE-INTENT] Routing to LLM")
        return {"triage": triage}

    return triage_intent


# ---------------------------------------------------------------------------
# Bundle node for triage early-exit (skips LLM but prepares state for memory)
# ---------------------------------------------------------------------------

def _bundle_triage_response(state: dict) -> dict:
    """Set assistant_text and source fields from the triage early response.

    This node runs instead of the LLM pipeline when triage decides to skip.
    It sets the same fields that bundle_sources normally sets, so that
    update_memory and format_response work unchanged.
    """
    triage = state.get("triage") or {}
    early_response = triage.get("early_response", "")
    exchange_id = f"ex-{uuid.uuid4().hex[:8]}"

    # Include FAQ sources if available (for FAQ route)
    faq_sources = triage.get("faq_sources", [])
    unique_sources = [
        {
            "title": src.get("title", ""),
            "url": src.get("url", ""),
            "section_title": src.get("section_title", ""),
            "snippet": src.get("snippet", ""),
            "relevance_score": src.get("relevance_score", 0.9),
            "document_id": f"faq-src-{i}",
        }
        for i, src in enumerate(faq_sources)
    ]
    source_ids = [src["document_id"] for src in unique_sources]

    logger.info(
        f"[TRIAGE] Early response ({triage.get('route', '?')}): "
        f"{len(early_response)} chars, sources={len(unique_sources)}"
    )
    return {
        "assistant_text": early_response,
        "exchange_id": exchange_id,
        "unique_sources": unique_sources,
        "source_ids": source_ids,
    }


# ---------------------------------------------------------------------------
# Node 1: validate_sources
# ---------------------------------------------------------------------------

def make_validate_sources_node(llm: ChatOpenAI):
    """Factory: creates a node that validates the answer against sources.

    ── Input (reads from state) ──────────────────────────────────
        assistant_text : str            the LLM's answer
        unique_sources : list[dict]     deduplicated source documents
            Each dict has at least: title, snippet, document_id

    ── Output (writes to state) ──────────────────────────────────
        source_validation : dict
            {
                "grounded":   bool,         is the answer supported?
                "issues":     list[str],    specific problems found
                "confidence": float,        0.0–1.0
            }

    ── Example replacement ideas ─────────────────────────────────
        • NLI model (e.g. cross-encoder/nli) instead of LLM call
        • Embedding cosine-similarity threshold
        • Rule-based keyword overlap check
    """

    async def validate_sources(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")
        unique_sources = state.get("unique_sources", [])

        # Nothing to validate when there are no sources (direct answer)
        if not unique_sources:
            return {
                "source_validation": {
                    "grounded": True,
                    "issues": [],
                    "confidence": 1.0,
                },
            }

        # Build source context for the validator
        source_texts = []
        for i, src in enumerate(unique_sources):
            title = src.get("title", "Untitled")
            snippet = src.get("snippet", "")
            source_texts.append(f"[{i+1}] {title}: {snippet}")
        sources_block = "\n".join(source_texts)

        prompt = f"""Controleer of het antwoord van de assistent wordt ondersteund door de bronnen.

BRONNEN:
{sources_block}

ANTWOORD:
{assistant_text[:1500]}

Beoordeel:
1. Worden de feitelijke claims in het antwoord ondersteund door de bronnen?
2. Bevat het antwoord informatie die NIET in de bronnen staat (hallucination)?
3. Zijn er bronnen genegeerd die relevant waren?

Antwoord ALLEEN met valid JSON:
{{"grounded": true, "issues": [], "confidence": 0.95}}"""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content="Je valideert antwoorden tegen bronnen. Antwoord alleen met JSON."),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
                max_tokens=200,
            )
            raw = (response.content or "{}").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(raw)
            result = {
                "grounded": data.get("grounded", True),
                "issues": data.get("issues", []),
                "confidence": data.get("confidence", 0.5),
            }
        except Exception as e:
            logger.warning(f"[VALIDATE-SOURCES] Validation failed: {e}")
            result = {"grounded": True, "issues": [], "confidence": 0.0}

        logger.info(
            f"[VALIDATE-SOURCES] grounded={result['grounded']}, "
            f"issues={len(result['issues'])}, confidence={result['confidence']}"
        )
        return {"source_validation": result}

    return validate_sources


# ---------------------------------------------------------------------------
# Node 2: validate_tone
# ---------------------------------------------------------------------------

def make_validate_tone_node(llm: ChatOpenAI):
    """Factory: creates a node that checks tone and optionally rewrites.

    ── Input (reads from state) ──────────────────────────────────
        assistant_text : str            the LLM's answer

    ── Output (writes to state) ──────────────────────────────────
        assistant_text  : str           original OR rewritten answer
        tone_validation : dict
            {
                "appropriate":   bool,          was the tone OK as-is?
                "original_text": str | None,    original if rewritten, else None
                "adjustments":   list[str],     what was changed and why
            }

    ── Example replacement ideas ─────────────────────────────────
        • Sentiment classifier + rule engine
        • Brand-voice scoring model
        • Simple regex checks (no emoji, no exclamation marks, etc.)
    """

    async def validate_tone(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")

        if not assistant_text.strip():
            return {
                "tone_validation": {
                    "appropriate": True,
                    "original_text": None,
                    "adjustments": [],
                },
            }

        prompt = f"""Beoordeel de toon van dit antwoord van een overheids-AI-assistent.

RICHTLIJNEN:
- Formeel maar toegankelijk (geen ambtelijk jargon)
- Behulpzaam zonder betuttelend te zijn
- Geen afsluitende vragen ("Wil je meer weten?", "Kan ik je ergens mee helpen?")
- Geen overdreven enthousiasme of emoji's
- Concreet en zakelijk

ANTWOORD:
{assistant_text[:2000]}

Als de toon correct is, antwoord met:
{{"appropriate": true, "adjustments": []}}

Als de toon aangepast moet worden, antwoord met:
{{"appropriate": false, "adjustments": ["reden1"], "rewritten": "het volledig herschreven antwoord"}}

Antwoord ALLEEN met valid JSON."""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content="Je controleert de toon van overheidsantwoorden. "
                        "Antwoord alleen met JSON."
                    ),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
                max_tokens=2500,
            )
            raw = (response.content or "{}").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(raw)
            appropriate = data.get("appropriate", True)
            adjustments = data.get("adjustments", [])

            if not appropriate and data.get("rewritten", "").strip():
                logger.info(f"[VALIDATE-TONE] Rewriting ({len(adjustments)} adjustments)")
                return {
                    "assistant_text": data["rewritten"],
                    "tone_validation": {
                        "appropriate": False,
                        "original_text": assistant_text,
                        "adjustments": adjustments,
                    },
                }

            result = {
                "appropriate": appropriate,
                "original_text": None,
                "adjustments": adjustments,
            }
        except Exception as e:
            logger.warning(f"[VALIDATE-TONE] Validation failed: {e}")
            result = {"appropriate": True, "original_text": None, "adjustments": []}

        logger.info(f"[VALIDATE-TONE] appropriate={result['appropriate']}")
        return {"tone_validation": result}

    return validate_tone


# ---------------------------------------------------------------------------
# Output guardrail: is the response safe to send?
# ---------------------------------------------------------------------------

def make_guardrail_output_node():
    """Factory: checks whether the assistant response is safe to deliver.

    This runs AFTER validate_tone (or after bundle_triage_response on
    the early-exit path) — it is the last gate before memory + response.

    ── When to block or rewrite ──────────────────────────────────
        • Response leaks internal system prompt or instructions
        • Response contains PII (phone numbers, emails, BSN)
        • Response contains hallucinated URLs or legal references
        • Response is too long or contains forbidden content
        • Response contradicts known policy or regulations

    ── Example implementation ideas ──────────────────────────────
        • Regex scan for PII patterns (phone, email, BSN)
        • URL validation against a known-good allowlist
        • LLM-as-judge checking for policy compliance
        • Embedding similarity to detect prompt leakage
        • Length / formatting rules

    ── State contract ────────────────────────────────────────────
        Reads:   assistant_text
        Writes:  assistant_text  (replaced with safe fallback if blocked)
                 output_guardrail : dict  {safe, issues, original_text}

    ── Current placeholder ───────────────────────────────────────
        Always passes through. Replace the body with your logic.
    """

    async def guardrail_output(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")

        # ── PLACEHOLDER: replace with your output guardrail logic ───
        #
        # Example 1: detect leaked system prompt fragments
        #
        # LEAK_MARKERS = ["KERNREGEL", "TOOL-KEUZE", "GEHEUGEN:", "[§USR]", "[§BOT]"]
        # if any(marker in assistant_text for marker in LEAK_MARKERS):
        #     logger.warning("[GUARDRAIL-OUTPUT] System prompt leakage detected")
        #     return {
        #         "assistant_text": (
        #             "Er is een fout opgetreden bij het genereren van het antwoord. "
        #             "Probeer het opnieuw."
        #         ),
        #         "output_guardrail": {
        #             "safe": False,
        #             "issues": ["system_prompt_leakage"],
        #             "original_text": assistant_text,
        #         },
        #     }
        #
        # Example 2: strip any PII from the response
        #
        # import re
        # cleaned = re.sub(r"\b\d{9}\b", "[BSN VERWIJDERD]", assistant_text)
        # if cleaned != assistant_text:
        #     logger.warning("[GUARDRAIL-OUTPUT] PII removed from response")
        #     return {
        #         "assistant_text": cleaned,
        #         "output_guardrail": {
        #             "safe": True,
        #             "issues": ["pii_removed"],
        #             "original_text": assistant_text,
        #         },
        #     }

        logger.info("[GUARDRAIL-OUTPUT] Response approved")
        return {
            "output_guardrail": {
                "safe": True,
                "issues": [],
                "original_text": None,
            },
        }

    return guardrail_output
