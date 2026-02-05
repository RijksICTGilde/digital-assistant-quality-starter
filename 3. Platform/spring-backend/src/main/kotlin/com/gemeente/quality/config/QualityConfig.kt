package com.gemeente.quality.config

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "quality")
data class QualityConfig(
    val thresholds: Thresholds = Thresholds(),
    val maxImprovementRounds: Int = 1
) {
    data class Thresholds(
        val relevance: Double = 0.6,
        val tone: Double = 0.7,
        val completeness: Double = 0.5,
        val policyCompliance: Double = 0.6
    )
}
