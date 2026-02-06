package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.annotation.JsonValue
import java.time.Instant
import java.util.UUID

data class AuditLogEntry(
    val id: String = UUID.randomUUID().toString(),
    val timestamp: Instant = Instant.now(),
    @JsonProperty("config_type")
    val configType: ConfigType,
    val action: AuditAction,
    @JsonProperty("config_key")
    val configKey: String?,
    @JsonProperty("old_value")
    val oldValue: String?,
    @JsonProperty("new_value")
    val newValue: String?,
    @JsonProperty("changed_by")
    val changedBy: String? = "admin" // Could be user ID in future
)

enum class ConfigType(@JsonValue val value: String) {
    THRESHOLD("threshold"),
    RAG("rag"),
    ALL("all")
}

enum class AuditAction(@JsonValue val value: String) {
    SET("set"),
    RESET("reset"),
    RESET_ALL("reset_all")
}

data class AuditLogStats(
    @JsonProperty("total_entries")
    val totalEntries: Int,
    @JsonProperty("by_config_type")
    val byConfigType: Map<String, Int>,
    @JsonProperty("by_action")
    val byAction: Map<String, Int>,
    @JsonProperty("last_change")
    val lastChange: AuditLogEntry?
)
