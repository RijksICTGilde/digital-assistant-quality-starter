package com.gemeente.quality.agent.domain

import com.gemeente.quality.model.*

/**
 * Typed blackboard objects for GOAP-based quality pipeline.
 *
 * Flow: ChatMessage → RagContext → InitialResponse → QualityEvaluation → ImprovedResponse → QualityAssuredResponse
 *
 * Embabel's GOAP planner chains @Action methods automatically based on these types.
 */

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
    val evaluationTimeMs: Long
)

data class ImprovedResponse(
    val mainAnswer: String,
    val improvementsApplied: List<String>,
    val wasImproved: Boolean,
    val improvementTimeMs: Long
)

data class QualityAssuredResponse(
    val response: StructuredAIResponse
)
