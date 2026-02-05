package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonProperty

data class UserContext(
    val role: UserRole? = null,
    @JsonProperty("roleName") val roleName: String? = null,
    @JsonProperty("projectPhase") val projectPhase: String? = null,
    @JsonProperty("focusAreas") val focusAreas: List<FocusArea> = emptyList(),
    @JsonProperty("specificNeeds") val specificNeeds: List<String> = emptyList(),
    @JsonProperty("customContext") val customContext: String? = null
)

data class ChatMessage(
    val message: String,
    val context: UserContext = UserContext(),
    val timestamp: String = System.currentTimeMillis().toString()
)
