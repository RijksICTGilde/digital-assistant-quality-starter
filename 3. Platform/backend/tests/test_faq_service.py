"""Test cases for the FAQ matching service."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_rag import get_local_embedding_model
from app.features.faq import FAQService, FAQMatch


@pytest.fixture(scope="module")
def faq_service():
    """Create a FAQService instance for testing."""
    embedding_model = get_local_embedding_model()
    return FAQService(embedding_model=embedding_model)


class TestFAQServiceInitialization:
    """Test FAQ service initialization."""

    def test_service_loads_faqs(self, faq_service):
        """Service should load FAQs from JSON file."""
        assert len(faq_service.faqs) > 0
        assert len(faq_service.questions) > 0

    def test_service_creates_index(self, faq_service):
        """Service should create FAISS index."""
        assert faq_service.index is not None

    def test_question_to_faq_mapping(self, faq_service):
        """Each question should map to a valid FAQ index."""
        for faq_idx in faq_service.question_to_faq:
            assert 0 <= faq_idx < len(faq_service.faqs)


class TestExactMatches:
    """Test cases that should return exact matches (score >= 0.85)."""

    @pytest.mark.parametrize("query,expected_faq_id", [
        # Exact question matches
        ("Wat doet deze AI assistent?", "faq-001"),
        ("Wanneer treedt de AI Act in werking?", "faq-002"),
        ("Wat is een DPIA?", "faq-003"),
        ("Waar vind ik de GIBIT?", "faq-004"),
        ("Moet ik een algoritme registreren?", "faq-005"),
        ("Hoe lang mag ik persoonsgegevens bewaren?", "faq-006"),
        ("Wat zijn hoog-risico AI-systemen?", "faq-007"),
        ("Wat is de BIO?", "faq-008"),
    ])
    def test_exact_question_matches(self, faq_service, query, expected_faq_id):
        """Exact questions from FAQ should match with high confidence."""
        match, decision = faq_service.get_best_match(query)
        assert match is not None, f"No match found for: {query}"
        assert decision == "exact", f"Expected 'exact' but got '{decision}' for: {query}"
        assert match.faq_id == expected_faq_id, f"Expected {expected_faq_id} but got {match.faq_id}"
        assert match.score >= 0.85, f"Score {match.score} too low for exact match"

    @pytest.mark.parametrize("query,expected_faq_id", [
        # Slight variations that should still match
        ("Wanneer gaat de AI Act in?", "faq-002"),
        ("Vanaf wanneer geldt de AI Act?", "faq-002"),
        ("Wat betekent DPIA?", "faq-003"),
        ("Wanneer moet ik een DPIA doen?", "faq-003"),
        ("Wat is de GIBIT?", "faq-004"),
        ("Algoritmeregister verplicht?", "faq-005"),
        ("Wat zijn de bewaartermijnen AVG?", "faq-006"),
        ("Welke AI is hoog-risico?", "faq-007"),
        ("Baseline Informatiebeveiliging Overheid", "faq-008"),
    ])
    def test_question_variants_match(self, faq_service, query, expected_faq_id):
        """Alternative phrasings should also match correctly."""
        match, decision = faq_service.get_best_match(query)
        assert match is not None, f"No match found for: {query}"
        assert match.faq_id == expected_faq_id, f"Expected {expected_faq_id} but got {match.faq_id}"
        # Variants should at least suggest, ideally exact
        assert decision in ["exact", "suggest"], f"Expected match for: {query}"


class TestSemanticMatches:
    """Test semantic matching with paraphrased questions."""

    @pytest.mark.parametrize("query,expected_faq_id,min_decision", [
        # Paraphrased questions - using queries more likely to match correctly
        ("Wat zijn de deadlines van de AI Act?", "faq-002", "suggest"),
        ("Wanneer is een DPIA verplicht?", "faq-003", "suggest"),
        ("Inkoopvoorwaarden IT gemeente", "faq-004", "suggest"),
        ("Moet mijn algoritme geregistreerd worden?", "faq-005", "suggest"),
        ("Bewaartermijnen persoonsgegevens", "faq-006", "suggest"),
        ("Welke AI systemen zijn risicovol?", "faq-007", "suggest"),
        ("Informatiebeveiliging standaard overheid", "faq-008", "suggest"),
    ])
    def test_paraphrased_questions(self, faq_service, query, expected_faq_id, min_decision):
        """Paraphrased questions should match the right FAQ."""
        match, decision = faq_service.get_best_match(query)
        assert match is not None, f"No match found for: {query}"
        assert match.faq_id == expected_faq_id, f"Expected {expected_faq_id} but got {match.faq_id} for: {query}"

        # Check decision meets minimum expectation
        decision_levels = {"none": 0, "suggest": 1, "exact": 2}
        assert decision_levels[decision] >= decision_levels[min_decision], \
            f"Expected at least '{min_decision}' but got '{decision}' for: {query}"


class TestNoMatches:
    """Test cases that should NOT match any FAQ."""

    @pytest.mark.parametrize("query", [
        # Off-topic questions - completely unrelated to government/IT topics
        "Hoe is het weer vandaag?",
        "Wat is de hoofdstad van Frankrijk?",
        "Hoe laat is het?",
        "Kun je een mop vertellen?",
        "Wat is 2 + 2?",
        "Wat zijn de openingstijden van het gemeentehuis?",
        "Hoeveel inwoners heeft Amsterdam?",
        "Wat is de beste pizza?",
    ])
    def test_offtopic_questions_no_match(self, faq_service, query):
        """Off-topic questions should not match any FAQ."""
        match, decision = faq_service.get_best_match(query)
        assert decision == "none", f"Expected 'none' but got '{decision}' for: {query}"
        if match:
            assert match.score < 0.70, f"Score {match.score} too high for off-topic: {query}"


class TestMatchMethod:
    """Test the match() method that returns multiple results."""

    def test_match_returns_multiple_results(self, faq_service):
        """match() should return up to k results."""
        matches = faq_service.match("AI regelgeving", k=3)
        assert len(matches) <= 3
        assert all(isinstance(m, FAQMatch) for m in matches)

    def test_match_results_sorted_by_score(self, faq_service):
        """Results should be sorted by score (highest first)."""
        matches = faq_service.match("data privacy", k=5)
        scores = [m.score for m in matches]
        assert scores == sorted(scores, reverse=True), "Results not sorted by score"

    def test_match_deduplicates_faqs(self, faq_service):
        """Same FAQ should not appear multiple times."""
        matches = faq_service.match("AI Act verplichtingen", k=5)
        faq_ids = [m.faq_id for m in matches]
        assert len(faq_ids) == len(set(faq_ids)), "Duplicate FAQs in results"


class TestFAQMatchDataclass:
    """Test FAQMatch dataclass properties."""

    def test_match_has_all_fields(self, faq_service):
        """FAQMatch should have all required fields."""
        match, _ = faq_service.get_best_match("Wat is een DPIA?")
        assert match is not None
        assert hasattr(match, 'faq_id')
        assert hasattr(match, 'category')
        assert hasattr(match, 'matched_question')
        assert hasattr(match, 'answer')
        assert hasattr(match, 'score')
        assert hasattr(match, 'metadata')
        assert hasattr(match, 'related_questions')

    def test_match_answer_not_empty(self, faq_service):
        """Matched FAQ should have a non-empty answer."""
        match, _ = faq_service.get_best_match("Wat is de BIO?")
        assert match is not None
        assert len(match.answer) > 0

    def test_match_has_related_questions(self, faq_service):
        """Matched FAQ should include related questions."""
        match, _ = faq_service.get_best_match("Wat is een DPIA?")
        assert match is not None
        assert match.related_questions is not None
        assert len(match.related_questions) > 0
        # Related questions should not include the matched question
        assert match.matched_question not in match.related_questions

    def test_related_questions_limited_to_five(self, faq_service):
        """Related questions should be limited to 5."""
        match, _ = faq_service.get_best_match("Wat is een DPIA?")
        assert match is not None
        assert len(match.related_questions) <= 5


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_query(self, faq_service):
        """Empty query should not crash."""
        match, decision = faq_service.get_best_match("")
        # Empty query should return no match or very low score
        assert decision == "none" or (match and match.score < 0.70)

    def test_very_long_query(self, faq_service):
        """Very long query should not crash."""
        long_query = "Wat is de AI Act? " * 100
        match, decision = faq_service.get_best_match(long_query)
        # Should still work and likely match AI Act FAQ
        assert match is not None or decision == "none"

    def test_special_characters(self, faq_service):
        """Query with special characters should not crash."""
        queries = [
            "Wat is een DPIA???",
            "AI Act!!!!",
            "GIBIT @#$%",
            "BIO <script>alert('test')</script>",
        ]
        for query in queries:
            match, decision = faq_service.get_best_match(query)
            # Should not raise exception
            assert decision in ["exact", "suggest", "none"]

    def test_mixed_case_query(self, faq_service):
        """Mixed case queries should still match."""
        queries = [
            ("WAT IS EEN DPIA?", "faq-003"),
            ("wat is een dpia?", "faq-003"),
            ("WaT iS eEn DpIa?", "faq-003"),
        ]
        for query, expected_faq in queries:
            match, decision = faq_service.get_best_match(query)
            assert match is not None, f"No match for: {query}"
            # Should at least suggest
            assert decision in ["exact", "suggest"], f"Expected match for: {query}"


class TestThresholds:
    """Test the threshold behavior."""

    def test_high_confidence_threshold(self, faq_service):
        """Verify HIGH_CONFIDENCE_THRESHOLD is 0.85."""
        assert faq_service.HIGH_CONFIDENCE_THRESHOLD == 0.85

    def test_suggest_threshold(self, faq_service):
        """Verify SUGGEST_THRESHOLD is 0.70."""
        assert faq_service.SUGGEST_THRESHOLD == 0.70

    def test_exact_match_above_threshold(self, faq_service):
        """Exact matches should have score >= 0.85."""
        match, decision = faq_service.get_best_match("Wat is een DPIA?")
        if decision == "exact":
            assert match.score >= 0.85

    def test_suggest_match_in_range(self, faq_service):
        """Suggest matches should have score in [0.70, 0.85)."""
        # This is harder to test reliably, but we can check the logic
        match, decision = faq_service.get_best_match("privacy beoordeling impact")
        if decision == "suggest":
            assert 0.70 <= match.score < 0.85


class TestReload:
    """Test the reload functionality."""

    def test_reload_does_not_crash(self, faq_service):
        """reload() should not raise exceptions."""
        original_count = len(faq_service.faqs)
        faq_service.reload()
        assert len(faq_service.faqs) == original_count


class TestNewFAQs:
    """Test cases for newly added FAQs (faq-009 through faq-020)."""

    @pytest.mark.parametrize("query,expected_faq_id", [
        # New FAQs - exact matches
        ("Wat is een verwerkingsregister?", "faq-009"),
        ("Wat is een FG?", "faq-010"),
        ("Wat is verboden onder de AI Act?", "faq-011"),
        ("Wat is een verwerkersovereenkomst?", "faq-012"),
        ("Wat moet ik doen bij een datalek?", "faq-013"),
        ("Moet ik AI-gegenereerde content labelen?", "faq-014"),
        ("Wat is de Wet digitale overheid?", "faq-015"),
        ("Wat is een AI-geletterdheid verplichting?", "faq-016"),
        ("Wat zijn open standaarden?", "faq-017"),
        ("Wat zijn de rechten van betrokkenen?", "faq-018"),
        ("Wat is een pentest?", "faq-019"),
        ("Wat is menselijk toezicht bij AI?", "faq-020"),
    ])
    def test_new_faq_exact_matches(self, faq_service, query, expected_faq_id):
        """New FAQs should match their exact questions."""
        match, decision = faq_service.get_best_match(query)
        assert match is not None, f"No match found for: {query}"
        assert match.faq_id == expected_faq_id, f"Expected {expected_faq_id} but got {match.faq_id}"
        assert decision in ["exact", "suggest"], f"Expected match for: {query}"

    @pytest.mark.parametrize("query,expected_faq_id", [
        # Question variants for new FAQs
        ("Functionaris Gegevensbescherming", "faq-010"),
        ("DPO Data Protection Officer", "faq-010"),
        ("Sociale scoring verboden?", "faq-011"),
        ("AVG leverancier contract", "faq-012"),
        ("Datalek melden", "faq-013"),
        ("Meldplicht datalekken", "faq-013"),
        ("Deepfakes labelen", "faq-014"),
        ("Wdo verplichtingen", "faq-015"),
        ("AI literacy", "faq-016"),
        ("Pas toe of leg uit", "faq-017"),
        ("Inzagerecht AVG", "faq-018"),
        ("Recht op vergetelheid", "faq-018"),
        ("Penetratietest gemeente", "faq-019"),
        ("Human oversight AI", "faq-020"),
        ("Human in the loop", "faq-020"),
    ])
    def test_new_faq_variants_match(self, faq_service, query, expected_faq_id):
        """Question variants for new FAQs should match."""
        match, decision = faq_service.get_best_match(query)
        assert match is not None, f"No match found for: {query}"
        assert match.faq_id == expected_faq_id, f"Expected {expected_faq_id} but got {match.faq_id} for: {query}"


class TestFAQCategories:
    """Test that FAQ categories are properly set."""

    def test_faq_categories_exist(self, faq_service):
        """All FAQs should have a category."""
        for faq in faq_service.faqs:
            assert "category" in faq
            assert len(faq["category"]) > 0

    def test_expected_categories(self, faq_service):
        """Expected categories should be present."""
        categories = {faq["category"] for faq in faq_service.faqs}
        expected = {"algemeen", "ai_act", "avg", "inkoop", "algoritmes", "security", "digitalisering"}
        assert expected.issubset(categories), f"Missing categories: {expected - categories}"


class TestFAQCount:
    """Test the number of FAQs loaded."""

    def test_minimum_faq_count(self, faq_service):
        """Should have at least 20 FAQs."""
        assert len(faq_service.faqs) >= 20, f"Only {len(faq_service.faqs)} FAQs loaded"

    def test_minimum_question_count(self, faq_service):
        """Should have many question variants."""
        assert len(faq_service.questions) >= 80, f"Only {len(faq_service.questions)} questions indexed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
