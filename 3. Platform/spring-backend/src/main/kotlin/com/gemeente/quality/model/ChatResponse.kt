package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonProperty

data class KnowledgeSource(
    val title: String,
    val url: String? = null,
    val snippet: String,
    @JsonProperty("relevance_score") val relevanceScore: Double,
    @JsonProperty("document_type") val documentType: String,
    @JsonProperty("document_id") val documentId: String? = null,
    @JsonProperty("file_path") val filePath: String? = null,
    @JsonProperty("section_title") val sectionTitle: String? = null,
    @JsonProperty("chunk_index") val chunkIndex: Int? = null,
    @JsonProperty("total_chunks") val totalChunks: Int? = null,
    @JsonProperty("original_url") val originalUrl: String? = null,
    @JsonProperty("document_title") val documentTitle: String? = null
)

data class ActionItem(
    val title: String,
    val description: String,
    val priority: String,
    val timeline: String? = null,
    val resources: List<String>? = null
)

data class ComplianceCheck(
    val regulation: RegulationType,
    val status: String,
    val requirements: List<String>,
    val recommendations: List<String>,
    @JsonProperty("risk_level") val riskLevel: String
)

data class FollowUpSuggestion(
    val question: String,
    val category: String,
    val relevance: Double
)

data class QualityTraceEntry(
    val action: String,
    val dimension: String? = null,
    val score: Double? = null,
    val passed: Boolean? = null,
    @JsonProperty("improvement_applied") val improvementApplied: String? = null,
    @JsonProperty("timestamp_ms") val timestampMs: Long
)

data class StructuredAIResponse(
    @JsonProperty("main_answer") val mainAnswer: String,
    @JsonProperty("response_type") val responseType: ResponseType = ResponseType.DIRECT_ANSWER,
    @JsonProperty("confidence_level") val confidenceLevel: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    val complexity: ComplexityLevel = ComplexityLevel.MODERATE,
    @JsonProperty("action_items") val actionItems: List<ActionItem>? = null,
    @JsonProperty("compliance_checks") val complianceChecks: List<ComplianceCheck>? = null,
    @JsonProperty("knowledge_sources") val knowledgeSources: List<KnowledgeSource> = emptyList(),
    @JsonProperty("follow_up_suggestions") val followUpSuggestions: List<FollowUpSuggestion> = emptyList(),
    @JsonProperty("needs_human_expert") val needsHumanExpert: Boolean = false,
    @JsonProperty("expert_reason") val expertReason: String? = null,
    @JsonProperty("expert_type") val expertType: String? = null,
    @JsonProperty("relevant_regulations") val relevantRegulations: List<RegulationType> = emptyList(),
    val stakeholders: List<String>? = null,
    @JsonProperty("processing_time_ms") val processingTimeMs: Int? = null,
    @JsonProperty("token_usage") val tokenUsage: Int? = null,
    // Quality transparency fields (hackathon differentiator)
    @JsonProperty("quality_scores") val qualityScores: Map<String, Double>? = null,
    @JsonProperty("quality_trace") val qualityTrace: List<QualityTraceEntry>? = null,
    @JsonProperty("quality_improved") val qualityImproved: Boolean? = null,
    @JsonProperty("quality_explanation") val qualityExplanation: String? = null,
    // Before/After comparison (shows original response before improvement)
    @JsonProperty("original_answer") val originalAnswer: String? = null,
    // Hallucination detection
    @JsonProperty("hallucination_detected") val hallucinationDetected: Boolean? = null,
    @JsonProperty("ungrounded_claims") val ungroundedClaims: List<String>? = null
)

data class ErrorResponse(
    @JsonProperty("error_type") val errorType: String,
    @JsonProperty("error_message") val errorMessage: String,
    @JsonProperty("technical_details") val technicalDetails: String? = null,
    @JsonProperty("suggested_action") val suggestedAction: String,
    @JsonProperty("needs_human_help") val needsHumanHelp: Boolean = true
)
