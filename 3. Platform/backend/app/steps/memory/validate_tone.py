"""Post-LLM validation: check and optionally rewrite tone."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

# ── Toggle: set to False to skip this step ──
ENABLED = False


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
        if not ENABLED:
            logger.debug("[VALIDATE-TONE] Step disabled, skipping")
            return {}

        assistant_text = state.get("assistant_text", "")

        if not assistant_text.strip():
            return {
                "tone_validation": {
                    "appropriate": True,
                    "original_text": None,
                    "adjustments": [],
                },
            }

        logger.info(f"[VALIDATE-TONE] ▶ Rewriting {len(assistant_text)} chars to B1-niveau")

        prompt = f"""Herschrijf het onderstaande antwoord naar B1-niveau (Makkelijker Nederlands).

SCHRIJFWIJZER B1-NIVEAU:

Zinsbouw:
- Houd zinnen kort en bondig (gemiddeld 10-15 woorden).
- Vermijd complexe samengestelde zinnen.
- Vermijd de tangconstructie: zet bij elkaar horende woorden (zoals werkwoorden) niet te ver uit elkaar.

Structuur:
- Gebruik korte alinea's en betekenisvolle tussenkoppen om de tekst scanbaar te maken.
- Gebruik bullet points of genummerde lijsten voor voorwaarden of opsommingen.

Stijl:
- Schrijf in de actieve vorm ("U betaalt binnen 14 dagen" in plaats van "De betaling dient binnen 14 dagen te geschieden").
- Spreek de lezer direct aan met 'u'.
- Vermijd vakjargon, moeilijke woorden en clichés. Gebruik alledaagse taal.
- Beperk hulpwerkwoorden zoals 'zullen', 'kunnen', 'moeten', 'zouden'.
- Vermijd 'er' en 'echter' aan het begin van zinnen.
- Vermijd overbodige woorden.

Verder:
- Behoud ALLE feitelijke informatie — laat niets weg.
- Behoud markdown-opmaak (##, ###, opsommingen).
- Geen afsluitende vragen ("Wil je meer weten?", "Kan ik u ergens mee helpen?").
- Antwoord alleen met de herschreven tekst, geen uitleg.

ORIGINEEL ANTWOORD:
{assistant_text}"""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content="Je herschrijft teksten naar B1-niveau (Makkelijker Nederlands). "
                        "Geef alleen de herschreven tekst terug, niets anders."
                    ),
                    HumanMessage(content=prompt),
                ],
                temperature=0.3,
                max_tokens=2500,
            )
            rewritten = (response.content or "").strip()
            if not rewritten:
                logger.warning("[VALIDATE-TONE] Empty rewrite, keeping original")
                return {"tone_validation": {"appropriate": True, "original_text": None, "adjustments": []}}

            logger.info(f"[VALIDATE-TONE] ✓ Rewritten to B1: {len(assistant_text)} → {len(rewritten)} chars")
            return {
                "assistant_text": rewritten,
                "tone_validation": {
                    "appropriate": False,
                    "original_text": assistant_text,
                    "adjustments": ["Herschreven naar B1-niveau"],
                },
            }
        except Exception as e:
            logger.warning(f"[VALIDATE-TONE] Rewrite failed: {e}, keeping original")
            return {"tone_validation": {"appropriate": True, "original_text": None, "adjustments": []}}

    return validate_tone
