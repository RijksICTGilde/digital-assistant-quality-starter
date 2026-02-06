package com.gemeente.quality.service

import com.embabel.agent.api.common.OperationContext
import com.gemeente.quality.agent.domain.ImprovedResponse
import com.gemeente.quality.agent.domain.IterationResult
import com.gemeente.quality.agent.domain.QualityEvaluation
import com.gemeente.quality.model.QualityDimension
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service

/**
 * Shared service for quality evaluation and improvement.
 * Used by all agents to ensure consistent quality standards.
 */
@Service
class QualityEvaluationService(
    private val promptBuilder: ContextPromptBuilder,
    private val dynamicConfig: DynamicConfigService
) {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val objectMapper = jacksonObjectMapper()

    /**
     * Evaluate response quality against dynamic thresholds.
     */
    fun evaluateQuality(
        originalQuestion: String,
        response: String,
        ragContext: String,
        organizationType: String?,
        context: OperationContext
    ): QualityEvaluation {
        logger.info("Evaluating quality...")
        val startTime = System.currentTimeMillis()

        val prompt = promptBuilder.buildEvaluationPrompt(
            originalQuestion = originalQuestion,
            response = response,
            ragContext = ragContext,
            organizationType = organizationType
        )

        val evaluationJson = context.ai()
            .withDefaultLlm()
            .generateText(prompt)

        return parseEvaluation(evaluationJson, startTime)
    }

    /**
     * Improve response if quality is below thresholds.
     * Returns the improved response or original if no improvement needed.
     */
    fun improveIfNeeded(
        originalQuestion: String,
        originalResponse: String,
        evaluation: QualityEvaluation,
        ragContext: String,
        organizationType: String?,
        context: OperationContext
    ): ImprovedResponse {
        val maxIterations = dynamicConfig.getMaxImprovementRounds()
        val iterationHistory = mutableListOf<IterationResult>()

        // Record initial evaluation
        iterationHistory.add(IterationResult(
            iteration = 0,
            overallScore = evaluation.scores.values.average(),
            dimensionScores = evaluation.scores.mapKeys { it.key.name.lowercase() },
            passed = evaluation.passed
        ))

        if (evaluation.passed && !evaluation.hallucinationDetected) {
            logger.info("Quality passed all thresholds, no improvement needed.")
            return ImprovedResponse(
                mainAnswer = originalResponse,
                improvementsApplied = emptyList(),
                wasImproved = false,
                improvementTimeMs = 0,
                iterationCount = 0,
                iterationHistory = iterationHistory
            )
        }

        logger.info("Quality below threshold on: ${evaluation.failedDimensions}. Starting improvement...")
        val startTime = System.currentTimeMillis()

        var currentAnswer = originalResponse
        var currentEvaluation = evaluation
        var iteration = 0
        val allImprovements = mutableSetOf<String>()

        while (iteration < maxIterations && (!currentEvaluation.passed || currentEvaluation.hallucinationDetected)) {
            iteration++
            logger.info("Improvement iteration $iteration/$maxIterations...")

            val improvementPrompt = promptBuilder.buildImprovementPrompt(
                originalQuestion = originalQuestion,
                originalResponse = currentAnswer,
                evaluation = currentEvaluation,
                ragContext = ragContext,
                organizationType = organizationType
            )

            currentAnswer = context.ai()
                .withDefaultLlm()
                .generateText(improvementPrompt)

            allImprovements.addAll(currentEvaluation.failedDimensions.map { it.name.lowercase() })

            // Re-evaluate if more iterations possible
            if (iteration < maxIterations) {
                val evalPrompt = promptBuilder.buildEvaluationPrompt(
                    originalQuestion = originalQuestion,
                    response = currentAnswer,
                    ragContext = ragContext,
                    organizationType = organizationType
                )

                val evalJson = context.ai()
                    .withDefaultLlm()
                    .generateText(evalPrompt)

                currentEvaluation = parseEvaluation(evalJson, System.currentTimeMillis())

                iterationHistory.add(IterationResult(
                    iteration = iteration,
                    overallScore = currentEvaluation.scores.values.average(),
                    dimensionScores = currentEvaluation.scores.mapKeys { it.key.name.lowercase() },
                    passed = currentEvaluation.passed
                ))

                if (currentEvaluation.passed && !currentEvaluation.hallucinationDetected) {
                    logger.info("Quality passed after iteration $iteration!")
                    break
                }
            }
        }

        return ImprovedResponse(
            mainAnswer = currentAnswer,
            improvementsApplied = allImprovements.toList(),
            wasImproved = true,
            improvementTimeMs = System.currentTimeMillis() - startTime,
            iterationCount = iteration,
            iterationHistory = iterationHistory
        )
    }

    /**
     * Get current thresholds as a map.
     */
    fun getThresholds(): Map<QualityDimension, Double> = mapOf(
        QualityDimension.RELEVANCE to dynamicConfig.getRelevanceThreshold(),
        QualityDimension.TONE to dynamicConfig.getToneThreshold(),
        QualityDimension.COMPLETENESS to dynamicConfig.getCompletenessThreshold(),
        QualityDimension.POLICY_COMPLIANCE to dynamicConfig.getPolicyComplianceThreshold()
    )

    private fun parseEvaluation(json: String, startTime: Long): QualityEvaluation {
        return try {
            val cleanJson = json
                .replace(Regex("```json\\s*"), "")
                .replace(Regex("```\\s*"), "")
                .trim()

            val tree = objectMapper.readTree(cleanJson)
            val scores = mapOf(
                QualityDimension.RELEVANCE to (tree["relevance"]?.asDouble() ?: 0.5),
                QualityDimension.TONE to (tree["tone"]?.asDouble() ?: 0.5),
                QualityDimension.COMPLETENESS to (tree["completeness"]?.asDouble() ?: 0.5),
                QualityDimension.POLICY_COMPLIANCE to (tree["policy_compliance"]?.asDouble() ?: 0.5)
            )

            val thresholds = getThresholds()

            logger.info("Quality thresholds: ${thresholds.map { "${it.key.name}=${it.value}" }}")
            logger.info("Quality scores: ${scores.map { "${it.key.name}=${it.value}" }}")

            val failedDimensions = scores.filter { (dim, score) ->
                val threshold = thresholds[dim] ?: 0.5
                val failed = score < threshold
                if (failed) {
                    logger.info("Dimension ${dim.name} FAILED: score=$score < threshold=$threshold")
                }
                failed
            }.keys.toList()

            val suggestions = mutableMapOf<QualityDimension, String>()
            tree["improvement_suggestions"]?.let { sugNode ->
                sugNode.fields().forEach { (key, value) ->
                    val dim = when (key) {
                        "relevance" -> QualityDimension.RELEVANCE
                        "tone" -> QualityDimension.TONE
                        "completeness" -> QualityDimension.COMPLETENESS
                        "policy_compliance" -> QualityDimension.POLICY_COMPLIANCE
                        else -> null
                    }
                    if (dim != null && !value.isNull) {
                        suggestions[dim] = value.asText()
                    }
                }
            }

            val hallucinationDetected = tree["hallucination_detected"]?.asBoolean() ?: false
            val ungroundedClaims = tree["ungrounded_claims"]?.mapNotNull { it.asText() } ?: emptyList()

            QualityEvaluation(
                scores = scores,
                passed = failedDimensions.isEmpty() && !hallucinationDetected,
                failedDimensions = failedDimensions,
                improvementSuggestions = suggestions,
                evaluationTimeMs = System.currentTimeMillis() - startTime,
                hallucinationDetected = hallucinationDetected,
                ungroundedClaims = ungroundedClaims
            )
        } catch (e: Exception) {
            logger.warn("Failed to parse quality evaluation: ${e.message}")
            QualityEvaluation(
                scores = mapOf(
                    QualityDimension.RELEVANCE to 0.5,
                    QualityDimension.TONE to 0.7,
                    QualityDimension.COMPLETENESS to 0.5,
                    QualityDimension.POLICY_COMPLIANCE to 0.5
                ),
                passed = false,
                failedDimensions = listOf(QualityDimension.RELEVANCE, QualityDimension.COMPLETENESS),
                improvementSuggestions = emptyMap(),
                evaluationTimeMs = System.currentTimeMillis() - startTime,
                hallucinationDetected = false,
                ungroundedClaims = emptyList()
            )
        }
    }
}
