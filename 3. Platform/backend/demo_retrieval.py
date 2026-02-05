#!/usr/bin/env python3
"""
Demo script to show what the LLM actually receives from the RAG system.

Run from the 'backend' directory:
    python demo_retrieval.py

Or with a custom query:
    python demo_retrieval.py "Wat zijn de GDPR eisen voor chatbots?"
"""

import sys
import os
import json

# Resolve paths relative to this script's location (backend/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(SCRIPT_DIR)  # 3. Platform/
PROJECT_ROOT = os.path.dirname(PLATFORM_DIR)  # project root

# Add the Platform dir to path so we can import enhanced_rag
sys.path.insert(0, PLATFORM_DIR)

# Load .env from backend directory
from dotenv import load_dotenv
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

from enhanced_rag import EnhancedRAGSystem

# Configuration - paths relative to project structure
DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "1. Datasets", "Scrapen", "scraped_content", "content")
CACHE_DIR = os.path.join(SCRIPT_DIR, "cache")
DEFAULT_QUERY = "Wat zijn de belangrijkste privacy eisen voor een chatbot bij de gemeente?"


def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def show_retrieval_results(rag: EnhancedRAGSystem, query: str, k: int = 5):
    """Show raw retrieval results from FAISS"""

    print_separator("1. RAW RETRIEVAL RESULTS (from FAISS vector search)")
    print(f"Query: \"{query}\"")
    print(f"Retrieving top {k} chunks...\n")

    from enhanced_rag import EMBEDDING_DIMENSIONS, USE_LOCAL_EMBEDDINGS, LOCAL_EMBEDDING_MODEL, EMBEDDING_MODEL
    model_name = LOCAL_EMBEDDING_MODEL if USE_LOCAL_EMBEDDINGS else EMBEDDING_MODEL
    print(f"  Embedding: {model_name} ({EMBEDDING_DIMENSIONS}d, {'local' if USE_LOCAL_EMBEDDINGS else 'API'})\n")
    results = rag.retrieve_documents(query, k=k)

    if not results:
        print("No results found!")
        return []

    for i, result in enumerate(results, 1):
        chunk = result.chunk
        print(f"--- Result {i} ---")
        print(f"  Similarity Score: {result.similarity_score:.4f} ({result.similarity_score * 100:.1f}%)")
        print(f"  File: {os.path.basename(chunk.file_path)}")
        print(f"  Section: {chunk.section_title or 'N/A'}")
        print(f"  Chunk: {chunk.chunk_index + 1} of {chunk.total_chunks}")
        print(f"  Original URL: {chunk.original_url or 'N/A'}")
        print(f"  Content preview ({len(chunk.content)} chars):")
        # Show first 300 chars of content
        preview = chunk.content[:300].replace('\n', ' ')
        print(f"    \"{preview}...\"")
        print()

    return results


def show_formatted_context(rag: EnhancedRAGSystem, query: str, max_chunks: int = 3):
    """Show the formatted context that gets passed to LLM"""

    print_separator("2. FORMATTED CONTEXT (what gets injected into prompt)")

    context, sources = rag.get_context_for_query(query, max_chunks=max_chunks)

    print(f"Sources list: {sources}\n")
    print("Context string:")
    print("-" * 40)
    print(context)
    print("-" * 40)

    return context, sources


def show_full_prompt(context: str, sources: list, query: str):
    """Show what the full LLM prompt looks like - the ACTUAL input to the model"""

    print_separator("3. FULL LLM PROMPT (exactly what the model receives)")

    # This mimics what enhanced_openai_service.py does
    system_prompt = f"""Je bent een AI assistant voor Nederlandse gemeentes, gespecialiseerd in digitale transformatie en AI implementatie.

GEBRUIKER CONTEXT:
- Rol: Gemeenteambtenaar
- Projectfase: Verkenning
- Focusgebieden: Privacy, AI Implementatie
- Specifieke context: Geen extra context

RELEVANTE KENNISBANK INFORMATIE:

{context}

INSTRUCTIES:
1. Gebruik de kennisbank informatie om accurate, brongestuurde antwoorden te geven
2. Wees specifiek over regelgeving en compliance requirements
3. Geef praktische, uitvoerbare adviezen
4. Verwijs naar menselijke experts voor complexe juridische interpretaties
5. Houd altijd rekening met de Nederlandse overheidscontext
6. Wees transparant over beperkingen van je kennis

RESPONSE FORMAT:
Geef een duidelijke hoofdrespons die de vraag volledig beantwoordt.
Voeg GEEN bronverwijzingen, vervolgvragen of escalatie-informatie toe - deze worden automatisch toegevoegd door het systeem.
"""

    print("=" * 40)
    print("  SYSTEM MESSAGE (role: system)")
    print("=" * 40)
    print(system_prompt)
    print("=" * 40)
    print("  USER MESSAGE (role: user)")
    print("=" * 40)
    print(query)
    print("=" * 40)

    # Token estimate
    total_chars = len(system_prompt) + len(query)
    estimated_tokens = total_chars // 4  # Rough estimate
    print(f"\nTotal characters: {total_chars}")
    print(f"Estimated tokens: ~{estimated_tokens}")


def show_what_llm_doesnt_see():
    """Show what information is NOT passed to the LLM"""

    print_separator("4. WHAT THE LLM DOES NOT SEE")

    print("""
The LLM does NOT receive:
- The full document database (only top-k retrieved chunks)
- Documents with low similarity scores
- The vector embeddings themselves
- The similarity scores (only used for ranking)
- Other user sessions or queries
- Real-time updates to documents (uses cached index)

This means:
- If the answer isn't in the top-k chunks, the LLM won't know about it
- The LLM may hallucinate if asked about topics not covered by retrieved chunks
- The relevance of chunks depends entirely on the embedding model's understanding
""")


def export_as_json(results: list, context: str, sources: list, query: str, output_file: str = None):
    """Export the retrieval data as JSON for inspection"""

    print_separator("5. EXPORTING DEBUG DATA")

    if output_file is None:
        output_file = os.path.join(SCRIPT_DIR, "retrieval_debug.json")

    data = {
        "query": query,
        "retrieval_results": [
            {
                "similarity_score": r.similarity_score,
                "file_path": r.chunk.file_path,
                "section_title": r.chunk.section_title,
                "chunk_index": r.chunk.chunk_index,
                "total_chunks": r.chunk.total_chunks,
                "original_url": r.chunk.original_url,
                "content": r.chunk.content
            }
            for r in results
        ],
        "formatted_sources": sources,
        "formatted_context": context
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Debug data exported to: {output_file}")
    print("You can inspect this file to see the full content of each retrieved chunk.")


def main():
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = DEFAULT_QUERY

    print("\n" + "=" * 80)
    print(" RAG RETRIEVAL DEMO - What does the LLM actually receive?")
    print("=" * 80)

    # Initialize RAG system
    print(f"Documents dir: {DOCUMENTS_DIR}")
    print(f"Cache dir:     {CACHE_DIR}")
    print("(This may take a moment on first run...)\n")

    if not os.path.exists(DOCUMENTS_DIR):
        print(f"ERROR: Documents directory not found: {DOCUMENTS_DIR}")
        sys.exit(1)

    try:
        rag = EnhancedRAGSystem(DOCUMENTS_DIR, cache_dir=CACHE_DIR)
    except Exception as e:
        print(f"Error initializing RAG system: {e}")
        print("\nMake sure you have:")
        print("  1. GREENPT_API_KEY set in backend/.env")
        print("  2. Documents in the correct directory")
        sys.exit(1)

    # Show each step
    results = show_retrieval_results(rag, query, k=5)
    context, sources = show_formatted_context(rag, query, max_chunks=3)
    show_full_prompt(context, sources, query)
    show_what_llm_doesnt_see()

    if results:
        export_as_json(results, context, sources, query)

    print("\n" + "=" * 80)
    print(" END OF DEMO")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()