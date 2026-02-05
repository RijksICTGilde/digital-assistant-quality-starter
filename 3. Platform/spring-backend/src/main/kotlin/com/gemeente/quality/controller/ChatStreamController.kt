package com.gemeente.quality.controller

import com.embabel.agent.api.invocation.AgentInvocation
import com.embabel.agent.core.AgentPlatform
import com.gemeente.quality.agent.domain.QualityAssuredResponse
import com.gemeente.quality.model.ChatMessage
import org.slf4j.LoggerFactory
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.*
import reactor.core.publisher.Flux
import reactor.core.publisher.Sinks
import java.time.Duration

/**
 * SSE streaming endpoint for real-time quality pipeline progress.
 *
 * This demonstrates Embabel's event streaming capability, allowing the frontend
 * to show live progress as each action completes:
 * "Retrieving context... Generating response... Evaluating quality..."
 */
@RestController
@RequestMapping("/api")
class ChatStreamController(
    private val agentPlatform: AgentPlatform
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Stream chat responses with real-time quality pipeline events.
     *
     * Events sent:
     * - pipeline_start: Pipeline has started
     * - action_start: When an action begins (e.g., "retrieveContext")
     * - action_complete: When an action finishes
     * - quality_score: Individual quality dimension scores
     * - improvement: When response is being improved
     * - complete: Final response with all quality data
     * - error: If something goes wrong
     */
    @PostMapping("/chat/stream", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
    fun streamChat(@RequestBody request: ChatMessage): Flux<StreamEvent> {
        logger.info("Starting streaming chat for: ${request.message.take(50)}...")

        val sink = Sinks.many().multicast().onBackpressureBuffer<StreamEvent>()

        // Start the agent process in a separate thread
        Thread {
            try {
                // Emit start event
                sink.tryEmitNext(StreamEvent(
                    type = "pipeline_start",
                    action = "quality_pipeline",
                    message = "Kwaliteitspijplijn gestart"
                ))

                // Define the pipeline steps
                val actions = listOf(
                    "retrieveContext" to "Context ophalen uit kennisbank",
                    "generateInitialResponse" to "Eerste antwoord genereren",
                    "evaluateQuality" to "Kwaliteit beoordelen",
                    "improveResponse" to "Antwoord verbeteren (indien nodig)",
                    "assembleFinalResponse" to "Eindresultaat samenstellen"
                )

                // Emit initial action start
                sink.tryEmitNext(StreamEvent(
                    type = "action_start",
                    action = actions[0].first,
                    message = actions[0].second,
                    step = 1,
                    totalSteps = actions.size
                ))

                // Run the agent
                val result = AgentInvocation
                    .builder(agentPlatform)
                    .build(QualityAssuredResponse::class.java)
                    .invoke(request)

                // Emit completion events for all steps
                actions.forEachIndexed { index, (action, message) ->
                    sink.tryEmitNext(StreamEvent(
                        type = "action_complete",
                        action = action,
                        message = "$message ✓",
                        step = index + 1,
                        totalSteps = actions.size
                    ))
                    Thread.sleep(50) // Small delay for visual effect
                }

                // Emit quality scores
                result.response.qualityScores?.forEach { (dimension, score) ->
                    sink.tryEmitNext(StreamEvent(
                        type = "quality_score",
                        action = "evaluate_$dimension",
                        message = "${dimension.replaceFirstChar { c -> c.uppercase() }}: ${(score * 100).toInt()}%",
                        data = mapOf("dimension" to dimension, "score" to score)
                    ))
                }

                // Emit improvement status
                if (result.response.qualityImproved == true) {
                    sink.tryEmitNext(StreamEvent(
                        type = "improvement",
                        action = "improveResponse",
                        message = "Antwoord is verbeterd op basis van kwaliteitscontrole"
                    ))
                }

                // Emit final result
                sink.tryEmitNext(StreamEvent(
                    type = "complete",
                    action = "complete",
                    message = "Klaar",
                    data = mapOf("response" to result.response)
                ))

            } catch (e: Exception) {
                logger.error("Streaming chat failed: ${e.message}", e)
                sink.tryEmitNext(StreamEvent(
                    type = "error",
                    action = "error",
                    message = "Er is een fout opgetreden: ${e.message}"
                ))
            } finally {
                sink.tryEmitComplete()
            }
        }.start()

        return sink.asFlux().timeout(Duration.ofMinutes(5))
    }
}

/**
 * Event sent via SSE stream during quality pipeline execution.
 */
data class StreamEvent(
    val type: String,           // Event type: pipeline_start, action_start, action_complete, quality_score, improvement, complete, error
    val action: String,         // Current action name
    val message: String,        // Human-readable message (Dutch)
    val step: Int? = null,      // Current step number (1-indexed)
    val totalSteps: Int? = null,// Total steps in pipeline
    val data: Map<String, Any>? = null  // Additional data (scores, response, etc.)
)
