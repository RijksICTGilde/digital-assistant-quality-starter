package com.gemeente.quality.service

import com.embabel.agent.api.invocation.AgentInvocation
import com.embabel.agent.core.AgentPlatform
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.readValue
import com.gemeente.quality.agent.domain.QualityAssuredResponse
import com.gemeente.quality.model.*
import jakarta.annotation.PostConstruct
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import java.io.File
import java.time.Instant

@Service
class GoldenAnswerService(
    private val agentPlatform: AgentPlatform,
    private val dynamicConfig: DynamicConfigService
) {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val goldenAnswerStore = mutableListOf<GoldenAnswer>()
    private val cacheFile = File("./cache/golden-answers.json")
    private val objectMapper = ObjectMapper().apply {
        registerModule(JavaTimeModule())
    }
    private var lastRegressionTest: RegressionTestResult? = null

    @PostConstruct
    fun loadFromCache() {
        if (cacheFile.exists()) {
            try {
                val answers: List<GoldenAnswer> = objectMapper.readValue(cacheFile)
                goldenAnswerStore.addAll(answers)
                logger.info("Loaded ${answers.size} golden answers from cache")
            } catch (e: Exception) {
                logger.warn("Failed to load golden answers cache: ${e.message}")
            }
        }
    }

    private fun saveToCache() {
        try {
            cacheFile.parentFile?.mkdirs()
            objectMapper.writeValue(cacheFile, goldenAnswerStore)
        } catch (e: Exception) {
            logger.warn("Failed to save golden answers cache: ${e.message}")
        }
    }

    fun addGoldenAnswer(request: GoldenAnswerRequest): GoldenAnswer {
        val answer = GoldenAnswer(
            question = request.question,
            answer = request.answer,
            category = request.category,
            source = GoldenAnswerSource.MANUAL,
            qualityScores = request.qualityScores,
            tags = request.tags
        )
        goldenAnswerStore.add(answer)
        saveToCache()
        logger.info("Added golden answer: ${answer.id}")
        return answer
    }

    fun addGoldenAnswer(goldenAnswer: GoldenAnswer): GoldenAnswer {
        goldenAnswerStore.add(goldenAnswer)
        saveToCache()
        logger.info("Added golden answer: ${goldenAnswer.id}")
        return goldenAnswer
    }

    fun importFromReview(reviewItem: ReviewItem): GoldenAnswer? {
        // Only import corrected or approved items
        if (reviewItem.status != ReviewStatus.CORRECTED && reviewItem.status != ReviewStatus.APPROVED) {
            logger.warn("Cannot import non-approved/corrected review item: ${reviewItem.id}")
            return null
        }

        val answer = GoldenAnswer(
            question = reviewItem.originalQuestion,
            answer = reviewItem.correctedResponse ?: reviewItem.aiResponse,
            category = detectCategory(reviewItem.originalQuestion),
            source = GoldenAnswerSource.FROM_REVIEW,
            qualityScores = reviewItem.qualityScores,
            sourceReviewId = reviewItem.id
        )
        goldenAnswerStore.add(answer)
        saveToCache()
        logger.info("Imported golden answer from review: ${reviewItem.id} -> ${answer.id}")
        return answer
    }

    fun getAll(): List<GoldenAnswer> {
        return goldenAnswerStore.sortedByDescending { it.createdAt }
    }

    fun getActive(): List<GoldenAnswer> {
        return goldenAnswerStore.filter { it.isActive }.sortedByDescending { it.createdAt }
    }

    fun getById(id: String): GoldenAnswer? {
        return goldenAnswerStore.find { it.id == id }
    }

    fun deactivate(id: String): GoldenAnswer? {
        val index = goldenAnswerStore.indexOfFirst { it.id == id }
        if (index == -1) return null

        val answer = goldenAnswerStore[index]
        val updated = answer.copy(isActive = false)
        goldenAnswerStore[index] = updated
        saveToCache()
        logger.info("Deactivated golden answer: $id")
        return updated
    }

    fun delete(id: String): Boolean {
        val removed = goldenAnswerStore.removeIf { it.id == id }
        if (removed) {
            saveToCache()
            logger.info("Deleted golden answer: $id")
        }
        return removed
    }

    fun runRegressionTest(): RegressionTestResult {
        logger.info("Starting regression test with ${goldenAnswerStore.size} golden answers...")
        val startTime = System.currentTimeMillis()
        val activeAnswers = getActive()

        if (activeAnswers.isEmpty()) {
            val result = RegressionTestResult(
                totalTests = 0,
                passed = 0,
                failed = 0,
                passRate = 1.0,
                results = emptyList(),
                durationMs = 0
            )
            lastRegressionTest = result
            return result
        }

        val results = activeAnswers.map { golden ->
            try {
                // Run the question through the agent
                val chatMessage = ChatMessage(
                    message = golden.question,
                    context = UserContext()
                )

                val response = AgentInvocation
                    .builder(agentPlatform)
                    .build(QualityAssuredResponse::class.java)
                    .invoke(chatMessage)

                val actualAnswer = response.response.mainAnswer
                val similarityScore = calculateSimilarity(golden.answer, actualAnswer)
                val passed = similarityScore >= dynamicConfig.getRegressionThreshold()

                TestCaseResult(
                    goldenAnswerId = golden.id,
                    question = golden.question,
                    expectedAnswer = golden.answer.take(200),
                    actualAnswer = actualAnswer.take(200),
                    similarityScore = similarityScore,
                    passed = passed,
                    qualityScores = response.response.qualityScores,
                    category = golden.category
                )
            } catch (e: Exception) {
                logger.error("Regression test failed for golden answer ${golden.id}: ${e.message}")
                TestCaseResult(
                    goldenAnswerId = golden.id,
                    question = golden.question,
                    expectedAnswer = golden.answer.take(200),
                    actualAnswer = "ERROR: ${e.message}",
                    similarityScore = 0.0,
                    passed = false,
                    category = golden.category
                )
            }
        }

        val passed = results.count { it.passed }
        val failed = results.size - passed
        val durationMs = System.currentTimeMillis() - startTime

        val result = RegressionTestResult(
            totalTests = results.size,
            passed = passed,
            failed = failed,
            passRate = if (results.isNotEmpty()) passed.toDouble() / results.size else 1.0,
            results = results,
            durationMs = durationMs
        )

        lastRegressionTest = result
        logger.info("Regression test completed: ${passed}/${results.size} passed in ${durationMs}ms")
        return result
    }

    fun getStats(): GoldenAnswerStats {
        val byCategory = goldenAnswerStore
            .filter { it.isActive }
            .groupBy { it.category ?: "uncategorized" }
            .mapValues { it.value.size }

        val bySource = goldenAnswerStore
            .filter { it.isActive }
            .groupBy { it.source.value }
            .mapValues { it.value.size }

        return GoldenAnswerStats(
            totalAnswers = goldenAnswerStore.size,
            activeAnswers = goldenAnswerStore.count { it.isActive },
            byCategory = byCategory,
            bySource = bySource,
            lastRegressionTest = lastRegressionTest
        )
    }

    private fun calculateSimilarity(expected: String, actual: String): Double {
        // Simple word overlap similarity
        val expectedWords = expected.lowercase().split(Regex("\\s+")).toSet()
        val actualWords = actual.lowercase().split(Regex("\\s+")).toSet()

        if (expectedWords.isEmpty() || actualWords.isEmpty()) return 0.0

        val intersection = expectedWords.intersect(actualWords).size
        val union = expectedWords.union(actualWords).size

        return intersection.toDouble() / union.toDouble()
    }

    private fun detectCategory(question: String): String? {
        val lower = question.lowercase()
        return when {
            lower.containsAny("gdpr", "avg", "privacy") -> "GDPR"
            lower.containsAny("ai act", "ai verordening") -> "AI_ACT"
            lower.containsAny("woo", "wet open overheid") -> "WOO"
            lower.containsAny("architectuur", "api", "integratie") -> "TECHNICAL"
            else -> "GENERAL"
        }
    }

    private fun String.containsAny(vararg terms: String): Boolean =
        terms.any { this.contains(it) }
}
