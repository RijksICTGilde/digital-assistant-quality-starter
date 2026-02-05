"""Triage node 2: FAQ / known-answer lookup using FAISS semantic search."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.steps.memory._triage import _default_triage, _triage_already_decided


def make_triage_faq_node(faq_service: Any = None):
    """Factory: checks whether the question matches a known FAQ entry.

    Uses the FAQService to perform semantic matching with FAISS:
    - Score >= 0.85: Direct FAQ answer (skip LLM)
    - Score 0.70-0.85: FAQ as suggestion for LLM
    - Score < 0.70: No match, normal LLM processing

    Args:
        faq_service: Optional FAQService instance for FAQ matching.
                     If None, the node passes through without matching.
    """

    async def triage_faq(state: dict) -> dict:
        if _triage_already_decided(state):
            return {}

        triage = dict(state.get("triage") or _default_triage())
        message = state.get("message", "")

        # Skip if no FAQ service is configured
        if faq_service is None:
            triage["triage_log"].append("triage_faq: NO SERVICE")
            logger.debug("[TRIAGE-FAQ] No FAQ service configured, passing through")
            return {"triage": triage}

        # Get best FAQ match
        match, decision = faq_service.get_best_match(message)

        if decision == "exact":
            # High confidence match - skip LLM and return FAQ answer directly
            triage["route"] = "faq"
            triage["skip_llm"] = True
            triage["early_response"] = match.answer
            triage["faq_match"] = {
                "faq_id": match.faq_id,
                "category": match.category,
                "matched_question": match.matched_question,
                "score": match.score,
                "related_questions": match.related_questions or [],
            }
            triage["faq_sources"] = match.sources or []
            triage["triage_log"].append(
                f"triage_faq: EXACT ({match.faq_id}, score={match.score:.3f}) → skip LLM"
            )
            logger.info(
                f"[TRIAGE-FAQ] Exact match: {match.faq_id} (score={match.score:.3f})"
            )
            return {"triage": triage}

        if decision == "suggest":
            # Medium confidence - pass FAQ as suggestion for LLM to consider
            triage["faq_suggestion"] = {
                "faq_id": match.faq_id,
                "category": match.category,
                "matched_question": match.matched_question,
                "answer": match.answer,
                "score": match.score,
                "related_questions": match.related_questions or [],
            }
            triage["triage_log"].append(
                f"triage_faq: SUGGEST ({match.faq_id}, score={match.score:.3f})"
            )
            logger.info(
                f"[TRIAGE-FAQ] Suggest match: {match.faq_id} (score={match.score:.3f})"
            )
            return {"triage": triage}

        # No match or low confidence
        triage["triage_log"].append("triage_faq: NO MATCH")
        logger.debug("[TRIAGE-FAQ] No FAQ match")
        return {"triage": triage}

    return triage_faq
