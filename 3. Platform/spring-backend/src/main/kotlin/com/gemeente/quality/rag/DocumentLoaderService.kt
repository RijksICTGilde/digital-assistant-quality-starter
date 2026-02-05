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

    @PostConstruct
    fun init() {
        val cacheFile = File(ragConfig.cachePath)
        if (cacheFile.exists()) {
            try {
                vectorStore.load(cacheFile)
                isLoaded = true
                logger.info("Loaded vector store from cache: ${cacheFile.absolutePath}")
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

        logger.info("Created $chunkCount chunks, generating embeddings (rate-limited with backoff)...")

        val cacheFile = File(ragConfig.cachePath)
        cacheFile.parentFile?.mkdirs()
        var embedded = 0

        for (chunk in chunks) {
            var attempt = 0
            var backoffMs = 5000L

            while (true) {
                try {
                    vectorStore.add(listOf(chunk))
                    embedded++
                    if (embedded % 100 == 0) {
                        logger.info("Embedded $embedded/$chunkCount chunks, saving intermediate cache...")
                        vectorStore.save(cacheFile)
                    } else if (embedded % 25 == 0) {
                        logger.info("Embedded $embedded/$chunkCount chunks...")
                    }
                    Thread.sleep(1500) // 1.5s between successful calls
                    break
                } catch (e: Exception) {
                    attempt++
                    if (attempt > 10) {
                        logger.error("Chunk $embedded failed after 10 retries, saving partial cache ($embedded chunks)...")
                        vectorStore.save(cacheFile)
                        isLoaded = embedded > 100 // partial load is better than nothing
                        logger.info("Partial vector store saved. Available with $embedded/$chunkCount chunks.")
                        return
                    }
                    logger.warn("Chunk $embedded attempt $attempt failed (429 rate limit), backing off ${backoffMs / 1000}s...")
                    Thread.sleep(backoffMs)
                    backoffMs = (backoffMs * 2).coerceAtMost(120000) // max 2min backoff
                }
            }
        }

        vectorStore.save(cacheFile)
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
