import pytest
from app.recommender import ShoeRecommender
from app.schemas import RecommendationRequest, IntendedUse, CostLimiter


class TestShoeRecommender:
    """Test the core recommendation engine"""
    
    @pytest.fixture
    def recommender(self):
        return ShoeRecommender()
    
    @pytest.fixture
    def basic_request(self):
        return RecommendationRequest(
            intended_use=IntendedUse(easy_runs=True),
            cost_limiter=CostLimiter(enabled=True, max_usd=150)
        )
    
    def test_load_catalog(self, recommender):
        """Test that catalog loads successfully"""
        assert len(recommender.catalog) > 0
        assert all("brand" in shoe for shoe in recommender.catalog)
        assert all("model" in shoe for shoe in recommender.catalog)
    
    def test_brand_filtering(self, recommender, basic_request):
        """Test brand preference filtering"""
        # Test with brand preferences
        request = RecommendationRequest(
            intended_use=IntendedUse(easy_runs=True),
            cost_limiter=CostLimiter(enabled=True, max_usd=200),
            brand_preferences=["Saucony", "Adidas"]
        )
        
        candidates = recommender.filter_and_score(request)
        assert all(shoe["brand"] in ["Saucony", "Adidas"] for shoe in candidates)
    
    def test_budget_filtering(self, recommender):
        """Test budget constraint filtering"""
        request = RecommendationRequest(
            intended_use=IntendedUse(easy_runs=True),
            cost_limiter=CostLimiter(enabled=True, max_usd=140)
        )
        
        candidates = recommender.filter_and_score(request)
        # Should allow up to 2 above-budget options
        above_budget = [s for s in candidates if s["price_usd"] > 140]
        assert len(above_budget) <= 2
    
    def test_intended_use_filtering(self, recommender):
        """Test intended use filtering"""
        # Test race shoes
        race_request = RecommendationRequest(
            intended_use=IntendedUse(races=["5k"]),
            cost_limiter=CostLimiter(enabled=True, max_usd=250)
        )
        
        race_candidates = recommender.filter_and_score(race_request)
        assert all("race" in shoe["category"] for shoe in race_candidates)
        
        # Test daily/easy shoes
        daily_request = RecommendationRequest(
            intended_use=IntendedUse(easy_runs=True),
            cost_limiter=CostLimiter(enabled=True, max_usd=200)
        )
        
        daily_candidates = recommender.filter_and_score(daily_request)
        assert any("daily" in shoe["category"] or "easy" in shoe["category"] 
                  for shoe in daily_candidates)
    
    def test_scoring(self, recommender):
        """Test that scoring produces reasonable results"""
        request = RecommendationRequest(
            intended_use=IntendedUse(races=["marathon"]),
            cost_limiter=CostLimiter(enabled=True, max_usd=200)
        )
        
        candidates = recommender.filter_and_score(request)
        
        # Should have scores between 0 and 1
        assert all(0 <= shoe["score"] <= 1 for shoe in candidates)
        
        # Should be sorted by score (highest first)
        scores = [shoe["score"] for shoe in candidates]
        assert scores == sorted(scores, reverse=True)
    
    def test_why_rules_generation(self, recommender):
        """Test rule-based explanation generation"""
        request = RecommendationRequest(
            intended_use=IntendedUse(races=["5k"]),
            cost_limiter=CostLimiter(enabled=True, max_usd=200)
        )
        
        # Get a race shoe
        candidates = recommender.filter_and_score(request)
        race_shoe = next((s for s in candidates if "race" in s["category"]), None)
        
        if race_shoe:
            why_rules = recommender.generate_why_rules(race_shoe, request)
            assert "race" in why_rules.lower() or "speed" in why_rules.lower()
    
    def test_empty_results(self, recommender):
        """Test handling of no matching results"""
        # Impossible request
        request = RecommendationRequest(
            intended_use=IntendedUse(trail=True),  # No trail shoes in catalog
            cost_limiter=CostLimiter(enabled=True, max_usd=50)
        )
        
        candidates = recommender.filter_and_score(request)
        assert len(candidates) == 0
