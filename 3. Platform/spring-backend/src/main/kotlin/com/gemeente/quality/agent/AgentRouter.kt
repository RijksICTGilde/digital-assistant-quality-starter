package com.gemeente.quality.agent

import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service

/**
 * Routes incoming questions to the most appropriate specialized agent.
 *
 * Agents:
 * - ComplianceAgent: Legal, regulatory, privacy questions
 * - TechnicalAgent: Implementation, architecture, API questions
 * - QualityAssuranceAgent: General questions (default, with full quality pipeline)
 */
@Service
class AgentRouter {
    private val logger = LoggerFactory.getLogger(javaClass)

    enum class AgentType {
        COMPLIANCE,
        TECHNICAL,
        GENERAL
    }

    data class RoutingDecision(
        val agentType: AgentType,
        val confidence: Double,
        val matchedKeywords: List<String>,
        val reason: String
    )

    /**
     * Determine which agent should handle the given question.
     */
    fun route(message: String): RoutingDecision {
        val lower = message.lowercase()

        // Check for compliance keywords
        val complianceMatches = ComplianceAgent.TRIGGER_KEYWORDS.filter { lower.contains(it) }
        val complianceScore = calculateScore(complianceMatches, ComplianceAgent.TRIGGER_KEYWORDS.size)

        // Check for technical keywords
        val technicalMatches = TechnicalAgent.TRIGGER_KEYWORDS.filter { lower.contains(it) }
        val technicalScore = calculateScore(technicalMatches, TechnicalAgent.TRIGGER_KEYWORDS.size)

        // Determine winner
        val decision = when {
            complianceScore > 0.15 && complianceScore >= technicalScore -> {
                RoutingDecision(
                    agentType = AgentType.COMPLIANCE,
                    confidence = complianceScore,
                    matchedKeywords = complianceMatches,
                    reason = "Vraag bevat compliance/juridische termen: ${complianceMatches.take(3).joinToString(", ")}"
                )
            }
            technicalScore > 0.1 && technicalScore > complianceScore -> {
                RoutingDecision(
                    agentType = AgentType.TECHNICAL,
                    confidence = technicalScore,
                    matchedKeywords = technicalMatches,
                    reason = "Vraag bevat technische termen: ${technicalMatches.take(3).joinToString(", ")}"
                )
            }
            else -> {
                RoutingDecision(
                    agentType = AgentType.GENERAL,
                    confidence = 1.0,
                    matchedKeywords = emptyList(),
                    reason = "Algemene vraag - gebruik standaard kwaliteitsagent"
                )
            }
        }

        logger.info("Routing decision: ${decision.agentType} (confidence: ${String.format("%.2f", decision.confidence)}) - ${decision.reason}")
        return decision
    }

    private fun calculateScore(matches: List<String>, totalKeywords: Int): Double {
        if (matches.isEmpty()) return 0.0
        // Score based on number of matches, with diminishing returns
        val matchRatio = matches.size.toDouble() / totalKeywords
        val matchBonus = minOf(matches.size * 0.15, 0.6)  // Up to 0.6 bonus for multiple matches
        return minOf(matchRatio + matchBonus, 1.0)
    }
}
