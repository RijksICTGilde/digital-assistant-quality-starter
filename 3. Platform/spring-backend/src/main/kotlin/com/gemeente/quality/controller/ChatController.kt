package com.gemeente.quality.controller

import com.embabel.agent.api.invocation.AgentInvocation
import com.embabel.agent.core.AgentPlatform
import com.gemeente.quality.agent.domain.QualityAssuredResponse
import com.gemeente.quality.model.ChatMessage
import com.gemeente.quality.model.ErrorResponse
import com.gemeente.quality.model.StructuredAIResponse
import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api")
class ChatController(
    private val agentPlatform: AgentPlatform
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    @PostMapping("/chat/structured")
    fun structuredChat(@RequestBody request: ChatMessage): ResponseEntity<Any> {
        logger.info("Structured chat request: ${request.message.take(80)}...")
        return try {
            val result = AgentInvocation
                .builder(agentPlatform)
                .build(QualityAssuredResponse::class.java)
                .invoke(request)

            ResponseEntity.ok(result.response)
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

    @PostMapping("/chat")
    fun simpleChat(@RequestBody request: ChatMessage): ResponseEntity<Any> {
        // Delegate to structured endpoint
        return structuredChat(request)
    }
}
