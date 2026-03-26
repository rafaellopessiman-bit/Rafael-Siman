"""Tests for src.knowledge.confidence module."""
import pytest

from src.knowledge.confidence import (
    ABSTENTION_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    ConfidenceAssessment,
    assess_confidence,
)


class TestAssessConfidence:
    def test_empty_documents_abstains(self):
        result = assess_confidence([])
        assert result.level == "abstain"
        assert not result.should_answer
        assert result.relevant_count == 0

    def test_all_zero_scores_abstains(self):
        docs = [{"score": 0}, {"score": 0}]
        result = assess_confidence(docs)
        assert result.level == "abstain"
        assert not result.should_answer

    def test_below_threshold_abstains(self):
        docs = [{"score": ABSTENTION_THRESHOLD - 0.1}]
        result = assess_confidence(docs)
        assert result.level == "abstain"
        assert not result.should_answer

    def test_above_threshold_answers(self):
        docs = [{"score": ABSTENTION_THRESHOLD + 0.1}]
        result = assess_confidence(docs)
        assert result.should_answer

    def test_high_score_multiple_sources_high_confidence(self):
        docs = [
            {"score": HIGH_CONFIDENCE_THRESHOLD + 5},
            {"score": HIGH_CONFIDENCE_THRESHOLD},
            {"score": 2.0},
        ]
        result = assess_confidence(docs)
        assert result.level == "high"
        assert result.should_answer
        assert result.relevant_count == 3
        assert not result.warnings

    def test_high_score_single_source_medium_confidence(self):
        docs = [{"score": HIGH_CONFIDENCE_THRESHOLD + 1}]
        result = assess_confidence(docs)
        assert result.level == "medium"
        assert result.should_answer
        assert any("uma fonte" in w.lower() for w in result.warnings)

    def test_low_score_single_source_low_confidence(self):
        docs = [{"score": ABSTENTION_THRESHOLD + 0.2}]
        result = assess_confidence(docs)
        assert result.level == "low"
        assert result.should_answer
        assert len(result.warnings) > 0

    def test_explanation_varies_by_level(self):
        abstain = assess_confidence([])
        assert "insuficiente" in abstain.explanation.lower()

        low = assess_confidence([{"score": 1.0}])
        assert "baixa" in low.explanation.lower()

        high = assess_confidence([
            {"score": 20.0},
            {"score": 15.0},
            {"score": 10.0},
        ])
        assert "alta" in high.explanation.lower()

    def test_score_gap_ratio_calculated(self):
        docs = [{"score": 10.0}, {"score": 2.0}]
        result = assess_confidence(docs)
        assert result.score_gap_ratio == pytest.approx(5.0)

    def test_single_doc_infinite_gap_ratio(self):
        docs = [{"score": 10.0}]
        result = assess_confidence(docs)
        assert result.score_gap_ratio == float("inf")

    def test_negative_scores_ignored(self):
        docs = [{"score": -1.0}, {"score": 0.0}]
        result = assess_confidence(docs)
        assert result.level == "abstain"
        assert result.relevant_count == 0

    def test_mixed_scores(self):
        docs = [
            {"score": 8.0},
            {"score": 0.0},
            {"score": 3.0},
            {"score": -0.5},
        ]
        result = assess_confidence(docs)
        assert result.should_answer
        assert result.relevant_count == 2
        assert result.top_score == 8.0
