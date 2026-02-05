from fastapi import APIRouter, Request
from loguru import logger
import time

from app.features.memory.models import MemoryChatRequest
from app.features.memory.memory_service import MemoryService
from app.features.memory.session_store import SessionStore

router = APIRouter()


def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service


@router.post("/chat/memory")
async def memory_chat_endpoint(request: Request):
    """Chat endpoint with conversation memory and tool use."""
    start_time = time.time()

    memory_service: MemoryService = get_memory_service(request)

    try:
        body = await request.json()
        chat_req = MemoryChatRequest(**body)
    except Exception as e:
        logger.error(f"[CHAT] Invalid request: {e}")
        return {
            "main_answer": "Ongeldig verzoek. Controleer je invoer.",
            "response_type": "direct_answer",
            "confidence_level": "low",
            "error": str(e),
        }

    logger.info(
        f"[CHAT] Incoming message: session_id={chat_req.session_id or 'NEW'} "
        f"use_memory={chat_req.use_memory} message={chat_req.message[:80]!r}"
    )

    try:
        result = await memory_service.chat(
            message=chat_req.message,
            session_id=chat_req.session_id,
            user_context=chat_req.user_context,
            use_memory=chat_req.use_memory,
        )
        elapsed = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = elapsed
        logger.info(
            f"[CHAT] Response sent: session_id={result.get('session_id')} "
            f"time={elapsed}ms answer_len={len(result.get('main_answer', ''))}"
        )
        return result

    except Exception as e:
        logger.error(f"[CHAT] Error for session_id={chat_req.session_id}: {e}")
        return {
            "main_answer": "Er ging iets mis bij het verwerken van je bericht. Probeer het opnieuw.",
            "response_type": "direct_answer",
            "confidence_level": "low",
            "needs_human_expert": True,
            "error": str(e),
        }


@router.delete("/chat/memory/{session_id}")
async def delete_session_endpoint(session_id: str, request: Request):
    """Delete a conversation session."""
    logger.info(f"[CHAT] Delete request for session_id={session_id}")
    memory_service: MemoryService = get_memory_service(request)
    store: SessionStore = memory_service.session_store
    deleted = store.delete(session_id)
    if deleted:
        logger.info(f"[CHAT] Session deleted: session_id={session_id}")
        return {"status": "ok", "message": "Sessie verwijderd."}
    logger.warning(f"[CHAT] Session not found for delete: session_id={session_id}")
    return {"status": "not_found", "message": "Sessie niet gevonden."}
