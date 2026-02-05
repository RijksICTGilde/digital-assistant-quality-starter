"""Thin wrapper: creates LLM + graph, exposes chat()."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from loguru import logger

from app.features.memory.graph import build_chat_graph
from app.features.memory.session_store import SessionStore


class MemoryService:
    """Orchestrates memory-augmented chat via a LangGraph graph."""

    def __init__(
        self,
        enhanced_rag: Any,
        session_store: Optional[SessionStore] = None,
        faq_service: Any = None,
    ):
        api_key = os.getenv("GREENPT_API_KEY")
        base_url = os.getenv("GREENPT_BASE_URL") or None
        model = os.getenv("GREENPT_MODEL", "gpt-4o-2024-08-06")

        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.3,
            max_tokens=2000,
        )
        self.enhanced_rag = enhanced_rag
        self.session_store = session_store or SessionStore()
        self.faq_service = faq_service
        self.graph = build_chat_graph(
            self.llm,
            self.enhanced_rag,
            self.session_store,
            faq_service=self.faq_service,
        )
        logger.info(
            f"MemoryService initialised (model={model}, base_url={base_url}, "
            f"faq_service={'enabled' if faq_service else 'disabled'})"
        )

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_context: Optional[Dict] = None,
        use_memory: bool = True,
    ) -> Dict[str, Any]:
        """Process a single user turn with memory + tools.

        Returns a dict compatible with the existing StructuredAIResponse
        shape so the frontend can render it unchanged.
        """
        logger.info(
            f"[GRAPH] ═══ START ═══ session={session_id or '(new)'}, "
            f"memory={'ON' if use_memory else 'OFF'}, "
            f"message='{message[:60]}{'...' if len(message) > 60 else ''}'"
        )

        result = await self.graph.ainvoke({
            "message": message,
            "session_id": session_id or "",
            "user_context": user_context or {},
            "use_memory": use_memory,
        })

        resp = result["response"]
        triage = resp.get("triage", {})
        logger.info(
            f"[GRAPH] ═══ DONE ════ route={triage.get('route', 'llm')}, "
            f"answer={len(resp.get('main_answer', ''))} chars, "
            f"sources={len(resp.get('knowledge_sources', []))}, "
            f"session={resp.get('session_id', '?')}"
        )
        return resp
