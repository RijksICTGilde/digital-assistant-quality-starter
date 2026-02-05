# Kwaliteitsverbeteringen Digital Assistant

Overzicht van de verbeteringen die we hebben doorgevoerd om de kwaliteit van AI-output te definiëren, meten, vergelijken en verbeteren.

---

## 1. Embabel GOAP Agent Pipeline

**Probleem:** De meeste AI-assistenten genereren output in één stap. Kwaliteitsproblemen worden pas achteraf gesignaleerd of helemaal niet gecorrigeerd.

**Oplossing:** Een 5-staps pipeline met automatische kwaliteitscontrole en verbetering:

```
Gebruikersvraag
    ↓
[1] Context ophalen uit kennisbank (RAG)
    ↓
[2] Eerste antwoord genereren (LLM call #1)
    ↓
[3] Kwaliteit beoordelen op 4 dimensies (LLM call #2 - "LLM als Rechter")
    ↓
[4] Antwoord verbeteren indien nodig (LLM call #3)
    ↓
[5] Eindresultaat samenstellen met transparante scores
```

**Voordeel:** Het systeem corrigeert zichzelf automatisch. De gebruiker ziet het verbeterde antwoord én de kwaliteitsscores.

---

## 2. Vier Kwaliteitsdimensies

**Probleem:** "Kwaliteit" is vaag. Wat maakt een antwoord goed of slecht?

**Oplossing:** Vier concrete, meetbare dimensies (0-100%):

| Dimensie | Wat wordt gemeten? | Drempelwaarde |
|----------|-------------------|---------------|
| **Relevantie** | Beantwoordt het de vraag? Is het gebaseerd op de bronnen? | 60% |
| **Toon** | Professioneel, neutraal, passend voor overheidscontext? | 70% |
| **Volledigheid** | Is de informatie compleet? Worden bronnen benut? | 50% |
| **Beleidsconformiteit** | Worden wetten/regelgeving correct gerefereerd? | 60% |

**Voordeel:** Objectieve, reproduceerbare kwaliteitsmeting. Als een dimensie onder de drempel valt, wordt het antwoord automatisch verbeterd.

---

## 3. LLM als Rechter (LLM-as-Judge)

**Probleem:** Hoe beoordeel je automatisch of een AI-antwoord goed is?

**Oplossing:** We gebruiken een tweede LLM-call om het gegenereerde antwoord te beoordelen:

1. Het eerste antwoord wordt gegenereerd
2. Een tweede prompt vraagt het LLM: "Beoordeel dit antwoord op 4 dimensies (0.0-1.0)"
3. Het LLM retourneert JSON met scores én verbetersugesties
4. Bij scores onder de drempel wordt een derde call gedaan om te verbeteren

**Voordeel:** Schaalbare kwaliteitscontrole zonder menselijke reviewers voor elk antwoord.

---

## 4. Transparante Kwaliteitsweergave

**Probleem:** Gebruikers weten niet waarom een antwoord betrouwbaar is (of niet).

**Oplossing:** Elke response bevat:

- **Kwaliteitsscores** als visuele progress bars (groen/oranje/rood)
- **"Verbeterd" badge** als het antwoord is gecorrigeerd
- **Uitleg in het Nederlands** ("Dit antwoord heeft de kwaliteitscontrole doorstaan. Scores: relevantie: 100%, toon: 100%...")
- **Uitklapbare trace** met alle stappen die het systeem heeft doorlopen

**Voordeel:** Niet-technische gebruikers begrijpen direct hoe betrouwbaar het antwoord is.

---

## 5. Grounding: Alleen Antwoorden uit Bronnen

**Probleem:** Het LLM beantwoordt ook vragen buiten zijn kennisdomein met algemene kennis ("hallucinaties").

**Oplossing:**

1. **Similarity threshold** van 0.5 - alleen documenten met voldoende relevantie (50%+) worden meegenomen
2. **Aangepaste prompt** - het LLM mag ALLEEN antwoorden op basis van de meegegeven bronnen
3. **Off-topic detectie** - als geen relevante bronnen gevonden worden, weigert de assistent vriendelijk en legt uit welke onderwerpen wel beantwoord kunnen worden

**Voorbeeld off-topic vraag:**
> "Wat zijn goede restaurants in Den Haag?"

**Response:**
> "Ik kan deze vraag niet beantwoorden op basis van de beschikbare bronnen. De kennisbank bevat informatie over digitale transformatie, AI implementatie en overheidsrichtlijnen voor Nederlandse gemeentes."

**Voordeel:** Eerlijke, betrouwbare antwoorden. Geen misleidende informatie.

---

## 6. Intelligente Bronweergave

**Probleem:** Bronnen werden altijd getoond, ook als ze niet relevant waren voor het antwoord (bijv. bij een begroeting of off-topic vraag).

**Oplossing:** Bronnen worden alleen getoond als aan **beide** voorwaarden is voldaan:

1. RAG vond documenten boven de similarity threshold (0.5)
2. De kwaliteitsevaluatie gaf een relevantie-score boven de drempel (0.6)

**Voorbeeld begroeting:**
> "Hallo!"

**Gedrag:**
- Assistent legt uit wat het kan doen ✅
- Geen bronnen getoond (niet relevant) ✅
- Hoge kwaliteitsscores (correct gedrag wordt beloond) ✅

**Voordeel:** Gebruikers zien alleen bronnen die daadwerkelijk bijdroegen aan het antwoord.

---

## 7. Voor/Na Vergelijking

**Probleem:** Gebruikers zien niet wat er precies verbeterd is aan een antwoord.

**Oplossing:** Wanneer een antwoord wordt verbeterd, toont de interface beide versies:

- **VOOR (Oorspronkelijk)** - het eerste gegenereerde antwoord
- **NA (Verbeterd)** - het antwoord na kwaliteitsverbetering

De vergelijking is uitklapbaar in het kwaliteitsdashboard.

**Voordeel:** Volledige transparantie over de kwaliteitsinterventie. Gebruikers kunnen zelf beoordelen of de verbetering nuttig was.

---

## 8. RAG met 320 Overheidsdocumenten

**Probleem:** Antwoorden moeten gebaseerd zijn op actuele, betrouwbare overheidsinformatie.

**Oplossing:**

- **320 markdown documenten** geladen uit de dataset
- **2052 chunks** met vector embeddings (GreenPT `green-embedding` model)
- **Similarity search** vindt de meest relevante passages voor elke vraag
- **Bronvermelding** toont welke documenten zijn gebruikt

**Voordeel:** Antwoorden zijn traceerbaar naar officiële bronnen.

---

## 9. Twee Chat-interfaces

**Probleem:** Verschillende gebruikersbehoeften op verschillende momenten.

**Oplossing:**

1. **ChatSidebar** - compacte chat naast de informatiegids, voor snelle vragen tijdens het lezen
2. **EnhancedChatInterface** - volledige chatervaring met uitgebreide kwaliteitsweergave en brondetails

Beide interfaces tonen nu kwaliteitsscores en bronnen.

---

## 10. Hallucinatie Detectie

**Probleem:** LLM's kunnen informatie "verzinnen" die niet in de bronnen staat. Dit is gevaarlijk voor overheidscontext waar betrouwbaarheid cruciaal is.

**Oplossing:** Automatische detectie van ongecontroleerde informatie:

1. **Evaluatie prompt** vraagt expliciet: "Bevat het antwoord claims die NIET in de bronnen staan?"
2. **Twee nieuwe velden** in de response:
   - `hallucination_detected`: boolean vlag
   - `ungrounded_claims`: lijst van specifieke claims die niet gegrond zijn
3. **Visuele waarschuwing** in de UI wanneer hallucinatie gedetecteerd wordt

**Voorbeeld detectie:**
```json
{
  "hallucination_detected": true,
  "ungrounded_claims": [
    "De AI Act treedt in werking op 1 januari 2025",
    "85% van de gemeentes gebruikt al AI"
  ]
}
```

**UI Weergave:**
- Rode waarschuwingsbox met "Mogelijk ongecontroleerde informatie gedetecteerd"
- Uitklapbare lijst met de specifieke claims
- Advies om feiten te controleren

**Voordeel:** Gebruikers worden gewaarschuwd wanneer antwoorden mogelijk onbetrouwbare informatie bevatten, zonder dat het antwoord geblokkeerd wordt.

---

## 11. Iteratieve Kwaliteitsverbetering

**Probleem:** Een enkele verbeterpoging is niet altijd genoeg om de kwaliteitsdrempels te halen.

**Oplossing:** Het systeem herhaalt het verbeterproces tot maximaal 3 keer totdat de kwaliteit acceptabel is:

1. Eerste antwoord genereren
2. Kwaliteit beoordelen
3. **Als onvoldoende:** Verbeteren → Opnieuw beoordelen → Herhaal (max 3x)
4. Voortgang per iteratie bijhouden

**Response bevat:**
```json
{
  "improvement_iterations": 2,
  "iteration_history": [
    {"iteration": 0, "overall_score": 0.55, "passed": false},
    {"iteration": 1, "overall_score": 0.72, "passed": false},
    {"iteration": 2, "overall_score": 0.85, "passed": true}
  ]
}
```

**UI Weergave:**
- Badge toont aantal iteraties: "Verbeterd (2x)"
- Uitklapbare grafiek toont kwaliteitsverloop per iteratie
- Visuele progressiebalken per ronde

**Voordeel:** Hogere eindkwaliteit doordat het systeem blijft verbeteren tot de drempelwaarden gehaald zijn.

---

## 12. Real-time Streaming Pipeline

**Probleem:** Gebruikers zien een loading spinner zonder te weten wat er gebeurt.

**Oplossing:** Server-Sent Events (SSE) streamen de pipeline-voortgang in real-time:

**Endpoint:** `POST /api/chat/stream`

**Events:**
- `pipeline_start` - Pipeline gestart
- `action_start` / `action_complete` - Elke stap met voortgang (1/5, 2/5, etc.)
- `quality_score` - Individuele dimensiescores
- `improvement` - Wanneer antwoord wordt verbeterd
- `complete` - Eindresultaat met volledige response

**UI Weergave:**
- Progressiebalk met percentage
- Checkmarks voor voltooide stappen
- Live update van huidige actie

**Voordeel:** Transparant proces zichtbaar voor gebruikers. Demonstreert de kwaliteitspijplijn visueel.

---

## Architectuur Overzicht

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    React + Vite (port 3000)                     │
│  ┌─────────────────┐        ┌─────────────────────────────┐    │
│  │  ChatSidebar    │        │  EnhancedChatInterface      │    │
│  │  (compact)      │        │  (volledig + kwaliteits-    │    │
│  │                 │        │   dashboard)                │    │
│  └────────┬────────┘        └──────────────┬──────────────┘    │
└───────────┼─────────────────────────────────┼──────────────────┘
            │                                 │
            └────────────┬────────────────────┘
                         │ /api/chat/structured
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SPRING BACKEND (port 8080)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Embabel GOAP Agent Pipeline                   │ │
│  │                                                            │ │
│  │  [retrieveContext] → [generateInitialResponse]            │ │
│  │          ↓                      ↓                         │ │
│  │    RAG Search            LLM Call #1                      │ │
│  │          ↓                      ↓                         │ │
│  │  [evaluateQuality] ←────────────┘                         │ │
│  │          ↓                                                │ │
│  │    LLM Call #2 ("LLM als Rechter")                       │ │
│  │          ↓                                                │ │
│  │  [improveResponse] (alleen indien nodig)                  │ │
│  │          ↓                                                │ │
│  │    LLM Call #3                                            │ │
│  │          ↓                                                │ │
│  │  [assembleFinalResponse] → JSON met scores + trace        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │ Vector Store    │  │ GreenPT API     │                       │
│  │ (2052 chunks)   │  │ (EU-hosted LLM) │                       │
│  └─────────────────┘  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Challenge Criteria Checklist

### Verplicht ✅

| Criterium | Implementatie |
|-----------|---------------|
| Duidelijke definitie van kwaliteit | 4 dimensies: relevantie, toon, volledigheid, beleidsconformiteit |
| Minstens één meetbaar kwaliteitscriterium | Alle 4 dimensies hebben scores (0.0-1.0) en drempelwaarden |
| Inzicht waar en waarom de assistent ingrijpt | Quality trace toont elke stap + "Verbeterd" badge |
| Begrijpelijk voor niet-technische gebruikers | Nederlandse uitleg, visuele progress bars, kleurcodering |

### Bonus ✅

| Criterium | Implementatie |
|-----------|---------------|
| LLM's als beoordelaar | "LLM als Rechter" pattern in evaluateQuality stap |
| Hallucinatie detectie | Automatische detectie van ongecontroleerde claims |
| Voor/Na vergelijking | Toon origineel en verbeterd antwoord naast elkaar |
| Transparantie over onzekerheid | Confidence level (high/medium/low) + grounding check |
| Governance/beleidskaders in de flow | Beleidsconformiteit als aparte kwaliteitsdimensie |

---

## Tech Stack

- **Frontend:** React 18 + Vite + Tailwind CSS
- **Backend:** Spring Boot 3.5.6 + Kotlin
- **Agent Framework:** Embabel 0.3.3 (GOAP planning)
- **Vector Store:** Spring AI SimpleVectorStore
- **LLM:** GreenPT API (EU-hosted, privacy-focused)
- **Embeddings:** GreenPT `green-embedding` (2560 dimensies)
