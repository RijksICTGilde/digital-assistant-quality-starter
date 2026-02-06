package com.gemeente.quality.controller

import com.gemeente.quality.service.ConfigExport
import com.gemeente.quality.service.ConfigSnapshot
import com.gemeente.quality.service.DynamicConfigService
import com.gemeente.quality.service.RagConfigSnapshot
import com.gemeente.quality.service.ThresholdConfig
import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/admin/config")
class ConfigController(
    private val configService: DynamicConfigService
) {
    private val logger = LoggerFactory.getLogger(javaClass)
    @GetMapping
    fun getCurrentConfig(): ResponseEntity<ConfigSnapshot> {
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @GetMapping("/defaults")
    fun getDefaultConfig(): ResponseEntity<ConfigSnapshot> {
        return ResponseEntity.ok(configService.getDefaultConfig())
    }

    @PutMapping("/thresholds/{dimension}")
    fun setThreshold(
        @PathVariable dimension: String,
        @RequestBody request: ThresholdValueRequest
    ): ResponseEntity<ConfigSnapshot> {
        configService.setThreshold(dimension, request.value)
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PutMapping("/thresholds")
    fun setAllThresholds(@RequestBody thresholds: ThresholdConfig): ResponseEntity<ConfigSnapshot> {
        logger.info("setAllThresholds called with: relevance=${thresholds.relevance}, tone=${thresholds.tone}, completeness=${thresholds.completeness}, policyCompliance=${thresholds.policyCompliance}")
        configService.setAllThresholds(thresholds)
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PutMapping("/rag/similarity-threshold")
    fun setSimilarityThreshold(@RequestBody request: ThresholdValueRequest): ResponseEntity<ConfigSnapshot> {
        configService.setSimilarityThreshold(request.value)
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PutMapping("/rag/max-results")
    fun setMaxResults(@RequestBody request: IntValueRequest): ResponseEntity<ConfigSnapshot> {
        configService.setMaxResults(request.value)
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PutMapping("/max-improvement-rounds")
    fun setMaxImprovementRounds(@RequestBody request: IntValueRequest): ResponseEntity<ConfigSnapshot> {
        configService.setMaxImprovementRounds(request.value)
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PostMapping("/reset/thresholds")
    fun resetThresholds(): ResponseEntity<ConfigSnapshot> {
        configService.resetAllThresholds()
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PostMapping("/reset/thresholds/{dimension}")
    fun resetThreshold(@PathVariable dimension: String): ResponseEntity<ConfigSnapshot> {
        configService.resetThreshold(dimension)
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PostMapping("/reset/rag")
    fun resetRag(): ResponseEntity<ConfigSnapshot> {
        configService.resetRagConfig()
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @PostMapping("/reset/all")
    fun resetAll(): ResponseEntity<ConfigSnapshot> {
        configService.resetAll()
        return ResponseEntity.ok(configService.getCurrentConfig())
    }

    @GetMapping("/export")
    fun exportConfig(): ResponseEntity<ConfigExport> {
        return ResponseEntity.ok(configService.exportConfig())
    }

    @PostMapping("/import")
    fun importConfig(@RequestBody config: ConfigExport): ResponseEntity<Map<String, Any>> {
        return try {
            configService.importConfig(config)
            ResponseEntity.ok(mapOf(
                "success" to true,
                "config" to configService.getCurrentConfig()
            ))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(mapOf(
                "success" to false,
                "error" to (e.message ?: "Import failed")
            ))
        }
    }
}

data class ThresholdValueRequest(val value: Double)
data class IntValueRequest(val value: Int)
