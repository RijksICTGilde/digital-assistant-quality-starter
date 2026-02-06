package com.gemeente.quality.controller

import com.gemeente.quality.model.*
import com.gemeente.quality.service.ReviewQueueService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/admin/review")
class ReviewController(
    private val reviewQueueService: ReviewQueueService
) {
    @GetMapping("/pending")
    fun getPendingItems(): ResponseEntity<List<ReviewItem>> {
        return ResponseEntity.ok(reviewQueueService.getPendingItems())
    }

    @GetMapping("/all")
    fun getAllItems(): ResponseEntity<List<ReviewItem>> {
        return ResponseEntity.ok(reviewQueueService.getAllItems())
    }

    @GetMapping("/stats")
    fun getStats(): ResponseEntity<ReviewStats> {
        return ResponseEntity.ok(reviewQueueService.getStats())
    }

    @GetMapping("/{id}")
    fun getItem(@PathVariable id: String): ResponseEntity<ReviewItem> {
        val item = reviewQueueService.getItemById(id)
            ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(item)
    }

    @PostMapping("/{id}/approve")
    fun approveItem(
        @PathVariable id: String,
        @RequestBody(required = false) request: ReviewActionRequest?
    ): ResponseEntity<ReviewItem> {
        val item = reviewQueueService.approveItem(
            id = id,
            reviewerNotes = request?.notes,
            reviewedBy = request?.reviewedBy
        ) ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(item)
    }

    @PostMapping("/{id}/reject")
    fun rejectItem(
        @PathVariable id: String,
        @RequestBody(required = false) request: ReviewActionRequest?
    ): ResponseEntity<ReviewItem> {
        val item = reviewQueueService.rejectItem(
            id = id,
            reviewerNotes = request?.notes,
            reviewedBy = request?.reviewedBy
        ) ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(item)
    }

    @PostMapping("/{id}/correct")
    fun correctItem(
        @PathVariable id: String,
        @RequestBody request: ReviewActionRequest
    ): ResponseEntity<ReviewItem> {
        if (request.correctedResponse.isNullOrBlank()) {
            return ResponseEntity.badRequest().build()
        }
        val item = reviewQueueService.correctItem(
            id = id,
            correctedResponse = request.correctedResponse,
            reviewerNotes = request.notes,
            reviewedBy = request.reviewedBy
        ) ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(item)
    }

    @DeleteMapping("/{id}")
    fun deleteItem(@PathVariable id: String): ResponseEntity<Map<String, Any>> {
        val deleted = reviewQueueService.deleteItem(id)
        return if (deleted) {
            ResponseEntity.ok(mapOf("deleted" to true, "id" to id))
        } else {
            ResponseEntity.notFound().build()
        }
    }

    // Endpoint for users to flag a response for review
    @PostMapping("/flag")
    fun flagForReview(@RequestBody request: FlagForReviewRequest): ResponseEntity<ReviewItem> {
        val item = reviewQueueService.addToQueue(
            originalQuestion = request.originalQuestion,
            aiResponse = request.aiResponse,
            flagReason = FlagReason.USER_FLAGGED,
            qualityScores = request.qualityScores,
            confidenceLevel = request.confidenceLevel,
            agentType = request.agentType
        )
        return ResponseEntity.ok(item)
    }
}
