"""FAQ matching service using FAISS and SentenceTransformer embeddings.

This service matches user questions against a predefined FAQ database
for faster, more consistent responses without requiring LLM calls.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np
from loguru import logger


@dataclass
class FAQMatch:
    """Represents a matched FAQ entry."""

    faq_id: str
    category: str
    matched_question: str
    answer: str
    score: float
    metadata: dict
    related_questions: List[str] = None  # Other question variants for this FAQ
    sources: List[dict] = None  # Pre-defined knowledge sources for this FAQ


class FAQService:
    """Service for matching user questions against FAQ database using semantic search.

    Matching thresholds:
    - Score >= 0.85: Direct FAQ answer (skip LLM)
    - Score 0.70-0.85: FAQ as suggestion for LLM
    - Score < 0.70: No match, normal LLM processing
    """

    HIGH_CONFIDENCE_THRESHOLD = 0.85
    SUGGEST_THRESHOLD = 0.70

    def __init__(self, embedding_model):
        """Initialize the FAQ service.

        Args:
            embedding_model: A SentenceTransformer model for creating embeddings
        """
        self.embedding_model = embedding_model
        self.faqs: List[dict] = []
        self.questions: List[str] = []  # All questions (flattened)
        self.question_to_faq: List[int] = []  # Maps question index to FAQ index
        self.index: Optional[faiss.IndexFlatIP] = None
        self._load_and_index()

    def _load_and_index(self) -> None:
        """Load FAQ data and build the FAISS index."""
        # Find the FAQ data file
        faq_file = Path(__file__).parent / "faq_data.json"

        if not faq_file.exists():
            logger.warning(f"[FAQ] FAQ data file not found: {faq_file}")
            return

        try:
            with open(faq_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.faqs = data.get("faqs", [])
            logger.info(f"[FAQ] Loaded {len(self.faqs)} FAQ entries")

            # Flatten all questions and track which FAQ they belong to
            self.questions = []
            self.question_to_faq = []

            for faq_idx, faq in enumerate(self.faqs):
                for question in faq.get("questions", []):
                    self.questions.append(question)
                    self.question_to_faq.append(faq_idx)

            if not self.questions:
                logger.warning("[FAQ] No questions found in FAQ data")
                return

            # Create embeddings for all questions
            logger.info(f"[FAQ] Creating embeddings for {len(self.questions)} questions...")
            embeddings = self.embedding_model.encode(
                self.questions, show_progress_bar=False
            ).astype(np.float32)

            # Normalize for cosine similarity
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            # Build FAISS index
            embedding_dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(embedding_dim)
            self.index.add(embeddings)

            logger.info(
                f"[FAQ] Indexed {len(self.questions)} questions "
                f"(dim={embedding_dim}, faqs={len(self.faqs)})"
            )

        except Exception as e:
            logger.error(f"[FAQ] Failed to load and index FAQs: {e}")
            self.faqs = []
            self.questions = []
            self.index = None

    def match(self, query: str, k: int = 3) -> List[FAQMatch]:
        """Find the best matching FAQ entries for a query.

        Args:
            query: The user's question
            k: Number of matches to return

        Returns:
            List of FAQMatch objects sorted by score (highest first)
        """
        if not self.index or not self.questions:
            return []

        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode([query]).astype(np.float32)
            query_embedding = query_embedding / np.linalg.norm(
                query_embedding, axis=1, keepdims=True
            )

            # Search
            scores, indices = self.index.search(query_embedding, k)

            matches = []
            seen_faqs = set()  # Deduplicate by FAQ ID

            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.questions):
                    continue

                faq_idx = self.question_to_faq[idx]
                faq = self.faqs[faq_idx]
                faq_id = faq.get("id", f"faq-{faq_idx}")

                # Skip if we already have this FAQ (from a different question variant)
                if faq_id in seen_faqs:
                    continue
                seen_faqs.add(faq_id)

                # Get related questions (other variants, excluding the matched one)
                all_questions = faq.get("questions", [])
                related = [q for q in all_questions if q != self.questions[idx]]

                matches.append(
                    FAQMatch(
                        faq_id=faq_id,
                        category=faq.get("category", ""),
                        matched_question=self.questions[idx],
                        answer=faq.get("answer", ""),
                        score=float(score),
                        metadata=faq.get("metadata", {}),
                        related_questions=related[:5],  # Limit to 5 examples
                        sources=faq.get("sources", []),  # Pre-defined sources
                    )
                )

            return matches

        except Exception as e:
            logger.error(f"[FAQ] Match failed: {e}")
            return []

    def get_best_match(self, query: str) -> Tuple[Optional[FAQMatch], str]:
        """Get the best FAQ match and determine the routing decision.

        Args:
            query: The user's question

        Returns:
            Tuple of (FAQMatch or None, decision string)
            Decision is one of: "exact", "suggest", "none"
        """
        matches = self.match(query, k=1)

        if not matches:
            logger.debug(f"[FAQ] No matches for: {query[:50]}...")
            return None, "none"

        best_match = matches[0]
        score = best_match.score

        if score >= self.HIGH_CONFIDENCE_THRESHOLD:
            logger.info(
                f"[FAQ] EXACT match (score={score:.3f}): "
                f"'{query[:30]}...' → {best_match.faq_id}"
            )
            return best_match, "exact"

        if score >= self.SUGGEST_THRESHOLD:
            logger.info(
                f"[FAQ] SUGGEST match (score={score:.3f}): "
                f"'{query[:30]}...' → {best_match.faq_id}"
            )
            return best_match, "suggest"

        logger.debug(
            f"[FAQ] Low score match (score={score:.3f}): "
            f"'{query[:30]}...' → {best_match.faq_id}"
        )
        return best_match, "none"

    def reload(self) -> None:
        """Reload FAQs from file (hot reload support)."""
        logger.info("[FAQ] Reloading FAQ data...")
        self._load_and_index()
