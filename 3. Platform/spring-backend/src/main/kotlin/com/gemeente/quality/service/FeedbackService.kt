package com.gemeente.quality.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.readValue
import com.gemeente.quality.model.*
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import jakarta.annotation.PostConstruct
import java.io.File
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

@Service
class FeedbackService {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val feedbackStore = mutableListOf<FeedbackEntry>()
    private val cacheFile = File("./cache/feedback.json")
    private val objectMapper = ObjectMapper().apply {
        registerModule(JavaTimeModule())
    }

    @PostConstruct
    fun loadFromCache() {
        if (cacheFile.exists()) {
            try {
                val entries: List<FeedbackEntry> = objectMapper.readValue(cacheFile)
                feedbackStore.addAll(entries)
                logger.info("Loaded ${entries.size} feedback entries from cache")
            } catch (e: Exception) {
                logger.warn("Failed to load feedback cache: ${e.message}")
            }
        }
    }

    private fun saveToCache() {
        try {
            cacheFile.parentFile?.mkdirs()
            objectMapper.writeValue(cacheFile, feedbackStore)
        } catch (e: Exception) {
            logger.warn("Failed to save feedback cache: ${e.message}")
        }
    }

    fun saveFeedback(request: FeedbackRequest): FeedbackEntry {
        val entry = FeedbackEntry(
            messageId = request.messageId,
            timestamp = Instant.now(),
            rating = request.rating,
            comment = request.comment,
            originalQuestion = request.originalQuestion,
            response = request.response,
            qualityScores = request.qualityScores,
            wasImproved = request.wasImproved,
            hallucinationDetected = request.hallucinationDetected,
            agentType = request.agentType,
            organizationType = request.organizationType
        )
        feedbackStore.add(entry)
        saveToCache()
        logger.info("Saved feedback: ${entry.rating} for message ${entry.messageId}")
        return entry
    }

    fun getFeedbackStats(): FeedbackStats {
        val positive = feedbackStore.count { it.rating == FeedbackRating.POSITIVE }
        val negative = feedbackStore.count { it.rating == FeedbackRating.NEGATIVE }
        val total = feedbackStore.size

        // Stats by agent type
        val byAgentType = feedbackStore
            .groupBy { it.agentType ?: "unknown" }
            .mapValues { (_, entries) ->
                AgentFeedbackStats(
                    positive = entries.count { it.rating == FeedbackRating.POSITIVE },
                    negative = entries.count { it.rating == FeedbackRating.NEGATIVE },
                    total = entries.size
                )
            }

        // Average quality scores from positive feedback
        val scoresFromPositive = feedbackStore
            .filter { it.rating == FeedbackRating.POSITIVE && it.qualityScores != null }
            .flatMap { it.qualityScores!!.entries }
            .groupBy { it.key }
            .mapValues { (_, values) -> values.map { it.value }.average() }

        // Improved responses feedback
        val improved = feedbackStore.filter { it.wasImproved }
        val positiveAfterImprovement = improved.count { it.rating == FeedbackRating.POSITIVE }

        return FeedbackStats(
            totalFeedback = total,
            positiveCount = positive,
            negativeCount = negative,
            approvalRate = if (total > 0) positive.toDouble() / total else 0.0,
            feedbackWithComments = feedbackStore.count { !it.comment.isNullOrBlank() },
            byAgentType = byAgentType,
            averageQualityScores = scoresFromPositive,
            improvedResponsesFeedback = ImprovedFeedbackStats(
                totalImproved = improved.size,
                positiveAfterImprovement = positiveAfterImprovement,
                improvementApprovalRate = if (improved.isNotEmpty())
                    positiveAfterImprovement.toDouble() / improved.size else 0.0
            )
        )
    }

    fun getFeedbackByRating(rating: FeedbackRating): List<FeedbackEntry> {
        return feedbackStore.filter { it.rating == rating }
    }

    fun getRecentFeedback(limit: Int = 50): List<FeedbackEntry> {
        return feedbackStore.sortedByDescending { it.timestamp }.take(limit)
    }

    fun exportFeedback(): List<FeedbackEntry> = feedbackStore.toList()

    fun getFeedbackCount(): Int = feedbackStore.size

    fun getAnalytics(): FeedbackAnalytics {
        val dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd")
        val zone = ZoneId.systemDefault()

        // Daily trends (last 30 days)
        val now = Instant.now()
        val thirtyDaysAgo = now.minus(30, ChronoUnit.DAYS)

        val recentFeedback = feedbackStore.filter { it.timestamp.isAfter(thirtyDaysAgo) }

        val dailyTrends = recentFeedback
            .groupBy { it.timestamp.atZone(zone).toLocalDate().format(dateFormatter) }
            .map { (date, entries) ->
                val positive = entries.count { it.rating == FeedbackRating.POSITIVE }
                val total = entries.size
                FeedbackTrend(
                    date = date,
                    positive = positive,
                    negative = total - positive,
                    total = total,
                    approvalRate = if (total > 0) positive.toDouble() / total else 0.0
                )
            }
            .sortedBy { it.date }

        // Weekly trends (last 12 weeks)
        val twelveWeeksAgo = now.minus(84, ChronoUnit.DAYS)
        val weeklyFeedback = feedbackStore.filter { it.timestamp.isAfter(twelveWeeksAgo) }

        val weeklyTrends = weeklyFeedback
            .groupBy {
                val localDate = it.timestamp.atZone(zone).toLocalDate()
                // Get the Monday of the week
                localDate.minusDays(localDate.dayOfWeek.value.toLong() - 1).format(dateFormatter)
            }
            .map { (weekStart, entries) ->
                val positive = entries.count { it.rating == FeedbackRating.POSITIVE }
                val total = entries.size
                FeedbackTrend(
                    date = weekStart,
                    positive = positive,
                    negative = total - positive,
                    total = total,
                    approvalRate = if (total > 0) positive.toDouble() / total else 0.0
                )
            }
            .sortedBy { it.date }

        // Quality score distribution by dimension
        val positiveFeedback = feedbackStore.filter { it.rating == FeedbackRating.POSITIVE && it.qualityScores != null }
        val negativeFeedback = feedbackStore.filter { it.rating == FeedbackRating.NEGATIVE && it.qualityScores != null }
        val allWithScores = feedbackStore.filter { it.qualityScores != null }

        val dimensions = listOf("relevance", "tone", "completeness", "policy_compliance")
        val qualityDistribution = dimensions.map { dim ->
            QualityScoreDistribution(
                dimension = dim,
                avgPositive = positiveFeedback
                    .mapNotNull { it.qualityScores?.get(dim) }
                    .let { if (it.isNotEmpty()) it.average() else 0.0 },
                avgNegative = negativeFeedback
                    .mapNotNull { it.qualityScores?.get(dim) }
                    .let { if (it.isNotEmpty()) it.average() else 0.0 },
                avgOverall = allWithScores
                    .mapNotNull { it.qualityScores?.get(dim) }
                    .let { if (it.isNotEmpty()) it.average() else 0.0 }
            )
        }

        // Recent negative feedback for review
        val recentNegative = feedbackStore
            .filter { it.rating == FeedbackRating.NEGATIVE }
            .sortedByDescending { it.timestamp }
            .take(10)
            .map { FeedbackSummary(
                id = it.id,
                timestamp = it.timestamp,
                comment = it.comment,
                originalQuestion = it.originalQuestion,
                qualityScores = it.qualityScores
            )}

        // Hallucination feedback stats
        val hallucinationFeedback = feedbackStore.filter { it.hallucinationDetected }
        val hallucinationStats = HallucinationFeedbackStats(
            totalWithHallucination = hallucinationFeedback.size,
            positiveDespitefHallucination = hallucinationFeedback.count { it.rating == FeedbackRating.POSITIVE },
            negativeDueToHallucination = hallucinationFeedback.count { it.rating == FeedbackRating.NEGATIVE }
        )

        return FeedbackAnalytics(
            dailyTrends = dailyTrends,
            weeklyTrends = weeklyTrends,
            qualityDistribution = qualityDistribution,
            recentNegative = recentNegative,
            hallucinationFeedback = hallucinationStats
        )
    }
}
