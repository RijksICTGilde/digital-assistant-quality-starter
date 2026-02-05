# Plan: Admin Dashboard & Feedback System

## Overview

Dit plan beschrijft de implementatie van een admin dashboard voor het beheren van de AI-assistent kwaliteit, inclusief user feedback, human-in-the-loop review, en configureerbare parameters.

---

## 1. User Feedback Storage

### Backend

**Nieuw model:** `model/Feedback.kt`
```kotlin
data class FeedbackEntry(
    val id: String = UUID.randomUUID().toString(),
    val messageId: String,
    val timestamp: Instant = Instant.now(),
    val rating: FeedbackRating,  // POSITIVE, NEGATIVE
    val comment: String? = null,
    val originalQuestion: String,
    val response: String,
    val qualityScores: Map<String, Double>,
    val wasImproved: Boolean,
    val hallucinationDetected: Boolean,
    val organizationType: String?
)

enum class FeedbackRating { POSITIVE, NEGATIVE }
```

**Nieuw service:** `service/FeedbackService.kt`
```kotlin
@Service
class FeedbackService {
    private val feedbackStore = mutableListOf<FeedbackEntry>()

    fun saveFeedback(entry: FeedbackEntry)
    fun getFeedbackStats(): FeedbackStats
    fun getFeedbackByRating(rating: FeedbackRating): List<FeedbackEntry>
    fun exportFeedback(): List<FeedbackEntry>
}
```

**Nieuw controller:** `controller/FeedbackController.kt`
```kotlin
@RestController
@RequestMapping("/api/feedback")
class FeedbackController {
    POST /api/feedback              // Submit feedback
    GET  /api/feedback/stats        // Get aggregated stats
    GET  /api/feedback/export       // Export all feedback (CSV/JSON)
}
```

**Persistentie opties:**
- Fase 1: In-memory + JSON file cache (zoals vector store)
- Fase 2: SQLite of PostgreSQL

### Frontend

**Component:** `FeedbackButtons.jsx`
- Thumbs up/down knoppen onder elk AI antwoord
- Optioneel: comment field bij negatieve feedback
- Toast notification bij success

**Integratie in:** `EnhancedChatInterface.jsx`
- Na elke AI response feedback knoppen tonen
- Disable na feedback gegeven

---

## 2. Human Review Queue

### Backend

**Nieuw model:** `model/ReviewQueue.kt`
```kotlin
data class ReviewItem(
    val id: String = UUID.randomUUID().toString(),
    val timestamp: Instant = Instant.now(),
    val status: ReviewStatus,  // PENDING, APPROVED, REJECTED, CORRECTED
    val originalQuestion: String,
    val aiResponse: String,
    val qualityScores: Map<String, Double>,
    val hallucinationDetected: Boolean,
    val flagReason: FlagReason,  // LOW_CONFIDENCE, HALLUCINATION, USER_FLAGGED
    val reviewerNotes: String? = null,
    val correctedResponse: String? = null,
    val reviewedAt: Instant? = null,
    val reviewedBy: String? = null
)

enum class ReviewStatus { PENDING, APPROVED, REJECTED, CORRECTED }
enum class FlagReason { LOW_CONFIDENCE, HALLUCINATION, USER_FLAGGED, EXPERT_REQUIRED }
```

**Nieuw service:** `service/ReviewQueueService.kt`
```kotlin
@Service
class ReviewQueueService {
    fun addToQueue(item: ReviewItem)
    fun getPendingItems(): List<ReviewItem>
    fun approveItem(id: String, reviewerNotes: String?)
    fun rejectItem(id: String, reviewerNotes: String?)
    fun correctItem(id: String, correctedResponse: String, reviewerNotes: String?)
    fun getStats(): ReviewStats
}
```

**Auto-flag triggers in QualityAssuranceAgent:**
```kotlin
// In assembleFinalResponse:
if (evaluation.hallucinationDetected ||
    initialResponse.confidenceLevel == ConfidenceLevel.LOW ||
    initialResponse.needsHumanExpert) {
    reviewQueueService.addToQueue(ReviewItem(...))
}
```

**Controller:** `controller/ReviewController.kt`
```kotlin
@RestController
@RequestMapping("/api/admin/review")
class ReviewController {
    GET  /api/admin/review/pending     // Get pending items
    GET  /api/admin/review/stats       // Get review stats
    POST /api/admin/review/{id}/approve
    POST /api/admin/review/{id}/reject
    POST /api/admin/review/{id}/correct
}
```

### Frontend

**Button in chat:** "Vraag expert beoordeling"
- Zichtbaar bij lage confidence of hallucinatie
- Stuurt naar review queue

---

## 3. Golden Answer Set

### Backend

**Nieuw model:** `model/GoldenAnswer.kt`
```kotlin
data class GoldenAnswer(
    val id: String = UUID.randomUUID().toString(),
    val question: String,
    val answer: String,
    val category: String?,  // e.g., "AI_ACT", "GDPR", "GENERAL"
    val createdAt: Instant = Instant.now(),
    val source: GoldenAnswerSource,  // MANUAL, FROM_REVIEW, FROM_FEEDBACK
    val qualityScores: Map<String, Double>?,
    val isActive: Boolean = true
)

enum class GoldenAnswerSource { MANUAL, FROM_REVIEW, FROM_FEEDBACK }
```

**Service:** `service/GoldenAnswerService.kt`
```kotlin
@Service
class GoldenAnswerService {
    fun addGoldenAnswer(answer: GoldenAnswer)
    fun findSimilar(question: String): GoldenAnswer?  // Vector similarity
    fun getAll(): List<GoldenAnswer>
    fun deactivate(id: String)
    fun importFromReview(reviewItem: ReviewItem)  // When review is approved/corrected
    fun runRegressionTest(): RegressionTestResult
}
```

**Regression testing:**
```kotlin
data class RegressionTestResult(
    val totalTests: Int,
    val passed: Int,
    val failed: Int,
    val results: List<TestCaseResult>
)

data class TestCaseResult(
    val goldenAnswerId: String,
    val question: String,
    val expectedAnswer: String,
    val actualAnswer: String,
    val similarityScore: Double,
    val passed: Boolean
)
```

**Controller:** `controller/GoldenAnswerController.kt`
```kotlin
@RestController
@RequestMapping("/api/admin/golden")
class GoldenAnswerController {
    GET    /api/admin/golden              // List all
    POST   /api/admin/golden              // Add new
    DELETE /api/admin/golden/{id}         // Deactivate
    POST   /api/admin/golden/import/{reviewId}  // Import from review
    POST   /api/admin/golden/test         // Run regression test
}
```

---

## 4. Dynamic Configuration

### Concept

**Belangrijk:** Alle constanten die het gedrag van de assistent bepalen worden gelezen via `DynamicConfigService`. Dit zorgt ervoor dat wijzigingen in het dashboard direct effect hebben zonder herstart.

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  application.yml │────▶│ DynamicConfigService │◀────│ Admin Dashboard │
│  (defaults)      │     │ (runtime overrides)  │     │ (UI changes)    │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │ QualityAssuranceAgent│
                        │ RagSearchService     │
                        │ ContextPromptBuilder │
                        └─────────────────────┘
```

### Backend

**Config model:** `config/DynamicConfigService.kt`
```kotlin
@Service
class DynamicConfigService(
    private val qualityConfig: QualityConfig,  // Defaults from application.yml
    private val ragConfig: RagConfig
) {
    // ============================================================
    // DEFAULTS (loaded from application.yml, never modified)
    // ============================================================

    val defaultThresholds = ThresholdConfig(
        relevance = qualityConfig.thresholds.relevance,
        tone = qualityConfig.thresholds.tone,
        completeness = qualityConfig.thresholds.completeness,
        policyCompliance = qualityConfig.thresholds.policyCompliance
    )

    val defaultRagConfig = RagConfigSnapshot(
        similarityThreshold = 0.5,  // From RagSearchService.MINIMUM_RELEVANCE_THRESHOLD
        maxResults = 5,
        chunkSize = ragConfig.chunkSize
    )

    // ============================================================
    // RUNTIME OVERRIDES (null = use default)
    // ============================================================

    private var thresholdOverrides = mutableMapOf<String, Double?>()
    private var ragOverrides = mutableMapOf<String, Any?>()

    // ============================================================
    // GETTERS (used by agent and services)
    // ============================================================

    fun getRelevanceThreshold(): Double =
        thresholdOverrides["relevance"] ?: defaultThresholds.relevance

    fun getToneThreshold(): Double =
        thresholdOverrides["tone"] ?: defaultThresholds.tone

    fun getCompletenessThreshold(): Double =
        thresholdOverrides["completeness"] ?: defaultThresholds.completeness

    fun getPolicyComplianceThreshold(): Double =
        thresholdOverrides["policyCompliance"] ?: defaultThresholds.policyCompliance

    fun getSimilarityThreshold(): Double =
        (ragOverrides["similarityThreshold"] as? Double) ?: defaultRagConfig.similarityThreshold

    fun getMaxResults(): Int =
        (ragOverrides["maxResults"] as? Int) ?: defaultRagConfig.maxResults

    // ============================================================
    // SETTERS (called from admin dashboard)
    // ============================================================

    fun setThreshold(dimension: String, value: Double) {
        thresholdOverrides[dimension] = value
        logger.info("Threshold '$dimension' set to $value (default: ${getDefault(dimension)})")
    }

    fun setRagConfig(key: String, value: Any) {
        ragOverrides[key] = value
        logger.info("RAG config '$key' set to $value")
    }

    // ============================================================
    // RESET FUNCTIONS
    // ============================================================

    fun resetThreshold(dimension: String) {
        thresholdOverrides.remove(dimension)
        logger.info("Threshold '$dimension' reset to default: ${getDefault(dimension)}")
    }

    fun resetAllThresholds() {
        thresholdOverrides.clear()
        logger.info("All thresholds reset to defaults")
    }

    fun resetRagConfig() {
        ragOverrides.clear()
        logger.info("RAG config reset to defaults")
    }

    fun resetAll() {
        resetAllThresholds()
        resetRagConfig()
        logger.info("ALL configuration reset to defaults")
    }

    // ============================================================
    // SNAPSHOT FOR UI
    // ============================================================

    fun getCurrentConfig(): ConfigSnapshot = ConfigSnapshot(
        thresholds = ThresholdConfig(
            relevance = getRelevanceThreshold(),
            tone = getToneThreshold(),
            completeness = getCompletenessThreshold(),
            policyCompliance = getPolicyComplianceThreshold()
        ),
        rag = RagConfigSnapshot(
            similarityThreshold = getSimilarityThreshold(),
            maxResults = getMaxResults(),
            chunkSize = ragConfig.chunkSize
        ),
        isModified = thresholdOverrides.isNotEmpty() || ragOverrides.isNotEmpty()
    )

    fun getDefaultConfig(): ConfigSnapshot = ConfigSnapshot(
        thresholds = defaultThresholds,
        rag = defaultRagConfig,
        isModified = false
    )

    // Helper to check if a specific value differs from default
    fun isModified(key: String): Boolean =
        thresholdOverrides.containsKey(key) || ragOverrides.containsKey(key)
}

data class ConfigSnapshot(
    val thresholds: ThresholdConfig,
    val rag: RagConfigSnapshot,
    val isModified: Boolean
)

data class ThresholdConfig(
    val relevance: Double,
    val tone: Double,
    val completeness: Double,
    val policyCompliance: Double
)

data class RagConfigSnapshot(
    val similarityThreshold: Double,
    val maxResults: Int,
    val chunkSize: Int
)
```

**Controller:** `controller/ConfigController.kt`
```kotlin
@RestController
@RequestMapping("/api/admin/config")
class ConfigController(private val configService: DynamicConfigService) {

    @GetMapping
    fun getCurrentConfig() = configService.getCurrentConfig()

    @GetMapping("/defaults")
    fun getDefaultConfig() = configService.getDefaultConfig()

    @PutMapping("/thresholds/{dimension}")
    fun setThreshold(@PathVariable dimension: String, @RequestBody value: Double) {
        configService.setThreshold(dimension, value)
        return configService.getCurrentConfig()
    }

    @PutMapping("/thresholds")
    fun setAllThresholds(@RequestBody thresholds: ThresholdConfig) {
        configService.setThreshold("relevance", thresholds.relevance)
        configService.setThreshold("tone", thresholds.tone)
        configService.setThreshold("completeness", thresholds.completeness)
        configService.setThreshold("policyCompliance", thresholds.policyCompliance)
        return configService.getCurrentConfig()
    }

    @PostMapping("/reset/thresholds")
    fun resetThresholds(): ConfigSnapshot {
        configService.resetAllThresholds()
        return configService.getCurrentConfig()
    }

    @PostMapping("/reset/rag")
    fun resetRag(): ConfigSnapshot {
        configService.resetRagConfig()
        return configService.getCurrentConfig()
    }

    @PostMapping("/reset/all")
    fun resetAll(): ConfigSnapshot {
        configService.resetAll()
        return configService.getCurrentConfig()
    }
}
```

### Update Existing Services to Use DynamicConfigService

**QualityAssuranceAgent.kt** - Wijzig van direct QualityConfig naar DynamicConfigService:

```kotlin
// BEFORE:
@Agent
class QualityAssuranceAgent(
    private val qualityConfig: QualityConfig,  // ❌ Direct config
    ...
)

// In parseEvaluation:
val thresholds = mapOf(
    QualityDimension.RELEVANCE to qualityConfig.thresholds.relevance,  // ❌
    ...
)

// AFTER:
@Agent
class QualityAssuranceAgent(
    private val dynamicConfig: DynamicConfigService,  // ✅ Dynamic config
    ...
)

// In parseEvaluation:
val thresholds = mapOf(
    QualityDimension.RELEVANCE to dynamicConfig.getRelevanceThreshold(),  // ✅
    QualityDimension.TONE to dynamicConfig.getToneThreshold(),
    QualityDimension.COMPLETENESS to dynamicConfig.getCompletenessThreshold(),
    QualityDimension.POLICY_COMPLIANCE to dynamicConfig.getPolicyComplianceThreshold()
)
```

**RagSearchService.kt** - Wijzig van hardcoded constant naar DynamicConfigService:

```kotlin
// BEFORE:
companion object {
    const val MINIMUM_RELEVANCE_THRESHOLD = 0.5  // ❌ Hardcoded
}

fun searchDocuments(query: String, maxResults: Int = 5): List<KnowledgeSource> {
    vectorStore.similaritySearch(
        SearchRequest.builder()
            .similarityThreshold(MINIMUM_RELEVANCE_THRESHOLD)  // ❌
            .topK(maxResults)
            ...
    )
}

// AFTER:
class RagSearchService(
    private val dynamicConfig: DynamicConfigService,  // ✅ Inject
    ...
) {
    fun searchDocuments(query: String, maxResults: Int? = null): List<KnowledgeSource> {
        vectorStore.similaritySearch(
            SearchRequest.builder()
                .similarityThreshold(dynamicConfig.getSimilarityThreshold())  // ✅
                .topK(maxResults ?: dynamicConfig.getMaxResults())  // ✅
                ...
        )
    }
}
```

### Frontend UI for Config

**ThresholdEditor.jsx**
```jsx
const ThresholdEditor = () => {
  const [config, setConfig] = useState(null)
  const [defaults, setDefaults] = useState(null)

  useEffect(() => {
    Promise.all([
      adminAPI.getConfig(),
      adminAPI.getDefaults()
    ]).then(([current, defs]) => {
      setConfig(current)
      setDefaults(defs)
    })
  }, [])

  const isModified = (key) => config?.thresholds[key] !== defaults?.thresholds[key]

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3>Quality Thresholds</h3>
        <button onClick={handleResetAll} className="btn-secondary">
          Reset to Defaults
        </button>
      </div>

      {['relevance', 'tone', 'completeness', 'policyCompliance'].map(dim => (
        <div key={dim} className="flex items-center space-x-4">
          <label className="w-32">{dim}</label>

          <input
            type="range"
            min="0" max="1" step="0.05"
            value={config?.thresholds[dim] || 0}
            onChange={(e) => handleChange(dim, e.target.value)}
          />

          <span className={isModified(dim) ? 'text-amber-600 font-bold' : ''}>
            {config?.thresholds[dim]?.toFixed(2)}
          </span>

          <span className="text-gray-400 text-sm">
            (default: {defaults?.thresholds[dim]?.toFixed(2)})
          </span>

          {isModified(dim) && (
            <button onClick={() => handleReset(dim)} className="text-xs text-blue-600">
              Reset
            </button>
          )}
        </div>
      ))}

      {config?.isModified && (
        <div className="bg-amber-50 border border-amber-200 rounded p-2 text-sm">
          ⚠️ Configuration has been modified from defaults
        </div>
      )}
    </div>
  )
}
```

---

## 5. Admin Dashboard (Frontend)

### New Route
```jsx
// App.jsx or router
<Route path="/admin" element={<AdminDashboard />} />
```

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Admin Dashboard                              [Reset All Defaults]│
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │ FEEDBACK STATS      │  │ REVIEW QUEUE        │               │
│  │ 👍 124 positive     │  │ 🔔 7 pending        │               │
│  │ 👎 23 negative      │  │ ✓ 45 approved       │               │
│  │ 📊 84% approval     │  │ ✗ 12 rejected       │               │
│  └─────────────────────┘  └─────────────────────┘               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ QUALITY THRESHOLDS                          [Reset Defaults] │ │
│  │                                                               │ │
│  │ Relevance      [====|====] 0.60  (default: 0.60)            │ │
│  │ Tone           [=====|===] 0.70  (default: 0.70)            │ │
│  │ Completeness   [===|=====] 0.50  (default: 0.50)            │ │
│  │ Policy         [====|====] 0.60  (default: 0.60)            │ │
│  │                                                               │ │
│  │ [Save Changes]                                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ RAG CONFIGURATION                           [Reset Defaults] │ │
│  │                                                               │ │
│  │ Similarity Threshold  [===|=====] 0.50                       │ │
│  │ Max Results           [5 ▼]                                  │ │
│  │                                                               │ │
│  │ [Save Changes]                                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ GOLDEN ANSWERS                                    [Add New]  │ │
│  │                                                               │ │
│  │ 📝 12 golden answers    [Run Regression Test]                │ │
│  │                                                               │ │
│  │ Last test: 12/12 passed ✓                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

**`AdminDashboard.jsx`** - Main container
**`FeedbackStats.jsx`** - Shows feedback statistics
**`ReviewQueue.jsx`** - List and manage pending reviews
**`ThresholdEditor.jsx`** - Sliders for quality thresholds
**`RagConfigEditor.jsx`** - RAG settings
**`GoldenAnswerManager.jsx`** - Manage golden answers
**`RegressionTestRunner.jsx`** - Run and show test results

### API Service

**`admin_api.js`**
```javascript
export const adminAPI = {
  // Feedback
  getFeedbackStats: () => api.get('/api/feedback/stats'),
  exportFeedback: () => api.get('/api/feedback/export'),

  // Review
  getPendingReviews: () => api.get('/api/admin/review/pending'),
  approveReview: (id, notes) => api.post(`/api/admin/review/${id}/approve`, { notes }),
  rejectReview: (id, notes) => api.post(`/api/admin/review/${id}/reject`, { notes }),
  correctReview: (id, response, notes) => api.post(`/api/admin/review/${id}/correct`, { response, notes }),

  // Config
  getConfig: () => api.get('/api/admin/config'),
  getDefaults: () => api.get('/api/admin/config/defaults'),
  updateThresholds: (thresholds) => api.put('/api/admin/config/thresholds', thresholds),
  updateRag: (config) => api.put('/api/admin/config/rag', config),
  resetConfig: () => api.post('/api/admin/config/reset'),

  // Golden Answers
  getGoldenAnswers: () => api.get('/api/admin/golden'),
  addGoldenAnswer: (answer) => api.post('/api/admin/golden', answer),
  deleteGoldenAnswer: (id) => api.delete(`/api/admin/golden/${id}`),
  importFromReview: (reviewId) => api.post(`/api/admin/golden/import/${reviewId}`),
  runRegressionTest: () => api.post('/api/admin/golden/test'),
}
```

---

## 6. Implementation Order

### Phase 1: Foundation (Feedback + Config)
1. `FeedbackService` + `FeedbackController`
2. `DynamicConfigService` + `ConfigController`
3. Update `QualityAssuranceAgent` to use dynamic config
4. Basic admin dashboard with config editor
5. Feedback buttons in chat UI

### Phase 2: Human Review
1. `ReviewQueueService` + `ReviewController`
2. Auto-flagging in agent
3. "Flag for review" button in chat
4. Review queue UI in admin dashboard

### Phase 3: Golden Answers
1. `GoldenAnswerService` + `GoldenAnswerController`
2. Import from review flow
3. Regression testing
4. Golden answer manager UI

### Phase 4: Analytics & Refinement
1. Feedback analytics (trends, per-dimension breakdown)
2. A/B testing support for thresholds
3. Export/import of all configurations
4. Audit log for config changes

---

## 7. File Structure

```
spring-backend/src/main/kotlin/com/gemeente/quality/
├── model/
│   ├── Feedback.kt          # NEW
│   ├── ReviewQueue.kt       # NEW
│   └── GoldenAnswer.kt      # NEW
├── service/
│   ├── FeedbackService.kt   # NEW
│   ├── ReviewQueueService.kt # NEW
│   ├── GoldenAnswerService.kt # NEW
│   └── DynamicConfigService.kt # NEW
├── controller/
│   ├── FeedbackController.kt # NEW
│   ├── ReviewController.kt   # NEW
│   ├── GoldenAnswerController.kt # NEW
│   └── ConfigController.kt   # NEW
└── config/
    └── AdminSecurityConfig.kt # NEW (optional: protect admin endpoints)

frontend/src/
├── pages/
│   └── AdminDashboard.jsx    # NEW
├── components/admin/
│   ├── FeedbackStats.jsx     # NEW
│   ├── ReviewQueue.jsx       # NEW
│   ├── ThresholdEditor.jsx   # NEW
│   ├── RagConfigEditor.jsx   # NEW
│   ├── GoldenAnswerManager.jsx # NEW
│   └── RegressionTestRunner.jsx # NEW
└── services/
    └── admin_api.js          # NEW
```

---

## 8. Database Schema (Future)

Voor productie-ready implementatie met PostgreSQL:

```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY,
    message_id VARCHAR(255),
    timestamp TIMESTAMP,
    rating VARCHAR(20),
    comment TEXT,
    original_question TEXT,
    response TEXT,
    quality_scores JSONB,
    was_improved BOOLEAN,
    hallucination_detected BOOLEAN,
    organization_type VARCHAR(50)
);

CREATE TABLE review_queue (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    status VARCHAR(20),
    original_question TEXT,
    ai_response TEXT,
    quality_scores JSONB,
    hallucination_detected BOOLEAN,
    flag_reason VARCHAR(50),
    reviewer_notes TEXT,
    corrected_response TEXT,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(255)
);

CREATE TABLE golden_answers (
    id UUID PRIMARY KEY,
    question TEXT,
    answer TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP,
    source VARCHAR(50),
    quality_scores JSONB,
    is_active BOOLEAN,
    embedding VECTOR(384)  -- For similarity search
);

CREATE TABLE config_audit_log (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    changed_by VARCHAR(255),
    config_type VARCHAR(50),
    old_value JSONB,
    new_value JSONB
);
```

---

## 9. Security Considerations

- Admin endpoints under `/api/admin/*`
- Optional: Basic auth or API key for admin routes
- Audit logging for config changes
- Rate limiting on feedback submission
- Sanitize user comments before storage

---

## Resume Implementation

To start implementation, load this file and say:
> "Implement Phase 1 of the admin dashboard plan"

Or for specific components:
> "Implement the FeedbackService from the admin dashboard plan"
