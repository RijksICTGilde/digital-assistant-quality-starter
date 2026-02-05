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

## 7. RAG met 320 Overheidsdocumenten

**Probleem:** Antwoorden moeten gebaseerd zijn op actuele, betrouwbare overheidsinformatie.

**Oplossing:**

- **320 markdown documenten** geladen uit de dataset
- **2052 chunks** met vector embeddings (GreenPT `green-embedding` model)
- **Similarity search** vindt de meest relevante passages voor elke vraag
- **Bronvermelding** toont welke documenten zijn gebruikt

**Voordeel:** Antwoorden zijn traceerbaar naar officiële bronnen.

---

## 8. Twee Chat-interfaces

**Probleem:** Verschillende gebruikersbehoeften op verschillende momenten.

**Oplossing:**

1. **ChatSidebar** - compacte chat naast de informatiegids, voor snelle vragen tijdens het lezen
2. **EnhancedChatInterface** - volledige chatervaring met uitgebreide kwaliteitsweergave en brondetails

Beide interfaces tonen nu kwaliteitsscores en bronnen.

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
