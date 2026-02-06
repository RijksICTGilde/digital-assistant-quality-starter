"""Triage node 2: FAQ / known-answer lookup."""

from __future__ import annotations

from loguru import logger

from app.steps.memory._triage import _default_triage, _triage_already_decided

# ── Toggle: set to False to skip this step ──
ENABLED = True


def make_triage_faq_node():
    """Factory: checks whether the question matches a known FAQ entry.

    ── When to short-circuit ─────────────────────────────────────
        • Exact or fuzzy match against a FAQ database
        • The answer is static and doesn't need LLM generation

    ── Example implementation ideas ──────────────────────────────
        • Embedding similarity against a small FAQ index
        • BM25 / keyword search over FAQ entries
        • Simple dict lookup on normalised question text
        • Database query on a FAQ table

    ── Current placeholder ───────────────────────────────────────
        Always passes through. Replace the body with your logic.
    """

    # Example FAQ database — replace with your own data source
    # FAQ_DB: Dict[str, str] = {
    #     "wat zijn de openingstijden": "Het gemeentehuis is open van ...",
    #     "hoe vraag ik een paspoort aan": "U kunt een paspoort aanvragen ...",
    # }

    async def triage_faq(state: dict) -> dict:
        if not ENABLED:
            logger.debug("[TRIAGE-FAQ] Step disabled, skipping")
            return {}

        if _triage_already_decided(state):
            return {}

        triage = dict(state.get("triage") or _default_triage())
        message = state.get("message", "")

        # ── PLACEHOLDER: replace with your FAQ lookup ───────────────
        #
        # Example: simple exact match
        #
        # normalised = message.strip().lower().rstrip("?.")
        # if normalised in FAQ_DB:
        #     triage["route"] = "faq"
        #     triage["skip_llm"] = True
        #     triage["early_response"] = FAQ_DB[normalised]
        #     triage["triage_log"].append("triage_faq: FAQ HIT → skip")
        #     logger.info("[TRIAGE-FAQ] FAQ match found, skipping LLM")
        #     return {"triage": triage}

        triage["triage_log"].append("triage_faq: NO MATCH")
        logger.info("[TRIAGE-FAQ] No FAQ match")
        return {"triage": triage}

    return triage_faq
