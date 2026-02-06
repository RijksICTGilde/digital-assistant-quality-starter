package com.gemeente.quality.service

import com.fasterxml.jackson.annotation.JsonProperty
import com.gemeente.quality.config.QualityConfig
import com.gemeente.quality.config.RagConfig
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service

@Service
class DynamicConfigService(
    private val qualityConfig: QualityConfig,
    private val ragConfig: RagConfig,
    private val auditLogService: AuditLogService
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    // ============================================================
    // DEFAULTS (loaded from application.yml, never modified)
    // ============================================================

    val defaultThresholds = ThresholdConfig(
        relevance = qualityConfig.thresholds.relevance,
        tone = qualityConfig.thresholds.tone,
        completeness = qualityConfig.thresholds.completeness,
        policyCompliance = qualityConfig.thresholds.policyCompliance
    )

    val defaultRagConfig = RagConfigSnapshot(
        similarityThreshold = 0.5,
        maxResults = 5,
        chunkSize = ragConfig.chunkSize
    )

    val defaultMaxImprovementRounds = qualityConfig.maxImprovementRounds
    val defaultRegressionThreshold = 0.7 // 70% similarity for regression tests

    // ============================================================
    // RUNTIME OVERRIDES (null = use default)
    // ============================================================

    private val thresholdOverrides = mutableMapOf<String, Double?>()
    private val ragOverrides = mutableMapOf<String, Any?>()
    private var maxImprovementRoundsOverride: Int? = null
    private var regressionThresholdOverride: Double? = null

    // ============================================================
    // GETTERS (used by agent and services)
    // ============================================================

    fun getRelevanceThreshold(): Double =
        thresholdOverrides["relevance"] ?: defaultThresholds.relevance

    fun getToneThreshold(): Double =
        thresholdOverrides["tone"] ?: defaultThresholds.tone

    fun getCompletenessThreshold(): Double =
        thresholdOverrides["completeness"] ?: defaultThresholds.completeness

    fun getPolicyComplianceThreshold(): Double =
        thresholdOverrides["policyCompliance"] ?: defaultThresholds.policyCompliance

    fun getSimilarityThreshold(): Double =
        (ragOverrides["similarityThreshold"] as? Double) ?: defaultRagConfig.similarityThreshold

    fun getMaxResults(): Int =
        (ragOverrides["maxResults"] as? Int) ?: defaultRagConfig.maxResults

    fun getMaxImprovementRounds(): Int =
        maxImprovementRoundsOverride ?: defaultMaxImprovementRounds

    fun getRegressionThreshold(): Double =
        regressionThresholdOverride ?: defaultRegressionThreshold

    // Get all thresholds as a map (for agent use)
    fun getThresholdsMap(): Map<String, Double> = mapOf(
        "relevance" to getRelevanceThreshold(),
        "tone" to getToneThreshold(),
        "completeness" to getCompletenessThreshold(),
        "policyCompliance" to getPolicyComplianceThreshold()
    )

    // ============================================================
    // SETTERS (called from admin dashboard)
    // ============================================================

    fun setThreshold(dimension: String, value: Double) {
        require(value in 0.0..1.0) { "Threshold must be between 0.0 and 1.0" }
        val oldValue = thresholdOverrides[dimension] ?: getDefault(dimension)
        thresholdOverrides[dimension] = value
        auditLogService.logThresholdChange(dimension, oldValue, value)
        logger.info("Threshold '$dimension' set to $value (default: ${getDefault(dimension)})")
    }

    fun setAllThresholds(thresholds: ThresholdConfig) {
        setThreshold("relevance", thresholds.relevance)
        setThreshold("tone", thresholds.tone)
        setThreshold("completeness", thresholds.completeness)
        setThreshold("policyCompliance", thresholds.policyCompliance)
    }

    fun setRagConfig(key: String, value: Any) {
        ragOverrides[key] = value
        logger.info("RAG config '$key' set to $value")
    }

    fun setSimilarityThreshold(value: Double) {
        require(value in 0.0..1.0) { "Similarity threshold must be between 0.0 and 1.0" }
        val oldValue = getSimilarityThreshold()
        ragOverrides["similarityThreshold"] = value
        auditLogService.logRagChange("similarityThreshold", oldValue, value)
        logger.info("Similarity threshold set to $value (default: ${defaultRagConfig.similarityThreshold})")
    }

    fun setMaxResults(value: Int) {
        require(value in 1..20) { "Max results must be between 1 and 20" }
        val oldValue = getMaxResults()
        ragOverrides["maxResults"] = value
        auditLogService.logRagChange("maxResults", oldValue, value)
        logger.info("Max results set to $value (default: ${defaultRagConfig.maxResults})")
    }

    fun setMaxImprovementRounds(value: Int) {
        require(value in 0..5) { "Max improvement rounds must be between 0 and 5" }
        val oldValue = getMaxImprovementRounds()
        maxImprovementRoundsOverride = value
        auditLogService.logRagChange("maxImprovementRounds", oldValue, value)
        logger.info("Max improvement rounds set to $value (default: $defaultMaxImprovementRounds)")
    }

    // ============================================================
    // RESET FUNCTIONS
    // ============================================================

    fun resetThreshold(dimension: String) {
        thresholdOverrides.remove(dimension)
        auditLogService.logThresholdReset(dimension, getDefault(dimension))
        logger.info("Threshold '$dimension' reset to default: ${getDefault(dimension)}")
    }

    fun resetAllThresholds() {
        thresholdOverrides.clear()
        auditLogService.logAllThresholdsReset()
        logger.info("All thresholds reset to defaults")
    }

    fun resetRagConfig() {
        ragOverrides.clear()
        auditLogService.logRagReset()
        logger.info("RAG config reset to defaults")
    }

    fun resetMaxImprovementRounds() {
        maxImprovementRoundsOverride = null
        logger.info("Max improvement rounds reset to default: $defaultMaxImprovementRounds")
    }

    fun resetAll() {
        thresholdOverrides.clear()
        ragOverrides.clear()
        maxImprovementRoundsOverride = null
        auditLogService.logAllReset()
        logger.info("ALL configuration reset to defaults")
    }

    // ============================================================
    // SNAPSHOT FOR UI
    // ============================================================

    fun getCurrentConfig(): ConfigSnapshot = ConfigSnapshot(
        thresholds = ThresholdConfig(
            relevance = getRelevanceThreshold(),
            tone = getToneThreshold(),
            completeness = getCompletenessThreshold(),
            policyCompliance = getPolicyComplianceThreshold()
        ),
        rag = RagConfigSnapshot(
            similarityThreshold = getSimilarityThreshold(),
            maxResults = getMaxResults(),
            chunkSize = ragConfig.chunkSize
        ),
        maxImprovementRounds = getMaxImprovementRounds(),
        isModified = thresholdOverrides.isNotEmpty() || ragOverrides.isNotEmpty() || maxImprovementRoundsOverride != null
    )

    fun getDefaultConfig(): ConfigSnapshot = ConfigSnapshot(
        thresholds = defaultThresholds,
        rag = defaultRagConfig,
        maxImprovementRounds = defaultMaxImprovementRounds,
        isModified = false
    )

    // Helper to check if a specific value differs from default
    fun isModified(key: String): Boolean =
        thresholdOverrides.containsKey(key) || ragOverrides.containsKey(key)

    private fun getDefault(dimension: String): Double = when (dimension) {
        "relevance" -> defaultThresholds.relevance
        "tone" -> defaultThresholds.tone
        "completeness" -> defaultThresholds.completeness
        "policyCompliance" -> defaultThresholds.policyCompliance
        else -> 0.5
    }

    // ============================================================
    // EXPORT/IMPORT
    // ============================================================

    fun exportConfig(): ConfigExport {
        return ConfigExport(
            exportedAt = java.time.Instant.now(),
            thresholds = ThresholdConfig(
                relevance = getRelevanceThreshold(),
                tone = getToneThreshold(),
                completeness = getCompletenessThreshold(),
                policyCompliance = getPolicyComplianceThreshold()
            ),
            rag = RagConfigSnapshot(
                similarityThreshold = getSimilarityThreshold(),
                maxResults = getMaxResults(),
                chunkSize = ragConfig.chunkSize
            ),
            maxImprovementRounds = getMaxImprovementRounds()
        )
    }

    fun importConfig(config: ConfigExport) {
        // Import thresholds
        if (config.thresholds.relevance != defaultThresholds.relevance) {
            setThreshold("relevance", config.thresholds.relevance)
        }
        if (config.thresholds.tone != defaultThresholds.tone) {
            setThreshold("tone", config.thresholds.tone)
        }
        if (config.thresholds.completeness != defaultThresholds.completeness) {
            setThreshold("completeness", config.thresholds.completeness)
        }
        if (config.thresholds.policyCompliance != defaultThresholds.policyCompliance) {
            setThreshold("policyCompliance", config.thresholds.policyCompliance)
        }

        // Import RAG settings
        if (config.rag.similarityThreshold != defaultRagConfig.similarityThreshold) {
            setSimilarityThreshold(config.rag.similarityThreshold)
        }
        if (config.rag.maxResults != defaultRagConfig.maxResults) {
            setMaxResults(config.rag.maxResults)
        }

        // Import max improvement rounds
        if (config.maxImprovementRounds != defaultMaxImprovementRounds) {
            setMaxImprovementRounds(config.maxImprovementRounds)
        }

        logger.info("Configuration imported successfully")
    }
}

data class ConfigSnapshot(
    val thresholds: ThresholdConfig,
    val rag: RagConfigSnapshot,
    @JsonProperty("max_improvement_rounds")
    val maxImprovementRounds: Int,
    @JsonProperty("is_modified")
    val isModified: Boolean
)

data class ThresholdConfig(
    val relevance: Double,
    val tone: Double,
    val completeness: Double,
    @JsonProperty("policy_compliance")
    val policyCompliance: Double
)

data class RagConfigSnapshot(
    @JsonProperty("similarity_threshold")
    val similarityThreshold: Double,
    @JsonProperty("max_results")
    val maxResults: Int,
    @JsonProperty("chunk_size")
    val chunkSize: Int
)

data class ConfigExport(
    @JsonProperty("exported_at")
    val exportedAt: java.time.Instant,
    val thresholds: ThresholdConfig,
    val rag: RagConfigSnapshot,
    @JsonProperty("max_improvement_rounds")
    val maxImprovementRounds: Int
)
