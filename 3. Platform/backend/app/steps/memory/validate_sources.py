"""Post-LLM validation: check answer against retrieved sources."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

# ── Toggle: set to False to skip this step ──
ENABLED = True


def make_validate_sources_node(llm: ChatOpenAI):
    """Factory: creates a node that validates the answer against sources.

    ── Input (reads from state) ──────────────────────────────────
        assistant_text : str            the LLM's answer
        unique_sources : list[dict]     deduplicated source documents
            Each dict has at least: title, snippet, document_id

    ── Output (writes to state) ──────────────────────────────────
        source_validation : dict
            {
                "grounded":   bool,         is the answer supported?
                "issues":     list[str],    specific problems found
                "confidence": float,        0.0–1.0
            }

    ── Example replacement ideas ─────────────────────────────────
        • NLI model (e.g. cross-encoder/nli) instead of LLM call
        • Embedding cosine-similarity threshold
        • Rule-based keyword overlap check
    """

    async def validate_sources(state: dict) -> dict:
        if not ENABLED:
            logger.debug("[VALIDATE-SOURCES] Step disabled, skipping")
            return {}

        assistant_text = state.get("assistant_text", "")
        unique_sources = state.get("unique_sources", [])

        # Nothing to validate when there are no sources (direct answer)
        if not unique_sources:
            return {
                "source_validation": {
                    "grounded": True,
                    "issues": [],
                    "confidence": 1.0,
                },
            }

        # Build source context for the validator
        source_texts = []
        for i, src in enumerate(unique_sources):
            title = src.get("title", "Untitled")
            snippet = src.get("snippet", "")
            source_texts.append(f"[{i+1}] {title}: {snippet}")
        sources_block = "\n".join(source_texts)

        prompt = f"""Controleer of het antwoord van de assistent wordt ondersteund door de bronnen.

BRONNEN:
{sources_block}

ANTWOORD:
{assistant_text[:1500]}

Beoordeel:
1. Worden de feitelijke claims in het antwoord ondersteund door de bronnen?
2. Bevat het antwoord informatie die NIET in de bronnen staat (hallucination)?
3. Zijn er bronnen genegeerd die relevant waren?

Antwoord ALLEEN met valid JSON:
{{"grounded": true, "issues": [], "confidence": 0.95}}"""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content="Je valideert antwoorden tegen bronnen. Antwoord alleen met JSON."),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
                max_tokens=200,
            )
            raw = (response.content or "{}").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(raw)
            result = {
                "grounded": data.get("grounded", True),
                "issues": data.get("issues", []),
                "confidence": data.get("confidence", 0.5),
            }
        except Exception as e:
            logger.warning(f"[VALIDATE-SOURCES] Validation failed: {e}")
            result = {"grounded": True, "issues": [], "confidence": 0.0}

        logger.info(
            f"[VALIDATE-SOURCES] grounded={result['grounded']}, "
            f"issues={len(result['issues'])}, confidence={result['confidence']}"
        )
        return {"source_validation": result}

    return validate_sources
