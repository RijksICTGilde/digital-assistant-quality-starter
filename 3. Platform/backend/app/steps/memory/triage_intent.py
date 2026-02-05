"""Triage node 3: intent classification."""

from __future__ import annotations

from loguru import logger

from app.steps.memory._triage import _default_triage, _triage_already_decided


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
