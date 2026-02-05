package com.gemeente.quality.service

import com.gemeente.quality.agent.domain.QualityEvaluation
import com.gemeente.quality.model.QualityDimension
import com.gemeente.quality.model.UserContext
import org.springframework.stereotype.Service

@Service
class ContextPromptBuilder {

    fun buildGenerationPrompt(
        message: String,
        userContext: UserContext,
        ragContext: String
    ): String {
        val hasContext = ragContext.isNotBlank() && !ragContext.contains("Geen relevante bronnen")

        return """
Je bent een AI assistant voor Nederlandse gemeentes, gespecialiseerd in digitale transformatie en AI implementatie.

GEBRUIKER CONTEXT:
- Rol: ${userContext.roleName ?: userContext.role?.value ?: "onbekend"}
- Projectfase: ${userContext.projectPhase ?: "niet gespecificeerd"}
- Focusgebieden: ${userContext.focusAreas.joinToString(", ") { it.value }}
- Specifieke context: ${userContext.customContext ?: "geen"}

RELEVANTE KENNISBANK INFORMATIE:
$ragContext

BELANGRIJKE INSTRUCTIES:
${if (hasContext) """
1. Beantwoord de vraag UITSLUITEND op basis van de hierboven gegeven kennisbank informatie
2. Als de kennisbank informatie niet relevant is voor de vraag, zeg dan eerlijk dat je deze vraag niet kunt beantwoorden op basis van de beschikbare bronnen
3. Gebruik GEEN algemene kennis die niet in de bronnen staat
4. Wees specifiek over regelgeving en compliance
5. Verwijs naar menselijke experts voor complexe juridische interpretaties
""" else """
1. De kennisbank bevat GEEN relevante informatie voor deze vraag
2. Leg uit dat je alleen vragen kunt beantwoorden over digitale transformatie, AI implementatie, en overheidsrichtlijnen voor Nederlandse gemeentes
3. Geef aan welke onderwerpen je WEL kunt beantwoorden
4. Beantwoord de vraag NIET met algemene kennis
"""}

RESPONSE FORMAT:
${if (hasContext) """
Geef een duidelijke hoofdrespons die de vraag beantwoordt op basis van de bronnen.
""" else """
Leg vriendelijk uit dat deze vraag buiten je kennisdomein valt en welke onderwerpen je wel kunt helpen.
"""}
Voeg GEEN bronverwijzingen, vervolgvragen of escalatie-informatie toe aan je antwoord.
Deze worden automatisch door het systeem toegevoegd.

Antwoord altijd in het Nederlands.

VRAAG: $message
        """.trimIndent()
    }

    fun buildEvaluationPrompt(
        originalQuestion: String,
        response: String,
        ragContext: String
    ): String {
        return """
Je bent een kwaliteitsbeoordelaar voor AI-responses van een Nederlandse overheids-assistent.

Beoordeel de volgende response op 4 dimensies (score 0.0 tot 1.0):

1. RELEVANTIE (relevance):
   - Is het antwoord gebaseerd op de BESCHIKBARE BRONNEN hieronder?
   - Als het antwoord informatie bevat die NIET in de bronnen staat, geef dan een LAGE score (0.0-0.3)
   - Als de vraag buiten het domein valt en de assistent dat correct aangeeft, geef een HOGE score

2. TOON (tone): Is de toon professioneel, neutraal en passend voor overheidscontext?

3. VOLLEDIGHEID (completeness):
   - Wordt de beschikbare broninformatie goed benut?
   - Als er geen relevante bronnen zijn, is het dan correct om te zeggen dat de vraag niet beantwoord kan worden?

4. BELEIDSCONFORMITEIT (policy_compliance):
   - Worden relevante wetten/regelgeving correct gerefereerd?
   - Wordt er GEEN informatie verzonnen die niet in de bronnen staat?

OORSPRONKELIJKE VRAAG:
$originalQuestion

BESCHIKBARE BRONNEN:
$ragContext

AI RESPONSE:
$response

Geef je beoordeling UITSLUITEND als JSON (geen andere tekst):
{
    "relevance": 0.0,
    "tone": 0.0,
    "completeness": 0.0,
    "policy_compliance": 0.0,
    "improvement_suggestions": {
        "relevance": "suggestie of null",
        "tone": "suggestie of null",
        "completeness": "suggestie of null",
        "policy_compliance": "suggestie of null"
    }
}
        """.trimIndent()
    }

    fun buildImprovementPrompt(
        originalQuestion: String,
        originalResponse: String,
        evaluation: QualityEvaluation,
        ragContext: String
    ): String {
        val suggestions = evaluation.failedDimensions.joinToString("\n") { dim ->
            val label = when (dim) {
                QualityDimension.RELEVANCE -> "Relevantie"
                QualityDimension.TONE -> "Toon"
                QualityDimension.COMPLETENESS -> "Volledigheid"
                QualityDimension.POLICY_COMPLIANCE -> "Beleidsconformiteit"
            }
            val score = evaluation.scores[dim] ?: 0.0
            val suggestion = evaluation.improvementSuggestions[dim] ?: "Verbeter dit aspect"
            "- $label (score: ${"%.1f".format(score)}): $suggestion"
        }

        return """
Je bent een AI-assistent die een eerder antwoord moet verbeteren voor een Nederlandse overheidscontext.

OORSPRONKELIJKE VRAAG:
$originalQuestion

EERDER ANTWOORD:
$originalResponse

KWALITEITSBEOORDELING - VERBETERPUNTEN:
$suggestions

BESCHIKBARE BRONNEN:
$ragContext

OPDRACHT:
Schrijf een verbeterd antwoord dat de genoemde verbeterpunten adresseert.
Behoud de goede aspecten van het oorspronkelijke antwoord.
Antwoord in het Nederlands, professioneel en geschikt voor overheidscontext.
Voeg GEEN bronverwijzingen of vervolgvragen toe.
        """.trimIndent()
    }
}
