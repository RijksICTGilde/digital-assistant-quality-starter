"""Refine the answer based on quality evaluation (single pass, fail-open)."""

from __future__ import annotations

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def _build_sources_block(sources: list[dict]) -> str:
    lines = []
    for i, src in enumerate(sources[:5]):
        title = src.get("title", "Untitled")
        snippet = src.get("snippet", "")
        lines.append(f"[{i+1}] {title}: {snippet}")
    return "\n".join(lines) or "Geen bronnen beschikbaar."


def make_refine_answer_node(llm: ChatOpenAI):
    async def refine_answer(state: dict) -> dict:
        if state.get("refined_once"):
            logger.info("[REFINE] Skipping: already refined once")
            return {}

        decision = state.get("refine_decision", {}) or {}
        if not decision.get("should_refine", False):
            return {}

        message = state.get("message", "")
        assistant_text = state.get("assistant_text", "")
        reasons = decision.get("reasons", [])
        evaluation = state.get("answer_evaluation", {})
        sources_block = _build_sources_block(state.get("unique_sources", []))

        logger.info("[REFINE] Triggered with %d reason(s)", len(reasons))
        answer_before = assistant_text

        prompt = f"""Je bent een kwaliteitsassistent voor de overheid.
Verbeter het antwoord op basis van de signalen hieronder.

VRAAG:
{message}

HUIDIG ANTWOORD:
{assistant_text}

SIGNAAL (problemen):
- """ + "\n- ".join(reasons) + f"""

SCORES (0-1):
- relevance: {evaluation.get('relevance')}
- groundedness: {evaluation.get('groundedness')}
- completeness: {evaluation.get('completeness')}
- tone: {evaluation.get('tone')}
- policy_compliance: {evaluation.get('policy_compliance')}

BRONNEN (indien aanwezig):
{sources_block}

INSTRUCTIES:
- Antwoord in het Nederlands.
- Focus op de vraag; verwijder irrelevante details.
- Gebruik alleen informatie die in de bronnen staat als je bronnen hebt.
- Verbeter volledigheid met concrete stappen.
- Houd een neutrale, formele overheids-toon.
- Vermijd politiek advies of speculatie.

Geef alleen het verbeterde antwoord terug.
"""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content="Je verbetert overheidsantwoorden. Antwoord alleen met het verbeterde antwoord."),
                    HumanMessage(content=prompt),
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            new_text = (response.content or "").strip()
            if not new_text:
                return {"refined_once": True, "answer_before": answer_before}
            logger.info("[REFINE] Updated answer (%d chars)", len(new_text))
            return {
                "assistant_text": new_text,
                "refined_once": True,
                "answer_before": answer_before,
            }
        except Exception as e:
            logger.warning(f"[REFINE] Failed: {e}")
            return {"refined_once": True, "answer_before": answer_before}

    return refine_answer
