"""Post-LLM evaluation: score the answer (fail-open)."""

from __future__ import annotations

import json

import os

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

    def _format_metric(value: object) -> str:
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
        return "n/a"

    def _build_retrieval_context(sources: list[dict]) -> list[str]:
        context = []
        for src in sources[:5]:
            title = src.get("title", "Untitled")
            snippet = src.get("snippet", "")
            context.append(f"{title}: {snippet}")
        return context

    def _avg(values: list[float]) -> float:
        vals = [v for v in values if isinstance(v, (int, float))]
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def _normalize_geval(score: object) -> float | None:
        if not isinstance(score, (int, float)):
            return None
        if score <= 1.0:
            return float(score)
        if score <= 5.0:
            return float(score) / 5.0
        if score <= 10.0:
            return float(score) / 10.0
        return 1.0

    def _make_deepeval_model() -> object | None:
        try:
            from deepeval.models import LiteLLMModel
        except Exception as e:
            logger.info(f"[EVAL] deepeval model import failed: {e}")
            return None

        api_key = os.getenv("GREENPT_API_KEY")
        base_url = os.getenv("GREENPT_BASE_URL") or None
        model_name = os.getenv("GREENPT_MODEL", "gpt-4o-2024-08-06")

        if not api_key:
            logger.warning("[EVAL] GREENPT_API_KEY not set; deepeval model disabled")
            return None

        # LiteLLM expects provider prefix; GreenPT is OpenAI-compatible.
        return LiteLLMModel(
            model=f"openai/{model_name}",
            api_key=api_key,
            base_url=base_url,
            temperature=0,
        )

    def _eval_with_deepeval(
        message: str,
        assistant_text: str,
        unique_sources: list[dict],
    ) -> dict | None:
        try:
            from deepeval.metrics import (
                AnswerRelevancyMetric,
                ContextualRelevancyMetric,
                FaithfulnessMetric,
                GEval,
            )
            from deepeval.test_case import LLMTestCase, LLMTestCaseParams
        except Exception as e:
            logger.info(f"[EVAL] deepeval not available: {e}")
            return None

        try:
            deepeval_model = _make_deepeval_model()
            if deepeval_model is None:
                return None

            retrieval_context = _build_retrieval_context(unique_sources)
            test_case = LLMTestCase(
                input=message,
                actual_output=assistant_text,
                retrieval_context=retrieval_context,
            )

            relevancy = AnswerRelevancyMetric(model=deepeval_model)
            faithfulness = FaithfulnessMetric(model=deepeval_model)
            contextual = ContextualRelevancyMetric(model=deepeval_model)

            relevancy.measure(test_case)
            faithfulness.measure(test_case)
            contextual.measure(test_case)

            notes = []
            if getattr(relevancy, "reason", None):
                notes.append(f"relevance: {relevancy.reason}")
            if getattr(faithfulness, "reason", None):
                notes.append(f"groundedness: {faithfulness.reason}")
            if getattr(contextual, "reason", None):
                notes.append(f"completeness(proxy): {contextual.reason}")

            # Optional GEval metrics (tone + policy). Disable by setting:
            #   DEEPEVAL_USE_GEVAL=0
            tone_score = None
            policy_score = None
            if os.getenv("DEEPEVAL_USE_GEVAL", "1") != "0":
                tone_metric = GEval(
                    name="Tone",
                    evaluation_steps=[
                        "Check if the response maintains a formal yet accessible government tone.",
                        "Penalize informal, overly casual, or overly enthusiastic language.",
                        "Ensure the response remains respectful and neutral.",
                    ],
                    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
                    model=deepeval_model,
                )
                policy_metric = GEval(
                    name="PolicyCompliance",
                    evaluation_steps=[
                        "Check that the response avoids political advice or persuasion.",
                        "Ensure the response stays neutral and compliant with public-sector guidelines.",
                        "Prefer factual, cautious phrasing over speculative claims.",
                    ],
                    evaluation_params=[
                        LLMTestCaseParams.ACTUAL_OUTPUT,
                        LLMTestCaseParams.RETRIEVAL_CONTEXT,
                        LLMTestCaseParams.INPUT,
                    ],
                    model=deepeval_model,
                )

                tone_metric.measure(test_case)
                policy_metric.measure(test_case)

                tone_score = _normalize_geval(getattr(tone_metric, "score", None))
                policy_score = _normalize_geval(getattr(policy_metric, "score", None))

                if getattr(tone_metric, "reason", None):
                    notes.append(f"tone: {tone_metric.reason}")
                if getattr(policy_metric, "reason", None):
                    notes.append(f"policy: {policy_metric.reason}")

            result = {
                "overall": _avg([
                    relevancy.score,
                    faithfulness.score,
                    contextual.score,
                    tone_score,
                    policy_score,
                ]),
                "relevance": float(relevancy.score),
                "tone": tone_score,
                "policy_compliance": policy_score,
                "groundedness": float(faithfulness.score),
                "completeness": float(contextual.score),
                "notes": notes[:3],
            }
            logger.info("[EVAL] judge=deepeval (AnswerRelevancy/Faithfulness/ContextualRelevancy)")
            return result
        except Exception as e:
            logger.warning(f"[EVAL] deepeval failed: {e}")
            return None

    async def _eval_with_llm_judge(
        message: str,
        assistant_text: str,
        unique_sources: list[dict],
        user_context: dict,
    ) -> dict:
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
        logger.info("[EVAL] judge=llm (greenpt), input=message+answer+sources+user_context")
        return result

    async def evaluate_answer(state: dict) -> dict:
        assistant_text = state.get("assistant_text", "")
        message = state.get("message", "")
        unique_sources = state.get("unique_sources", [])
        user_context = state.get("user_context", {})

        snippet = assistant_text[:100].replace("\n", " ")
        logger.info(f"[EVAL] answer_snippet='{snippet}'")

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

        try:
            result = _eval_with_deepeval(message, assistant_text, unique_sources)
            if result is None:
                result = await _eval_with_llm_judge(message, assistant_text, unique_sources, user_context)
        except Exception as e:
            logger.warning(f"[EVAL] Evaluation failed: {e}")
            return {}

        logger.info(
            "[EVAL] overall={overall}, relevance={relevance}, tone={tone}, "
            "policy={policy_compliance}, grounded={groundedness}, completeness={completeness}".format(
                overall=_format_metric(result.get("overall")),
                relevance=_format_metric(result.get("relevance")),
                tone=_format_metric(result.get("tone")),
                policy_compliance=_format_metric(result.get("policy_compliance")),
                groundedness=_format_metric(result.get("groundedness")),
                completeness=_format_metric(result.get("completeness")),
            )
        )
        if result.get("notes"):
            logger.info(f"[EVAL] notes={result['notes']}")
        return {"answer_evaluation": result}

    return evaluate_answer
