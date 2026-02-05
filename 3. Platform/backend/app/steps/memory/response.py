"""Response formatting step node and memory conditional edge."""

from __future__ import annotations

from loguru import logger

from app.steps.state import ChatState


def should_update_memory(state: ChatState) -> str:
    """Conditional edge: skip memory update when use_memory is False."""
    if state.get("use_memory", True):
        logger.info("[EDGE] → update_memory")
        return "update_memory"
    logger.info("[EDGE] → format_response (memory OFF)")
    return "format_response"


def format_response(state: ChatState) -> dict:
    """Build the API response dict."""
    assistant_text = state.get("assistant_text", "")
    unique_sources = state.get("unique_sources", [])
    session = state["session"]
    triage = state.get("triage", {})
    logger.info(
        f"[NODE:format_response] ▶ answer={len(assistant_text)} chars, "
        f"sources={len(unique_sources)}, route={triage.get('route', 'llm')}, "
        f"session={session.get('session_id', '?')}"
    )

    knowledge_sources = [
        {
            "title": s.get("title", ""),
            "document_id": s.get("document_id", ""),
            "relevance_score": s.get("relevance_score", 0),
            "url": s.get("url", ""),
            "section_title": s.get("section_title", ""),
        }
        for s in unique_sources
    ]

    return {
        "response": {
            "main_answer": assistant_text,
            "response_type": "direct_answer",
            "confidence_level": "medium",
            "complexity": "moderate",
            "knowledge_sources": knowledge_sources,
            "action_items": [],
            "compliance_checks": [],
            "follow_up_suggestions": [],
            "needs_human_expert": False,
            "relevant_regulations": [],
            "processing_time_ms": 0,
            "session_id": session.get("session_id", ""),
            "validation": {
                "sources": state.get("source_validation", {}),
                "tone": state.get("tone_validation", {}),
                "output_guardrail": state.get("output_guardrail", {}),
            },
            "triage": state.get("triage", {}),
        }
    }
