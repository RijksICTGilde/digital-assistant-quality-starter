package com.gemeente.quality.controller

import com.gemeente.quality.model.FeedbackAnalytics
import com.gemeente.quality.model.FeedbackEntry
import com.gemeente.quality.model.FeedbackRating
import com.gemeente.quality.model.FeedbackRequest
import com.gemeente.quality.model.FeedbackStats
import com.gemeente.quality.service.FeedbackService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/feedback")
class FeedbackController(
    private val feedbackService: FeedbackService
) {
    @PostMapping
    fun submitFeedback(@RequestBody request: FeedbackRequest): ResponseEntity<FeedbackEntry> {
        val entry = feedbackService.saveFeedback(request)
        return ResponseEntity.ok(entry)
    }

    @GetMapping("/stats")
    fun getStats(): ResponseEntity<FeedbackStats> {
        return ResponseEntity.ok(feedbackService.getFeedbackStats())
    }

    @GetMapping("/export")
    fun exportFeedback(): ResponseEntity<List<FeedbackEntry>> {
        return ResponseEntity.ok(feedbackService.exportFeedback())
    }

    @GetMapping("/recent")
    fun getRecentFeedback(
        @RequestParam(defaultValue = "50") limit: Int
    ): ResponseEntity<List<FeedbackEntry>> {
        return ResponseEntity.ok(feedbackService.getRecentFeedback(limit))
    }

    @GetMapping("/by-rating/{rating}")
    fun getFeedbackByRating(
        @PathVariable rating: String
    ): ResponseEntity<List<FeedbackEntry>> {
        val feedbackRating = try {
            FeedbackRating.valueOf(rating.uppercase())
        } catch (e: IllegalArgumentException) {
            return ResponseEntity.badRequest().build()
        }
        return ResponseEntity.ok(feedbackService.getFeedbackByRating(feedbackRating))
    }

    @GetMapping("/analytics")
    fun getAnalytics(): ResponseEntity<FeedbackAnalytics> {
        return ResponseEntity.ok(feedbackService.getAnalytics())
    }
}
