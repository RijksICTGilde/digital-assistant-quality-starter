# Conversation Memory & Tool Use (LangGraph)

## What it does
Adds persistent conversation memory and LLM-driven tool use to the chat system. The LLM can autonomously search the knowledge base, look up past conversation topics, and retrieve earlier answers. The entire flow is implemented as a **LangGraph** state graph for composability.

## Architecture

### LangGraph State Graph

The chat flow is a compiled LangGraph `StateGraph`. Every node is a plain function that reads from and writes to a shared `ChatState` TypedDict.

```
START
  │
  ▼
load_session ─── loads/creates SessionMemory
  │
  ▼
build_prompt ─── 3-layer system prompt → LangChain messages
  │
  ▼
┌─► call_llm ──── ChatOpenAI with bound tools
│     │
│     ├── tool_calls? ──► execute_tools ── runs tools, accumulates sources
│     │                       │
│     └── no ──────────► bundle_sources ── dedup retrieved_sources
│                              │
└─────────────────────────┘    ▼
                      ┌── use_memory? ──┐
                      │                 │
                      ▼                 ▼
                update_memory     format_response
                      │                 │
                      ▼                 │
                save_session            │
                      │                 │
                      ▼                 │
                format_response ◄───────┘
                      │
                      ▼
                     END
```

### ChatState (the contract)

Every node receives the full state and returns a partial dict with only the fields it changed. This is the only thing blocks need to agree on.

```python
class ChatState(TypedDict, total=False):
    # --- Input ---
    message: str                    # raw user message
    session_id: str                 # "" for new sessions
    user_context: dict              # {} if none
    use_memory: bool                # whether to persist

    # --- Session ---
    session: dict                   # SessionMemory.model_dump()

    # --- LLM messages (add_messages reducer appends) ---
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Sources (operator.add reducer accumulates across tool rounds) ---
    retrieved_sources: Annotated[list, operator.add]

    # --- Output ---
    assistant_text: str
    exchange_id: str
    unique_sources: list
    source_ids: list
    response: dict                  # final API response
    tool_rounds: int                # internal loop counter
```

Key: `retrieved_sources` uses `operator.add` — each tool round **appends** sources, they accumulate automatically.

### Node responsibilities

| Node | Reads from state | Writes to state |
|------|-----------------|-----------------|
| `load_session` | session_id, use_memory | session |
| `build_prompt` | session, message, user_context | messages, retrieved_sources (init), tool_rounds (init) |
| `call_llm` | messages | messages (AI response appended), tool_rounds |
| `execute_tools` | messages (tool_calls), session | messages (ToolMessages), retrieved_sources |
| `bundle_sources` | retrieved_sources, messages | unique_sources, source_ids, assistant_text, exchange_id |
| `update_memory` | session, message, assistant_text, exchange_id, source_ids | session (updated) |
| `save_session` | session | (side-effect: writes to disk) |
| `format_response` | assistant_text, unique_sources, session | response |

### 3-Layer Memory
1. **Recent messages** (Layer 1) – last 5 message pairs stored server-side
2. **Session summary** (Layer 2) – rolling ~200-word summary updated after each exchange
3. **Q&A index** (Layer 3) – compact one-line summaries with topic tags

### Source Storage (Q+A+Sources per exchange)
Each exchange is stored as a self-contained unit of (question, answer, sources):
- `full_answers[exchange_id]` → `{"text": str, "sources": List[dict]}`
- `QAIndexEntry.source_ids` → compact list of `document_id` strings
- `SourceReference` model — defines the compact source metadata shape

### Tool Use
The LLM receives 3 LangChain `@tool`-decorated functions bound via `ChatOpenAI.bind_tools()`:
- `search_knowledge_base(query)` – RAG search across 350+ documents
- `retrieve_past_answer(exchange_id)` – fetch full text of a previous answer
- `lookup_past_conversation(topic)` – keyword search over the Q&A index

Tools are created via `create_tools()` factory which binds dependencies (enhanced_rag, session) via closures.

### Session Storage
JSON files in `backend/sessions/<session_id>.json`. Each file contains: summary, Q&A index, full answers dict (with sources), metadata.

### Backwards Compatibility
- Existing session JSON files auto-migrate on load (model_validator on SessionMemory)
- `QAIndexEntry.source_ids` defaults to `[]`
- No migration script needed

## Files
- `models.py` – Pydantic models (SessionMemory, QAIndexEntry, SourceReference, MemoryChatRequest)
- `session_store.py` – file-based session CRUD
- `tools.py` – LangChain @tool definitions, `create_tools()` factory, `make_execute_tools_node()`
- `graph.py` – ChatState, all node functions, conditional edges, `build_chat_graph()`
- `memory_service.py` – thin wrapper: creates ChatOpenAI + graph, exposes `chat()`
- `routers/memory_chat.py` – POST `/api/chat/memory` endpoint

## How to add a new node (plug-and-play)

### Add a "classify intent" block before the LLM:
```python
def classify_intent(state: ChatState) -> dict:
    # your classification logic
    return {"intent": "factual"}  # add "intent" field to ChatState first

graph.add_node("classify_intent", classify_intent)
graph.add_edge("build_prompt", "classify_intent")
graph.add_edge("classify_intent", "call_llm")
# remove old edge: build_prompt → call_llm
```

### Add a "compliance check" after the response:
```python
graph.add_node("compliance_check", compliance_check_node)
graph.add_edge("format_response", "compliance_check")
graph.add_edge("compliance_check", END)
# remove old edge: format_response → END
```

### Skip RAG for greetings:
```python
graph.add_conditional_edges("classify_intent", route_by_intent, {
    "greeting": "format_greeting",
    "factual": "call_llm",
})
```

## API

### POST /api/chat/memory
```json
{
  "message": "Wat is GDPR?",
  "session_id": null,
  "user_context": {"role": "hoe", "organization": "Gemeente"},
  "use_memory": true
}
```
Response is compatible with `StructuredAIResponse` shape plus a `session_id` field.

## How to test

### curl smoke test
```bash
# First message (creates session)
curl -X POST http://localhost:8000/api/chat/memory \
  -H "Content-Type: application/json" \
  -d '{"message": "Wat zijn de GDPR vereisten voor een chatbot?"}'

# Follow-up (pass session_id from first response)
curl -X POST http://localhost:8000/api/chat/memory \
  -H "Content-Type: application/json" \
  -d '{"message": "Wat hadden we eerder besproken?", "session_id": "<id>"}'
```

### Verification checklist
1. Send message → session file appears in `backend/sessions/`
2. Response includes `knowledge_sources` with populated entries
3. Session JSON file has `full_answers` entries with `{"text": ..., "sources": [...]}`
4. Follow-up question → LLM references previous context
5. QA index entry has `source_ids` populated for exchanges that used RAG search
6. Say "niet X, alleen Y" → session summary updates
7. Ask "wat hadden we eerder besproken" → LLM calls `lookup_past_conversation`
8. Load an existing (old-format) session → no errors (backwards compat auto-migration)
9. Send with `use_memory: false` → memory nodes are skipped
