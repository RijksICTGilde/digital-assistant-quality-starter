package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.annotation.JsonValue
import java.time.Instant
import java.util.UUID

data class FeedbackEntry(
    val id: String = UUID.randomUUID().toString(),
    @JsonProperty("message_id")
    val messageId: String,
    val timestamp: Instant = Instant.now(),
    val rating: FeedbackRating,
    val comment: String? = null,
    @JsonProperty("original_question")
    val originalQuestion: String,
    val response: String,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    @JsonProperty("was_improved")
    val wasImproved: Boolean = false,
    @JsonProperty("hallucination_detected")
    val hallucinationDetected: Boolean = false,
    @JsonProperty("agent_type")
    val agentType: String? = null,
    @JsonProperty("organization_type")
    val organizationType: String? = null
)

enum class FeedbackRating(@JsonValue val value: String) {
    POSITIVE("positive"),
    NEGATIVE("negative")
}

data class FeedbackStats(
    @JsonProperty("total_feedback")
    val totalFeedback: Int,
    @JsonProperty("positive_count")
    val positiveCount: Int,
    @JsonProperty("negative_count")
    val negativeCount: Int,
    @JsonProperty("approval_rate")
    val approvalRate: Double,
    @JsonProperty("feedback_with_comments")
    val feedbackWithComments: Int,
    @JsonProperty("by_agent_type")
    val byAgentType: Map<String, AgentFeedbackStats>,
    @JsonProperty("average_quality_scores")
    val averageQualityScores: Map<String, Double>,
    @JsonProperty("improved_responses_feedback")
    val improvedResponsesFeedback: ImprovedFeedbackStats
)

data class AgentFeedbackStats(
    val positive: Int,
    val negative: Int,
    val total: Int
)

data class ImprovedFeedbackStats(
    @JsonProperty("total_improved")
    val totalImproved: Int,
    @JsonProperty("positive_after_improvement")
    val positiveAfterImprovement: Int,
    @JsonProperty("improvement_approval_rate")
    val improvementApprovalRate: Double
)

data class FeedbackRequest(
    @JsonProperty("message_id")
    val messageId: String,
    val rating: FeedbackRating,
    val comment: String? = null,
    @JsonProperty("original_question")
    val originalQuestion: String,
    val response: String,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    @JsonProperty("was_improved")
    val wasImproved: Boolean = false,
    @JsonProperty("hallucination_detected")
    val hallucinationDetected: Boolean = false,
    @JsonProperty("agent_type")
    val agentType: String? = null,
    @JsonProperty("organization_type")
    val organizationType: String? = null
)

// Analytics models
data class FeedbackTrend(
    val date: String, // YYYY-MM-DD format
    val positive: Int,
    val negative: Int,
    val total: Int,
    @JsonProperty("approval_rate")
    val approvalRate: Double
)

data class QualityScoreDistribution(
    val dimension: String,
    @JsonProperty("avg_positive")
    val avgPositive: Double,
    @JsonProperty("avg_negative")
    val avgNegative: Double,
    @JsonProperty("avg_overall")
    val avgOverall: Double
)

data class FeedbackAnalytics(
    @JsonProperty("daily_trends")
    val dailyTrends: List<FeedbackTrend>,
    @JsonProperty("weekly_trends")
    val weeklyTrends: List<FeedbackTrend>,
    @JsonProperty("quality_distribution")
    val qualityDistribution: List<QualityScoreDistribution>,
    @JsonProperty("recent_negative")
    val recentNegative: List<FeedbackSummary>,
    @JsonProperty("hallucination_feedback")
    val hallucinationFeedback: HallucinationFeedbackStats
)

data class FeedbackSummary(
    val id: String,
    val timestamp: Instant,
    val comment: String?,
    @JsonProperty("original_question")
    val originalQuestion: String,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>?
)

data class HallucinationFeedbackStats(
    @JsonProperty("total_with_hallucination")
    val totalWithHallucination: Int,
    @JsonProperty("positive_despite_hallucination")
    val positiveDespitefHallucination: Int,
    @JsonProperty("negative_due_to_hallucination")
    val negativeDueToHallucination: Int
)
