package com.gemeente.quality.agent

import com.embabel.agent.api.annotation.Action
import com.embabel.agent.api.annotation.AchievesGoal
import com.embabel.agent.api.annotation.Agent
import com.embabel.agent.api.annotation.Condition
import com.embabel.agent.api.common.OperationContext
import com.gemeente.quality.agent.domain.*
import com.gemeente.quality.config.QualityConfig
import com.gemeente.quality.model.*
import com.gemeente.quality.rag.RagSearchService
import com.gemeente.quality.service.ContextPromptBuilder
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import org.slf4j.LoggerFactory

/**
 * Quality-aware AI assistant using Embabel's GOAP planning.
 *
 * Features:
 * - @Condition methods let GOAP decide when to improve (not hardcoded if-statements)
 * - LLM role-based model selection for cost/quality optimization
 * - 5-step quality pipeline: retrieve → generate → evaluate → improve → assemble
 */
@Agent(description = "Quality-aware AI assistant for Dutch municipalities. Generates, evaluates, and improves responses with transparent quality scoring.")
class QualityAssuranceAgent(
    private val ragSearchService: RagSearchService,
    private val promptBuilder: ContextPromptBuilder,
    private val qualityConfig: QualityConfig
) {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val objectMapper = jacksonObjectMapper()

    // ==================== CONDITIONS ====================
    // Let GOAP decide when to run actions based on conditions

    /**
     * Condition: Quality evaluation indicates improvement is needed.
     * GOAP uses this to decide whether to run the improveResponse action.
     */
    @Condition
    fun needsImprovement(evaluation: QualityEvaluation): Boolean {
        val needsWork = !evaluation.passed || evaluation.hallucinationDetected
        if (needsWork) {
            logger.info("Condition needsImprovement=true: passed=${evaluation.passed}, hallucination=${evaluation.hallucinationDetected}")
        }
        return needsWork
    }

    /**
     * Condition: Quality evaluation passed all thresholds.
     * Used for actions that should only run when quality is already good.
     */
    @Condition
    fun qualityPassed(evaluation: QualityEvaluation): Boolean =
        evaluation.passed && !evaluation.hallucinationDetected

    // Step 1: Retrieve relevant context from the knowledge base
    @Action(description = "Retrieve relevant documents from the knowledge base for the user's question")
    fun retrieveContext(request: ChatMessage): RagContext {
        logger.info("Retrieving RAG context for: ${request.message.take(80)}...")
        val sources = ragSearchService.searchDocuments(request.message, 5)

        // Only include sources if they are actually relevant
        if (sources.isEmpty()) {
            logger.info("No relevant sources found for query")
            return RagContext(
                formattedContext = "Geen relevante bronnen gevonden.",
                sourceReferences = emptyList(),
                knowledgeSources = emptyList(),  // Don't show sources for off-topic questions
                hasRelevantSources = false
            )
        }

        // Build context from relevant sources
        val formattedContext = sources.take(3).mapIndexed { i, source ->
            "[Bron ${i + 1}: ${source.title}]\n${source.snippet}"
        }.joinToString("\n\n")

        val sourceRefs = sources.take(3).map { it.title }

        // Optionally add role-specific documents
        val roleSources = request.context.role?.let {
            ragSearchService.getRoleSpecificDocuments(it, 2)
        } ?: emptyList()

        val allSources = (sources + roleSources).distinctBy { it.documentId ?: it.title }

        return RagContext(
            formattedContext = formattedContext,
            sourceReferences = sourceRefs,
            knowledgeSources = allSources,
            hasRelevantSources = true
        )
    }

    // Step 2: Generate the initial AI response
    @Action(description = "Generate an initial response using the LLM with RAG context")
    fun generateInitialResponse(
        request: ChatMessage,
        ragContext: RagContext,
        context: OperationContext
    ): InitialResponse {
        logger.info("Generating initial response...")
        val startTime = System.currentTimeMillis()

        val prompt = promptBuilder.buildGenerationPrompt(
            message = request.message,
            userContext = request.context,
            ragContext = ragContext.formattedContext
        )

        val answer = context.ai()
            .withDefaultLlm()
            .generateText(prompt)

        val complexity = assessComplexity(request.message)
        val confidence = assessConfidence(ragContext.knowledgeSources)
        val regulations = detectRegulations(request.message)

        return InitialResponse(
            mainAnswer = answer,
            responseType = ResponseType.DIRECT_ANSWER,
            confidenceLevel = confidence,
            complexity = complexity,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = regulations,
            needsHumanExpert = complexity == ComplexityLevel.EXPERT_REQUIRED,
            expertReason = if (complexity == ComplexityLevel.EXPERT_REQUIRED) "Complexe juridische of technische vraag vereist menselijke expertise" else null,
            expertType = if (complexity == ComplexityLevel.EXPERT_REQUIRED) "specialist" else null,
            generationTimeMs = System.currentTimeMillis() - startTime
        )
    }

    // Step 3: Evaluate quality of the initial response across 4 dimensions
    @Action(description = "Evaluate the quality of the generated response on relevance, tone, completeness, and policy compliance")
    fun evaluateQuality(
        request: ChatMessage,
        initialResponse: InitialResponse,
        ragContext: RagContext,
        context: OperationContext
    ): QualityEvaluation {
        logger.info("Evaluating quality...")
        val startTime = System.currentTimeMillis()

        val prompt = promptBuilder.buildEvaluationPrompt(
            originalQuestion = request.message,
            response = initialResponse.mainAnswer,
            ragContext = ragContext.formattedContext,
            organizationType = request.context.organizationType
        )

        val evaluationJson = context.ai()
            .withDefaultLlm()
            .generateText(prompt)

        return parseEvaluation(evaluationJson, startTime)
    }

    // Step 4: Iteratively improve the response until quality thresholds are met
    @Action(description = "Iteratively improve the response based on quality evaluation feedback (max 3 iterations)")
    fun improveResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        ragContext: RagContext,
        context: OperationContext
    ): ImprovedResponse {
        val maxIterations = qualityConfig.maxImprovementRounds
        val iterationHistory = mutableListOf<IterationResult>()

        // Record initial evaluation
        iterationHistory.add(IterationResult(
            iteration = 0,
            overallScore = evaluation.scores.values.average(),
            dimensionScores = evaluation.scores.mapKeys { it.key.name.lowercase() },
            passed = evaluation.passed
        ))

        if (evaluation.passed && !evaluation.hallucinationDetected) {
            logger.info("Quality passed all thresholds on first evaluation, no improvement needed.")
            return ImprovedResponse(
                mainAnswer = initialResponse.mainAnswer,
                improvementsApplied = emptyList(),
                wasImproved = false,
                improvementTimeMs = 0,
                iterationCount = 0,
                iterationHistory = iterationHistory
            )
        }

        logger.info("Quality below threshold on: ${evaluation.failedDimensions}. Starting iterative improvement (max $maxIterations iterations)...")
        val startTime = System.currentTimeMillis()

        var currentAnswer = initialResponse.mainAnswer
        var currentEvaluation = evaluation
        var iteration = 0
        val allImprovements = mutableSetOf<String>()

        while (iteration < maxIterations && (!currentEvaluation.passed || currentEvaluation.hallucinationDetected)) {
            iteration++
            logger.info("Improvement iteration $iteration/$maxIterations...")

            // Generate improved response
            val improvementPrompt = promptBuilder.buildImprovementPrompt(
                originalQuestion = request.message,
                originalResponse = currentAnswer,
                evaluation = currentEvaluation,
                ragContext = ragContext.formattedContext,
                organizationType = request.context.organizationType
            )

            currentAnswer = context.ai()
                .withDefaultLlm()
                .generateText(improvementPrompt)

            // Track which dimensions were improved
            allImprovements.addAll(currentEvaluation.failedDimensions.map { it.name.lowercase() })

            // Re-evaluate the improved response
            if (iteration < maxIterations) {
                val evalPrompt = promptBuilder.buildEvaluationPrompt(
                    originalQuestion = request.message,
                    response = currentAnswer,
                    ragContext = ragContext.formattedContext,
                    organizationType = request.context.organizationType
                )

                val evalJson = context.ai()
                    .withDefaultLlm()
                    .generateText(evalPrompt)

                currentEvaluation = parseEvaluation(evalJson, System.currentTimeMillis())

                // Record iteration result
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

                logger.info("Iteration $iteration scores: ${currentEvaluation.scores.map { "${it.key}=${String.format("%.2f", it.value)}" }}")
            }
        }

        val totalTimeMs = System.currentTimeMillis() - startTime
        logger.info("Iterative improvement completed: $iteration iterations in ${totalTimeMs}ms")

        return ImprovedResponse(
            mainAnswer = currentAnswer,
            improvementsApplied = allImprovements.toList(),
            wasImproved = true,
            improvementTimeMs = totalTimeMs,
            iterationCount = iteration,
            iterationHistory = iterationHistory
        )
    }

    // Step 5: Assemble the final quality-assured response with full transparency
    @AchievesGoal(description = "Assemble the final quality-assured response with quality scores, trace, and explanation")
    @Action(description = "Combine all pipeline outputs into a transparent, quality-assured response")
    fun assembleFinalResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        improvedResponse: ImprovedResponse,
        ragContext: RagContext
    ): QualityAssuredResponse {
        logger.info("Assembling final response (improved=${improvedResponse.wasImproved})...")

        val totalTimeMs = initialResponse.generationTimeMs +
                evaluation.evaluationTimeMs +
                improvedResponse.improvementTimeMs

        val qualityScores = evaluation.scores.entries.associate { (dim, score) ->
            dim.name.lowercase() to score
        }

        val trace = buildQualityTrace(initialResponse, evaluation, improvedResponse)
        val explanation = buildDutchExplanation(evaluation, improvedResponse)

        // Only include sources if:
        // 1. RAG found relevant documents AND
        // 2. The quality evaluation shows the response is actually relevant (relevance >= threshold)
        val relevanceScore = evaluation.scores[QualityDimension.RELEVANCE] ?: 0.0
        val relevanceThreshold = qualityConfig.thresholds.relevance
        val sourcesAreRelevant = ragContext.hasRelevantSources && relevanceScore >= relevanceThreshold

        val sourcesToInclude = if (sourcesAreRelevant) {
            initialResponse.knowledgeSources
        } else {
            emptyList()
        }

        // Include original answer for before/after comparison when improved
        val originalAnswerForComparison = if (improvedResponse.wasImproved) {
            initialResponse.mainAnswer
        } else {
            null
        }

        // Convert iteration history to response format
        val iterationHistoryForResponse = if (improvedResponse.iterationHistory.isNotEmpty()) {
            improvedResponse.iterationHistory.map { iter ->
                QualityIterationEntry(
                    iteration = iter.iteration,
                    overallScore = iter.overallScore,
                    dimensionScores = iter.dimensionScores,
                    passed = iter.passed
                )
            }
        } else null

        val response = StructuredAIResponse(
            mainAnswer = improvedResponse.mainAnswer,
            responseType = initialResponse.responseType,
            confidenceLevel = if (sourcesAreRelevant) initialResponse.confidenceLevel else ConfidenceLevel.LOW,
            complexity = initialResponse.complexity,
            knowledgeSources = sourcesToInclude,
            relevantRegulations = initialResponse.relevantRegulations,
            needsHumanExpert = initialResponse.needsHumanExpert,
            expertReason = initialResponse.expertReason,
            expertType = initialResponse.expertType,
            processingTimeMs = totalTimeMs.toInt(),
            qualityScores = qualityScores,
            qualityTrace = trace,
            qualityImproved = improvedResponse.wasImproved,
            qualityExplanation = explanation,
            originalAnswer = originalAnswerForComparison,
            hallucinationDetected = evaluation.hallucinationDetected,
            ungroundedClaims = if (evaluation.ungroundedClaims.isNotEmpty()) evaluation.ungroundedClaims else null,
            improvementIterations = if (improvedResponse.wasImproved) improvedResponse.iterationCount else null,
            iterationHistory = iterationHistoryForResponse
        )

        return QualityAssuredResponse(response = response)
    }

    // --- Helper methods ---

    private fun assessComplexity(message: String): ComplexityLevel {
        val lower = message.lowercase()
        return when {
            lower.containsAny("juridisch advies", "contract", "aanbesteding", "bezwaar") ->
                ComplexityLevel.EXPERT_REQUIRED
            lower.containsAny("implementatie strategie", "architectuur design", "migratieplan") ->
                ComplexityLevel.COMPLEX
            lower.containsAny("best practices", "richtlijnen", "standaarden", "aanbevelingen") ->
                ComplexityLevel.MODERATE
            lower.containsAny("wat is", "hoe werkt", "definitie", "uitleg") ->
                ComplexityLevel.SIMPLE
            else -> ComplexityLevel.MODERATE
        }
    }

    private fun assessConfidence(sources: List<KnowledgeSource>): ConfidenceLevel {
        if (sources.isEmpty()) return ConfidenceLevel.LOW
        val avgScore = sources.map { it.relevanceScore }.average()
        return when {
            avgScore > 0.7 -> ConfidenceLevel.HIGH
            avgScore > 0.4 -> ConfidenceLevel.MEDIUM
            else -> ConfidenceLevel.LOW
        }
    }

    private fun detectRegulations(message: String): List<RegulationType> {
        val lower = message.lowercase()
        return buildList {
            if (lower.containsAny("gdpr", "avg", "privacy", "gegevens", "persoonsgegevens")) add(RegulationType.GDPR)
            if (lower.containsAny("ai act", "kunstmatige intelligentie", "ai verordening")) add(RegulationType.AI_ACT)
            if (lower.containsAny("woo", "wet open overheid", "transparantie")) add(RegulationType.WOO)
            if (lower.containsAny("archief", "archiefwet", "bewaarplicht")) add(RegulationType.ARCHIEFWET)
            if (lower.containsAny("toegankelijk", "wcag", "digitoegankelijk")) add(RegulationType.TOEGANKELIJKHEID)
        }
    }

    private fun parseEvaluation(json: String, startTime: Long): QualityEvaluation {
        return try {
            // Extract JSON from response (may contain markdown code blocks)
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

            val thresholds = mapOf(
                QualityDimension.RELEVANCE to qualityConfig.thresholds.relevance,
                QualityDimension.TONE to qualityConfig.thresholds.tone,
                QualityDimension.COMPLETENESS to qualityConfig.thresholds.completeness,
                QualityDimension.POLICY_COMPLIANCE to qualityConfig.thresholds.policyCompliance
            )

            val failedDimensions = scores.filter { (dim, score) ->
                score < (thresholds[dim] ?: 0.5)
            }.keys.toList()

            val suggestions = mutableMapOf<QualityDimension, String>()
            tree["improvement_suggestions"]?.let { sugNode ->
                sugNode.properties().forEach { (key, value) ->
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

            // Parse hallucination detection
            val hallucinationDetected = tree["hallucination_detected"]?.asBoolean() ?: false
            val ungroundedClaims = tree["ungrounded_claims"]?.mapNotNull { it.asText() } ?: emptyList()

            if (hallucinationDetected) {
                logger.warn("Hallucination detected! Ungrounded claims: $ungroundedClaims")
            }

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
            logger.warn("Failed to parse quality evaluation, using defaults: ${e.message}")
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

    private fun buildQualityTrace(
        initial: InitialResponse,
        evaluation: QualityEvaluation,
        improved: ImprovedResponse
    ): List<QualityTraceEntry> {
        val trace = mutableListOf<QualityTraceEntry>()
        val baseTime = System.currentTimeMillis()

        trace.add(QualityTraceEntry(
            action = "generate_initial_response",
            timestampMs = baseTime - initial.generationTimeMs - evaluation.evaluationTimeMs - improved.improvementTimeMs
        ))

        evaluation.scores.forEach { (dim, score) ->
            val threshold = when (dim) {
                QualityDimension.RELEVANCE -> qualityConfig.thresholds.relevance
                QualityDimension.TONE -> qualityConfig.thresholds.tone
                QualityDimension.COMPLETENESS -> qualityConfig.thresholds.completeness
                QualityDimension.POLICY_COMPLIANCE -> qualityConfig.thresholds.policyCompliance
            }
            trace.add(QualityTraceEntry(
                action = "evaluate_quality",
                dimension = dim.name.lowercase(),
                score = score,
                passed = score >= threshold,
                timestampMs = baseTime - evaluation.evaluationTimeMs - improved.improvementTimeMs
            ))
        }

        if (improved.wasImproved) {
            improved.improvementsApplied.forEach { dim ->
                trace.add(QualityTraceEntry(
                    action = "improve_response",
                    dimension = dim,
                    improvementApplied = "Response improved based on $dim feedback",
                    timestampMs = baseTime - improved.improvementTimeMs
                ))
            }
        }

        trace.add(QualityTraceEntry(
            action = "assemble_final_response",
            timestampMs = baseTime
        ))

        return trace
    }

    private fun buildDutchExplanation(
        evaluation: QualityEvaluation,
        improved: ImprovedResponse
    ): String {
        val scoreDesc = evaluation.scores.entries.joinToString(", ") { (dim, score) ->
            val label = when (dim) {
                QualityDimension.RELEVANCE -> "relevantie"
                QualityDimension.TONE -> "toon"
                QualityDimension.COMPLETENESS -> "volledigheid"
                QualityDimension.POLICY_COMPLIANCE -> "beleidsconformiteit"
            }
            "$label: ${"%.0f".format(score * 100)}%"
        }

        return if (improved.wasImproved) {
            val iterationInfo = if (improved.iterationCount > 1) {
                " Na ${improved.iterationCount} verbeterrondes."
            } else {
                ""
            }
            "Dit antwoord is automatisch verbeterd op basis van kwaliteitscontrole. " +
                    "Scores: $scoreDesc. " +
                    "Verbeterd op: ${improved.improvementsApplied.joinToString(", ")}.$iterationInfo"
        } else {
            "Dit antwoord heeft de kwaliteitscontrole doorstaan. Scores: $scoreDesc."
        }
    }

    private fun String.containsAny(vararg terms: String): Boolean =
        terms.any { this.contains(it) }
}
