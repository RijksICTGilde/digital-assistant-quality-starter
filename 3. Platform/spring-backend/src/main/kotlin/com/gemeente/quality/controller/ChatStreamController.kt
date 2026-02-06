package com.gemeente.quality.controller

import com.gemeente.quality.agent.AgentRouter
import com.gemeente.quality.model.ChatMessage
import com.gemeente.quality.model.QualityTraceEntry
import com.gemeente.quality.service.StreamingQualityService
import org.slf4j.LoggerFactory
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.*
import reactor.core.publisher.Flux
import reactor.core.publisher.Sinks
import java.time.Duration

/**
 * SSE streaming endpoint for real-time quality pipeline progress.
 *
 * Uses StreamingQualityService for manual step orchestration,
 * enabling real-time progress events between each pipeline step.
 */
@RestController
@RequestMapping("/api")
class ChatStreamController(
    private val streamingQualityService: StreamingQualityService,
    private val agentRouter: AgentRouter
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
     * - improvement_start: When improvement begins
     * - complete: Final response with all quality data
     * - error: If something goes wrong
     */
    @PostMapping("/chat/stream", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
    fun streamChat(@RequestBody request: ChatMessage): Flux<StreamEvent> {
        logger.info("Starting streaming chat for: ${request.message.take(50)}...")

        val sink = Sinks.many().multicast().onBackpressureBuffer<StreamEvent>()

        // Route to determine agent type (for info only)
        val routing = agentRouter.route(request.message)

        // Start the pipeline in a separate thread
        Thread {
            try {
                // Emit start event with routing info
                sink.tryEmitNext(StreamEvent(
                    type = "pipeline_start",
                    action = "quality_pipeline",
                    message = "Kwaliteitspijplijn gestart",
                    data = mapOf("agent" to routing.agentType.name.lowercase())
                ))

                // Execute the streaming pipeline with callback
                val response = streamingQualityService.executeWithStreaming(request) { type, action, message, step, totalSteps, data ->
                    logger.debug("Stream event: $type - $action - $message")
                    sink.tryEmitNext(StreamEvent(
                        type = type,
                        action = action,
                        message = message,
                        step = step,
                        totalSteps = totalSteps,
                        data = data
                    ))
                }

                // Add routing trace to response
                val routingTrace = QualityTraceEntry(
                    action = "agent_routing",
                    dimension = routing.agentType.name.lowercase(),
                    score = routing.confidence,
                    passed = true,
                    timestampMs = System.currentTimeMillis()
                )
                val responseWithRouting = response.copy(
                    qualityTrace = listOf(routingTrace) + (response.qualityTrace ?: emptyList())
                )

                // Emit final result
                sink.tryEmitNext(StreamEvent(
                    type = "complete",
                    action = "complete",
                    message = "Klaar",
                    data = mapOf("response" to responseWithRouting)
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
    val type: String,           // Event type: pipeline_start, action_start, action_complete, quality_score, improvement_start, complete, error
    val action: String,         // Current action name
    val message: String,        // Human-readable message (Dutch)
    val step: Int? = null,      // Current step number (1-indexed)
    val totalSteps: Int? = null,// Total steps in pipeline
    val data: Map<String, Any>? = null  // Additional data (scores, response, etc.)
)
