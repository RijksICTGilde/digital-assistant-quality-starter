package com.gemeente.quality.rag

import com.gemeente.quality.model.KnowledgeSource
import com.gemeente.quality.model.RegulationType
import com.gemeente.quality.model.UserRole
import com.gemeente.quality.service.DynamicConfigService
import org.slf4j.LoggerFactory
import org.springframework.ai.document.Document
import org.springframework.ai.vectorstore.SearchRequest
import org.springframework.ai.vectorstore.SimpleVectorStore
import org.springframework.stereotype.Service

@Service
class RagSearchService(
    private val vectorStore: SimpleVectorStore,
    private val documentLoaderService: DocumentLoaderService,
    private val dynamicConfig: DynamicConfigService
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    fun searchDocuments(query: String, maxResults: Int? = null): List<KnowledgeSource> {
        if (!documentLoaderService.isLoaded) return emptyList()

        val effectiveMaxResults = maxResults ?: dynamicConfig.getMaxResults()
        val results = vectorStore.similaritySearch(
            SearchRequest.builder()
                .query(query)
                .topK(effectiveMaxResults)
                .similarityThreshold(dynamicConfig.getSimilarityThreshold())
                .build()
        )
        return results.map { doc -> toKnowledgeSource(doc) }
    }

    fun hasRelevantDocuments(query: String): Boolean {
        if (!documentLoaderService.isLoaded) return false
        val results = vectorStore.similaritySearch(
            SearchRequest.builder()
                .query(query)
                .topK(1)
                .similarityThreshold(dynamicConfig.getSimilarityThreshold())
                .build()
        )
        return results.isNotEmpty()
    }

    fun getContextForQuery(query: String, maxChunks: Int = 3): Pair<String, List<String>> {
        val results = searchDocuments(query, maxChunks)
        if (results.isEmpty()) return Pair("Geen relevante bronnen gevonden.", emptyList())

        val context = results.mapIndexed { i, source ->
            "[Bron ${i + 1}: ${source.title}]\n${source.snippet}"
        }.joinToString("\n\n")

        val sourceRefs = results.map { it.title }
        return Pair(context, sourceRefs)
    }

    fun getRoleSpecificDocuments(role: UserRole, maxResults: Int = 3): List<KnowledgeSource> {
        val roleQuery = when (role) {
            UserRole.DIGITAL_GUIDE -> "digitale transformatie gemeenten begeleiding"
            UserRole.CIVIL_SERVANT -> "regelgeving compliance ambtenaren overheid"
            UserRole.IT_MANAGER -> "IT architectuur standaarden overheid"
            UserRole.PROJECT_MANAGER -> "projectmanagement digitalisering overheid"
            UserRole.DEVELOPER -> "API standaarden ontwikkeling overheid"
            UserRole.OTHER -> "digitale overheid algemeen"
        }
        return searchDocuments(roleQuery, maxResults)
    }

    fun getComplianceDocuments(regulation: RegulationType, maxResults: Int = 3): List<KnowledgeSource> {
        val query = when (regulation) {
            RegulationType.GDPR -> "AVG GDPR privacy gegevensbescherming"
            RegulationType.AI_ACT -> "AI Act verordening kunstmatige intelligentie"
            RegulationType.WOO -> "Wet open overheid Woo transparantie"
            RegulationType.ARCHIEFWET -> "Archiefwet digitale archivering"
            RegulationType.TOEGANKELIJKHEID -> "digitale toegankelijkheid WCAG"
            RegulationType.GENERAL -> "regelgeving overheid digitalisering"
        }
        return searchDocuments(query, maxResults)
    }

    fun getStatistics(): Map<String, Any> {
        return mapOf(
            "total_documents" to documentLoaderService.documentCount,
            "total_chunks" to documentLoaderService.chunkCount,
            "is_loaded" to documentLoaderService.isLoaded,
            "loaded_from_cache" to documentLoaderService.loadedFromCache,
            "status" to if (documentLoaderService.isLoaded) "ready" else "loading",
            "similarity_threshold" to dynamicConfig.getSimilarityThreshold(),
            "max_results" to dynamicConfig.getMaxResults()
        )
    }

    private fun toKnowledgeSource(doc: Document): KnowledgeSource {
        val meta = doc.metadata
        // Get the actual similarity score from Spring AI (stored as "distance" or "score")
        val score = (meta["score"] as? Number)?.toDouble()
            ?: (meta["distance"] as? Number)?.toDouble()?.let { 1.0 - it }  // Convert distance to similarity
            ?: 0.5  // Default if not available

        return KnowledgeSource(
            title = (meta["section_title"] as? String)
                ?: (meta["title"] as? String)
                ?: (meta["file_name"] as? String)
                ?: "Document",
            url = meta["url"] as? String,
            snippet = doc.text?.take(500) ?: "",
            relevanceScore = score,
            documentType = meta["document_type"] as? String ?: "knowledge_base",
            documentId = meta["file_name"] as? String,
            filePath = meta["file_path"] as? String,
            sectionTitle = meta["section_title"] as? String,
            chunkIndex = (meta["chunk_index"] as? Number)?.toInt(),
            totalChunks = (meta["total_chunks"] as? Number)?.toInt(),
            originalUrl = meta["original_url"] as? String,
            documentTitle = meta["title"] as? String
        )
    }
}
