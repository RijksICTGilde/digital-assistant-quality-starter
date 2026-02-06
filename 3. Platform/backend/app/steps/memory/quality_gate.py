"""Quality gate step: decide whether to refine the answer."""

from __future__ import annotations

from loguru import logger

from app.steps.memory.refine_policy import decide_refine


def should_refine_from_state(state: dict) -> str:
    if state.get("refined_once"):
        logger.info("[EDGE] quality_gate → validate_sources (already refined)")
        return "validate_sources"
    decision = state.get("refine_decision", {}) or {}
    if decision.get("should_refine", False):
        logger.info("[EDGE] quality_gate → refine_answer")
        return "refine_answer"
    logger.info("[EDGE] quality_gate → validate_sources (no refine)")
    return "validate_sources"


def should_route_after_evaluate(state: dict) -> str:
    if state.get("refined_once"):
        logger.info("[EDGE] evaluate_answer → validate_sources (post-refine)")
        return "validate_sources"
    logger.info("[EDGE] evaluate_answer → quality_gate")
    return "quality_gate"


def make_quality_gate_node():
    async def quality_gate(state: dict) -> dict:
        if state.get("refined_once"):
            return {}
        evaluation = state.get("answer_evaluation", {})
        source_validation = state.get("source_validation", {})
        tone_validation = state.get("tone_validation", {})

        decision = decide_refine(evaluation, source_validation, tone_validation)
        reasons = decision.get("reasons", [])
        logger.info(f"[QUALITY-GATE] refine={decision.get('should_refine')} reasons={len(reasons)}")
        if reasons:
            logger.info(f"[QUALITY-GATE] reasons={reasons}")
        return {
            "refine_decision": decision,
            "answer_evaluation_before": evaluation,
        }

    return quality_gate
