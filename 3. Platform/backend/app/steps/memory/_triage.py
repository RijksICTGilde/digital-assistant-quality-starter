"""Shared triage helpers used by multiple triage/guardrail nodes."""

from __future__ import annotations


def _default_triage() -> dict:
    """Return the initial triage state dict."""
    return {
        "route": "llm",          # "llm" | "faq" | "irrelevant" | "chitchat"
        "skip_llm": False,       # True → bypass build_prompt + call_llm
        "early_response": None,  # str set when skip_llm=True
        "triage_log": [],        # human-readable log of each validator decision
    }


def _triage_already_decided(state: dict) -> bool:
    """Check whether a previous triage node already decided to skip."""
    triage = state.get("triage") or {}
    return triage.get("skip_llm", False)
