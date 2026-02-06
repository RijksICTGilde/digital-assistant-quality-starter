package com.gemeente.quality.controller

import com.gemeente.quality.model.AuditLogEntry
import com.gemeente.quality.model.AuditLogStats
import com.gemeente.quality.model.ConfigType
import com.gemeente.quality.service.AuditLogService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/admin/audit")
class AuditLogController(
    private val auditLogService: AuditLogService
) {
    @GetMapping
    fun getAllAuditLogs(): ResponseEntity<List<AuditLogEntry>> {
        return ResponseEntity.ok(auditLogService.getAll())
    }

    @GetMapping("/recent")
    fun getRecentAuditLogs(
        @RequestParam(defaultValue = "50") limit: Int
    ): ResponseEntity<List<AuditLogEntry>> {
        return ResponseEntity.ok(auditLogService.getRecent(limit))
    }

    @GetMapping("/stats")
    fun getAuditStats(): ResponseEntity<AuditLogStats> {
        return ResponseEntity.ok(auditLogService.getStats())
    }

    @GetMapping("/by-type/{type}")
    fun getByConfigType(@PathVariable type: String): ResponseEntity<List<AuditLogEntry>> {
        val configType = try {
            ConfigType.valueOf(type.uppercase())
        } catch (e: IllegalArgumentException) {
            return ResponseEntity.badRequest().build()
        }
        return ResponseEntity.ok(auditLogService.getByConfigType(configType))
    }

    @DeleteMapping("/cleanup")
    fun cleanupOldEntries(
        @RequestParam(defaultValue = "90") daysToKeep: Int
    ): ResponseEntity<Map<String, Int>> {
        val removed = auditLogService.clearOldEntries(daysToKeep)
        return ResponseEntity.ok(mapOf("removed" to removed))
    }
}
