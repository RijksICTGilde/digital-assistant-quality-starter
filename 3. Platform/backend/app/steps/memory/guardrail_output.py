"""Output guardrail node: checks whether the assistant response is safe."""

from __future__ import annotations

from loguru import logger


def make_guardrail_output_node():
    """Factory: checks whether the assistant response is safe to deliver.

    This runs AFTER validate_tone (or after bundle_triage_response on
    the early-exit path) — it is the last gate before memory + response.

    ── When to block or rewrite ──────────────────────────────────
        • Response leaks internal system prompt or instructions
        • Response contains PII (phone numbers, emails, BSN)
        • Response contains hallucinated URLs or legal references
        • Response is too long or contains forbidden content
        • Response contradicts known policy or regulations

    ── Example implementation ideas ──────────────────────────────
        • Regex scan for PII patterns (phone, email, BSN)
        • URL validation against a known-good allowlist
        • LLM-as-judge checking for policy compliance
        • Embedding similarity to detect prompt leakage
        • Length / formatting rules

    ── State contract ────────────────────────────────────────────
        Reads:   assistant_text
        Writes:  assistant_text  (replaced with safe fallback if blocked)
                 output_guardrail : dict  {safe, issues, original_text}

    ── Current placeholder ───────────────────────────────────────
        Always passes through. Replace the body with your logic.
    """

    async def guardrail_output(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")

        # ── PLACEHOLDER: replace with your output guardrail logic ───
        #
        # Example 1: detect leaked system prompt fragments
        #
        # LEAK_MARKERS = ["KERNREGEL", "TOOL-KEUZE", "GEHEUGEN:", "[§USR]", "[§BOT]"]
        # if any(marker in assistant_text for marker in LEAK_MARKERS):
        #     logger.warning("[GUARDRAIL-OUTPUT] System prompt leakage detected")
        #     return {
        #         "assistant_text": (
        #             "Er is een fout opgetreden bij het genereren van het antwoord. "
        #             "Probeer het opnieuw."
        #         ),
        #         "output_guardrail": {
        #             "safe": False,
        #             "issues": ["system_prompt_leakage"],
        #             "original_text": assistant_text,
        #         },
        #     }
        #
        # Example 2: strip any PII from the response
        #
        # import re
        # cleaned = re.sub(r"\b\d{9}\b", "[BSN VERWIJDERD]", assistant_text)
        # if cleaned != assistant_text:
        #     logger.warning("[GUARDRAIL-OUTPUT] PII removed from response")
        #     return {
        #         "assistant_text": cleaned,
        #         "output_guardrail": {
        #             "safe": True,
        #             "issues": ["pii_removed"],
        #             "original_text": assistant_text,
        #         },
        #     }

        logger.info("[GUARDRAIL-OUTPUT] Response approved")
        return {
            "output_guardrail": {
                "safe": True,
                "issues": [],
                "original_text": None,
            },
        }

    return guardrail_output
