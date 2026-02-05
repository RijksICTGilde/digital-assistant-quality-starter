package com.gemeente.quality.config

import org.springframework.ai.embedding.EmbeddingModel
import org.springframework.ai.vectorstore.SimpleVectorStore
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class VectorStoreConfig {

    @Bean
    fun vectorStore(embeddingModel: EmbeddingModel): SimpleVectorStore {
        return SimpleVectorStore.builder(embeddingModel).build()
    }
}
