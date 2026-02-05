package com.gemeente.quality.controller

import com.embabel.agent.api.invocation.AgentInvocation
import com.embabel.agent.core.AgentPlatform
import com.gemeente.quality.agent.AgentRouter
import com.gemeente.quality.agent.AgentRouter.AgentType
import com.gemeente.quality.agent.domain.QualityAssuredResponse
import com.gemeente.quality.model.ChatMessage
import com.gemeente.quality.model.ErrorResponse
import com.gemeente.quality.model.QualityTraceEntry
import com.gemeente.quality.model.StructuredAIResponse
import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api")
class ChatController(
    private val agentPlatform: AgentPlatform,
    private val agentRouter: AgentRouter
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    @PostMapping("/chat/structured")
    fun structuredChat(@RequestBody request: ChatMessage): ResponseEntity<Any> {
        logger.info("Structured chat request: ${request.message.take(80)}...")

        // Route to appropriate specialized agent
        val routing = agentRouter.route(request.message)
        logger.info("Agent routing: ${routing.agentType} - ${routing.reason}")

        return try {
            // Embabel will automatically select the best agent based on @Agent descriptions
            // The routing info is added for transparency
            val result = AgentInvocation
                .builder(agentPlatform)
                .build(QualityAssuredResponse::class.java)
                .invoke(request)

            // Add routing info to response trace
            val routingTrace = QualityTraceEntry(
                action = "agent_routing",
                dimension = routing.agentType.name.lowercase(),
                score = routing.confidence,
                passed = true,
                timestampMs = System.currentTimeMillis()
            )

            val response = result.response.copy(
                qualityTrace = listOf(routingTrace) + (result.response.qualityTrace ?: emptyList())
            )

            ResponseEntity.ok(response)
        } catch (e: Exception) {
            logger.error("Chat failed: ${e.message}", e)
            ResponseEntity.internalServerError().body(
                ErrorResponse(
                    errorType = "processing_error",
                    errorMessage = "Er is een fout opgetreden bij het verwerken van uw vraag.",
                    technicalDetails = e.message,
                    suggestedAction = "Probeer het opnieuw of neem contact op met ondersteuning.",
                    needsHumanHelp = true
                )
            )
        }
    }

    /**
     * Get routing decision without executing (for debugging/transparency)
     */
    @PostMapping("/chat/route")
    fun getRouting(@RequestBody request: ChatMessage): ResponseEntity<AgentRouter.RoutingDecision> {
        val routing = agentRouter.route(request.message)
        return ResponseEntity.ok(routing)
    }

    @PostMapping("/chat")
    fun simpleChat(@RequestBody request: ChatMessage): ResponseEntity<Any> {
        // Delegate to structured endpoint
        return structuredChat(request)
    }
}
