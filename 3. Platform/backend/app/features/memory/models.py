from pydantic import BaseModel, Field, model_validator
from typing import Any, List, Literal, Optional, Dict
from datetime import datetime, timezone


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceReference(BaseModel):
    """Compact source metadata stored alongside an answer."""
    title: str = ""
    document_id: str = ""
    snippet: str = Field(default="", description="First ~200 chars of the source content")
    relevance_score: float = 0.0
    url: str = ""
    file_path: str = ""
    section_title: str = ""
    chunk_index: int = 0
    total_chunks: int = 0
    document_title: str = ""


class QAIndexEntry(BaseModel):
    """Compact summary of a single Q&A exchange for the session index."""
    exchange_id: str = Field(description="Unique ID for this exchange")
    question_summary: str = Field(description="One-line summary of the user question")
    answer_summary: str = Field(description="One-line summary of the answer")
    topics: List[str] = Field(default_factory=list, description="Key topics covered")
    source_ids: List[str] = Field(default_factory=list, description="document_ids of sources used for this answer")
    user_intent: Literal["question", "assumption", "verified", "preference", "correction"] = Field(
        default="question",
        description="What the user was doing: asking a question, making an assumption, stating a verified fact, expressing a preference, or correcting the assistant"
    )
    verified: bool = Field(
        default=False,
        description="Whether the information was verified against the knowledge base"
    )
    timestamp: str = Field(description="ISO timestamp of the exchange")


class SessionMemory(BaseModel):
    """Persistent session state stored as JSON on disk."""
    session_id: str
    summary: str = Field(default="", description="Rolling ~200 word session summary")
    qa_index: List[QAIndexEntry] = Field(default_factory=list, description="Compact Q&A index")
    full_answers: Dict[str, Any] = Field(
        default_factory=dict,
        description="exchange_id -> {text: str, sources: List[dict]} or legacy str"
    )
    recent_messages: List[Dict] = Field(
        default_factory=list,
        description="Last N message pairs [{role, content}, ...] stored server-side"
    )
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)
    message_count: int = Field(default=0)

    @model_validator(mode="after")
    def _migrate_legacy_full_answers(self) -> "SessionMemory":
        """Auto-migrate old str values in full_answers to {text, sources} dicts."""
        for key, value in self.full_answers.items():
            if isinstance(value, str):
                self.full_answers[key] = {"text": value, "sources": []}
        return self


class MemoryChatRequest(BaseModel):
    """Request body for the /api/chat/memory endpoint."""
    message: str = Field(description="User message text", max_length=2000)
    session_id: Optional[str] = Field(default=None, description="Existing session ID, or null for new session")
    user_context: Optional[Dict] = Field(default=None, description="Optional user context (role, org, etc.)")
    use_memory: bool = Field(default=True, description="Set to false to skip session memory (tools still active)")
