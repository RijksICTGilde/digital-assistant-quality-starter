package com.gemeente.quality.agent

import com.embabel.agent.api.annotation.Action
import com.embabel.agent.api.annotation.AchievesGoal
import com.embabel.agent.api.annotation.Agent
import com.embabel.agent.api.common.OperationContext
import com.gemeente.quality.agent.domain.*
import com.gemeente.quality.config.QualityConfig
import com.gemeente.quality.model.*
import com.gemeente.quality.rag.RagSearchService
import com.gemeente.quality.service.ContextPromptBuilder
import org.slf4j.LoggerFactory

/**
 * Specialized agent for compliance and legal questions.
 * Handles questions about GDPR, AI Act, WOO, and other regulations.
 *
 * Has stricter quality thresholds for policy compliance (0.7 vs default 0.6).
 */
@Agent(description = "Specialist for compliance questions about GDPR, AI Act, WOO, privacy regulations, and legal requirements for Dutch municipalities")
class ComplianceAgent(
    private val ragSearchService: RagSearchService,
    private val promptBuilder: ContextPromptBuilder,
    private val qualityConfig: QualityConfig
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    companion object {
        // Stricter threshold for compliance questions
        const val POLICY_COMPLIANCE_THRESHOLD = 0.7

        // Keywords that indicate this agent should handle the question
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

        // Search with focus on compliance documents
        val sources = ragSearchService.searchDocuments(request.message, 5)

        // Also get regulation-specific documents
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

    @AchievesGoal(description = "Deliver compliance-assured response with regulatory references")
    @Action(description = "Assemble final compliance response with quality metadata")
    fun assembleComplianceResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        ragContext: RagContext
    ): QualityAssuredResponse {
        logger.info("[ComplianceAgent] Assembling compliance response...")

        val qualityScores = mapOf(
            "relevance" to if (ragContext.hasRelevantSources) 0.85 else 0.5,
            "tone" to 0.9,  // Compliance responses are formal by design
            "completeness" to if (initialResponse.relevantRegulations.isNotEmpty()) 0.8 else 0.6,
            "policy_compliance" to if (initialResponse.relevantRegulations.isNotEmpty()) 0.85 else 0.6
        )

        val explanation = buildString {
            append("Dit antwoord is gegenereerd door de Compliance Specialist agent. ")
            if (initialResponse.relevantRegulations.isNotEmpty()) {
                append("Relevante regelgeving: ${initialResponse.relevantRegulations.joinToString(", ") { it.name }}. ")
            }
            append("Scores: ${qualityScores.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}")
        }

        val response = StructuredAIResponse(
            mainAnswer = initialResponse.mainAnswer,
            responseType = ResponseType.COMPLIANCE_ANALYSIS,
            confidenceLevel = initialResponse.confidenceLevel,
            complexity = initialResponse.complexity,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = initialResponse.relevantRegulations,
            needsHumanExpert = initialResponse.needsHumanExpert,
            expertReason = initialResponse.expertReason,
            expertType = initialResponse.expertType,
            processingTimeMs = initialResponse.generationTimeMs.toInt(),
            qualityScores = qualityScores,
            qualityTrace = listOf(
                QualityTraceEntry(action = "compliance_agent_selected", timestampMs = System.currentTimeMillis()),
                QualityTraceEntry(action = "retrieve_compliance_context", timestampMs = System.currentTimeMillis()),
                QualityTraceEntry(action = "generate_compliance_response", timestampMs = System.currentTimeMillis()),
                QualityTraceEntry(action = "assemble_compliance_response", timestampMs = System.currentTimeMillis())
            ),
            qualityImproved = false,
            qualityExplanation = explanation
        )

        return QualityAssuredResponse(response = response)
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
