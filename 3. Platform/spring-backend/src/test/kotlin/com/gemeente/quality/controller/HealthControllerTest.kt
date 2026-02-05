package com.gemeente.quality.controller

import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get

/**
 * Integration tests for the health endpoints.
 */
@SpringBootTest
@AutoConfigureMockMvc
class HealthControllerTest {

    @Autowired
    lateinit var mockMvc: MockMvc

    @Test
    fun `health endpoint returns ok`() {
        mockMvc.get("/api/health")
            .andExpect {
                status { isOk() }
                jsonPath("$.status") { value("healthy") }
            }
    }

    @Test
    fun `ready endpoint returns ok`() {
        mockMvc.get("/api/ready")
            .andExpect {
                status { isOk() }
                jsonPath("$.ready") { value(true) }
            }
    }

    @Test
    fun `live endpoint returns ok`() {
        mockMvc.get("/api/live")
            .andExpect {
                status { isOk() }
                jsonPath("$.status") { value("alive") }
            }
    }
}
