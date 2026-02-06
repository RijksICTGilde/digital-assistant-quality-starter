"""Input guardrail node: checks whether the user message is allowed."""

from __future__ import annotations

from loguru import logger

from app.steps.memory._triage import _default_triage

# ── Toggle: set to False to skip this step ──
ENABLED = True


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
        if not ENABLED:
            logger.debug("[GUARDRAIL-INPUT] Step disabled, skipping")
            return {}

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
