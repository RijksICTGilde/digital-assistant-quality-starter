package com.gemeente.quality.config

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "rag")
data class RagConfig(
    val documentsPath: String = "../../1. Datasets/Scrapen/scraped_content/content",
    val cachePath: String = "./cache/vector-store.json",
    val chunkSize: Int = 800,
    val chunkOverlap: Int = 100
)
