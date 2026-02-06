import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE any app imports — modules like enhanced_rag.py
# read env vars at import time for embedding config.
# Use explicit path to ensure .env is found regardless of working directory.
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger

from app.routers import chat, health, enhanced_chat
from app.routers import memory_chat
from app.services.openai_service import OpenAIService
from app.services.enhanced_openai_service import EnhancedOpenAIService
from app.features.memory.memory_service import MemoryService
from app.features.faq import FAQService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Gemeente AI Assistant API")
    
    # Initialize OpenAI services
    try:
        # Legacy service for backwards compatibility
        openai_service = OpenAIService()
        app.state.openai_service = openai_service
        logger.info("Legacy OpenAI service initialized successfully")
        
        # Enhanced service with structured outputs
        enhanced_openai_service = EnhancedOpenAIService()
        app.state.enhanced_openai_service = enhanced_openai_service
        logger.info("Enhanced OpenAI service initialized successfully")

        # Initialize FAQ service with the same embedding model used by enhanced_rag
        # This reuses the SentenceTransformer model for efficient FAQ matching
        faq_service = None
        try:
            # Import the local embedding model getter from enhanced_rag
            # enhanced_rag.py is in the parent directory of backend (3. Platform/)
            import sys
            platform_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            if platform_dir not in sys.path:
                sys.path.insert(0, platform_dir)
            logger.info(f"Added {platform_dir} to sys.path for enhanced_rag import")

            from enhanced_rag import get_local_embedding_model
            embedding_model = get_local_embedding_model()
            faq_service = FAQService(embedding_model=embedding_model)
            logger.info(f"FAQ service initialized: {len(faq_service.faqs)} FAQs, {len(faq_service.questions)} questions")
        except Exception as e:
            logger.warning(f"FAQ service initialization failed (non-critical): {e}")
            import traceback
            logger.warning(traceback.format_exc())
            faq_service = None

        # Memory-augmented chat service (creates its own ChatOpenAI from env vars)
        memory_service = MemoryService(
            enhanced_rag=enhanced_openai_service.enhanced_rag,
            faq_service=faq_service,
        )
        app.state.memory_service = memory_service
        logger.info("Memory service initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize OpenAI services: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Gemeente AI Assistant API")

# Create FastAPI application
app = FastAPI(
    title="Gemeente AI Assistant API",
    description="AI-powered assistant for Dutch municipal digital transformation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
        "https://gemeente-ai.nl",  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(enhanced_chat.router, prefix="/api", tags=["enhanced-chat"])
app.include_router(memory_chat.router, prefix="/api", tags=["memory-chat"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for better error responses"""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Er ging iets mis op de server. Probeer het later opnieuw.",
            "needsHumanHelp": True
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Gemeente AI Assistant API", 
        "status": "active",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") != "production" else False,
        log_level="info"
    )