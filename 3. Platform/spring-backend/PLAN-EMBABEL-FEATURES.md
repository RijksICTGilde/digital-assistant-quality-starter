# Plan: Advanced Embabel Features Implementation

This plan outlines how to better leverage Embabel's GOAP agent framework capabilities to showcase AI output quality improvements for the hackathon.

---

## Current State

Previously using:
- `@Agent` - Single QualityAssuranceAgent
- `@Action` - 5 linear actions in fixed pipeline
- `@AchievesGoal` - Final assembly step
- Basic blackboard with typed domain objects
- `AgentPlatform.invoke()` for synchronous execution

**Now also using (after Quick Wins):**
- ✅ `@Condition` - `needsImprovement()` and `qualityPassed()` methods
- ✅ SSE streaming - `/api/chat/stream` endpoint
- ✅ LLM role configuration in `application.yml`

Not yet using:
- Sub-processes / nested agents
- Parallel patterns (ScatterGather, Consensus)
- Human-in-the-loop (process pausing)
- StuckHandler for self-recovery (API differs from docs)
- RepeatUntilAcceptable for iterative improvement

---

## Quick Wins (IMPLEMENTED ✅)

### 1. @Condition for Dynamic Planning ✅ DONE
**File:** `agent/QualityAssuranceAgent.kt`

Added condition methods that GOAP can use to evaluate state:

```kotlin
@Condition
fun needsImprovement(evaluation: QualityEvaluation): Boolean =
    !evaluation.passed || evaluation.hallucinationDetected

@Condition
fun qualityPassed(evaluation: QualityEvaluation): Boolean =
    evaluation.passed && !evaluation.hallucinationDetected
```

**Note:** Embabel 0.3.3 `@Condition` has no `description` parameter. Conditions are logged when evaluated.

**Benefit:** Demonstrates GOAP's condition evaluation for dynamic planning.

### 2. SSE Streaming for Real-Time Progress ✅ DONE
**File:** `controller/ChatStreamController.kt`

Added SSE endpoint for real-time quality pipeline progress:

```kotlin
@PostMapping("/chat/stream", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun streamChat(@RequestBody request: ChatMessage): Flux<StreamEvent>
```

**Events emitted:**
- `pipeline_start` - Pipeline begins
- `action_start` / `action_complete` - Each step with progress (1/5, 2/5, etc.)
- `quality_score` - Individual dimension scores
- `improvement` - When response was improved
- `complete` - Final result with full response
- `error` - If something fails

**Frontend TODO:** Connect to `/api/chat/stream` for live progress display.

**Benefit:** Transparent quality process visible to users in real-time.

### 3. StuckHandler for Self-Recovery ⏸️ DEFERRED
**Status:** The `StuckHandler` interface exists in Embabel but the package path differs from documentation (`com.embabel.agent.core.hitl.*` not found in 0.3.3).

**Workaround:** Current implementation handles failures gracefully in `improveResponse` action.

**Future:** When correct API is clarified, implement graceful degradation.

### 4. LLM Mixing (Model Roles) ✅ DONE
**File:** `resources/application.yml`

Configured role-based model selection:

```yaml
embabel:
  models:
    llms:
      generator: llama-3.3-70b-instruct
      evaluator: llama-3.3-70b-instruct
      improver: llama-3.3-70b-instruct
```

**Note:** All roles currently use same GreenPT model. When multiple models available, use `context.ai().withLlmByRole("evaluator")`.

**Benefit:** Infrastructure ready for cost/quality optimization.

---

## Medium Effort Features (Future)

### 5. Iterative Improvement ✅ DONE
**Effort:** 2 hours

Implemented iterative improvement that repeats until quality passes (max iterations configurable):

```kotlin
@Action(description = "Iteratively improve until quality threshold met")
fun iterativeImprovement(
    request: ChatMessage,
    initial: InitialResponse,
    ragContext: RagContext,
    context: ActionContext
): ImprovedResponse {
    return RepeatUntilAcceptable.builder<ResponseDraft, QualityScore>()
        .initialValue(ResponseDraft(initial.mainAnswer))
        .improver { draft -> improveDraft(draft, context) }
        .evaluator { draft -> evaluateDraft(draft, context) }
        .acceptanceCriteria { score -> score.allDimensionsPass() }
        .maxIterations(3)
        .build()
        .run(context)
}
```

**Benefit:** Shows quality improvement loop - directly addresses hackathon's "improve quality" requirement.

### 6. ScatterGather for Parallel Quality Evaluation
**Effort:** 2 hours

Evaluate all 4 quality dimensions in parallel:

```kotlin
@Action(description = "Evaluate quality dimensions in parallel")
fun parallelEvaluation(
    response: InitialResponse,
    ragContext: RagContext,
    context: ActionContext
): QualityEvaluation {
    return ScatterGatherBuilder
        .returning(QualityEvaluation::class.java)
        .fromElements(DimensionScore::class.java)
        .inputs(listOf(RELEVANCE, TONE, COMPLETENESS, POLICY_COMPLIANCE))
        .generatedBy { dim -> evaluateSingleDimension(dim, response, context) }
        .consolidatedBy { scores -> mergeIntoEvaluation(scores) }
        .asSubProcess(context)
}
```

**Benefit:** Faster evaluation, showcases parallel processing.

---

## Bigger Features (Future)

### 7. Multiple Specialized Agents
**Effort:** 3 hours

Create domain-specific agents, let Embabel route automatically:

```kotlin
@Agent(description = "Handles compliance questions about GDPR, AI Act, WOO")
class ComplianceAgent { ... }

@Agent(description = "Handles technical AI implementation questions")
class TechnicalAgent { ... }

@Agent(description = "Handles general digital transformation questions")
class GeneralAgent { ... }
```

**Benefit:** Specialized quality per domain - routing improves answer quality.

### 8. Human-in-the-Loop with Process Pausing
**Effort:** 3 hours

For low-confidence or sensitive topics, pause for human review:

```kotlin
@Action(description = "Request human review for sensitive content")
fun requestHumanReview(
    evaluation: QualityEvaluation,
    context: ActionContext
): HumanReviewedResponse {
    if (evaluation.scores[POLICY_COMPLIANCE]!! < 0.5) {
        context.pause(
            reason = "Low policy compliance - needs human verification",
            data = mapOf("evaluation" to evaluation)
        )
    }
    return HumanReviewedResponse(...)
}
```

Requires:
- Admin dashboard endpoint to list paused processes
- Approve/reject UI
- Resume process API

**Benefit:** Directly addresses bonus criterion "human-in-the-loop feedback".

### 9. ConsensusBuilder for Multi-Evaluator Agreement
**Effort:** 2 hours

Have multiple "evaluators" agree on quality scores:

```kotlin
return ConsensusBuilder
    .returning(QualityEvaluation::class.java)
    .withParticipants(3)
    .evaluatedBy { context.ai().withDefaultLlm().createObject(...) }
    .consensusStrategy(ConsensusStrategy.MAJORITY)
    .build()
    .run(context)
```

**Benefit:** More reliable quality scores through consensus.

### 10. ContextRepository for Quality History
**Effort:** 2 hours

Persist quality evaluations across sessions for learning:

```kotlin
@Autowired
lateinit var contextRepository: ContextRepository

// In assembleFinalResponse
contextRepository.save(
    contextId = "quality-history-${LocalDate.now()}",
    data = QualityHistoryEntry(request, evaluation, improved)
)
```

**Benefit:** Enables quality trend analysis in admin dashboard.

---

## Implementation Priority

| Priority | Feature               | Effort  | Status       | Hackathon Impact   |
|----------|-----------------------|---------|--------------|---------------------|
| 1        | @Condition for GOAP   | 30 min  | ✅ DONE      | Shows planning      |
| 2        | SSE streaming         | 1 hour  | ✅ DONE      | User transparency   |
| 3        | LLM role config       | 30 min  | ✅ DONE      | Cost optimization   |
| 4        | StuckHandler          | 30 min  | ⏸️ Deferred  | Robustness          |
| 5        | Iterative Improvement | 2 hours | ✅ DONE      | Quality iteration   |
| 6        | Human-in-the-loop     | 3 hours | TODO         | Governance          |
| 7        | Multiple agents       | 3 hours | TODO         | Specialization      |

---

## Testing

After implementing, verify with:

```bash
# Run existing tests
./mvnw test

# Manual test - should see GOAP planning in logs
curl -X POST http://localhost:8080/api/chat/structured \
  -H "Content-Type: application/json" \
  -d '{"message": "Wat is de AI Act?", "context": {}}'

# SSE streaming test (if implemented)
curl -N http://localhost:8080/api/chat/stream?message=test
```

---

## References

- [Embabel User Guide](https://docs.embabel.com/embabel-agent/guide/0.3.0/)
- [Embabel GitHub](https://github.com/embabel/embabel-agent)
- [Rod Johnson's Embabel Update](https://medium.com/@springrod/embabel-year-end-update-building-the-best-agent-framework-25ed98728e79)
