"""Post-LLM validation: check and optionally rewrite tone."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger


def make_validate_tone_node(llm: ChatOpenAI):
    """Factory: creates a node that checks tone and optionally rewrites.

    ── Input (reads from state) ──────────────────────────────────
        assistant_text : str            the LLM's answer

    ── Output (writes to state) ──────────────────────────────────
        assistant_text  : str           original OR rewritten answer
        tone_validation : dict
            {
                "appropriate":   bool,          was the tone OK as-is?
                "original_text": str | None,    original if rewritten, else None
                "adjustments":   list[str],     what was changed and why
            }

    ── Example replacement ideas ─────────────────────────────────
        • Sentiment classifier + rule engine
        • Brand-voice scoring model
        • Simple regex checks (no emoji, no exclamation marks, etc.)
    """

    async def validate_tone(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")

        if not assistant_text.strip():
            return {
                "tone_validation": {
                    "appropriate": True,
                    "original_text": None,
                    "adjustments": [],
                },
            }

        prompt = f"""Beoordeel de toon van dit antwoord van een overheids-AI-assistent.

RICHTLIJNEN:
- Formeel maar toegankelijk (geen ambtelijk jargon)
- Behulpzaam zonder betuttelend te zijn
- Geen afsluitende vragen ("Wil je meer weten?", "Kan ik je ergens mee helpen?")
- Geen overdreven enthousiasme of emoji's
- Concreet en zakelijk

ANTWOORD:
{assistant_text[:2000]}

Als de toon correct is, antwoord met:
{{"appropriate": true, "adjustments": []}}

Als de toon aangepast moet worden, antwoord met:
{{"appropriate": false, "adjustments": ["reden1"], "rewritten": "het volledig herschreven antwoord"}}

Antwoord ALLEEN met valid JSON."""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content="Je controleert de toon van overheidsantwoorden. "
                        "Antwoord alleen met JSON."
                    ),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
                max_tokens=2500,
            )
            raw = (response.content or "{}").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(raw)
            appropriate = data.get("appropriate", True)
            adjustments = data.get("adjustments", [])

            if not appropriate and data.get("rewritten", "").strip():
                logger.info(f"[VALIDATE-TONE] Rewriting ({len(adjustments)} adjustments)")
                return {
                    "assistant_text": data["rewritten"],
                    "tone_validation": {
                        "appropriate": False,
                        "original_text": assistant_text,
                        "adjustments": adjustments,
                    },
                }

            result = {
                "appropriate": appropriate,
                "original_text": None,
                "adjustments": adjustments,
            }
        except Exception as e:
            logger.warning(f"[VALIDATE-TONE] Validation failed: {e}")
            result = {"appropriate": True, "original_text": None, "adjustments": []}

        logger.info(f"[VALIDATE-TONE] appropriate={result['appropriate']}")
        return {"tone_validation": result}

    return validate_tone
