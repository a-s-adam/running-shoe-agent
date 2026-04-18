import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


class TestAPI:
    """Test the FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def sample_request(self):
        return {
            "brand_preferences": ["Saucony", "Adidas"],
            "intended_use": {
                "easy_runs": True,
                "tempo_runs": True,
                "races": ["half_marathon"],
                "trail": False
            },
            "cost_limiter": {
                "enabled": True,
                "max_usd": 180
            }
        }
    
    def test_root_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "ollama_host" in data
        assert "ollama_model" in data
    
    @patch('app.enhanced_recommender.complete_text')
    @patch('app.enhanced_ai_analyzer.complete_text')
    def test_recommend_endpoint_success(self, mock_llm_text, mock_rerank_text, client, sample_request):
        """Test successful recommendation generation"""
        mock_rerank_text.side_effect = Exception("skip LLM re-rank in unit test")
        mock_llm_text.return_value = (
            "Great for tempo runs and half marathons; matches your goals well."
        )
        
        response = client.post("/recommend", json=sample_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "shortlist" in data
        assert "inputs_echo" in data
        assert "notes" in data
        
        # Should return 3-5 recommendations
        shortlist = data["shortlist"]
        assert 3 <= len(shortlist) <= 5
        
        # Each item should have required fields
        for item in shortlist:
            assert "brand" in item
            assert "model" in item
            assert "why_rules" in item
            assert "why_llm" in item
            assert "score" in item
            assert 0 <= item["score"] <= 1
    
    @patch('app.enhanced_ai_analyzer.complete_text')
    @patch('app.enhanced_recommender.complete_text')
    def test_recommend_endpoint_llm_fallback(self, mock_rerank, mock_analyze, client, sample_request):
        """Test fallback when LLM is unavailable"""
        mock_analyze.side_effect = Exception("Ollama connection failed")
        mock_rerank.side_effect = Exception("Ollama connection failed")

        response = client.post("/recommend", json=sample_request)
        assert response.status_code == 200

        data = response.json()
        shortlist = data["shortlist"]

        assert len(shortlist) > 0
        for item in shortlist:
            assert "solid performance" in item["why_llm"].lower()
    
    def test_recommend_endpoint_validation(self, client):
        """Test input validation"""
        # Missing required fields
        invalid_request = {
            "intended_use": {
                "easy_runs": True
            }
            # Missing cost_limiter
        }
        
        response = client.post("/recommend", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_recommend_endpoint_budget_notes(self, client):
        """Test budget-related notes generation"""
        # Request with low budget to trigger above-budget notes
        low_budget_request = {
            "intended_use": {"races": ["5k"]},
            "cost_limiter": {"enabled": True, "max_usd": 150}
        }
        
        with patch('app.enhanced_recommender.complete_text') as mock_rerank, patch(
            'app.enhanced_ai_analyzer.complete_text'
        ) as mock_llm_text:
            mock_rerank.side_effect = Exception("skip LLM re-rank in unit test")
            mock_llm_text.return_value = "Good race shoe for 5K events."
            
            response = client.post("/recommend", json=low_budget_request)
            assert response.status_code == 200
            
            data = response.json()
            notes = data["notes"]
            
            # Should have budget-related notes if above-budget items exist
            above_budget_count = sum(1 for item in data["shortlist"] 
                                   if item["price_usd"] > 150)
            if above_budget_count > 0:
                assert any("exceed your budget" in note for note in notes)
    
    def test_recommend_endpoint_no_results(self, client):
        """Test handling of no matching results"""
        impossible_request = {
            "brand_preferences": ["__NonexistentBrand__"],
            "intended_use": {"easy_runs": True},
            "cost_limiter": {"enabled": True, "max_usd": 500},
        }
        
        response = client.post("/recommend", json=impossible_request)
        assert response.status_code == 200

        data = response.json()
        assert len(data["shortlist"]) == 0
        assert len(data["notes"]) > 0
        assert "No shoes match your criteria" in data["notes"][0]
    
    @patch('app.enhanced_recommender.complete_text')
    @patch('app.enhanced_ai_analyzer.complete_text')
    def test_llm_explanation_alignment(self, mock_llm_text, mock_rerank, client, sample_request):
        """Test that LLM explanations align with candidates"""
        mock_rerank.side_effect = Exception("skip LLM re-rank in unit test")
        mock_llm_text.return_value = "Good for tempo runs."
        
        response = client.post("/recommend", json=sample_request)
        assert response.status_code == 200
        
        data = response.json()
        shortlist = data["shortlist"]
        
        # Should have explanations for all candidates
        for item in shortlist:
            assert item["why_llm"] is not None
            assert len(item["why_llm"]) > 0
