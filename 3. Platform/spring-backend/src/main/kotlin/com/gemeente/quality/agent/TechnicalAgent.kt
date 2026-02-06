package com.gemeente.quality.agent

import com.embabel.agent.api.annotation.Action
import com.embabel.agent.api.annotation.AchievesGoal
import com.embabel.agent.api.annotation.Agent
import com.embabel.agent.api.common.OperationContext
import com.gemeente.quality.agent.domain.*
import com.gemeente.quality.model.*
import com.gemeente.quality.rag.RagSearchService
import com.gemeente.quality.service.ContextPromptBuilder
import com.gemeente.quality.service.DynamicConfigService
import com.gemeente.quality.service.QualityEvaluationService
import com.gemeente.quality.service.ReviewQueueService
import org.slf4j.LoggerFactory

/**
 * Specialized agent for technical AI implementation questions.
 * Handles questions about architecture, APIs, integrations, and technical best practices.
 *
 * Uses the shared QualityEvaluationService to ensure dynamic thresholds are respected.
 */
@Agent(description = "Technical specialist for AI implementation, architecture, APIs, Common Ground, and technical best practices for Dutch municipalities")
class TechnicalAgent(
    private val ragSearchService: RagSearchService,
    private val promptBuilder: ContextPromptBuilder,
    private val dynamicConfig: DynamicConfigService,
    private val qualityEvaluationService: QualityEvaluationService,
    private val reviewQueueService: ReviewQueueService
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    companion object {
        val TRIGGER_KEYWORDS = listOf(
            "api", "architectuur", "integratie", "implementatie",
            "common ground", "haven", "nlx", "digikoppeling",
            "code", "programmeren", "ontwikkelen", "developer",
            "security", "beveiliging", "authenticatie", "oauth",
            "cloud", "hosting", "infrastructure", "devops",
            "microservices", "containers", "kubernetes", "docker",
            "database", "sql", "nosql", "datamodel",
            "performance", "schaling", "monitoring", "logging"
        )
    }

    @Action(description = "Retrieve technical documentation and implementation guides")
    fun retrieveTechnicalContext(request: ChatMessage): RagContext {
        logger.info("[TechnicalAgent] Retrieving technical context for: ${request.message.take(60)}...")

        val maxResults = dynamicConfig.getMaxResults()
        val sources = ragSearchService.searchDocuments(request.message, maxResults)

        val developerSources = ragSearchService.getRoleSpecificDocuments(UserRole.DEVELOPER, 2)
        val itManagerSources = ragSearchService.getRoleSpecificDocuments(UserRole.IT_MANAGER, 2)

        val allSources = (sources + developerSources + itManagerSources)
            .distinctBy { it.documentId ?: it.title }
            .take(maxResults)

        if (allSources.isEmpty()) {
            return RagContext(
                formattedContext = "Geen relevante technische documentatie gevonden.",
                sourceReferences = emptyList(),
                knowledgeSources = emptyList(),
                hasRelevantSources = false
            )
        }

        val formattedContext = allSources.mapIndexed { i, source ->
            "[Bron ${i + 1}: ${source.title}]\n${source.snippet}"
        }.joinToString("\n\n")

        return RagContext(
            formattedContext = formattedContext,
            sourceReferences = allSources.map { it.title },
            knowledgeSources = allSources,
            hasRelevantSources = true
        )
    }

    @Action(description = "Generate technical response with implementation details")
    fun generateTechnicalResponse(
        request: ChatMessage,
        ragContext: RagContext,
        context: OperationContext
    ): InitialResponse {
        logger.info("[TechnicalAgent] Generating technical response...")
        val startTime = System.currentTimeMillis()

        val technicalPrompt = """
Je bent een technisch specialist voor AI-implementaties bij Nederlandse gemeentes. Je helpt met:
- Architectuur en systeemontwerp
- API-integraties en Common Ground
- Security en authenticatie
- Cloud en infrastructure
- Best practices voor ontwikkeling

BELANGRIJK:
- Geef concrete, praktische adviezen
- Verwijs naar open standaarden waar mogelijk
- Noem specifieke tools en frameworks
- Waarschuw voor vendor lock-in
- Geef voorbeelden van implementaties

Bronnen:
${ragContext.formattedContext}

Vraag: ${request.message}

Geef een technisch gedetailleerd antwoord met concrete stappen of voorbeelden:
""".trimIndent()

        val answer = context.ai()
            .withDefaultLlm()
            .generateText(technicalPrompt)

        val complexity = assessTechnicalComplexity(request.message)

        return InitialResponse(
            mainAnswer = answer,
            responseType = ResponseType.TECHNICAL_GUIDANCE,
            confidenceLevel = if (ragContext.hasRelevantSources) ConfidenceLevel.HIGH else ConfidenceLevel.MEDIUM,
            complexity = complexity,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = emptyList(),
            needsHumanExpert = complexity == ComplexityLevel.EXPERT_REQUIRED,
            expertReason = if (complexity == ComplexityLevel.EXPERT_REQUIRED) "Complexe technische vraag - raadpleeg een architect" else null,
            expertType = "solution architect",
            generationTimeMs = System.currentTimeMillis() - startTime
        )
    }

    @Action(description = "Evaluate quality of technical response against dynamic thresholds")
    fun evaluateTechnicalQuality(
        request: ChatMessage,
        initialResponse: InitialResponse,
        ragContext: RagContext,
        context: OperationContext
    ): QualityEvaluation {
        logger.info("[TechnicalAgent] Evaluating quality with dynamic thresholds...")
        return qualityEvaluationService.evaluateQuality(
            originalQuestion = request.message,
            response = initialResponse.mainAnswer,
            ragContext = ragContext.formattedContext,
            organizationType = request.context.organizationType,
            context = context
        )
    }

    @Action(description = "Improve technical response if quality is below thresholds")
    fun improveTechnicalResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        ragContext: RagContext,
        context: OperationContext
    ): ImprovedResponse {
        logger.info("[TechnicalAgent] Checking if improvement needed...")
        return qualityEvaluationService.improveIfNeeded(
            originalQuestion = request.message,
            originalResponse = initialResponse.mainAnswer,
            evaluation = evaluation,
            ragContext = ragContext.formattedContext,
            organizationType = request.context.organizationType,
            context = context
        )
    }

    @AchievesGoal(description = "Deliver technical response with implementation guidance and quality evaluation")
    @Action(description = "Assemble final technical response with quality metadata")
    fun assembleTechnicalResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        improvedResponse: ImprovedResponse,
        ragContext: RagContext
    ): QualityAssuredResponse {
        logger.info("[TechnicalAgent] Assembling technical response (improved=${improvedResponse.wasImproved})...")

        val totalTimeMs = initialResponse.generationTimeMs +
                evaluation.evaluationTimeMs +
                improvedResponse.improvementTimeMs

        val qualityScores = evaluation.scores.entries.associate { (dim, score) ->
            dim.name.lowercase() to score
        }

        val thresholds = qualityEvaluationService.getThresholds()
        val trace = mutableListOf<QualityTraceEntry>()

        trace.add(QualityTraceEntry(
            action = "technical_agent_selected",
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

        trace.add(QualityTraceEntry(
            action = "assemble_technical_response",
            timestampMs = System.currentTimeMillis()
        ))

        val explanation = buildString {
            append("Dit antwoord is gegenereerd door de Technische Specialist agent. ")
            append("Complexiteit: ${initialResponse.complexity.name.lowercase()}. ")
            if (improvedResponse.wasImproved) {
                append("Automatisch verbeterd op: ${improvedResponse.improvementsApplied.joinToString(", ")}. ")
            }
            append("Scores: ${qualityScores.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}")
        }

        val response = StructuredAIResponse(
            mainAnswer = improvedResponse.mainAnswer,
            responseType = ResponseType.TECHNICAL_GUIDANCE,
            confidenceLevel = initialResponse.confidenceLevel,
            complexity = initialResponse.complexity,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = emptyList(),
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

        // Auto-flag for human review if quality concerns detected
        autoFlagForReviewIfNeeded(request, response, evaluation, initialResponse)

        return QualityAssuredResponse(response = response)
    }

    private fun autoFlagForReviewIfNeeded(
        request: ChatMessage,
        response: StructuredAIResponse,
        evaluation: QualityEvaluation,
        initialResponse: InitialResponse
    ) {
        try {
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
                    agentType = "technical"
                )
                logger.info("Auto-flagged technical response for review: reason=$flagReason")
            }
        } catch (e: Exception) {
            logger.warn("Failed to auto-flag response for review: ${e.message}")
        }
    }

    private fun assessTechnicalComplexity(message: String): ComplexityLevel {
        val lower = message.lowercase()
        return when {
            lower.containsAny("architectuur", "migratie", "enterprise", "strategie") ->
                ComplexityLevel.EXPERT_REQUIRED
            lower.containsAny("integratie", "api", "security", "authenticatie") ->
                ComplexityLevel.COMPLEX
            lower.containsAny("implementatie", "configuratie", "setup") ->
                ComplexityLevel.MODERATE
            else -> ComplexityLevel.SIMPLE
        }
    }

    private fun String.containsAny(vararg terms: String): Boolean =
        terms.any { this.contains(it) }
}
