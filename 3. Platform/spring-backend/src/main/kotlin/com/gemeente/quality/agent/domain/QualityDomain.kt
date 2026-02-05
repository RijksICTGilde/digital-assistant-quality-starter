package com.gemeente.quality.agent.domain

import com.embabel.agent.api.common.workflow.loop.Feedback
import com.embabel.common.core.types.ZeroToOne
import com.gemeente.quality.model.*

/**
 * Typed blackboard objects for GOAP-based quality pipeline.
 *
 * Flow: ChatMessage → RagContext → InitialResponse → QualityEvaluation → ImprovedResponse → QualityAssuredResponse
 *
 * Embabel's GOAP planner chains @Action methods automatically based on these types.
 */

/**
 * Quality feedback for RepeatUntilAcceptable workflow.
 * Implements Embabel's Feedback interface with quality-specific data.
 */
data class QualityFeedback(
    override val score: ZeroToOne,
    val evaluation: QualityEvaluation,
    val improvementSuggestions: String
) : Feedback

/**
 * Draft response being iteratively improved.
 */
data class ResponseDraft(
    val content: String,
    val iteration: Int = 0,
    val previousScores: List<Double> = emptyList()
)

data class RagContext(
    val formattedContext: String,
    val sourceReferences: List<String>,
    val knowledgeSources: List<KnowledgeSource>,
    val hasRelevantSources: Boolean = true
)

data class InitialResponse(
    val mainAnswer: String,
    val responseType: ResponseType,
    val confidenceLevel: ConfidenceLevel,
    val complexity: ComplexityLevel,
    val knowledgeSources: List<KnowledgeSource>,
    val relevantRegulations: List<RegulationType>,
    val needsHumanExpert: Boolean,
    val expertReason: String?,
    val expertType: String?,
    val generationTimeMs: Long
)

data class QualityEvaluation(
    val scores: Map<QualityDimension, Double>,
    val passed: Boolean,
    val failedDimensions: List<QualityDimension>,
    val improvementSuggestions: Map<QualityDimension, String>,
    val evaluationTimeMs: Long,
    val hallucinationDetected: Boolean = false,
    val ungroundedClaims: List<String> = emptyList()
)

data class ImprovedResponse(
    val mainAnswer: String,
    val improvementsApplied: List<String>,
    val wasImproved: Boolean,
    val improvementTimeMs: Long,
    val iterationCount: Int = 1,
    val iterationHistory: List<IterationResult> = emptyList()
)

/**
 * Result of a single improvement iteration for tracking quality progression.
 */
data class IterationResult(
    val iteration: Int,
    val overallScore: Double,
    val dimensionScores: Map<String, Double>,
    val passed: Boolean
)

data class QualityAssuredResponse(
    val response: StructuredAIResponse
)
