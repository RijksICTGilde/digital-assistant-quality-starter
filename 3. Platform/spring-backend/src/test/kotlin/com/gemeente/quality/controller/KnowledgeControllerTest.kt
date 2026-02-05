package com.gemeente.quality.controller

import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get

/**
 * Integration tests for the knowledge/RAG endpoints.
 */
@SpringBootTest
@AutoConfigureMockMvc
class KnowledgeControllerTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Test
    fun `stats endpoint returns document statistics`() {
        mockMvc.get("/api/knowledge/stats")
            .andExpect {
                status { isOk() }
                jsonPath("$.total_documents") { isNumber() }
                jsonPath("$.total_chunks") { isNumber() }
            }
    }

    @Test
    fun `search endpoint accepts query parameter`() {
        mockMvc.get("/api/knowledge/search") {
            param("query", "AI implementatie")
        }.andExpect {
            status { isOk() }
            jsonPath("$") { isArray() }
        }
    }

    @Test
    fun `role endpoint returns results for valid role`() {
        mockMvc.get("/api/knowledge/role/digital-guide")
            .andExpect {
                status { isOk() }
                jsonPath("$") { isArray() }
            }
    }
}
