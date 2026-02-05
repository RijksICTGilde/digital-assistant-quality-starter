package com.gemeente.quality

import com.embabel.agent.config.annotation.EnableAgents
import com.gemeente.quality.config.QualityConfig
import com.gemeente.quality.config.RagConfig
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.boot.runApplication

@SpringBootApplication
@EnableAgents
@EnableConfigurationProperties(QualityConfig::class, RagConfig::class)
class GemeenteQualityApplication

fun main(args: Array<String>) {
    runApplication<GemeenteQualityApplication>(*args)
}
