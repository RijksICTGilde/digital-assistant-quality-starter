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
 * Specialized agent for compliance and legal questions.
 * Handles questions about GDPR, AI Act, WOO, and other regulations.
 *
 * Uses the shared QualityEvaluationService to ensure dynamic thresholds are respected.
 */
@Agent(description = "Specialist for compliance questions about GDPR, AI Act, WOO, privacy regulations, and legal requirements for Dutch municipalities")
class ComplianceAgent(
    private val ragSearchService: RagSearchService,
    private val promptBuilder: ContextPromptBuilder,
    private val dynamicConfig: DynamicConfigService,
    private val qualityEvaluationService: QualityEvaluationService,
    private val reviewQueueService: ReviewQueueService
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    companion object {
        val TRIGGER_KEYWORDS = listOf(
            "gdpr", "avg", "privacy", "persoonsgegevens",
            "ai act", "ai verordening", "kunstmatige intelligentie wet",
            "woo", "wet open overheid", "transparantie", "openbaarheid",
            "archiefwet", "bewaarplicht",
            "toegankelijkheid", "wcag", "digitoegankelijk",
            "compliance", "regelgeving", "wetgeving", "juridisch",
            "aansprakelijkheid", "risico", "audit"
        )
    }

    @Action(description = "Retrieve compliance-specific documents from knowledge base")
    fun retrieveComplianceContext(request: ChatMessage): RagContext {
        logger.info("[ComplianceAgent] Retrieving compliance context for: ${request.message.take(60)}...")

        val sources = ragSearchService.searchDocuments(request.message, dynamicConfig.getMaxResults())
        val regulations = detectRegulations(request.message)
        val regulationSources = regulations.flatMap { reg ->
            ragSearchService.getComplianceDocuments(reg, 2)
        }

        val allSources = (sources + regulationSources).distinctBy { it.documentId ?: it.title }.take(5)

        if (allSources.isEmpty()) {
            return RagContext(
                formattedContext = "Geen relevante compliance bronnen gevonden.",
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

    @Action(description = "Generate compliance-focused response with legal accuracy")
    fun generateComplianceResponse(
        request: ChatMessage,
        ragContext: RagContext,
        context: OperationContext
    ): InitialResponse {
        logger.info("[ComplianceAgent] Generating compliance response...")
        val startTime = System.currentTimeMillis()

        val compliancePrompt = """
Je bent een compliance-specialist voor Nederlandse gemeentes. Je beantwoordt vragen over:
- GDPR/AVG en privacy wetgeving
- AI Act en AI-regelgeving
- Wet open overheid (WOO)
- Archiefwet en bewaartermijnen
- Digitale toegankelijkheid (WCAG)

BELANGRIJK:
- Wees nauwkeurig over wettelijke vereisten
- Geef concrete artikelnummers waar mogelijk
- Waarschuw voor risico's en aansprakelijkheid
- Verwijs naar officiële bronnen
- Als je het niet zeker weet, zeg dat expliciet

Bronnen:
${ragContext.formattedContext}

Vraag: ${request.message}

Geef een uitgebreid, juridisch accuraat antwoord:
""".trimIndent()

        val answer = context.ai()
            .withDefaultLlm()
            .generateText(compliancePrompt)

        val regulations = detectRegulations(request.message)

        return InitialResponse(
            mainAnswer = answer,
            responseType = ResponseType.COMPLIANCE_ANALYSIS,
            confidenceLevel = if (ragContext.hasRelevantSources) ConfidenceLevel.HIGH else ConfidenceLevel.LOW,
            complexity = ComplexityLevel.COMPLEX,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = regulations,
            needsHumanExpert = regulations.isEmpty() && !ragContext.hasRelevantSources,
            expertReason = if (regulations.isEmpty()) "Geen specifieke regelgeving geïdentificeerd - juridische verificatie aanbevolen" else null,
            expertType = "juridisch adviseur",
            generationTimeMs = System.currentTimeMillis() - startTime
        )
    }

    @Action(description = "Evaluate quality of compliance response against dynamic thresholds")
    fun evaluateComplianceQuality(
        request: ChatMessage,
        initialResponse: InitialResponse,
        ragContext: RagContext,
        context: OperationContext
    ): QualityEvaluation {
        logger.info("[ComplianceAgent] Evaluating quality with dynamic thresholds...")
        return qualityEvaluationService.evaluateQuality(
            originalQuestion = request.message,
            response = initialResponse.mainAnswer,
            ragContext = ragContext.formattedContext,
            organizationType = request.context.organizationType,
            context = context
        )
    }

    @Action(description = "Improve compliance response if quality is below thresholds")
    fun improveComplianceResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        ragContext: RagContext,
        context: OperationContext
    ): ImprovedResponse {
        logger.info("[ComplianceAgent] Checking if improvement needed...")
        return qualityEvaluationService.improveIfNeeded(
            originalQuestion = request.message,
            originalResponse = initialResponse.mainAnswer,
            evaluation = evaluation,
            ragContext = ragContext.formattedContext,
            organizationType = request.context.organizationType,
            context = context
        )
    }

    @AchievesGoal(description = "Deliver compliance-assured response with regulatory references and quality evaluation")
    @Action(description = "Assemble final compliance response with quality metadata")
    fun assembleComplianceResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        evaluation: QualityEvaluation,
        improvedResponse: ImprovedResponse,
        ragContext: RagContext
    ): QualityAssuredResponse {
        logger.info("[ComplianceAgent] Assembling compliance response (improved=${improvedResponse.wasImproved})...")

        val totalTimeMs = initialResponse.generationTimeMs +
                evaluation.evaluationTimeMs +
                improvedResponse.improvementTimeMs

        // Use actual evaluation scores, not hardcoded
        val qualityScores = evaluation.scores.entries.associate { (dim, score) ->
            dim.name.lowercase() to score
        }

        val thresholds = qualityEvaluationService.getThresholds()
        val trace = mutableListOf<QualityTraceEntry>()

        trace.add(QualityTraceEntry(
            action = "compliance_agent_selected",
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
            action = "assemble_compliance_response",
            timestampMs = System.currentTimeMillis()
        ))

        val explanation = buildString {
            append("Dit antwoord is gegenereerd door de Compliance Specialist agent. ")
            if (initialResponse.relevantRegulations.isNotEmpty()) {
                append("Relevante regelgeving: ${initialResponse.relevantRegulations.joinToString(", ") { it.name }}. ")
            }
            if (improvedResponse.wasImproved) {
                append("Automatisch verbeterd op: ${improvedResponse.improvementsApplied.joinToString(", ")}. ")
            }
            append("Scores: ${qualityScores.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}")
        }

        val response = StructuredAIResponse(
            mainAnswer = improvedResponse.mainAnswer,
            responseType = ResponseType.COMPLIANCE_ANALYSIS,
            confidenceLevel = initialResponse.confidenceLevel,
            complexity = initialResponse.complexity,
            knowledgeSources = ragContext.knowledgeSources,
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
                    agentType = "compliance"
                )
                logger.info("Auto-flagged compliance response for review: reason=$flagReason")
            }
        } catch (e: Exception) {
            logger.warn("Failed to auto-flag response for review: ${e.message}")
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

    private fun String.containsAny(vararg terms: String): Boolean =
        terms.any { this.contains(it) }
}
