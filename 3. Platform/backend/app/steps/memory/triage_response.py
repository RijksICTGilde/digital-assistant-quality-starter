"""Bundle node for triage early-exit (skips LLM but prepares state for memory)."""

from __future__ import annotations

import uuid

from loguru import logger


def _bundle_triage_response(state: dict) -> dict:
    """Set assistant_text and source fields from the triage early response.

    This node runs instead of the LLM pipeline when triage decides to skip.
    It sets the same fields that bundle_sources normally sets, so that
    update_memory and format_response work unchanged.
    """
    triage = state.get("triage") or {}
    early_response = triage.get("early_response", "")
    exchange_id = f"ex-{uuid.uuid4().hex[:8]}"

    logger.info(
        f"[TRIAGE] Early response ({triage.get('route', '?')}): "
        f"{len(early_response)} chars"
    )
    return {
        "assistant_text": early_response,
        "exchange_id": exchange_id,
        "unique_sources": [],
        "source_ids": [],
    }
