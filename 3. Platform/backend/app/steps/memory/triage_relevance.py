"""Triage node 1: domain relevance check."""

from __future__ import annotations

from loguru import logger

from app.steps.memory._triage import _default_triage, _triage_already_decided

# ── Toggle: set to False to skip this step ──
ENABLED = True


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
        if not ENABLED:
            logger.debug("[TRIAGE-RELEVANCE] Step disabled, skipping")
            return {}

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
