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
 * Specialized agent for technical AI implementation questions.
 * Handles questions about architecture, APIs, integrations, and technical best practices.
 *
 * Focuses on completeness (code examples, step-by-step guides).
 */
@Agent(description = "Technical specialist for AI implementation, architecture, APIs, Common Ground, and technical best practices for Dutch municipalities")
class TechnicalAgent(
    private val ragSearchService: RagSearchService,
    private val promptBuilder: ContextPromptBuilder,
    private val qualityConfig: QualityConfig
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    companion object {
        // Keywords that indicate this agent should handle the question
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

        val sources = ragSearchService.searchDocuments(request.message, 5)

        // Also search for role-specific technical docs
        val developerSources = ragSearchService.getRoleSpecificDocuments(UserRole.DEVELOPER, 2)
        val itManagerSources = ragSearchService.getRoleSpecificDocuments(UserRole.IT_MANAGER, 2)

        val allSources = (sources + developerSources + itManagerSources)
            .distinctBy { it.documentId ?: it.title }
            .take(5)

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

    @AchievesGoal(description = "Deliver technical response with implementation guidance")
    @Action(description = "Assemble final technical response with quality metadata")
    fun assembleTechnicalResponse(
        request: ChatMessage,
        initialResponse: InitialResponse,
        ragContext: RagContext
    ): QualityAssuredResponse {
        logger.info("[TechnicalAgent] Assembling technical response...")

        val qualityScores = mapOf(
            "relevance" to if (ragContext.hasRelevantSources) 0.85 else 0.5,
            "tone" to 0.85,
            "completeness" to 0.8,  // Technical responses aim for completeness
            "policy_compliance" to 0.75  // Technical focus, less policy-heavy
        )

        val explanation = buildString {
            append("Dit antwoord is gegenereerd door de Technische Specialist agent. ")
            append("Complexiteit: ${initialResponse.complexity.name.lowercase()}. ")
            append("Scores: ${qualityScores.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}")
        }

        val response = StructuredAIResponse(
            mainAnswer = initialResponse.mainAnswer,
            responseType = ResponseType.TECHNICAL_GUIDANCE,
            confidenceLevel = initialResponse.confidenceLevel,
            complexity = initialResponse.complexity,
            knowledgeSources = ragContext.knowledgeSources,
            relevantRegulations = emptyList(),
            needsHumanExpert = initialResponse.needsHumanExpert,
            expertReason = initialResponse.expertReason,
            expertType = initialResponse.expertType,
            processingTimeMs = initialResponse.generationTimeMs.toInt(),
            qualityScores = qualityScores,
            qualityTrace = listOf(
                QualityTraceEntry(action = "technical_agent_selected", timestampMs = System.currentTimeMillis()),
                QualityTraceEntry(action = "retrieve_technical_context", timestampMs = System.currentTimeMillis()),
                QualityTraceEntry(action = "generate_technical_response", timestampMs = System.currentTimeMillis()),
                QualityTraceEntry(action = "assemble_technical_response", timestampMs = System.currentTimeMillis())
            ),
            qualityImproved = false,
            qualityExplanation = explanation
        )

        return QualityAssuredResponse(response = response)
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
