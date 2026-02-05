package com.gemeente.quality.config

import org.slf4j.LoggerFactory
import org.springframework.ai.embedding.EmbeddingModel
import org.springframework.ai.transformers.TransformersEmbeddingModel
import org.springframework.ai.vectorstore.SimpleVectorStore
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Primary
import java.io.File

@Configuration
class VectorStoreConfig(
    private val ragConfig: RagConfig
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Local ONNX embedding model - runs entirely in the JVM, no external API calls.
     * Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions, fast and accurate).
     * First run downloads the model (~90MB), subsequent runs use cached version.
     */
    @Bean
    @Primary
    fun localEmbeddingModel(): EmbeddingModel {
        logger.info("Initializing local ONNX embedding model (all-MiniLM-L6-v2)...")

        // Ensure cache directory exists
        val cacheDir = File(ragConfig.onnxCachePath)
        if (!cacheDir.exists()) {
            cacheDir.mkdirs()
            logger.info("Created ONNX cache directory: ${cacheDir.absolutePath}")
        }

        val model = TransformersEmbeddingModel()
        model.setResourceCacheDirectory(cacheDir.absolutePath)
        model.afterPropertiesSet()
        logger.info("Local embedding model initialized (cache: ${cacheDir.absolutePath})")
        return model
    }

    @Bean
    fun vectorStore(localEmbeddingModel: EmbeddingModel): SimpleVectorStore {
        return SimpleVectorStore.builder(localEmbeddingModel).build()
    }
}
