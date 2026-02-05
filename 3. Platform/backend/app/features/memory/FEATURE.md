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
load_session ──────── loads/creates SessionMemory
  │
  ▼
guardrail_input ───── INPUT GUARDRAIL: PII, injection, toxicity
  │
  ▼
triage_relevance ──── TRIAGE 1: is the message on-topic?
  │
  ▼
triage_faq ────────── TRIAGE 2: does it match a known FAQ?
  │
  ▼
triage_intent ─────── TRIAGE 3: classify intent, final routing decision
  │
  ├── skip_llm=True ──► bundle_triage_response ── sets assistant_text from triage
  │                            │
  ├── skip_llm=False           │
  │                            │
  ▼                            │
build_prompt                   │
  │                            │
  ▼                            │
┌─► call_llm                   │
│     │                        │
│     ├── tool_calls? ──► execute_tools
│     │                       │
│     └── no ───────────┐     │
│                       │     │
└───────────────────────┘     │
                              ▼
                        bundle_sources
                              │
                              ▼
                      validate_sources
                              │
                              ▼
                       validate_tone
                              │
                              ▼                ▼
                       guardrail_output ◄──────┘  OUTPUT GUARDRAIL
                              │
                       ┌── use_memory? ──┐
                       │                 │
                       ▼                 │
                 update_memory           │
                       │                 │
                       ▼                 │
                  save_session           │
                       │                 │
                       ▼                 │
                 format_response ◄───────┘
                       │
                       ▼
                      END
```

**Triage short-circuit:** Any triage node (or the input guardrail) can set `triage["skip_llm"] = True` to bypass the entire LLM pipeline. The remaining triage nodes pass through when this is set. The graph still runs `guardrail_output` → memory → response, so the conversation history stays complete.

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

    # --- Triage (set by guardrail/triage nodes, before LLM) ---
    triage: dict                    # {route, skip_llm, early_response, triage_log}

    # --- Validation (set by post-LLM validators + output guardrail) ---
    source_validation: dict         # {grounded, issues, confidence}
    tone_validation: dict           # {appropriate, original_text, adjustments}
    output_guardrail: dict          # {safe, issues, original_text}

    # --- Internal ---
    tool_rounds: int                # loop counter
```

Key: `retrieved_sources` uses `operator.add` — each tool round **appends** sources, they accumulate automatically.

### Node responsibilities

| Node | Reads from state | Writes to state |
|------|-----------------|-----------------|
| `load_session` | session_id, use_memory | session |
| `guardrail_input` | message, triage | triage (may set skip_llm) |
| `triage_relevance` | message, triage | triage (may set skip_llm) |
| `triage_faq` | message, triage | triage (may set skip_llm) |
| `triage_intent` | message, triage | triage (may set skip_llm) |
| `bundle_triage_response` | triage | assistant_text, exchange_id, unique_sources, source_ids |
| `build_prompt` | session, message, user_context | messages, retrieved_sources (init), tool_rounds (init) |
| `call_llm` | messages | messages (AI response appended), tool_rounds |
| `execute_tools` | messages (tool_calls), session | messages (ToolMessages), retrieved_sources |
| `bundle_sources` | retrieved_sources, messages | unique_sources, source_ids, assistant_text, exchange_id |
| `validate_sources` | assistant_text, unique_sources | source_validation |
| `validate_tone` | assistant_text | assistant_text (if rewritten), tone_validation |
| `guardrail_output` | assistant_text | assistant_text (if blocked), output_guardrail |
| `update_memory` | session, message, assistant_text, exchange_id, source_ids | session (updated) |
| `save_session` | session | (side-effect: writes to disk) |
| `format_response` | assistant_text, unique_sources, session, validations, triage | response |

### Guardrails & Triage nodes

All guardrail and triage nodes are defined in `validators.py` as factory functions. They are **placeholder implementations** — replace the commented example code with your own logic.

#### Input guardrail (`guardrail_input`)
First line of defence. Checks for PII, prompt injection, toxic content before any processing. Can block the message entirely by setting `skip_llm=True`.

#### Triage nodes (run sequentially, can short-circuit)

| Node | Purpose | Example trigger |
|------|---------|----------------|
| `triage_relevance` | Is the message on-topic for the domain? | "what's the weather?" → off-topic |
| `triage_faq` | Does it match a known FAQ entry? | "wat zijn de openingstijden?" → FAQ hit |
| `triage_intent` | Classify intent, final routing decision | "hallo" → chitchat, skip LLM |

Each node checks `_triage_already_decided()` — if a prior node set `skip_llm=True`, it passes through immediately.

### Post-LLM validation nodes

Two validation nodes run **after** the LLM produces an answer.

#### validate_sources
Checks whether the answer is grounded in the retrieved source documents. Returns a `source_validation` dict with `grounded` (bool), `issues` (list), and `confidence` (float).

#### validate_tone
Checks whether the tone matches guidelines. Can **rewrite** `assistant_text` if the tone is inappropriate. Returns `tone_validation` with `appropriate` (bool), `original_text` (str if rewritten), and `adjustments` (list).

#### Output guardrail (`guardrail_output`)
Last gate before memory update. Checks for leaked system prompts, PII in the response, hallucinated URLs. Can replace `assistant_text` with a safe fallback. Returns `output_guardrail` with `safe` (bool), `issues` (list), and `original_text` (str if replaced).

All are defined in `validators.py` as factory functions. See [Replacing validators](#replacing-validators) below.

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
- `validators.py` – guardrail + triage + validation node factories (see table above)
- `graph.py` – ChatState, all node functions, conditional edges, `build_chat_graph()`
- `memory_service.py` – thin wrapper: creates ChatOpenAI + graph, exposes `chat()`
- `routers/memory_chat.py` – POST `/api/chat/memory` endpoint

## How to add a new node (plug-and-play)

### Add a 4th triage validator:
```python
# In validators.py:
def make_triage_language_node():
    async def triage_language(state: dict) -> dict:
        if _triage_already_decided(state):
            return {}
        triage = dict(state.get("triage") or _default_triage())
        # your language detection logic here
        return {"triage": triage}
    return triage_language

# In graph.py — insert between triage_intent and the conditional edge:
graph.add_node("triage_language", triage_language)
graph.add_edge("triage_intent", "triage_language")
graph.add_conditional_edges("triage_language", _should_call_llm, {...})
```

### Add a "compliance check" after the response:
```python
graph.add_node("compliance_check", compliance_check_node)
graph.add_edge("format_response", "compliance_check")
graph.add_edge("compliance_check", END)
# remove old edge: format_response → END
```

### Replacing validators

The validator nodes in `validators.py` are example implementations. To replace them, write a new factory function with the same input/output contract:

```python
# Example: replace source validation with embedding similarity
def make_my_source_validator(embedding_model):
    """
    Input (reads from state):
        assistant_text : str
        unique_sources : list[dict]   (each has "snippet")

    Output (writes to state):
        source_validation : dict
            {"grounded": bool, "issues": list[str], "confidence": float}
    """
    async def validate_sources(state: dict) -> dict:
        answer_emb = embedding_model.embed(state["assistant_text"])
        source_embs = [embedding_model.embed(s["snippet"]) for s in state["unique_sources"]]
        max_sim = max(cosine_sim(answer_emb, se) for se in source_embs)
        return {
            "source_validation": {
                "grounded": max_sim > 0.7,
                "issues": [] if max_sim > 0.7 else ["Low similarity to sources"],
                "confidence": max_sim,
            }
        }
    return validate_sources

# Example: replace tone validation with regex rules
def make_my_tone_validator():
    """
    Input (reads from state):
        assistant_text : str

    Output (writes to state):
        assistant_text  : str           (original or rewritten)
        tone_validation : dict
            {"appropriate": bool, "original_text": str|None, "adjustments": list[str]}
    """
    import re
    async def validate_tone(state: dict) -> dict:
        text = state["assistant_text"]
        adjustments = []
        original = text

        # Remove trailing questions
        if re.search(r'\?["\s]*$', text):
            text = re.sub(r'\s*[^.!?]*\?["\s]*$', '', text)
            adjustments.append("Removed trailing question")

        # Remove emoji
        if re.search(r'[\U0001F600-\U0001F64F]', text):
            text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)
            adjustments.append("Removed emoji")

        changed = text != original
        return {
            "assistant_text": text,
            "tone_validation": {
                "appropriate": not changed,
                "original_text": original if changed else None,
                "adjustments": adjustments,
            },
        }
    return validate_tone
```

Then swap them in `build_chat_graph()`:
```python
validate_sources = make_my_source_validator(embedding_model)
validate_tone = make_my_tone_validator()
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
Response includes `validation` and `triage` fields:
```json
{
  "main_answer": "...",
  "knowledge_sources": [...],
  "session_id": "...",
  "validation": {
    "sources": {"grounded": true, "issues": [], "confidence": 0.92},
    "tone": {"appropriate": true, "original_text": null, "adjustments": []},
    "output_guardrail": {"safe": true, "issues": [], "original_text": null}
  },
  "triage": {
    "route": "llm",
    "skip_llm": false,
    "early_response": null,
    "triage_log": ["guardrail_input: PASS", "triage_relevance: PASS", "triage_faq: NO MATCH", "triage_intent: ROUTE → llm"]
  }
}
```

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
3. Response includes `validation.sources`, `validation.tone`, and `validation.output_guardrail`
4. Response includes `triage` with `route`, `skip_llm`, and `triage_log`
5. `triage_log` shows all guardrail/triage nodes that ran
6. Session JSON file has `full_answers` entries with `{"text": ..., "sources": [...]}`
7. Follow-up question → LLM references previous context
8. QA index entry has `source_ids` populated for exchanges that used RAG search
9. Say "niet X, alleen Y" → session summary updates
10. Ask "wat hadden we eerder besproken" → LLM calls `lookup_past_conversation`
11. Load an existing (old-format) session → no errors (backwards compat auto-migration)
12. Send with `use_memory: false` → memory nodes are skipped, validators still run
13. If tone is rewritten → `validation.tone.original_text` contains original, `main_answer` has rewrite
14. Memory stores the rewritten text (not the original)
15. When a triage node sets `skip_llm=True` → LLM is not called, but memory is still updated
16. When input guardrail blocks → response contains the early_response text, `triage.route` is "blocked"
