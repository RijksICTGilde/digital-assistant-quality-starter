# Digital Assistant Quality Strategy

## Context
**Challenge**: Hoe verbeteren we de kwaliteit van digitale assistent-output in real time?
**Focus**: Pre-search clarity, source attribution, consistent tone, dynamic data sources

---

## 1. Clear Input for the LLM (Pre-Search Processing)

### Current State
The current system takes user queries directly to embedding search without preprocessing. This can lead to:
- Ambiguous queries returning irrelevant results
- Context loss (user role, previous questions not factored in)
- No query reformulation for better retrieval

### Strategies to Implement

#### A. Query Understanding Layer
```
User Query → Intent Classification → Query Expansion → Search
```

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| **Intent Classification** | Determine what type of answer is needed | LLM call to classify: factual, procedural, compliance, opinion-seeking |
| **Query Expansion** | Add synonyms and related terms | Use LLM to generate search variants |
| **Context Injection** | Add user role/phase context | Prepend role-specific terms to query |

#### B. Query Reformulation Pipeline
```python
# Example: Pre-search query processing
def preprocess_query(user_query: str, context: UserContext) -> SearchQuery:
    # 1. Extract intent
    intent = classify_intent(user_query)  # e.g., "compliance_check"

    # 2. Expand query with role context
    expanded = f"{context.role} {context.project_phase}: {user_query}"

    # 3. Generate search variants
    variants = generate_query_variants(user_query)  # ["GDPR chatbot", "AVG conversational AI"]

    # 4. Return structured search request
    return SearchQuery(
        original=user_query,
        expanded=expanded,
        variants=variants,
        intent=intent,
        filters=intent_to_filters(intent)  # e.g., only compliance docs
    )
```

#### C. Multi-Query Retrieval
Instead of one search, do parallel searches:
1. **Literal search**: Exact user query
2. **Expanded search**: With role/context terms
3. **Hypothetical answer search**: "If I were to answer this, I would write about..." (HyDE technique)

Then merge and deduplicate results.

### What to Focus On
- **High impact, low effort**: Add intent classification to route to specific document subsets
- **Medium effort**: Query expansion using synonyms (especially Dutch/English terms)
- **Higher effort**: Full HyDE (Hypothetical Document Embeddings) implementation

---

## 2. Source Attribution (Where Information Comes From)

### Current State
The system tracks:
- `file_path`, `section_title`, `chunk_index`, `original_url`
- Relevance scores (0-1)

**Gap**: The LLM receives context but doesn't always cite specific sources in its answer.

### Strategies to Implement

#### A. Structured Source Injection
Instead of dumping context, format it with explicit citation markers:

```
[BRON 1: GDPR-Richtlijnen-Gemeenten.md, sectie "Chatbot-eisen"]
Gemeentelijke chatbots moeten voldoen aan...

[BRON 2: AI-Act-Implementatie.md, sectie "Hoog-risico systemen"]
...
```

Then instruct the LLM: "When using information, cite using [BRON X]."

#### B. Post-Generation Source Verification
After generating an answer, verify claims against sources:

```python
def verify_sources(answer: str, sources: List[Source]) -> VerifiedAnswer:
    # 1. Extract claims from answer
    claims = extract_claims(answer)

    # 2. For each claim, find supporting source
    verified_claims = []
    for claim in claims:
        support = find_supporting_source(claim, sources)
        verified_claims.append({
            "claim": claim,
            "source": support.source_id if support else None,
            "confidence": support.similarity if support else 0
        })

    # 3. Flag unsupported claims
    unsupported = [c for c in verified_claims if c["source"] is None]

    return VerifiedAnswer(
        answer=answer,
        citations=verified_claims,
        warnings=unsupported
    )
```

#### C. Source Metadata Enhancement
For dynamic sources (like legal texts), add rich metadata:

```python
@dataclass
class LegalSource:
    document_id: str           # e.g., "GDPR-Art-13"
    full_title: str            # "General Data Protection Regulation, Article 13"
    short_cite: str            # "AVG Art. 13"
    effective_date: date       # When law took effect
    last_amended: date         # Last change
    jurisdiction: str          # "EU", "NL"
    authority: str             # "European Parliament"
    url: str                   # Official publication URL
    version: str               # For tracking changes
```

#### D. Citation Format for Government Context
Define a consistent citation format:

```
Bron: [Documentnaam], [Sectie/Artikel], [Datum]
Voorbeeld: "AVG Art. 13, lid 1 (2018)"
```

### What to Focus On
- **Critical**: Add citation markers in prompt and parse them in output
- **Important**: Source verification step before returning answer
- **Nice-to-have**: Confidence indicators per citation

---

## 3. Consistent Tone and Concise Output

### Current State
The system has role-specific prompts but no strict output format enforcement.

### Government Communication Standards (Overheid)

Dutch government communication should be:
- **Direct taal** (B1 niveau)
- **Actief, niet passief**
- **Neutraal, geen politiek advies**
- **Concreet, niet abstract**

### Strategies to Implement

#### A. Output Style Guide (System Prompt)
```
SCHRIJFSTIJL:
- Gebruik directe taal op B1-niveau
- Vermijd jargon; leg technische termen uit
- Schrijf in actieve vorm ("U moet..." niet "Er moet worden...")
- Maximaal 3 zinnen per alinea
- Begin met het belangrijkste (inverted pyramid)
- Geen meningen of politiek advies
- Altijd bronvermelding

STRUCTUUR ANTWOORD:
1. Korte samenvatting (1-2 zinnen)
2. Uitleg/details (bullets waar mogelijk)
3. Bronnen (met links)
4. Eventuele vervolgvragen
```

#### B. Output Validation Layer
Use LLM-as-judge to check output before returning:

```python
def validate_output_style(answer: str) -> ValidationResult:
    checks = [
        ("readability", check_b1_level(answer)),
        ("tone", check_neutral_tone(answer)),
        ("length", check_conciseness(answer)),
        ("structure", check_has_sources(answer)),
        ("no_politics", check_no_political_advice(answer))
    ]

    failed = [c for c in checks if not c[1].passed]

    if failed:
        # Option 1: Auto-rewrite
        answer = rewrite_for_style(answer, failed)
        # Option 2: Flag for review
        # return ValidationResult(answer, warnings=failed)

    return ValidationResult(answer, passed=True)
```

#### C. Length Constraints
| Response Type | Max Length | Structure |
|--------------|------------|-----------|
| Quick Answer | 50 words | Direct answer + 1 source |
| Standard | 150 words | Summary + 2-3 bullets + sources |
| Detailed | 300 words | Summary + explanation + sources + follow-up |
| Compliance | 400 words | Summary + legal basis + requirements + sources |

#### D. Template-Based Responses
For common query types, use structured templates:

```
[SAMENVATTING]
{one_sentence_answer}

[DETAILS]
{bullet_points}

[BRONNEN]
{numbered_sources_with_links}

[VERVOLGVRAGEN]
{suggested_next_questions}
```

### What to Focus On
- **Essential**: Add style guide to system prompt
- **High value**: Post-generation style validation
- **Measurable**: Define and track readability metrics (Flesch-Douma for Dutch)

---

## 4. Dynamic Data Sources (Beyond Static Content)

### Current State
- 320 markdown files scraped from gemeente websites
- Static content, updated by re-scraping

### Alternative: Legal/Regulatory Data Sources

#### A. wetten.overheid.nl (Official Dutch Laws)
```
Source: https://wetten.overheid.nl
Format: XML (BWB - Basiswettenbestand)
Contains: All Dutch laws, regulations, treaties
API: Available via open data portal
```

**Integration approach:**
```python
# Fetch specific law/article
def get_law_article(bwb_id: str, article: str) -> LegalText:
    url = f"https://wetten.overheid.nl/xml/{bwb_id}"
    # Parse XML, extract article
    # Return structured legal text with metadata
```

#### B. EUR-Lex (EU Legislation)
```
Source: https://eur-lex.europa.eu
Contains: GDPR, AI Act, etc.
API: SPARQL endpoint available
```

#### C. Structured Legal Document Processing
For legal texts, different chunking strategy needed:

```python
# Legal document structure
@dataclass
class LegalChunk:
    law_id: str              # "GDPR"
    article: str             # "13"
    paragraph: str           # "1"
    subparagraph: str        # "a"
    text: str
    effective_date: date
    references: List[str]    # Cross-references to other articles
```

**Chunking by legal structure, not token count:**
- Each article = one chunk
- Preserve article/paragraph numbering
- Track cross-references

#### D. Hybrid Knowledge Base Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Router                             │
│  (Determines which knowledge base to search)                │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┬────────────┐
         │            │            │            │
         ▼            ▼            ▼            ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Static KB   │ │ Legal KB    │ │ Policy KB   │ │ Live API    │
│ (Scraped)   │ │ (wetten.nl) │ │ (Internal)  │ │ (Real-time) │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
     ↓                ↓              ↓              ↓
┌─────────────────────────────────────────────────────────────┐
│              Result Merger & Deduplication                  │
└─────────────────────────────────────────────────────────────┘
```

#### E. Version Tracking for Legal Content
Laws change. Track versions:

```python
@dataclass
class LegalVersion:
    bwb_id: str
    version_date: date
    text_hash: str
    changes_from_previous: List[str]

# On query: check if using latest version
# On answer: include "Gebaseerd op wetgeving per {date}"
```

### What to Focus On
- **Start with**: wetten.overheid.nl for core laws (AVG, AI Act, Archiefwet)
- **Key insight**: Legal content needs structure-aware chunking, not token-based
- **Important**: Version tracking - answers must cite which version of law

---

## 5. Intermediate Result Pattern (Validate Before Output)

### The Idea
Instead of generating a final answer directly, create a structured intermediate result that can be validated and scored before presenting to the user. This enables **real-time quality improvement** rather than just post-hoc signaling.

```
Query → Retrieval → INTERMEDIATE RESULT (JSON) → Validation → Final Output
                           ↓
                    [If score too low]
                           ↓
                    Regenerate / Refine
```

### When to Apply (Conditional)
Not every query needs full validation - it's resource intensive (extra LLM calls). Apply based on:

| Condition | Action |
|-----------|--------|
| **Simple factual query** | Skip validation, direct response |
| **Compliance/legal query** | Always validate (high stakes) |
| **Low confidence retrieval** (similarity < 0.7) | Validate + warn |
| **User role = decision-maker** | Validate (accountability) |
| **First query in session** | Validate (set quality baseline) |

```python
def should_validate(query: str, retrieval_results: List, context: UserContext) -> bool:
    # Always validate compliance queries
    if is_compliance_query(query):
        return True

    # Validate when retrieval confidence is low
    avg_similarity = mean([r.similarity for r in retrieval_results])
    if avg_similarity < 0.7:
        return True

    # Validate for high-stakes roles
    if context.role in ["manager", "legal", "policy"]:
        return True

    # Skip for simple queries with high-confidence retrieval
    return False
```

### Intermediate Result Structure

```json
{
  "query": {
    "original": "Wat zijn de GDPR eisen voor chatbots?",
    "intent": "compliance_check",
    "complexity": "moderate"
  },
  "retrieval": {
    "sources": [
      {
        "id": "src_1",
        "title": "AVG Richtlijnen Gemeenten",
        "section": "Chatbot-eisen",
        "url": "https://...",
        "similarity": 0.87,
        "text_snippet": "Gemeentelijke chatbots moeten..."
      }
    ],
    "avg_similarity": 0.82,
    "coverage": "partial"
  },
  "draft_answer": {
    "text": "Volgens de AVG moet een chatbot...",
    "claims": [
      {
        "claim": "Chatbots moeten transparant zijn over AI-gebruik",
        "source_id": "src_1",
        "supported": true,
        "quote": "..."
      },
      {
        "claim": "Boetes kunnen oplopen tot 4% van omzet",
        "source_id": null,
        "supported": false,
        "note": "Claim not found in retrieved sources"
      }
    ],
    "citations_used": ["src_1", "src_2"]
  },
  "validation": {
    "scores": {
      "groundedness": 0.75,
      "relevance": 0.90,
      "tone": 0.95,
      "completeness": 0.60
    },
    "overall": 0.80,
    "issues": [
      {
        "type": "unsupported_claim",
        "severity": "warning",
        "description": "Claim about fines not grounded in sources"
      },
      {
        "type": "incomplete",
        "severity": "info",
        "description": "Missing information about consent requirements"
      }
    ],
    "action": "refine"
  }
}
```

### Validation Actions

Based on overall score and issues:

| Score | Action | Description |
|-------|--------|-------------|
| **> 0.85** | `pass` | Return answer as-is |
| **0.70 - 0.85** | `refine` | Auto-fix minor issues (remove unsupported claims, add missing sources) |
| **0.50 - 0.70** | `regenerate` | Regenerate with stricter prompt |
| **< 0.50** | `escalate` | Flag for human review or refuse to answer |

```python
def determine_action(validation: ValidationResult) -> str:
    if validation.overall > 0.85:
        return "pass"
    elif validation.overall > 0.70:
        return "refine"
    elif validation.overall > 0.50:
        return "regenerate"
    else:
        return "escalate"
```

### Refinement Strategies

When `action = "refine"`:

```python
def refine_answer(intermediate: IntermediateResult) -> str:
    issues = intermediate.validation.issues

    for issue in issues:
        if issue.type == "unsupported_claim":
            # Remove or soften the unsupported claim
            intermediate.draft_answer = remove_claim(
                intermediate.draft_answer,
                issue.claim
            )

        elif issue.type == "missing_source":
            # Add source citation
            intermediate.draft_answer = add_citation(
                intermediate.draft_answer,
                issue.location,
                issue.suggested_source
            )

        elif issue.type == "tone_issue":
            # Rewrite specific sentence
            intermediate.draft_answer = rewrite_for_tone(
                intermediate.draft_answer,
                issue.sentence
            )

    return intermediate.draft_answer
```

### Implementation: Two-Pass Generation

**Pass 1: Generate structured draft**
```python
DRAFT_PROMPT = """
Genereer een antwoord in JSON-formaat:

VRAAG: {query}
BRONNEN: {sources}

Output JSON:
{
  "answer": "je antwoord hier",
  "claims": [
    {"text": "bewering 1", "source": "bron ID of null"},
    {"text": "bewering 2", "source": "bron ID of null"}
  ],
  "confidence": 0.0-1.0,
  "missing_info": ["wat je niet kon vinden"]
}
"""
```

**Pass 2: Validate (can use smaller/faster model)**
```python
VALIDATE_PROMPT = """
Valideer dit antwoord:

VRAAG: {query}
ANTWOORD: {answer}
BESCHIKBARE BRONNEN: {sources}
GECLAIMDE BRONNEN: {claimed_citations}

Check:
1. Staat elke bewering in de bronnen? (groundedness)
2. Beantwoordt het de vraag? (relevance)
3. Is de toon neutraal? (tone)
4. Ontbreekt belangrijke informatie? (completeness)

Output scores (0-1) en issues.
"""
```

### Efficiency Considerations

| Approach | Cost | When to Use |
|----------|------|-------------|
| **No validation** | 1 LLM call | Simple queries, high retrieval confidence |
| **Lightweight validation** | 1 LLM + rule-based checks | Medium complexity |
| **Full validation** | 2 LLM calls (draft + validate) | Compliance, low confidence, high stakes |
| **Parallel validation** | 1 LLM + async validator | When latency matters |

**Cost optimization:**
- Use smaller model (GPT-3.5 / Haiku) for validation pass
- Cache validation results for similar queries
- Batch validate in background for quality monitoring

### User Transparency

Show validation status to user (optional, for non-technical display):

```
┌────────────────────────────────────────────┐
│ 🟢 Betrouwbaarheid: Hoog                   │
│                                            │
│ Dit antwoord is gebaseerd op 3 bronnen     │
│ uit de AVG-richtlijnen.                    │
│                                            │
│ [Bekijk bronnen] [Feedback geven]          │
└────────────────────────────────────────────┘
```

Or for lower confidence:
```
┌────────────────────────────────────────────┐
│ 🟡 Betrouwbaarheid: Matig                  │
│                                            │
│ Let op: Dit antwoord is gebaseerd op       │
│ beperkte bronnen. Voor officieel advies,   │
│ raadpleeg een juridisch expert.            │
│                                            │
│ [Bekijk bronnen] [Vraag doorsturen]        │
└────────────────────────────────────────────┘
```

### What to Focus On
- **Start simple**: Rule-based validation (source count, length, keyword checks)
- **Add LLM validation**: For compliance queries only (conditional)
- **Show transparency**: Display confidence indicator to user
- **Measure impact**: Track % of queries that get refined vs passed through

---

## 6. Quality Metrics (Measuring Success)

### Required Metrics (from Challenge Brief)
1. **Relevance**: Does the answer address the question?
2. **Consistency**: Same question → similar answers?
3. **Tone/Sentiment**: Neutral, professional, no politics?
4. **Policy Compliance**: Follows government guidelines?

### Proposed Metric Implementation

```python
@dataclass
class QualityScore:
    relevance: float        # 0-1, semantic similarity to query
    groundedness: float     # 0-1, % of claims supported by sources
    tone_score: float       # 0-1, neutral/professional assessment
    readability: float      # 0-1, B1 level compliance
    conciseness: float      # 0-1, information density
    source_quality: float   # 0-1, authority of cited sources

    @property
    def overall(self) -> float:
        weights = {
            "relevance": 0.25,
            "groundedness": 0.25,
            "tone_score": 0.15,
            "readability": 0.15,
            "conciseness": 0.10,
            "source_quality": 0.10
        }
        return sum(getattr(self, k) * v for k, v in weights.items())
```

### LLM-as-Judge for Quality Checks
```python
JUDGE_PROMPT = """
Beoordeel dit antwoord op de volgende criteria (0-10):

VRAAG: {query}
ANTWOORD: {answer}
BRONNEN: {sources}

1. RELEVANTIE: Beantwoordt het de vraag?
2. GEGRONDHEID: Is alle informatie terug te vinden in de bronnen?
3. TOON: Is het neutraal en professioneel?
4. LEESBAARHEID: Is het begrijpelijk voor een gemiddelde burger?
5. BEKNOPTHEID: Is het zo kort als mogelijk zonder informatie te verliezen?

Geef per criterium een score en korte toelichting.
"""
```

---

## 7. Implementation Priorities

### For Hackathon (Focused Scope)

**Core Demo Flow:**
```
Query → Retrieval → Intermediate JSON → Validate → Refine (if needed) → Output
```

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 1 | Define intermediate JSON schema | Low | High |
| 2 | Add citation markers to prompt | Low | High |
| 3 | Implement rule-based validation | Medium | High |
| 4 | Add groundedness check (LLM) | Medium | High |
| 5 | Show confidence indicator to user | Low | Medium |
| 6 | Conditional validation logic | Low | Medium |

### Minimal Viable Demo
1. **Before**: Query → direct LLM response (no validation)
2. **After**: Query → intermediate result → validation score → refined output + confidence indicator

### Full Roadmap (Post-Hackathon)

#### Phase 1: Foundation
- [ ] Intermediate result JSON schema
- [ ] Citation markers in prompts
- [ ] Basic output validation (length, structure, source count)
- [ ] Style guide in system prompt

#### Phase 2: Validation Pipeline
- [ ] Groundedness scoring (claim → source matching)
- [ ] Conditional validation (when to apply)
- [ ] Refinement logic (auto-fix minor issues)
- [ ] Confidence indicator UI

#### Phase 3: Source Quality
- [ ] Source verification layer
- [ ] Citation format standard
- [ ] Dynamic sources (wetten.nl prototype)

#### Phase 4: Measurement & Iteration
- [ ] Quality metrics dashboard
- [ ] Before/after comparison
- [ ] Golden answer set for regression testing

---

## 9. Open Questions to Resolve

1. **Which laws to include first?** AVG (GDPR), AI Act, WOO, Archiefwet?
2. **How to handle conflicting sources?** (oude vs nieuwe wetgeving)
3. **Human-in-the-loop**: Where in the flow? Approval before sending? Feedback after?
4. **Golden answer set**: Who creates reference answers? Domain experts?
5. **Real-time vs batch quality checks**: Performance trade-off?
6. **When to skip validation?** Define clear thresholds for conditional application

---

## 10. Key Files to Modify

| File | Changes |
|------|---------|
| `enhanced_rag.py` | Add query preprocessing, multi-query retrieval |
| `enhanced_openai_service.py` | Add citation injection, intermediate result generation |
| `ai_responses.py` | Add IntermediateResult, ValidationResult dataclasses |
| `backend/app/routers/enhanced_chat.py` | Add validated chat endpoint |
| *NEW* `intermediate_validator.py` | Validation pipeline (groundedness, tone, completeness) |
| *NEW* `response_refiner.py` | Refinement logic for failed validations |
| *NEW* `legal_knowledge_base.py` | wetten.nl integration (future) |

---

## References

- [OpenEvals](https://github.com/openai/openevals) - LLM evaluation toolkit
- [DeepEval](https://github.com/confident-ai/deepeval) - LLM testing framework
- [wetten.overheid.nl](https://wetten.overheid.nl) - Dutch legal database
- [Rijksoverheid Schrijfwijzer](https://www.communicatierijk.nl/vakkennis/rijkswebsites/aanbevolen-richtlijnen/taalniveau-b1) - Government writing guidelines