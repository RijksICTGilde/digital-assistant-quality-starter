package com.gemeente.quality.rag

import com.gemeente.quality.config.RagConfig
import jakarta.annotation.PostConstruct
import org.slf4j.LoggerFactory
import org.springframework.ai.document.Document
import org.springframework.ai.transformer.splitter.TokenTextSplitter
import org.springframework.ai.vectorstore.SimpleVectorStore
import org.springframework.stereotype.Service
import java.io.File
import java.nio.file.Files
import java.nio.file.Path
import kotlin.concurrent.thread

@Service
class DocumentLoaderService(
    private val vectorStore: SimpleVectorStore,
    private val ragConfig: RagConfig
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    final var documentCount: Int = 0
        private set
    final var chunkCount: Int = 0
        private set
    @Volatile
    final var isLoaded: Boolean = false
        private set
    @Volatile
    final var loadedFromCache: Boolean = false
        private set

    @PostConstruct
    fun init() {
        val cacheFile = File(ragConfig.cachePath)
        val statsFile = File(ragConfig.cachePath.replace(".json", "-stats.json"))

        if (cacheFile.exists()) {
            try {
                vectorStore.load(cacheFile)
                isLoaded = true
                loadedFromCache = true

                // Load stats from companion file
                if (statsFile.exists()) {
                    try {
                        val stats = statsFile.readText().split(",")
                        documentCount = stats.getOrNull(0)?.toIntOrNull() ?: 0
                        chunkCount = stats.getOrNull(1)?.toIntOrNull() ?: 0
                    } catch (e: Exception) {
                        logger.warn("Could not read stats file, estimating from cache size")
                        // Estimate based on file size (roughly 5KB per chunk)
                        chunkCount = (cacheFile.length() / 5000).toInt().coerceAtLeast(1)
                        documentCount = (chunkCount / 10).coerceAtLeast(1)
                    }
                } else {
                    // Estimate based on file size
                    chunkCount = (cacheFile.length() / 5000).toInt().coerceAtLeast(1)
                    documentCount = (chunkCount / 10).coerceAtLeast(1)
                }

                logger.info("Loaded vector store from cache: ${cacheFile.absolutePath} (~$documentCount docs, ~$chunkCount chunks)")
                return
            } catch (e: Exception) {
                logger.warn("Failed to load cache, rebuilding: ${e.message}")
            }
        }
        // Load documents in background thread so app starts immediately
        thread(name = "document-loader", isDaemon = true) {
            try {
                loadDocuments()
            } catch (e: Exception) {
                logger.error("Background document loading failed: ${e.message}. RAG will be unavailable.")
            }
        }
    }

    fun loadDocuments() {
        val docsPath = Path.of(ragConfig.documentsPath)
        if (!Files.exists(docsPath)) {
            logger.error("Documents directory not found: ${docsPath.toAbsolutePath()}")
            return
        }

        logger.info("Loading documents from: ${docsPath.toAbsolutePath()}")
        val documents = mutableListOf<Document>()

        Files.walk(docsPath)
            .filter { it.toString().endsWith(".md") }
            .forEach { path ->
                try {
                    val content = Files.readString(path)
                    val metadata = extractMetadata(content, path)
                    val cleanContent = stripFrontmatter(content)

                    if (cleanContent.isNotBlank()) {
                        documents.add(Document(cleanContent, metadata))
                        documentCount++
                    }
                } catch (e: Exception) {
                    logger.warn("Failed to load ${path}: ${e.message}")
                }
            }

        logger.info("Loaded $documentCount documents, splitting into chunks...")

        val splitter = TokenTextSplitter(
            ragConfig.chunkSize,  // defaultChunkSize
            350,                  // minChunkSizeChars
            5,                    // minChunkLengthToEmbed
            10000,                // maxNumChunks
            true                  // keepSeparator
        )
        val chunks = splitter.apply(documents)
        chunkCount = chunks.size

        logger.info("Created $chunkCount chunks, generating embeddings with local ONNX model...")

        val cacheFile = File(ragConfig.cachePath)
        cacheFile.parentFile?.mkdirs()

        // With local embeddings, we can batch process - much faster than API calls
        val batchSize = 50
        var embedded = 0

        chunks.chunked(batchSize).forEachIndexed { batchIndex, batch ->
            try {
                vectorStore.add(batch)
                embedded += batch.size
                logger.info("Embedded $embedded/$chunkCount chunks (batch ${batchIndex + 1})...")

                // Save intermediate cache every 500 chunks
                if (embedded % 500 == 0) {
                    logger.info("Saving intermediate cache...")
                    vectorStore.save(cacheFile)
                }
            } catch (e: Exception) {
                logger.error("Batch ${batchIndex + 1} failed: ${e.message}")
                // Save what we have
                vectorStore.save(cacheFile)
                chunkCount = embedded
                val statsFile = File(ragConfig.cachePath.replace(".json", "-stats.json"))
                statsFile.writeText("$documentCount,$chunkCount")
                isLoaded = embedded > 100
                logger.info("Partial vector store saved with $embedded chunks.")
                return
            }
        }

        vectorStore.save(cacheFile)

        // Save stats to companion file
        val statsFile = File(ragConfig.cachePath.replace(".json", "-stats.json"))
        statsFile.writeText("$documentCount,$chunkCount")

        isLoaded = true
        logger.info("Vector store saved to cache. Ready with $documentCount docs, $chunkCount chunks.")
    }

    private fun extractMetadata(content: String, path: Path): MutableMap<String, Any> {
        val metadata = mutableMapOf<String, Any>(
            "file_path" to path.toString(),
            "file_name" to path.fileName.toString()
        )

        // Parse YAML frontmatter
        if (content.startsWith("---")) {
            val endIndex = content.indexOf("---", 3)
            if (endIndex > 0) {
                val frontmatter = content.substring(3, endIndex)
                frontmatter.lines().forEach { line ->
                    val parts = line.split(":", limit = 2)
                    if (parts.size == 2) {
                        val key = parts[0].trim()
                        val value = parts[1].trim()
                        if (key == "url" || key == "title" || key == "source") {
                            metadata[key] = value
                        }
                    }
                }
            }
        }

        // Extract section title from first header
        content.lines().take(10).forEach { line ->
            if (line.startsWith("#") && !metadata.containsKey("section_title")) {
                metadata["section_title"] = line.trimStart('#').trim()
            }
        }

        // Look for Source: URL pattern
        if (!metadata.containsKey("url")) {
            val sourceMatch = Regex("Source:\\s*(https?://\\S+)").find(content)
            sourceMatch?.let { metadata["original_url"] = it.groupValues[1] }
        }

        return metadata
    }

    private fun stripFrontmatter(content: String): String {
        if (!content.startsWith("---")) return content
        val endIndex = content.indexOf("---", 3)
        return if (endIndex > 0) content.substring(endIndex + 3).trim() else content
    }
}
