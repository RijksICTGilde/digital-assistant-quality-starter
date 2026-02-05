# Spring Backend - Quality-Aware AI Assistant

Embabel GOAP-based backend for the DigiCampus Hackathon challenge: "How do we improve the quality of digital assistant output in real time?"

## Quick Start

```bash
cd "3. Platform/spring-backend"

export JAVA_HOME=~/.jdks/ms-21.0.10
export GREENPT_API_KEY=your-api-key-here

./mvnw spring-boot:run
```

Starts on port **8080**. The frontend (port 3000) proxies `/api/*` requests here.

## Architecture

```
Frontend (3000) → Vite Proxy → Spring Boot (8080) → GreenPT API
                                    ↓
                              Embabel GOAP Agent
                                    ↓
                              RAG Vector Store (2052 chunks)
```

## Quality Pipeline (5 Steps)

The Embabel GOAP agent chains these actions automatically:

```
ChatMessage
  → [1. retrieveContext]      → RagContext (search 320 docs)
  → [2. generateInitialResponse] → InitialResponse (LLM call #1)
  → [3. evaluateQuality]      → QualityEvaluation (LLM call #2 - "LLM as Judge")
  → [4. improveResponse]      → ImprovedResponse (LLM call #3, only if needed)
  → [5. assembleFinalResponse] → QualityAssuredResponse (@AchievesGoal)
```

## Quality Dimensions

Each response is scored 0.0-1.0 on 4 dimensions:

| Dimension | Threshold | Description |
|-----------|-----------|-------------|
| **Relevance** | 0.6 | Is the answer based on the provided sources? |
| **Tone** | 0.7 | Professional, neutral, appropriate for government? |
| **Completeness** | 0.5 | Is the information complete? Sources used? |
| **Policy Compliance** | 0.6 | Are laws/regulations correctly referenced? |

If any dimension falls below its threshold, the response is automatically improved.

## Key Files

```
src/main/kotlin/com/gemeente/quality/
├── GemeenteQualityApplication.kt    # Entry point
├── agent/
│   ├── QualityAssuranceAgent.kt     # The 5-step GOAP agent
│   └── domain/QualityDomain.kt      # Typed blackboard objects
├── config/
│   ├── QualityConfig.kt             # Quality thresholds
│   └── RagConfig.kt                 # RAG settings
├── controller/
│   ├── ChatController.kt            # POST /api/chat/structured
│   ├── HealthController.kt          # GET /api/health
│   └── KnowledgeController.kt       # GET /api/knowledge/*
├── model/
│   ├── ChatRequest.kt               # Request DTOs
│   ├── ChatResponse.kt              # Response DTOs with quality fields
│   └── Enums.kt                     # UserRole, QualityDimension, etc.
├── rag/
│   ├── DocumentLoaderService.kt     # Loads 320 markdown files → 2052 chunks
│   └── RagSearchService.kt          # Vector similarity search
└── service/
    └── ContextPromptBuilder.kt      # Prompts for generation/evaluation/improvement
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/structured` | POST | Main chat endpoint with quality scoring |
| `/api/health` | GET | Health check |
| `/api/knowledge/stats` | GET | RAG statistics |
| `/api/knowledge/search?query=...` | GET | Search knowledge base |

## Response Format

```json
{
  "main_answer": "De AI Act is...",
  "confidence_level": "high",
  "knowledge_sources": [...],
  "quality_scores": {
    "relevance": 1.0,
    "tone": 1.0,
    "completeness": 0.8,
    "policy_compliance": 0.9
  },
  "quality_trace": [
    {"action": "generate_initial_response", "timestamp_ms": 1234567890},
    {"action": "evaluate_quality", "dimension": "relevance", "score": 1.0, "passed": true},
    ...
  ],
  "quality_improved": false,
  "quality_explanation": "Dit antwoord heeft de kwaliteitscontrole doorstaan. Scores: relevantie: 100%, toon: 100%, ..."
}
```

## Configuration

Key settings in `src/main/resources/application.yml`:

```yaml
# GreenPT API
embabel:
  models:
    default-llm: llama-3.3-70b-instruct
    default-embedding-model: green-embedding
  agent:
    platform:
      models:
        openai:
          api-key: ${GREENPT_API_KEY}
          base-url: https://api.greenpt.ai

# Quality thresholds
quality:
  thresholds:
    relevance: 0.6
    tone: 0.7
    completeness: 0.5
    policy-compliance: 0.6

# RAG
rag:
  documents-path: ../../1. Datasets/Scrapen/scraped_content/content/
  cache-path: ./cache/vector-store.json
```

## Grounding

The assistant only answers questions based on the RAG knowledge base (320 government documents about digital transformation, AI, regulations). Off-topic questions receive a polite refusal explaining what topics it can help with.

## Tech Stack

- **Spring Boot 3.5.6**
- **Embabel Agent Framework 0.3.3** (GOAP planning)
- **Spring AI 1.1.1** (vector store, embeddings)
- **GreenPT API** (EU-hosted, privacy-focused LLM)
- **Kotlin**
