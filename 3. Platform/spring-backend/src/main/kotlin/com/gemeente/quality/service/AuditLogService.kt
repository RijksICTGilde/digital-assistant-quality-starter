package com.gemeente.quality.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.readValue
import com.gemeente.quality.model.*
import jakarta.annotation.PostConstruct
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import java.io.File

@Service
class AuditLogService {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val auditStore = mutableListOf<AuditLogEntry>()
    private val cacheFile = File("./cache/audit-log.json")
    private val objectMapper = ObjectMapper().apply {
        registerModule(JavaTimeModule())
    }

    @PostConstruct
    fun loadFromCache() {
        if (cacheFile.exists()) {
            try {
                val entries: List<AuditLogEntry> = objectMapper.readValue(cacheFile)
                auditStore.addAll(entries)
                logger.info("Loaded ${entries.size} audit log entries from cache")
            } catch (e: Exception) {
                logger.warn("Failed to load audit log cache: ${e.message}")
            }
        }
    }

    private fun saveToCache() {
        try {
            cacheFile.parentFile?.mkdirs()
            objectMapper.writeValue(cacheFile, auditStore)
        } catch (e: Exception) {
            logger.warn("Failed to save audit log cache: ${e.message}")
        }
    }

    fun logThresholdChange(
        dimension: String,
        oldValue: Double?,
        newValue: Double,
        changedBy: String? = "admin"
    ) {
        val entry = AuditLogEntry(
            configType = ConfigType.THRESHOLD,
            action = AuditAction.SET,
            configKey = dimension,
            oldValue = oldValue?.toString(),
            newValue = newValue.toString(),
            changedBy = changedBy
        )
        auditStore.add(entry)
        saveToCache()
        logger.info("Audit: Threshold '$dimension' changed from $oldValue to $newValue")
    }

    fun logRagChange(
        key: String,
        oldValue: Any?,
        newValue: Any,
        changedBy: String? = "admin"
    ) {
        val entry = AuditLogEntry(
            configType = ConfigType.RAG,
            action = AuditAction.SET,
            configKey = key,
            oldValue = oldValue?.toString(),
            newValue = newValue.toString(),
            changedBy = changedBy
        )
        auditStore.add(entry)
        saveToCache()
        logger.info("Audit: RAG config '$key' changed from $oldValue to $newValue")
    }

    fun logThresholdReset(dimension: String, restoredValue: Double, changedBy: String? = "admin") {
        val entry = AuditLogEntry(
            configType = ConfigType.THRESHOLD,
            action = AuditAction.RESET,
            configKey = dimension,
            oldValue = null,
            newValue = restoredValue.toString(),
            changedBy = changedBy
        )
        auditStore.add(entry)
        saveToCache()
        logger.info("Audit: Threshold '$dimension' reset to default: $restoredValue")
    }

    fun logAllThresholdsReset(changedBy: String? = "admin") {
        val entry = AuditLogEntry(
            configType = ConfigType.THRESHOLD,
            action = AuditAction.RESET_ALL,
            configKey = null,
            oldValue = null,
            newValue = "defaults",
            changedBy = changedBy
        )
        auditStore.add(entry)
        saveToCache()
        logger.info("Audit: All thresholds reset to defaults")
    }

    fun logRagReset(changedBy: String? = "admin") {
        val entry = AuditLogEntry(
            configType = ConfigType.RAG,
            action = AuditAction.RESET_ALL,
            configKey = null,
            oldValue = null,
            newValue = "defaults",
            changedBy = changedBy
        )
        auditStore.add(entry)
        saveToCache()
        logger.info("Audit: RAG config reset to defaults")
    }

    fun logAllReset(changedBy: String? = "admin") {
        val entry = AuditLogEntry(
            configType = ConfigType.ALL,
            action = AuditAction.RESET_ALL,
            configKey = null,
            oldValue = null,
            newValue = "all defaults",
            changedBy = changedBy
        )
        auditStore.add(entry)
        saveToCache()
        logger.info("Audit: All configuration reset to defaults")
    }

    fun getAll(): List<AuditLogEntry> {
        return auditStore.sortedByDescending { it.timestamp }
    }

    fun getRecent(limit: Int = 50): List<AuditLogEntry> {
        return auditStore.sortedByDescending { it.timestamp }.take(limit)
    }

    fun getByConfigType(configType: ConfigType): List<AuditLogEntry> {
        return auditStore.filter { it.configType == configType }
            .sortedByDescending { it.timestamp }
    }

    fun getStats(): AuditLogStats {
        val byConfigType = auditStore
            .groupBy { it.configType.value }
            .mapValues { it.value.size }

        val byAction = auditStore
            .groupBy { it.action.value }
            .mapValues { it.value.size }

        return AuditLogStats(
            totalEntries = auditStore.size,
            byConfigType = byConfigType,
            byAction = byAction,
            lastChange = auditStore.maxByOrNull { it.timestamp }
        )
    }

    fun clearOldEntries(daysToKeep: Int = 90): Int {
        val cutoff = java.time.Instant.now().minus(java.time.Duration.ofDays(daysToKeep.toLong()))
        val initialSize = auditStore.size
        auditStore.removeIf { it.timestamp.isBefore(cutoff) }
        val removed = initialSize - auditStore.size
        if (removed > 0) {
            saveToCache()
            logger.info("Cleared $removed old audit log entries")
        }
        return removed
    }
}
