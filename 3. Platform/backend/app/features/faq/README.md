# FAQ Matching Service

Semantische FAQ-matching voor snelle, consistente antwoorden zonder LLM-calls.

## Hoe het werkt

1. **Startup**: Alle FAQ-vragen worden geëmbed met `robbert-2022-dutch-sentence-transformers`
2. **Runtime**: Gebruikersvraag wordt vergeleken via FAISS (cosine similarity)
3. **Routing**: Op basis van score wordt bepaald of LLM nodig is

## Thresholds

| Score | Beslissing | Actie |
|-------|------------|-------|
| ≥ 0.85 | `exact` | Direct FAQ-antwoord, skip LLM (~50ms) |
| 0.70-0.85 | `suggest` | FAQ als suggestie meegeven aan LLM |
| < 0.70 | `none` | Normale LLM-verwerking (~1500ms) |

## Bestanden

```
faq/
├── __init__.py          # Exports: FAQService, FAQMatch
├── faq_data.json        # FAQ database (vragen + antwoorden)
├── faq_service.py       # Core service met FAISS matching
└── README.md
```

## FAQ toevoegen

Edit `faq_data.json`:

```json
{
  "id": "faq-021",
  "category": "avg",
  "questions": [
    "Hoofdvraag?",
    "Variant 1?",
    "Variant 2?"
  ],
  "answer": "Het antwoord met **markdown** formatting.",
  "metadata": {"priority": "high", "source": "Bron"}
}
```

**Tips:**
- Voeg 3-8 vraagvarianten toe per FAQ
- Gebruik natuurlijke vraagformuleringen
- Herstart niet nodig: `faq_service.reload()` voor hot reload

## Testen

```bash
cd backend
python -m pytest tests/test_faq_service.py -v
```

## Architectuur

```
User Question
     ↓
[SentenceTransformer] → 768-dim vector
     ↓
[FAISS IndexFlatIP] → cosine similarity search
     ↓
score ≥ 0.85? ──yes──→ Return FAQ answer (skip LLM)
     ↓ no
score ≥ 0.70? ──yes──→ Pass suggestion to LLM
     ↓ no
Normal LLM processing
```

## Waarom FAISS?

### Voordelen
- **Al aanwezig**: Wordt al gebruikt in `enhanced_rag.py`, geen extra dependencies
- **Snel**: <1ms voor 100 FAQs, ~2ms voor 1000 FAQs
- **Eenvoudig**: 3 regels code voor create/index/search
- **Schaalt**: `IndexFlatIP` voor <10K, `IndexIVFFlat` voor grotere sets

### Alternatieven overwogen

| Optie | Reden niet gekozen |
|-------|-------------------|
| Pinecone/Weaviate | Externe service, overkill voor ~100 FAQs |
| ChromaDB | Extra dependency |
| Numpy dot product | Langzamer, geen indexing |
| Keyword search (BM25) | Mist semantische matches ("DPIA" ↔ "privacy impact assessment") |

FAISS is de pragmatische keuze: snel, lokaal, en al beschikbaar in de codebase.
