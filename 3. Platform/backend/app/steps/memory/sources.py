"""Source bundling step node."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from langchain_core.messages import AIMessage
from loguru import logger

from app.steps.state import ChatState


def bundle_sources(state: ChatState) -> dict:
    """Deduplicate retrieved_sources and extract assistant text."""
    messages = state["messages"]
    raw_sources = state.get("retrieved_sources", [])
    logger.info(f"[NODE:bundle_sources] ▶ {len(raw_sources)} raw sources, {len(messages)} messages")

    # Find last AIMessage with text content.
    # Some models return both tool_calls and content; we accept content
    # from any AIMessage, not just those without tool_calls.
    assistant_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
            assistant_text = msg.content
            break

    if not assistant_text:
        logger.warning("[MEMORY] No text in AI messages (max tool rounds reached?), using fallback")
        assistant_text = "Ik kon geen antwoord genereren op basis van de beschikbare informatie."

    # Deduplicate sources by document_id
    seen_doc_ids: set = set()
    unique_sources: List[Dict[str, Any]] = []
    for src in state.get("retrieved_sources", []):
        doc_id = src.get("document_id", "")
        if doc_id and doc_id in seen_doc_ids:
            continue
        if doc_id:
            seen_doc_ids.add(doc_id)
        unique_sources.append(src)

    source_ids = [s.get("document_id", "") for s in unique_sources if s.get("document_id")]
    exchange_id = f"ex-{uuid.uuid4().hex[:8]}"

    deduped = len(raw_sources) - len(unique_sources)
    logger.info(
        f"[NODE:bundle_sources] ✓ answer={len(assistant_text)} chars, "
        f"sources={len(unique_sources)} unique ({deduped} duplicates removed), "
        f"exchange_id={exchange_id}"
    )

    return {
        "assistant_text": assistant_text,
        "exchange_id": exchange_id,
        "unique_sources": unique_sources,
        "source_ids": source_ids,
    }
