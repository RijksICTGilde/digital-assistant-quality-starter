"""Post-LLM evaluation: score the answer (fail-open)."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger


def make_evaluate_answer_node(llm: ChatOpenAI):
    """Factory: creates a node that evaluates the LLM answer.

    This step is observational only and MUST NOT break the pipeline.

    ── Input (reads from state) ──────────────────────────────────
        message : str
        assistant_text : str
        unique_sources : list[dict]
        user_context : dict

    ── Output (writes to state) ──────────────────────────────────
        answer_evaluation : dict
            {
                "overall": float (0-1),
                "relevance": float (0-1),
                "tone": float (0-1),
                "policy_compliance": float (0-1),
                "groundedness": float (0-1),
                "completeness": float (0-1),
                "notes": list[str]
            }
    """

    async def evaluate_answer(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")
        message = state.get("message", "")
        unique_sources = state.get("unique_sources", [])
        user_context = state.get("user_context", {})

        snippet = assistant_text[:100].replace("\n", " ")
        logger.info(f"[EVAL] answer_snippet='{snippet}'")
        logger.info("[EVAL] judge=llm (greenpt), input=message+answer+sources+user_context")

        if not assistant_text.strip():
            return {
                "answer_evaluation": {
                    "overall": 0.0,
                    "relevance": 0.0,
                    "tone": 0.0,
                    "policy_compliance": 0.0,
                    "groundedness": 0.0,
                    "completeness": 0.0,
                    "notes": ["Empty response"],
                },
            }

        source_snippets = []
        for i, src in enumerate(unique_sources[:5]):
            title = src.get("title", "Untitled")
            snippet_text = src.get("snippet", "")
            source_snippets.append(f"[{i+1}] {title}: {snippet_text}")
        sources_block = "\n".join(source_snippets) or "Geen bronnen beschikbaar."

        prompt = f"""Beoordeel dit antwoord van een overheids-AI-assistent in context.

VRAAG:
{message}

CONTEXT (indien aanwezig):
{json.dumps(user_context)[:1000]}

BRONNEN (indien aanwezig):
{sources_block}

ANTWOORD:
{assistant_text[:2000]}

Geef scores van 0.0 (slecht) tot 1.0 (uitstekend) voor:
- relevance
- tone
- policy_compliance (beleidsmatige/ethische kaders)
- groundedness (mate waarin het antwoord is gebaseerd op bronnen)
- completeness

Geef ook een overall score (0.0-1.0) en maximaal 3 korte notes.

Antwoord ALLEEN met valid JSON, bijv:
{{"overall": 0.78, "relevance": 0.8, "tone": 0.9, "policy_compliance": 0.85, "groundedness": 0.6, "completeness": 0.7, "notes": ["Kort en duidelijk", "Mist een concrete stap"]}}
"""

        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content="Je beoordeelt antwoorden. Antwoord alleen met JSON."),
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
                "overall": float(data.get("overall", 0.0)),
                "relevance": float(data.get("relevance", 0.0)),
                "tone": float(data.get("tone", 0.0)),
                "policy_compliance": float(data.get("policy_compliance", 0.0)),
                "groundedness": float(data.get("groundedness", 0.0)),
                "completeness": float(data.get("completeness", 0.0)),
                "notes": data.get("notes", []),
            }
        except Exception as e:
            logger.warning(f"[EVAL] Evaluation failed: {e}")
            return {}

        logger.info(
            "[EVAL] overall={overall}, relevance={relevance}, tone={tone}, "
            "policy={policy_compliance}, grounded={groundedness}, completeness={completeness}".format(
                **result
            )
        )
        if result.get("notes"):
            logger.info(f"[EVAL] notes={result['notes']}")
        return {"answer_evaluation": result}

    return evaluate_answer
