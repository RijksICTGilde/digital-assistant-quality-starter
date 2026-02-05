import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.features.memory.models import SessionMemory


# Default sessions directory relative to backend root
_SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "../../../sessions")


class SessionStore:
    """File-based JSON session CRUD.

    Each session is stored as ``<sessions_dir>/<session_id>.json``.
    """

    def __init__(self, sessions_dir: str = _SESSIONS_DIR):
        self.sessions_dir = os.path.abspath(sessions_dir)
        os.makedirs(self.sessions_dir, exist_ok=True)
        logger.info(f"SessionStore initialised – dir: {self.sessions_dir}")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _path(self, session_id: str) -> str:
        # Sanitise to prevent directory traversal
        safe_id = os.path.basename(session_id)
        return os.path.join(self.sessions_dir, f"{safe_id}.json")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def create(self) -> SessionMemory:
        """Create a brand-new empty session and persist it."""
        session = SessionMemory(session_id=str(uuid.uuid4()))
        self.save(session)
        logger.info(f"Created new session {session.session_id}")
        return session

    def load(self, session_id: str) -> Optional[SessionMemory]:
        """Load a session from disk. Returns None if not found."""
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionMemory(**data)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def save(self, session: SessionMemory) -> None:
        """Persist session to disk."""
        session.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._path(session.session_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")

    def delete(self, session_id: str) -> bool:
        """Delete a session from disk. Returns True if deleted."""
        path = self._path(session_id)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def exists(self, session_id: str) -> bool:
        return os.path.exists(self._path(session_id))
