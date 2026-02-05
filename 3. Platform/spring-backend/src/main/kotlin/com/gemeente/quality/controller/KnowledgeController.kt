package com.gemeente.quality.controller

import com.gemeente.quality.model.KnowledgeSource
import com.gemeente.quality.model.RegulationType
import com.gemeente.quality.model.UserRole
import com.gemeente.quality.rag.RagSearchService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api")
class KnowledgeController(
    private val ragSearchService: RagSearchService
) {

    @GetMapping("/knowledge/search")
    fun searchKnowledge(
        @RequestParam query: String,
        @RequestParam(defaultValue = "5") limit: Int
    ): ResponseEntity<List<KnowledgeSource>> {
        return ResponseEntity.ok(ragSearchService.searchDocuments(query, limit))
    }

    @GetMapping("/knowledge/role/{role}")
    fun getRoleDocuments(@PathVariable role: String): ResponseEntity<List<KnowledgeSource>> {
        val userRole = UserRole.fromValue(role)
        return ResponseEntity.ok(ragSearchService.getRoleSpecificDocuments(userRole))
    }

    @GetMapping("/knowledge/compliance/{regulation}")
    fun getComplianceDocuments(@PathVariable regulation: String): ResponseEntity<List<KnowledgeSource>> {
        val regType = try {
            RegulationType.valueOf(regulation.uppercase())
        } catch (e: IllegalArgumentException) {
            RegulationType.GENERAL
        }
        return ResponseEntity.ok(ragSearchService.getComplianceDocuments(regType))
    }

    @GetMapping("/knowledge/stats")
    fun getStatistics(): ResponseEntity<Map<String, Any>> {
        return ResponseEntity.ok(ragSearchService.getStatistics())
    }

    @GetMapping("/enhanced-rag/context")
    fun getContext(@RequestParam query: String): ResponseEntity<Map<String, Any>> {
        val (context, sources) = ragSearchService.getContextForQuery(query)
        return ResponseEntity.ok(mapOf(
            "context" to context,
            "sources" to sources
        ))
    }
}
