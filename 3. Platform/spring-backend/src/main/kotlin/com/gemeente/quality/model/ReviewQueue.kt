package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.annotation.JsonValue
import java.time.Instant
import java.util.UUID

data class ReviewItem(
    val id: String = UUID.randomUUID().toString(),
    val timestamp: Instant = Instant.now(),
    val status: ReviewStatus = ReviewStatus.PENDING,
    @JsonProperty("original_question")
    val originalQuestion: String,
    @JsonProperty("ai_response")
    val aiResponse: String,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    @JsonProperty("hallucination_detected")
    val hallucinationDetected: Boolean = false,
    @JsonProperty("ungrounded_claims")
    val ungroundedClaims: List<String>? = null,
    @JsonProperty("flag_reason")
    val flagReason: FlagReason,
    @JsonProperty("confidence_level")
    val confidenceLevel: String? = null,
    @JsonProperty("agent_type")
    val agentType: String? = null,
    @JsonProperty("reviewer_notes")
    val reviewerNotes: String? = null,
    @JsonProperty("corrected_response")
    val correctedResponse: String? = null,
    @JsonProperty("reviewed_at")
    val reviewedAt: Instant? = null,
    @JsonProperty("reviewed_by")
    val reviewedBy: String? = null
)

enum class ReviewStatus(@JsonValue val value: String) {
    PENDING("pending"),
    APPROVED("approved"),
    REJECTED("rejected"),
    CORRECTED("corrected")
}

enum class FlagReason(@JsonValue val value: String) {
    LOW_CONFIDENCE("low_confidence"),
    HALLUCINATION("hallucination"),
    USER_FLAGGED("user_flagged"),
    EXPERT_REQUIRED("expert_required"),
    POLICY_VIOLATION("policy_violation")
}

data class ReviewStats(
    @JsonProperty("total_items")
    val totalItems: Int,
    @JsonProperty("pending_count")
    val pendingCount: Int,
    @JsonProperty("approved_count")
    val approvedCount: Int,
    @JsonProperty("rejected_count")
    val rejectedCount: Int,
    @JsonProperty("corrected_count")
    val correctedCount: Int,
    @JsonProperty("by_flag_reason")
    val byFlagReason: Map<String, Int>,
    @JsonProperty("average_review_time_hours")
    val averageReviewTimeHours: Double?
)

data class ReviewActionRequest(
    val notes: String? = null,
    @JsonProperty("corrected_response")
    val correctedResponse: String? = null,
    @JsonProperty("reviewed_by")
    val reviewedBy: String? = null
)

data class FlagForReviewRequest(
    @JsonProperty("original_question")
    val originalQuestion: String,
    @JsonProperty("ai_response")
    val aiResponse: String,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    @JsonProperty("confidence_level")
    val confidenceLevel: String? = null,
    @JsonProperty("agent_type")
    val agentType: String? = null,
    val reason: String? = null
)
