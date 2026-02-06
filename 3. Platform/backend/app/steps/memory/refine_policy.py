"""Refinement decision logic (isolated, easy to iterate)."""

from __future__ import annotations

from typing import Any, Dict, List


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def decide_refine(
    evaluation: Dict[str, Any] | None,
    source_validation: Dict[str, Any] | None,
    tone_validation: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Decide whether we should refine, and why.

    Returns:
        {
          "should_refine": bool,
          "reasons": list[str],
          "thresholds": dict,
          "scores_used": dict
        }
    """
    evaluation = evaluation or {}
    source_validation = source_validation or {}
    tone_validation = tone_validation or {}

    thresholds = {
        "relevance": 0.6,
        "groundedness": 0.6,
        "completeness": 0.5,
        "tone": 0.6,
        "policy_compliance": 0.6,
    }

    scores = {
        "relevance": _as_float(evaluation.get("relevance")),
        "groundedness": _as_float(evaluation.get("groundedness")),
        "completeness": _as_float(evaluation.get("completeness")),
        "tone": _as_float(evaluation.get("tone")),
        "policy_compliance": _as_float(evaluation.get("policy_compliance")),
    }

    reasons: List[str] = []

    if scores["relevance"] is not None and scores["relevance"] < thresholds["relevance"]:
        reasons.append("Low relevance to the user question")

    if scores["groundedness"] is not None and scores["groundedness"] < thresholds["groundedness"]:
        reasons.append("Answer not sufficiently grounded in sources")
    elif source_validation.get("grounded") is False:
        reasons.append("Source validation flagged grounding issues")

    if scores["completeness"] is not None and scores["completeness"] < thresholds["completeness"]:
        reasons.append("Answer seems incomplete for the user need")

    if scores["tone"] is not None and scores["tone"] < thresholds["tone"]:
        reasons.append("Tone is not aligned with public-sector guidelines")
    elif tone_validation.get("appropriate") is False:
        reasons.append("Tone validation flagged issues")

    if scores["policy_compliance"] is not None and scores["policy_compliance"] < thresholds["policy_compliance"]:
        reasons.append("Potential policy/ethics compliance risks")

    should_refine = len(reasons) > 0

    return {
        "should_refine": should_refine,
        "reasons": reasons,
        "thresholds": thresholds,
        "scores_used": scores,
    }
