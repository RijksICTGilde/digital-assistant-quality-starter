We # CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Dutch Government AI Hackathon starter kit for building municipal AI assistants. Uses GreenPT (a privacy-focused, OpenAI-compatible API) with RAG over 320+ government documents covering AI Act, GDPR, NORA, GEMMA, and other Dutch public sector standards.

## Important: Directory Names Have Spaces

All top-level directories have spaces in their names. Always quote paths:
```bash
cd "3. Platform/backend"    # correct
cd 3. Platform/backend      # WILL FAIL
```

## Commands

### Frontend (from `3. Platform/`)
```bash
npm run dev       # Start Vite dev server on port 3000
npm run build     # Production build
npm run lint      # ESLint
npm run preview   # Preview production build
```

### Backend (from `3. Platform/backend/`)
```bash
source venv/bin/activate    # Activate Python venv (already created)
python start.py             # Start FastAPI with auto-reload on port 8000
```

Or directly:
```bash
source venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

### Installing Dependencies
```bash
# Frontend (from "3. Platform/")
npm install

# Backend (from "3. Platform/backend/")
source venv/bin/activate && pip install -r requirements.txt
```

## Architecture

### Two-Service Stack
- **Frontend:** React 18 + Vite (port 3000) — Vite proxies `/api` requests to backend
- **Backend:** Python FastAPI (port 8000) — serves all API routes under `/api/`

### Frontend Flow (App.jsx)
Four-step wizard: `LANDING -> ORGANIZATION -> INFO -> CHAT`

1. `ChatbotLanding` — user selects a topic (waarom/wat/hoe)
2. `OrganizationSelector` — user picks organization type
3. `InfoPages` — information display with option to enter chat
4. `EnhancedChatInterface` — main chat UI, uses `enhanced_api.js` to call `/api/chat/structured`

User context (`selectedChoice`, `selectedOrganization`, `role`) flows through as props. The `enhanced_api.js` service maps the frontend context to backend `UserRole` enum values before sending.

### Backend Request Pipeline
1. `POST /api/chat/structured` receives `ChatMessage` (message + `UserContext`)
2. `EnhancedOpenAIService.generate_structured_response()`:
   - Queries `EnhancedRAGServiceWrapper` for relevant document chunks (FAISS vector search)
   - Builds context prompt with top 3 relevant docs + user role/phase info
   - Calls GreenPT API (OpenAI-compatible) with enhanced system prompt
   - Converts response to `StructuredAIResponse` with sources, action items, confidence, follow-ups
3. Response type is always `StructuredAIResponse` (other types like `ComplianceAnalysis`, `TechnicalGuidance` are defined but currently unused)

### RAG System
- `enhanced_rag.py` (in `3. Platform/`) — core RAG: loads markdown docs, chunks them, generates OpenAI embeddings, builds FAISS index
- `enhanced_rag_service.py` (in backend services) — wrapper that integrates RAG into FastAPI
- Documents source: `1. Datasets/Scrapen/scraped_content/content/` (320 markdown files)
- Embeddings are cached in `3. Platform/backend/cache/`
- Uses `text-embedding-3-small` model via OpenAI API

### Key Data Models (backend)
- `UserRole` enum: `digital-guide`, `civil-servant`, `it-manager`, `project-manager`, `developer`, `other`
- `ChatMessage`: message (max 2000 chars) + `UserContext` + timestamp
- `StructuredAIResponse`: main_answer (markdown) + knowledge_sources + action_items + compliance_checks + follow_up_suggestions + confidence/complexity levels + escalation flags

### Demo Mode
Set `DEMO_MODE=true` in backend `.env` to run without a real API key. Returns hardcoded structured responses for compliance, technical, and general queries.

## Environment Configuration

### Backend (`3. Platform/backend/.env`)
- `GREENPT_API_KEY` — **required** (or set `DEMO_MODE=true`)
- `GREENPT_BASE_URL` — defaults to `https://api.greenpt.ai/v1/`
- `GREENPT_MODEL` — defaults to `gpt-4o-2024-08-06`
- `GREENPT_MAX_TOKENS` — defaults to `2000`
- `GREENPT_TEMPERATURE` — defaults to `0.3`

### Frontend (`3. Platform/.env`)
- `VITE_API_URL` — defaults to `http://localhost:8000`

## Tailwind Theme
Custom color system under `chatbot` namespace: `chatbot-primary` (#0E0076), `chatbot-secondary` (#5EA0F7), `chatbot-dark`, `chatbot-light`, `chatbot-neutral-{50-900}`. All UI components use these tokens.

## API Endpoints
- `POST /api/chat/structured` — main chat (accepts `ChatMessage` body)
- `GET /api/knowledge/search?query=...` — direct RAG search
- `GET /api/knowledge/role/{role}` — role-specific documents
- `GET /api/knowledge/compliance/{regulation}` — compliance docs (gdpr, ai_act, woo, etc.)
- `GET /api/knowledge/stats` — RAG system statistics
- `GET /api/knowledge/document/{id}` — view specific document chunk
- `GET /api/health` — health check (includes RAG status)
- `GET /docs` — Swagger UI (development only)

## Language
The application UI and AI responses are in **Dutch**. Code comments and variable names mix Dutch and English.
