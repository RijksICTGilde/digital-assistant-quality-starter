package com.gemeente.quality.service

import com.gemeente.quality.agent.domain.*
import com.gemeente.quality.model.*
import com.gemeente.quality.model.FlagReason
import com.gemeente.quality.rag.RagSearchService
import org.slf4j.LoggerFactory
import org.springframework.ai.chat.client.ChatClient
import org.springframework.stereotype.Service
/**
 * Service for streaming quality pipeline with real-time progress updates.
 * Manually orchestrates the pipeline steps to enable SSE streaming between actions.
 */
@Service
class StreamingQualityService(
    private val ragSearchService: RagSearchService,
    private val promptBuilder: ContextPromptBuilder,
    private val dynamicConfig: DynamicConfigService,
    private val qualityEvaluationService: QualityEvaluationService,
    private val chatClient: ChatClient,
    private val reviewQueueService: ReviewQueueService
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Callback for streaming events
     */
    fun interface EventCallback {
        fun onEvent(type: String, action: String, message: String, step: Int?, totalSteps: Int?, data: Map<String, Any>?)
    }

    /**
     * Execute the quality pipeline with streaming progress events.
     */
    fun executeWithStreaming(
        request: ChatMessage,
        onEvent: EventCallback
    ): StructuredAIResponse {
        val totalSteps = 5
        var currentStep = 0

        try {
            // Step 1: Retrieve Context
            currentStep = 1
            onEvent.onEvent("action_start", "retrieveContext", "Context ophalen uit kennisbank", currentStep, totalSteps, null)

            val ragContext = retrieveContext(request)

            onEvent.onEvent("action_complete", "retrieveContext", "Context opgehaald (${ragContext.knowledgeSources.size} bronnen)", currentStep, totalSteps, null)

            // Step 2: Generate Initial Response
            currentStep = 2
            onEvent.onEvent("action_start", "generateInitialResponse", "Eerste antwoord genereren", currentStep, totalSteps, null)

            val initialResponse = generateInitialResponse(request, ragContext)

            onEvent.onEvent("action_complete", "generateInitialResponse", "Antwoord gegenereerd", currentStep, totalSteps, null)

            // Step 3: Evaluate Quality
            currentStep = 3
            onEvent.onEvent("action_start", "evaluateQuality", "Kwaliteit beoordelen", currentStep, totalSteps, null)

            val evaluation = evaluateQuality(request, initialResponse, ragContext)

            // Emit individual quality scores (keeping step context)
            evaluation.scores.forEach { (dim, score) ->
                val dimName = when (dim) {
                    QualityDimension.RELEVANCE -> "Relevantie"
                    QualityDimension.TONE -> "Toon"
                    QualityDimension.COMPLETENESS -> "Volledigheid"
                    QualityDimension.POLICY_COMPLIANCE -> "Beleidsconformiteit"
                }
                val threshold = qualityEvaluationService.getThresholds()[dim] ?: 0.5
                val passed = score >= threshold
                onEvent.onEvent(
                    "quality_score",
                    "score_${dim.name.lowercase()}",
                    "$dimName: ${(score * 100).toInt()}% ${if (passed) "✓" else "✗"}",
                    currentStep, totalSteps,
                    mapOf("dimension" to dim.name.lowercase(), "score" to score, "passed" to passed)
                )
            }

            onEvent.onEvent("action_complete", "evaluateQuality", "Kwaliteit beoordeeld", currentStep, totalSteps, null)

            // Step 4: Improve if Needed
            currentStep = 4
            val needsImprovement = !evaluation.passed || evaluation.hallucinationDetected

            if (needsImprovement) {
                onEvent.onEvent("action_start", "improveResponse", "Antwoord verbeteren", currentStep, totalSteps, null)
                onEvent.onEvent(
                    "improvement_start",
                    "improveResponse",
                    "Verbeterpunten: ${evaluation.failedDimensions.joinToString(", ") { it.name.lowercase() }}",
                    currentStep, totalSteps, null
                )
            } else {
                onEvent.onEvent("action_start", "improveResponse", "Kwaliteit voldoende, geen verbetering nodig", currentStep, totalSteps, null)
            }

            val improvedResponse = improveIfNeeded(request, initialResponse, evaluation, ragContext)

            if (improvedResponse.wasImproved) {
                onEvent.onEvent("action_complete", "improveResponse", "Antwoord verbeterd (${improvedResponse.iterationCount} ronde${if (improvedResponse.iterationCount > 1) "s" else ""})", currentStep, totalSteps, null)
            } else {
                onEvent.onEvent("action_complete", "improveResponse", "Geen verbetering nodig", currentStep, totalSteps, null)
            }

            // Step 5: Assemble Final Response
            currentStep = 5
            onEvent.onEvent("action_start", "assembleFinalResponse", "Eindresultaat samenstellen", currentStep, totalSteps, null)

            val finalResponse = assembleFinalResponse(request, initialResponse, evaluation, improvedResponse, ragContext)

            // Auto-flag for human review if quality concerns detected
            autoFlagForReviewIfNeeded(request, finalResponse, evaluation, initialResponse)

            onEvent.onEvent("action_complete", "assembleFinalResponse", "Klaar", currentStep, totalSteps, null)

            return finalResponse

        } catch (e: Exception) {
            logger.error("Streaming pipeline failed at step $currentStep: ${e.message}", e)
            throw e
        }
    }

    // --- Pipeline Steps ---

    private fun retrieveContext(request: ChatMessage): RagContext {
        val sources = ragSearchService.searchDocuments(request.message, dynamicConfig.getMaxResults())

        if (sources.isEmpty()) {
            return RagContext(
                formattedContext = "Geen relevante bronnen gevonden.",
                sourceReferences = emptyList(),
                knowledgeSources = emptyList(),
                hasRelevantSources = false
            )
        }

        val formattedContext = sources.take(3).mapIndexed { i, source ->
            "[Bron ${i + 1}: ${source.title}]\n${source.snippet}"
        }.joinToString("\n\n")

        val roleSources = request.context.role?.let {
            ragSearchService.getRoleSpecificDocuments(it, 2)
        } ?: emptyList()

        val allSources = (sources + roleSources).distinctBy { it.documentId ?: it.title }

        return RagContext(
            formattedContext = formattedContext,
            sourceReferences = sources.take(3).map { it.title },
            knowledgeSources = allSources,
            hasRelevantSources = true
        )
    }

    private fun generateInitialResponse(request: ChatMessage, ragContext: RagContext): InitialResponse {
        val startTime = System.currentTimeMillis()

        val prompt = promptBuilder.buildGenerationPrompt(
            message = request.message,
            userContext = request.context,
            ragContext = ragContext.formattedContext
        )

        val answer = chatClient.prompt()
            .user(prompt)
            .call()
            .content() ?: "Geen antwoord gegenereerd."

        return InitialResponse(
            mainAnswer = answer,
            responseType = ResponseType.DIRECT_ANSWER,
            confidenceLevel = if (ragContext.hasRelevantSources) ConfidenceLevel.HIGH else ConfidenceLevel.LOW,
            complexity = ComplexityLevel.MODERATE,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = emptyList(),
            needsHumanExpert = false,
            expertReason = null,
            expertType = null,
            generationTimeMs = System.currentTimeMillis() - startTime
        )
    }

    private fun evaluateQuality(
        request: ChatMessage,
        initialResponse: InitialResponse,
        ragContext: RagContext
    ): QualityEvaluation {
        val startTime = System.currentTimeMillis()

        val prompt = promptBuilder.buildEvaluationPrompt(
            originalQuestion = request.message,
            response = initialResponse.mainAnswer,
            ragContext = ragContext.formattedContext,
            organizationType = request.context.organizationType
        )

        val evaluationJson = chatClient.prompt()
            .user(prompt)
            .call()
            .content() ?: "{}"

        return parseEvaluation(evaluationJson, startTime)
    }

    private fun improveIfNeeded(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        ragContext: RagContext
    ): ImprovedResponse {
        if (evaluation.passed && !evaluation.hallucinationDetected) {
            return ImprovedResponse(
                mainAnswer = initialResponse.mainAnswer,
                improvementsApplied = emptyList(),
                wasImproved = false,
                improvementTimeMs = 0,
                iterationCount = 0,
                iterationHistory = listOf(IterationResult(
                    iteration = 0,
                    overallScore = evaluation.scores.values.average(),
                    dimensionScores = evaluation.scores.mapKeys { it.key.name.lowercase() },
                    passed = true
                ))
            )
        }

        val maxIterations = dynamicConfig.getMaxImprovementRounds()
        val startTime = System.currentTimeMillis()
        var currentAnswer = initialResponse.mainAnswer
        var currentEvaluation = evaluation
        var iteration = 0
        val allImprovements = mutableSetOf<String>()
        val iterationHistory = mutableListOf<IterationResult>()

        iterationHistory.add(IterationResult(
            iteration = 0,
            overallScore = evaluation.scores.values.average(),
            dimensionScores = evaluation.scores.mapKeys { it.key.name.lowercase() },
            passed = evaluation.passed
        ))

        while (iteration < maxIterations && (!currentEvaluation.passed || currentEvaluation.hallucinationDetected)) {
            iteration++

            val improvementPrompt = promptBuilder.buildImprovementPrompt(
                originalQuestion = request.message,
                originalResponse = currentAnswer,
                evaluation = currentEvaluation,
                ragContext = ragContext.formattedContext,
                organizationType = request.context.organizationType
            )

            currentAnswer = chatClient.prompt()
                .user(improvementPrompt)
                .call()
                .content() ?: currentAnswer

            allImprovements.addAll(currentEvaluation.failedDimensions.map { it.name.lowercase() })

            if (iteration < maxIterations) {
                val evalPrompt = promptBuilder.buildEvaluationPrompt(
                    originalQuestion = request.message,
                    response = currentAnswer,
                    ragContext = ragContext.formattedContext,
                    organizationType = request.context.organizationType
                )

                val evalJson = chatClient.prompt()
                    .user(evalPrompt)
                    .call()
                    .content() ?: "{}"

                currentEvaluation = parseEvaluation(evalJson, System.currentTimeMillis())

                iterationHistory.add(IterationResult(
                    iteration = iteration,
                    overallScore = currentEvaluation.scores.values.average(),
                    dimensionScores = currentEvaluation.scores.mapKeys { it.key.name.lowercase() },
                    passed = currentEvaluation.passed
                ))

                if (currentEvaluation.passed && !currentEvaluation.hallucinationDetected) {
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

    private fun assembleFinalResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        improvedResponse: ImprovedResponse,
        ragContext: RagContext
    ): StructuredAIResponse {
        val totalTimeMs = initialResponse.generationTimeMs +
                evaluation.evaluationTimeMs +
                improvedResponse.improvementTimeMs

        val qualityScores = evaluation.scores.entries.associate { (dim, score) ->
            dim.name.lowercase() to score
        }

        val thresholds = qualityEvaluationService.getThresholds()
        val trace = mutableListOf<QualityTraceEntry>()

        trace.add(QualityTraceEntry(
            action = "streaming_pipeline",
            timestampMs = System.currentTimeMillis() - totalTimeMs
        ))

        evaluation.scores.forEach { (dim, score) ->
            val threshold = thresholds[dim] ?: 0.5
            trace.add(QualityTraceEntry(
                action = "evaluate_quality",
                dimension = dim.name.lowercase(),
                score = score,
                passed = score >= threshold,
                timestampMs = System.currentTimeMillis() - improvedResponse.improvementTimeMs
            ))
        }

        if (improvedResponse.wasImproved) {
            improvedResponse.improvementsApplied.forEach { dim ->
                trace.add(QualityTraceEntry(
                    action = "improve_response",
                    dimension = dim,
                    improvementApplied = "Response improved based on $dim feedback",
                    timestampMs = System.currentTimeMillis()
                ))
            }
        }

        val explanation = if (improvedResponse.wasImproved) {
            "Dit antwoord is automatisch verbeterd. Verbeterd op: ${improvedResponse.improvementsApplied.joinToString(", ")}. " +
                    "Scores: ${qualityScores.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}"
        } else {
            "Dit antwoord heeft de kwaliteitscontrole doorstaan. " +
                    "Scores: ${qualityScores.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}"
        }

        val relevanceScore = evaluation.scores[QualityDimension.RELEVANCE] ?: 0.0
        val relevanceThreshold = dynamicConfig.getRelevanceThreshold()
        val sourcesAreRelevant = ragContext.hasRelevantSources && relevanceScore >= relevanceThreshold

        return StructuredAIResponse(
            mainAnswer = improvedResponse.mainAnswer,
            responseType = initialResponse.responseType,
            confidenceLevel = if (sourcesAreRelevant) initialResponse.confidenceLevel else ConfidenceLevel.LOW,
            complexity = initialResponse.complexity,
            knowledgeSources = if (sourcesAreRelevant) initialResponse.knowledgeSources else emptyList(),
            relevantRegulations = initialResponse.relevantRegulations,
            needsHumanExpert = initialResponse.needsHumanExpert,
            expertReason = initialResponse.expertReason,
            expertType = initialResponse.expertType,
            processingTimeMs = totalTimeMs.toInt(),
            qualityScores = qualityScores,
            qualityTrace = trace,
            qualityImproved = improvedResponse.wasImproved,
            qualityExplanation = explanation,
            originalAnswer = if (improvedResponse.wasImproved) initialResponse.mainAnswer else null,
            hallucinationDetected = evaluation.hallucinationDetected,
            ungroundedClaims = if (evaluation.ungroundedClaims.isNotEmpty()) evaluation.ungroundedClaims else null,
            improvementIterations = if (improvedResponse.wasImproved) improvedResponse.iterationCount else null,
            iterationHistory = if (improvedResponse.iterationHistory.isNotEmpty()) {
                improvedResponse.iterationHistory.map { iter ->
                    QualityIterationEntry(
                        iteration = iter.iteration,
                        overallScore = iter.overallScore,
                        dimensionScores = iter.dimensionScores,
                        passed = iter.passed
                    )
                }
            } else null
        )
    }

    private fun parseEvaluation(json: String, startTime: Long): QualityEvaluation {
        return try {
            val cleanJson = json
                .replace(Regex("```json\\s*"), "")
                .replace(Regex("```\\s*"), "")
                .trim()

            val mapper = com.fasterxml.jackson.module.kotlin.jacksonObjectMapper()
            val tree = mapper.readTree(cleanJson)

            val scores = mapOf(
                QualityDimension.RELEVANCE to (tree["relevance"]?.asDouble() ?: 0.5),
                QualityDimension.TONE to (tree["tone"]?.asDouble() ?: 0.5),
                QualityDimension.COMPLETENESS to (tree["completeness"]?.asDouble() ?: 0.5),
                QualityDimension.POLICY_COMPLIANCE to (tree["policy_compliance"]?.asDouble() ?: 0.5)
            )

            val thresholds = qualityEvaluationService.getThresholds()

            val failedDimensions = scores.filter { (dim, score) ->
                score < (thresholds[dim] ?: 0.5)
            }.keys.toList()

            val suggestions = mutableMapOf<QualityDimension, String>()
            tree["improvement_suggestions"]?.fields()?.forEach { (key, value) ->
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
            logger.warn("Failed to parse evaluation: ${e.message}")
            QualityEvaluation(
                scores = mapOf(
                    QualityDimension.RELEVANCE to 0.5,
                    QualityDimension.TONE to 0.7,
                    QualityDimension.COMPLETENESS to 0.5,
                    QualityDimension.POLICY_COMPLIANCE to 0.5
                ),
                passed = false,
                failedDimensions = listOf(QualityDimension.RELEVANCE),
                improvementSuggestions = emptyMap(),
                evaluationTimeMs = System.currentTimeMillis() - startTime,
                hallucinationDetected = false,
                ungroundedClaims = emptyList()
            )
        }
    }

    /**
     * Automatically add responses to the review queue when quality concerns are detected.
     * Triggers on: hallucination, low confidence, expert required, or quality still below threshold.
     */
    private fun autoFlagForReviewIfNeeded(
        request: ChatMessage,
        response: StructuredAIResponse,
        evaluation: QualityEvaluation,
        initialResponse: InitialResponse
    ) {
        try {
            // Calculate minimum acceptable quality as average of all thresholds
            val minQualityThreshold = listOf(
                dynamicConfig.getRelevanceThreshold(),
                dynamicConfig.getToneThreshold(),
                dynamicConfig.getCompletenessThreshold(),
                dynamicConfig.getPolicyComplianceThreshold()
            ).average()

            val flagReason: FlagReason? = when {
                evaluation.hallucinationDetected -> FlagReason.HALLUCINATION
                initialResponse.confidenceLevel == ConfidenceLevel.LOW -> FlagReason.LOW_CONFIDENCE
                initialResponse.needsHumanExpert -> FlagReason.EXPERT_REQUIRED
                // Also flag if overall quality is still below threshold after improvement
                evaluation.scores.values.average() < minQualityThreshold -> FlagReason.LOW_CONFIDENCE
                else -> null
            }

            if (flagReason != null) {
                reviewQueueService.addToQueue(
                    originalQuestion = request.message,
                    aiResponse = response.mainAnswer,
                    flagReason = flagReason,
                    qualityScores = response.qualityScores,
                    hallucinationDetected = evaluation.hallucinationDetected,
                    ungroundedClaims = evaluation.ungroundedClaims.takeIf { it.isNotEmpty() },
                    confidenceLevel = response.confidenceLevel.value,
                    agentType = "streaming"
                )
                logger.info("Auto-flagged response for review: reason=$flagReason, avgScore=${evaluation.scores.values.average()}, threshold=$minQualityThreshold")
            }
        } catch (e: Exception) {
            // Don't let flagging errors break the response flow
            logger.warn("Failed to auto-flag response for review: ${e.message}")
        }
    }
}
