import pytest

from app.enhanced_recommender import EnhancedShoeRecommender
from app.schemas import RecommendationRequest, IntendedUse, CostLimiter


def test_llm_explanations_are_not_identical(monkeypatch):
    """
    Ensure LLM explanations vary across recommendations.
    We monkeypatch the underlying analyzer completion to a constant string
    and verify the final messages differ due to ranking/context shaping.
    """

    rec = EnhancedShoeRecommender()

    # Force the analyzer to return the same base sentence every time
    from app.enhanced_ai_analyzer import EnhancedAIAnalyzer

    def fake_get_completion(self, prompt: str, timeout: int = 12) -> str:
        return "This shoe is a great option for your needs."

    monkeypatch.setattr(EnhancedAIAnalyzer, "_get_completion", fake_get_completion, raising=True)

    request = RecommendationRequest(
        intended_use=IntendedUse(easy_runs=True, tempo_runs=True),
        cost_limiter=CostLimiter(enabled=True, max_usd=200),
        num_recommendations=3,
    )

    shortlist = rec.get_enhanced_recommendations(request)

    assert len(shortlist) >= 2
    texts = [item.why_llm for item in shortlist]

    # At least two explanations should differ due to appended ranking/context
    assert len(set(texts)) > 1

