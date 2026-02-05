package com.gemeente.quality.controller

import com.gemeente.quality.rag.DocumentLoaderService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.time.Instant

@RestController
@RequestMapping("/api")
class HealthController(
    private val documentLoaderService: DocumentLoaderService
) {
    private val startTime = Instant.now()

    @GetMapping("/health")
    fun health(): ResponseEntity<Map<String, Any>> {
        return ResponseEntity.ok(mapOf(
            "status" to "healthy",
            "service" to "gemeente-quality-agent",
            "framework" to "spring-boot-embabel",
            "uptime_seconds" to java.time.Duration.between(startTime, Instant.now()).seconds,
            "knowledge_base" to mapOf(
                "loaded" to documentLoaderService.isLoaded,
                "documents" to documentLoaderService.documentCount,
                "chunks" to documentLoaderService.chunkCount
            )
        ))
    }

    @GetMapping("/ready")
    fun ready(): ResponseEntity<Map<String, Any>> {
        val isReady = documentLoaderService.isLoaded
        val response = mapOf(
            "ready" to isReady,
            "knowledge_base_loaded" to documentLoaderService.isLoaded
        )
        return if (isReady) ResponseEntity.ok(response)
        else ResponseEntity.status(503).body(response)
    }

    @GetMapping("/live")
    fun live(): ResponseEntity<Map<String, String>> {
        return ResponseEntity.ok(mapOf("status" to "alive"))
    }
}
