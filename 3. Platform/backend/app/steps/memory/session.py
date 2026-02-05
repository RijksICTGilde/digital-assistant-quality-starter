"""Session load/save step nodes."""

from __future__ import annotations

from loguru import logger

from app.features.memory.session_store import SessionStore
from app.steps.state import ChatState


def make_load_session(session_store: SessionStore):
    """Returns the load_session node."""

    def load_session(state: ChatState) -> dict:
        session_id = state.get("session_id", "")
        use_memory = state.get("use_memory", True)
        logger.info(f"[NODE:load_session] ▶ session_id='{session_id}', use_memory={use_memory}")

        if use_memory and session_id and session_store.exists(session_id):
            session = session_store.load(session_id)
            if session is not None:
                logger.info(
                    f"[NODE:load_session] ✓ Loaded existing session {session.session_id} "
                    f"(msgs: {session.message_count}, qa_index: {len(session.qa_index)}, "
                    f"recent: {len(session.recent_messages)})"
                )
                return {"session": session.model_dump()}

        session = session_store.create()
        logger.info(
            f"[NODE:load_session] ✓ Created new session {session.session_id} "
            f"(memory={'ON' if use_memory else 'OFF'})"
        )
        return {"session": session.model_dump()}

    return load_session


def make_save_session(session_store: SessionStore):
    """Returns the save_session node."""

    def save_session(state: ChatState) -> dict:
        from app.features.memory.models import SessionMemory

        session_data = state["session"]
        session = SessionMemory(**session_data)
        session_store.save(session)
        logger.info(
            f"[NODE:save_session] ✓ {session.session_id} "
            f"(summary: {len(session.summary)} chars, "
            f"qa_index: {len(session.qa_index)}, "
            f"recent: {len(session.recent_messages)}, "
            f"full_answers: {len(session.full_answers)})"
        )
        return {}

    return save_session
