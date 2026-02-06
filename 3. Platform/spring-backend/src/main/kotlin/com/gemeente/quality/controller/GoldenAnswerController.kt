package com.gemeente.quality.controller

import com.gemeente.quality.model.*
import com.gemeente.quality.service.GoldenAnswerService
import com.gemeente.quality.service.ReviewQueueService
import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/admin/golden")
class GoldenAnswerController(
    private val goldenAnswerService: GoldenAnswerService,
    private val reviewQueueService: ReviewQueueService
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    @GetMapping
    fun getAllGoldenAnswers(): ResponseEntity<List<GoldenAnswer>> {
        return ResponseEntity.ok(goldenAnswerService.getAll())
    }

    @GetMapping("/active")
    fun getActiveGoldenAnswers(): ResponseEntity<List<GoldenAnswer>> {
        return ResponseEntity.ok(goldenAnswerService.getActive())
    }

    @GetMapping("/{id}")
    fun getGoldenAnswer(@PathVariable id: String): ResponseEntity<GoldenAnswer> {
        val answer = goldenAnswerService.getById(id)
            ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(answer)
    }

    @PostMapping
    fun addGoldenAnswer(@RequestBody request: GoldenAnswerRequest): ResponseEntity<GoldenAnswer> {
        val answer = goldenAnswerService.addGoldenAnswer(request)
        return ResponseEntity.ok(answer)
    }

    @PostMapping("/import/{reviewId}")
    fun importFromReview(@PathVariable reviewId: String): ResponseEntity<Map<String, Any>> {
        val reviewItem = reviewQueueService.getItemById(reviewId)
            ?: return ResponseEntity.badRequest().body(mapOf(
                "success" to false,
                "error" to "Review item not found"
            ))

        val goldenAnswer = goldenAnswerService.importFromReview(reviewItem)
            ?: return ResponseEntity.badRequest().body(mapOf(
                "success" to false,
                "error" to "Can only import approved or corrected review items"
            ))

        return ResponseEntity.ok(mapOf(
            "success" to true,
            "golden_answer" to goldenAnswer
        ))
    }

    @DeleteMapping("/{id}")
    fun deactivateGoldenAnswer(@PathVariable id: String): ResponseEntity<GoldenAnswer> {
        val answer = goldenAnswerService.deactivate(id)
            ?: return ResponseEntity.notFound().build()
        return ResponseEntity.ok(answer)
    }

    @DeleteMapping("/{id}/permanent")
    fun deleteGoldenAnswer(@PathVariable id: String): ResponseEntity<Map<String, Boolean>> {
        val deleted = goldenAnswerService.delete(id)
        return ResponseEntity.ok(mapOf("deleted" to deleted))
    }

    @PostMapping("/test")
    fun runRegressionTest(): ResponseEntity<RegressionTestResult> {
        logger.info("Starting regression test via API...")
        val result = goldenAnswerService.runRegressionTest()
        return ResponseEntity.ok(result)
    }

    @GetMapping("/stats")
    fun getStats(): ResponseEntity<GoldenAnswerStats> {
        return ResponseEntity.ok(goldenAnswerService.getStats())
    }
}
