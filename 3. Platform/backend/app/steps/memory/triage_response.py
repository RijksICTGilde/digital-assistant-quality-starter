"""Bundle node for triage early-exit (skips LLM but prepares state for memory)."""

from __future__ import annotations

import uuid

from loguru import logger


def _bundle_triage_response(state: dict) -> dict:
    """Set assistant_text and source fields from the triage early response.

    This node runs instead of the LLM pipeline when triage decides to skip.
    It sets the same fields that bundle_sources normally sets, so that
    update_memory and format_response work unchanged.

    For FAQ matches, this also includes the pre-defined FAQ sources.
    """
    triage = state.get("triage") or {}
    early_response = triage.get("early_response", "")
    exchange_id = f"ex-{uuid.uuid4().hex[:8]}"

    # Build sources list from FAQ sources if available
    faq_sources = triage.get("faq_sources", [])
    unique_sources = []

    for i, src in enumerate(faq_sources):
        unique_sources.append({
            "title": src.get("title", ""),
            "url": src.get("url", ""),
            "section_title": src.get("section_title", ""),
            "snippet": src.get("snippet", ""),
            "relevance_score": src.get("relevance_score", 0.9),
            "document_id": f"faq-src-{i}",
        })

    logger.info(
        f"[TRIAGE] Early response ({triage.get('route', '?')}): "
        f"{len(early_response)} chars, {len(unique_sources)} sources"
    )
    return {
        "assistant_text": early_response,
        "exchange_id": exchange_id,
        "unique_sources": unique_sources,
        "source_ids": [src["document_id"] for src in unique_sources],
    }
