"""Memory update step node."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.features.memory.models import QAIndexEntry
from app.steps.state import ChatState, M_BOT, M_USR


def make_update_memory(llm: ChatOpenAI):
    """Returns the update_memory node."""

    async def _generate_qa_entry(
        question: str, answer: str, exchange_id: str, source_ids: List[str],
    ) -> QAIndexEntry:
        prompt = f"""Analyseer deze Q&A uitwisseling en maak een compacte samenvatting.

{M_USR}: {question[:500]}
{M_BOT}: {answer[:500]}

Bepaal:
- user_intent: wat deed de gebruiker?
  "question" = stelde een vraag
  "assumption" = beweerde iets / maakte een aanname
  "verified" = deelde informatie die de assistent heeft bevestigd
  "preference" = gaf een voorkeur/wens aan (bijv. "ik wil alleen X")
  "correction" = corrigeerde de assistent
- verified: heeft de assistent het antwoord gebaseerd op de kennisbank? (true/false)

Antwoord ALLEEN met valid JSON (geen markdown, geen uitleg):
{{"question_summary": "korte samenvatting vraag", "answer_summary": "korte samenvatting antwoord", "topics": ["topic1", "topic2"], "user_intent": "question", "verified": false}}"""

        response = await llm.ainvoke(
            [
                SystemMessage(content="Je maakt compacte samenvattingen. Antwoord alleen met valid JSON."),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
            max_tokens=200,
        )
        raw = response.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        return QAIndexEntry(
            exchange_id=exchange_id,
            question_summary=data.get("question_summary", question[:100]),
            answer_summary=data.get("answer_summary", answer[:100]),
            topics=data.get("topics", []),
            source_ids=source_ids or [],
            user_intent=data.get("user_intent", "question"),
            verified=data.get("verified", False),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _update_summary(current_summary: str, question: str, answer: str) -> str:
        prompt = f"""Update de sessie-samenvatting met de laatste uitwisseling.
Houd het onder 200 woorden.

BELANGRIJK: Markeer duidelijk de BRON van informatie:
- {M_USR} = uitspraken van de gebruiker (hun woorden, NIET per se waar)
- {M_BOT} = antwoorden van de assistent (gebaseerd op kennisbank)

Gebruik deze markers in de samenvatting. Voorbeeld:
"{M_USR} Gebruiker vroeg naar GDPR. {M_BOT} Assistent legde uit dat DPIA verplicht is. {M_USR} Gebruiker gaf aan alleen interesse te hebben in bewaartermijnen."

Focus op: gebruikersvoorkeuren, besluiten, en geverifieerde feiten.

Huidige samenvatting:
{current_summary or '(geen – dit is het eerste bericht)'}

Nieuwe uitwisseling:
{M_USR} {question[:300]}
{M_BOT} {answer[:300]}

Geef ALLEEN de bijgewerkte samenvatting terug, geen uitleg."""

        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="Je werkt sessie-samenvattingen bij. Maak altijd duidelijk onderscheid "
                    "tussen wat de gebruiker zei en wat de assistent antwoordde. "
                    "Antwoord alleen met de samenvatting."
                ),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
            max_tokens=300,
        )
        return response.content or current_summary

    async def update_memory(state: ChatState) -> dict:
        session = dict(state["session"])  # shallow copy
        message = state["message"]
        assistant_text = state["assistant_text"]
        exchange_id = state["exchange_id"]
        source_ids = state.get("source_ids", [])
        unique_sources = state.get("unique_sources", [])
        logger.info(
            f"[NODE:update_memory] ▶ exchange_id={exchange_id}, "
            f"answer={len(assistant_text)} chars, sources={len(source_ids)}"
        )

        # Store full answer
        full_answers = dict(session.get("full_answers", {}))
        full_answers[exchange_id] = {
            "text": assistant_text,
            "sources": unique_sources,
        }
        session["full_answers"] = full_answers

        # Increment message count
        session["message_count"] = session.get("message_count", 0) + 1

        # Update recent messages (keep last 10 = 5 pairs)
        # Only store pairs where the assistant actually responded
        recent = list(session.get("recent_messages", []))
        if assistant_text.strip():
            recent.append({"role": "user", "content": message})
            recent.append({"role": "assistant", "content": assistant_text})
            session["recent_messages"] = recent[-10:]

        # Run QA entry + summary update in parallel
        try:
            results = await asyncio.gather(
                _generate_qa_entry(message, assistant_text, exchange_id, source_ids),
                _update_summary(session.get("summary", ""), message, assistant_text),
                return_exceptions=True,
            )

            # Q&A entry
            qa_index = list(session.get("qa_index", []))
            if isinstance(results[0], QAIndexEntry):
                qa_index.append(results[0].model_dump())
            else:
                logger.warning(f"QA index generation failed: {results[0]}")
                qa_index.append(QAIndexEntry(
                    exchange_id=exchange_id,
                    question_summary=message[:100],
                    answer_summary=assistant_text[:100],
                    topics=[],
                    source_ids=source_ids,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ).model_dump())
            session["qa_index"] = qa_index

            # Summary
            if isinstance(results[1], str):
                session["summary"] = results[1]
            else:
                logger.warning(f"Summary update failed: {results[1]}")

        except Exception as e:
            logger.error(f"[NODE:update_memory] Session memory update failed: {e}")

        qa_count = len(session.get("qa_index", []))
        logger.info(
            f"[NODE:update_memory] ✓ qa_index={qa_count} entries, "
            f"summary={len(session.get('summary', ''))} chars"
        )
        return {"session": session}

    return update_memory
