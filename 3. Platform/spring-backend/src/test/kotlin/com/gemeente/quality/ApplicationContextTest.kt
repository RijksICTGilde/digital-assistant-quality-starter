package com.gemeente.quality

import com.gemeente.quality.agent.QualityAssuranceAgent
import com.gemeente.quality.config.QualityConfig
import com.gemeente.quality.config.RagConfig
import com.gemeente.quality.controller.ChatController
import com.gemeente.quality.controller.HealthController
import com.gemeente.quality.rag.RagSearchService
import com.gemeente.quality.service.ContextPromptBuilder
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.context.ApplicationContext
import org.assertj.core.api.Assertions.assertThat

/**
 * Smoke tests to verify the application context loads correctly
 * and all required beans are created.
 */
@SpringBootTest
class ApplicationContextTest {

    @Autowired
    lateinit var applicationContext: ApplicationContext

    @Autowired
    lateinit var qualityConfig: QualityConfig

    @Autowired
    lateinit var ragConfig: RagConfig

    @Test
    fun `context loads successfully`() {
        assertThat(applicationContext).isNotNull
    }

    @Test
    fun `quality config is loaded with default values`() {
        assertThat(qualityConfig).isNotNull
        assertThat(qualityConfig.thresholds.relevance).isEqualTo(0.6)
        assertThat(qualityConfig.thresholds.tone).isEqualTo(0.7)
        assertThat(qualityConfig.thresholds.completeness).isEqualTo(0.5)
        assertThat(qualityConfig.thresholds.policyCompliance).isEqualTo(0.6)
    }

    @Test
    fun `rag config is loaded`() {
        assertThat(ragConfig).isNotNull
        assertThat(ragConfig.chunkSize).isEqualTo(800)
    }

    @Test
    fun `health controller bean exists`() {
        assertThat(applicationContext.getBean(HealthController::class.java)).isNotNull
    }

    @Test
    fun `chat controller bean exists`() {
        assertThat(applicationContext.getBean(ChatController::class.java)).isNotNull
    }

    @Test
    fun `context prompt builder bean exists`() {
        assertThat(applicationContext.getBean(ContextPromptBuilder::class.java)).isNotNull
    }

    @Test
    fun `rag search service bean exists`() {
        assertThat(applicationContext.getBean(RagSearchService::class.java)).isNotNull
    }

    @Test
    fun `quality assurance agent bean exists`() {
        assertThat(applicationContext.getBean(QualityAssuranceAgent::class.java)).isNotNull
    }
}
