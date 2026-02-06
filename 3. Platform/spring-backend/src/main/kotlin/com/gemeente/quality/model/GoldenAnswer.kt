package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.annotation.JsonValue
import java.time.Instant
import java.util.UUID

data class GoldenAnswer(
    val id: String = UUID.randomUUID().toString(),
    val question: String,
    val answer: String,
    val category: String? = null,
    @JsonProperty("created_at")
    val createdAt: Instant = Instant.now(),
    val source: GoldenAnswerSource,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    @JsonProperty("is_active")
    val isActive: Boolean = true,
    @JsonProperty("source_review_id")
    val sourceReviewId: String? = null,
    val tags: List<String>? = null
)

enum class GoldenAnswerSource(@JsonValue val value: String) {
    MANUAL("manual"),
    FROM_REVIEW("from_review"),
    FROM_FEEDBACK("from_feedback")
}

data class GoldenAnswerRequest(
    val question: String,
    val answer: String,
    val category: String? = null,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    val tags: List<String>? = null
)

data class RegressionTestResult(
    @JsonProperty("total_tests")
    val totalTests: Int,
    val passed: Int,
    val failed: Int,
    @JsonProperty("pass_rate")
    val passRate: Double,
    val results: List<TestCaseResult>,
    @JsonProperty("timestamp")
    val timestamp: Instant = Instant.now(),
    @JsonProperty("duration_ms")
    val durationMs: Long
)

data class TestCaseResult(
    @JsonProperty("golden_answer_id")
    val goldenAnswerId: String,
    val question: String,
    @JsonProperty("expected_answer")
    val expectedAnswer: String,
    @JsonProperty("actual_answer")
    val actualAnswer: String,
    @JsonProperty("similarity_score")
    val similarityScore: Double,
    val passed: Boolean,
    @JsonProperty("quality_scores")
    val qualityScores: Map<String, Double>? = null,
    val category: String? = null
)

data class GoldenAnswerStats(
    @JsonProperty("total_answers")
    val totalAnswers: Int,
    @JsonProperty("active_answers")
    val activeAnswers: Int,
    @JsonProperty("by_category")
    val byCategory: Map<String, Int>,
    @JsonProperty("by_source")
    val bySource: Map<String, Int>,
    @JsonProperty("last_regression_test")
    val lastRegressionTest: RegressionTestResult?
)
