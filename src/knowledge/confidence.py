"""Evidence confidence assessment for retrieval-augmented answers.

Evaluates the quality and distribution of retrieved evidence to decide
whether to answer, abstain, or warn the user about low confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Thresholds ──────────────────────────────────────────
# Minimum top-1 score to consider any answer at all
ABSTENTION_THRESHOLD = 0.5

# Minimum top-1 score for "high" confidence
HIGH_CONFIDENCE_THRESHOLD = 5.0

# Minimum ratio between top-1 and top-2 scores to consider a clear winner
SCORE_GAP_RATIO = 1.5

# Minimum number of relevant documents (score > 0) for high confidence
MIN_SOURCES_HIGH = 2


@dataclass
class ConfidenceAssessment:
    """Result of evidence confidence analysis."""
    level: str  # "high", "medium", "low", "abstain"
    should_answer: bool
    top_score: float
    score_gap_ratio: float  # top1/top2 — higher means clearer winner
    relevant_count: int
    warnings: list[str] = field(default_factory=list)

    @property
    def explanation(self) -> str:
        if self.level == "abstain":
            return "Evidência insuficiente nos documentos locais."
        if self.level == "low":
            return (
                f"Confiança baixa (score máx: {self.top_score:.1f}, "
                f"{self.relevant_count} fonte(s)). Resposta pode ser imprecisa."
            )
        if self.level == "medium":
            return (
                f"Confiança média (score máx: {self.top_score:.1f}, "
                f"{self.relevant_count} fonte(s))."
            )
        return f"Confiança alta ({self.relevant_count} fonte(s), score máx: {self.top_score:.1f})."


def assess_confidence(ranked_documents: list[dict[str, Any]]) -> ConfidenceAssessment:
    """Analyze retrieval scores and produce a confidence assessment.

    Decision logic:
    - abstain: no documents or top score below ABSTENTION_THRESHOLD
    - low:     top score above threshold but below HIGH_CONFIDENCE_THRESHOLD
               and either only 1 source or no clear score gap
    - medium:  decent score but some concern (few sources or narrow gap)
    - high:    strong top score, multiple sources, clear winner
    """
    positive = [d for d in ranked_documents if float(d.get("score", 0)) > 0]

    if not positive:
        return ConfidenceAssessment(
            level="abstain",
            should_answer=False,
            top_score=0.0,
            score_gap_ratio=0.0,
            relevant_count=0,
            warnings=["Nenhum documento relevante encontrado."],
        )

    scores = sorted((float(d.get("score", 0)) for d in positive), reverse=True)
    top_score = scores[0]
    second_score = scores[1] if len(scores) > 1 else 0.0
    gap_ratio = top_score / second_score if second_score > 0 else float("inf")
    relevant_count = len(positive)

    if top_score < ABSTENTION_THRESHOLD:
        return ConfidenceAssessment(
            level="abstain",
            should_answer=False,
            top_score=top_score,
            score_gap_ratio=gap_ratio,
            relevant_count=relevant_count,
            warnings=["Score máximo abaixo do limiar de confiança."],
        )

    warnings: list[str] = []
    is_high_score = top_score >= HIGH_CONFIDENCE_THRESHOLD
    has_multiple = relevant_count >= MIN_SOURCES_HIGH
    has_clear_gap = gap_ratio >= SCORE_GAP_RATIO

    if is_high_score and has_multiple:
        level = "high"
    elif is_high_score or (has_multiple and has_clear_gap):
        level = "medium"
        if not has_multiple:
            warnings.append("Apenas uma fonte relevante encontrada.")
    else:
        level = "low"
        if not has_multiple:
            warnings.append("Apenas uma fonte relevante encontrada.")
        if not is_high_score:
            warnings.append(f"Score máximo relativamente baixo ({top_score:.1f}).")

    return ConfidenceAssessment(
        level=level,
        should_answer=True,
        top_score=top_score,
        score_gap_ratio=gap_ratio,
        relevant_count=relevant_count,
        warnings=warnings,
    )
