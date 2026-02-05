package com.gemeente.quality.model

import com.fasterxml.jackson.annotation.JsonValue

enum class UserRole(@JsonValue val value: String) {
    DIGITAL_GUIDE("digital-guide"),
    CIVIL_SERVANT("civil-servant"),
    IT_MANAGER("it-manager"),
    PROJECT_MANAGER("project-manager"),
    DEVELOPER("developer"),
    OTHER("other");

    companion object {
        fun fromValue(value: String): UserRole =
            entries.find { it.value == value } ?: OTHER
    }
}

enum class FocusArea(@JsonValue val value: String) {
    COMPLIANCE("compliance"),
    TECHNOLOGY("technology"),
    PROCESS("process"),
    INNOVATION("innovation")
}

enum class ConfidenceLevel(@JsonValue val value: String) {
    HIGH("high"),
    MEDIUM("medium"),
    LOW("low")
}

enum class ResponseType(@JsonValue val value: String) {
    DIRECT_ANSWER("direct_answer"),
    GUIDANCE("guidance"),
    ESCALATION("escalation"),
    CLARIFICATION("clarification"),
    COMPLIANCE_ANALYSIS("compliance_analysis"),
    TECHNICAL_GUIDANCE("technical_guidance")
}

enum class ComplexityLevel(@JsonValue val value: String) {
    SIMPLE("simple"),
    MODERATE("moderate"),
    COMPLEX("complex"),
    EXPERT_REQUIRED("expert_required")
}

enum class RegulationType(@JsonValue val value: String) {
    GDPR("gdpr"),
    AI_ACT("ai_act"),
    WOO("woo"),
    ARCHIEFWET("archiefwet"),
    TOEGANKELIJKHEID("toegankelijkheid"),
    GENERAL("general")
}

enum class QualityDimension {
    RELEVANCE,
    TONE,
    COMPLETENESS,
    POLICY_COMPLIANCE
}
