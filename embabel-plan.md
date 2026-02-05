# Plan: Spring Boot + Embabel Backend (alongside Python)

## Why This Wins the Hackathon

Embabel's GOAP (Goal-Oriented Action Planning) models the quality pipeline as typed actions that the planner chains automatically:
`Generate → Evaluate Quality → Improve → Assemble`. Each step is auditable, the planning is deterministic (non-LLM), and quality scores are measurable — hitting every mandatory criterion.

## Architecture

```
Frontend (port 3000) → Vite proxy → Spring Boot (port 8080)
                                   ↘ Python stays on 8000 for A/B demo

Spring Boot flow per request:
  ChatRequest
    → [RetrieveRAGContext] → RagContext
    → [GenerateInitialResponse] → InitialResponse  (the "before")
    → [EvaluateQuality] → QualityEvaluation (scores per dimension)
    → [ImproveResponse] → ImprovedResponse          (the "after")
    → [AssembleFinalResponse] → QualityAssuredResponse (@AchievesGoal)
```

GOAP plans this sequence automatically from type signatures. No hardcoded state machine.

## Phase 1: Scaffold Spring Boot project (~30 min)

Create `3. Platform/spring-backend/` with:

- **pom.xml**: Spring Boot 3.5.x + Embabel 0.3.0 + Spring AI OpenAI starter + Jackson Kotlin
- **application.yml**: GreenPT config (`base-url: https://api.greenpt.ai/v1/`, chat model: `llama-3.3-70b-instruct`, embedding model: `green-embedding`), port 8080, quality thresholds
- **GemeenteQualityApplication.kt**: `@SpringBootApplication` + `@EnableAgents`

Key deps (Embabel 0.2.0+ is on Maven Central, no custom repo needed):
```xml
com.embabel.agent:embabel-agent-starter:0.3.0
com.embabel.agent:embabel-agent-starter-openai:0.3.0
org.springframework.boot:spring-boot-starter-web
org.springframework.ai:spring-ai-openai-spring-boot-starter
com.fasterxml.jackson.module:jackson-module-kotlin
```

## Phase 2: Domain models (~30 min)

`model/Enums.kt` — All enums with `@JsonValue` for exact string serialization:
- UserRole: "digital-guide", "civil-servant", etc.
- ConfidenceLevel, ComplexityLevel, ResponseType, RegulationType, FocusArea

`model/ChatRequest.kt` — ChatMessage, UserContext (matching frontend JSON exactly)

`model/ChatResponse.kt` — StructuredAIResponse with `@JsonProperty` snake_case annotations + new quality fields:
- `quality_scores: Map<String, Double>` — per-dimension scores
- `quality_trace: List<QualityTraceEntry>` — action-by-action audit trail
- `quality_improved: Boolean` — was the response improved?
- `quality_explanation: String` — Dutch-language summary for non-technical users

These extra fields are additive — frontend ignores unknown fields, so backward-compatible.

## Phase 3: RAG system with Spring AI (~45 min)

`rag/DocumentLoaderService.kt`:
- Loads 320 markdown files from `../../1. Datasets/Scrapen/scraped_content/content/`
- Uses Spring AI `TokenTextSplitter` (800 tokens, 100 overlap)
- Stores in `SimpleVectorStore` (in-memory, no external DB needed)
- Embeddings via GreenPT `green-embedding` model (2560 dimensions), chat via `llama-3.3-70b-instruct`
- Caches to `spring-backend/cache/vector-store.json` via `SimpleVectorStore.save()`

`rag/RagSearchService.kt`:
- `searchDocuments(query, maxResults)` → similarity search
- `getRoleSpecificDocuments(role)` → keyword-based search
- `getComplianceDocuments(regulation)` → regulation-based search
- `getStatistics()` → document/chunk counts

## Phase 4: Embabel Quality Agent (~1.5 hours) — THE CORE

`agent/domain/QualityDomain.kt` — Typed blackboard objects:
- `ChatRequest` → input
- `RagContext` → after RAG retrieval
- `InitialResponse` → after first LLM call
- `QualityEvaluation` → scores for 4 dimensions
- `ImprovedResponse` → optionally improved text
- `QualityAssuredResponse` → final goal

`agent/QualityAssuranceAgent.kt` — The agent with 5 `@Action` methods:

1. **retrieveContext**(ChatRequest, OperationContext) → RagContext
2. **generateInitialResponse**(ChatRequest, RagContext, OperationContext) → InitialResponse
3. **evaluateQuality**(ChatRequest, InitialResponse, RagContext, OperationContext) → QualityEvaluation
   - Uses LLM-as-Judge to score 4 dimensions (0.0-1.0):
     - **Relevance**: Does it answer the question?
     - **Tone**: Professional, neutral, appropriate for government?
     - **Completeness**: Sources cited? Action items provided?
     - **Policy Compliance**: Relevant laws/regulations correctly referenced?
   - Configurable thresholds in application.yml
4. **improveResponse**(ChatRequest, InitialResponse, QualityEvaluation, RagContext, OperationContext) → ImprovedResponse
   - Only fires if any dimension below threshold
   - Sends improvement directions to LLM with original response
5. **assembleFinalResponse**(...) → QualityAssuredResponse `@AchievesGoal`
   - Merges quality metadata into StructuredAIResponse
   - Builds Dutch-language quality explanation

### Verified Embabel API patterns:
```kotlin
// LLM calls inside @Action methods:
context.ai().withDefaultLlm().generateText(prompt)         // plain text
context.ai().withDefaultLlm().createObject(prompt, T::class.java) // typed object

// Invoking agent from REST controller:
val invocation = AgentInvocation.builder(agentPlatform)
    .build(QualityAssuredResponse::class.java)
invocation.invoke(chatRequest)  // input goes on blackboard automatically
```

### GreenPT model selection (verified):
- **Chat model: `llama-3.3-70b-instruct`** — supports system prompts, required for Embabel's `createObject()` which injects system prompts for typed JSON output
- **`green-l` does NOT work with Embabel** — no system prompt support, `createObject()` will fail
- **`green-s` is broken** on GreenPT ("Unsupported model type")
- **Embedding model: `green-embedding`** (2560 dimensions) — works fine for RAG
- Configure GreenPT as custom LLM via `OpenAiCompatibleModelFactory` if `withDefaultLlm()` doesn't pick up `application.yml` settings

## Phase 5: REST Controllers (~30 min)

`controller/ChatController.kt`:
- `POST /api/chat/structured` → uses `AgentInvocation.builder(agentPlatform).build(QualityAssuredResponse::class.java).invoke(request)`

`controller/KnowledgeController.kt`:
- `GET /api/knowledge/search`, `/role/{role}`, `/compliance/{regulation}`, `/stats`, `/document/{id}`
- `GET /api/enhanced-rag/document/{id}`, `/enhanced-rag/context`

`controller/HealthController.kt`:
- `GET /api/health`, `/api/ready`, `/api/live`

All paths match the Python backend exactly. Frontend needs zero changes except proxy port.

## Phase 6: Frontend integration (~15 min)

Change `3. Platform/vite.config.js` proxy target from `8000` to `8080`. Both backends can run simultaneously for A/B comparison during the demo.

## Phase 7: Verification

1. `cd "3. Platform/spring-backend" && ./mvnw spring-boot:run`
2. `curl http://localhost:8080/api/health` — verify healthy
3. `curl http://localhost:8080/api/knowledge/stats` — verify RAG loaded
4. Send structured chat request, verify response has `quality_scores`, `quality_trace`, `quality_explanation`
5. Send same request to Python backend (port 8000) — compare before/after for hackathon demo

## File List (~15 files)

```
3. Platform/spring-backend/
  pom.xml
  src/main/kotlin/com/gemeente/quality/
    GemeenteQualityApplication.kt
    model/
      Enums.kt
      ChatRequest.kt
      ChatResponse.kt
    rag/
      RagDocument.kt
      DocumentLoaderService.kt
      RagSearchService.kt
    agent/
      domain/QualityDomain.kt
      QualityAssuranceAgent.kt
      QualityEvaluationParser.kt
    service/
      ContextPromptBuilder.kt
    controller/
      ChatController.kt
      KnowledgeController.kt
      HealthController.kt
  src/main/resources/
    application.yml
```

## Key Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| GreenPT `green-l` no system prompts | Use `llama-3.3-70b-instruct` for Embabel (supports system prompts); keep `green-embedding` for RAG |
| Embedding startup time (320 docs) | Cache to JSON file, load on subsequent runs |
| 3 LLM calls per request (generate + evaluate + improve) | Evaluation prompt kept concise; improvement only when needed |
| JSON field name mismatch | `@JsonProperty` on every field + global `SNAKE_CASE` strategy |
| Embabel/Spring AI version conflicts | Use Embabel's transitive Spring AI deps, don't override |
