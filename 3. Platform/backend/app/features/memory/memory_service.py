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
        self.graph = build_chat_graph(self.llm, self.enhanced_rag, self.session_store)
        logger.info(f"MemoryService initialised (model={model}, base_url={base_url})")

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
        logger.info(f"[MEMORY] use_memory={use_memory}")

        result = await self.graph.ainvoke({
            "message": message,
            "session_id": session_id or "",
            "user_context": user_context or {},
            "use_memory": use_memory,
        })
        return result["response"]
