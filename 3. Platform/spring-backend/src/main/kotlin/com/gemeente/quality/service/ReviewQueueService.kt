package com.gemeente.quality.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.readValue
import com.gemeente.quality.model.*
import jakarta.annotation.PostConstruct
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import java.io.File
import java.time.Duration
import java.time.Instant

@Service
class ReviewQueueService {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val reviewStore = mutableListOf<ReviewItem>()
    private val cacheFile = File("./cache/review-queue.json")
    private val objectMapper = ObjectMapper().apply {
        registerModule(JavaTimeModule())
    }

    @PostConstruct
    fun loadFromCache() {
        if (cacheFile.exists()) {
            try {
                val items: List<ReviewItem> = objectMapper.readValue(cacheFile)
                reviewStore.addAll(items)
                logger.info("Loaded ${items.size} review items from cache")
            } catch (e: Exception) {
                logger.warn("Failed to load review queue cache: ${e.message}")
            }
        }
    }

    private fun saveToCache() {
        try {
            cacheFile.parentFile?.mkdirs()
            objectMapper.writeValue(cacheFile, reviewStore)
        } catch (e: Exception) {
            logger.warn("Failed to save review queue cache: ${e.message}")
        }
    }

    fun addToQueue(item: ReviewItem): ReviewItem {
        reviewStore.add(item)
        saveToCache()
        logger.info("Added item to review queue: ${item.id} (reason: ${item.flagReason})")
        return item
    }

    fun addToQueue(
        originalQuestion: String,
        aiResponse: String,
        flagReason: FlagReason,
        qualityScores: Map<String, Double>? = null,
        hallucinationDetected: Boolean = false,
        ungroundedClaims: List<String>? = null,
        confidenceLevel: String? = null,
        agentType: String? = null
    ): ReviewItem {
        val item = ReviewItem(
            originalQuestion = originalQuestion,
            aiResponse = aiResponse,
            flagReason = flagReason,
            qualityScores = qualityScores,
            hallucinationDetected = hallucinationDetected,
            ungroundedClaims = ungroundedClaims,
            confidenceLevel = confidenceLevel,
            agentType = agentType
        )
        return addToQueue(item)
    }

    fun getPendingItems(): List<ReviewItem> {
        return reviewStore
            .filter { it.status == ReviewStatus.PENDING }
            .sortedByDescending { it.timestamp }
    }

    fun getAllItems(): List<ReviewItem> {
        return reviewStore.sortedByDescending { it.timestamp }
    }

    fun getItemById(id: String): ReviewItem? {
        return reviewStore.find { it.id == id }
    }

    fun approveItem(id: String, reviewerNotes: String? = null, reviewedBy: String? = null): ReviewItem? {
        val index = reviewStore.indexOfFirst { it.id == id }
        if (index == -1) return null

        val item = reviewStore[index]
        val updated = item.copy(
            status = ReviewStatus.APPROVED,
            reviewerNotes = reviewerNotes,
            reviewedAt = Instant.now(),
            reviewedBy = reviewedBy
        )
        reviewStore[index] = updated
        saveToCache()
        logger.info("Approved review item: $id")
        return updated
    }

    fun rejectItem(id: String, reviewerNotes: String? = null, reviewedBy: String? = null): ReviewItem? {
        val index = reviewStore.indexOfFirst { it.id == id }
        if (index == -1) return null

        val item = reviewStore[index]
        val updated = item.copy(
            status = ReviewStatus.REJECTED,
            reviewerNotes = reviewerNotes,
            reviewedAt = Instant.now(),
            reviewedBy = reviewedBy
        )
        reviewStore[index] = updated
        saveToCache()
        logger.info("Rejected review item: $id")
        return updated
    }

    fun correctItem(
        id: String,
        correctedResponse: String,
        reviewerNotes: String? = null,
        reviewedBy: String? = null
    ): ReviewItem? {
        val index = reviewStore.indexOfFirst { it.id == id }
        if (index == -1) return null

        val item = reviewStore[index]
        val updated = item.copy(
            status = ReviewStatus.CORRECTED,
            correctedResponse = correctedResponse,
            reviewerNotes = reviewerNotes,
            reviewedAt = Instant.now(),
            reviewedBy = reviewedBy
        )
        reviewStore[index] = updated
        saveToCache()
        logger.info("Corrected review item: $id")
        return updated
    }

    fun getStats(): ReviewStats {
        val pending = reviewStore.count { it.status == ReviewStatus.PENDING }
        val approved = reviewStore.count { it.status == ReviewStatus.APPROVED }
        val rejected = reviewStore.count { it.status == ReviewStatus.REJECTED }
        val corrected = reviewStore.count { it.status == ReviewStatus.CORRECTED }

        val byReason = reviewStore
            .groupBy { it.flagReason.value }
            .mapValues { it.value.size }

        // Calculate average review time for reviewed items
        val reviewedItems = reviewStore.filter { it.reviewedAt != null }
        val avgReviewTime = if (reviewedItems.isNotEmpty()) {
            reviewedItems
                .map { Duration.between(it.timestamp, it.reviewedAt).toHours().toDouble() }
                .average()
        } else null

        return ReviewStats(
            totalItems = reviewStore.size,
            pendingCount = pending,
            approvedCount = approved,
            rejectedCount = rejected,
            correctedCount = corrected,
            byFlagReason = byReason,
            averageReviewTimeHours = avgReviewTime
        )
    }

    fun deleteItem(id: String): Boolean {
        val removed = reviewStore.removeIf { it.id == id }
        if (removed) {
            saveToCache()
            logger.info("Deleted review item: $id")
        }
        return removed
    }
}
