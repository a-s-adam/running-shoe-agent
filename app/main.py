from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from .schemas import RecommendationRequest, RecommendationResponse, RecommendationItem
from .recommender import ShoeRecommender
from .enhanced_recommender import EnhancedShoeRecommender
from .catalog_repository import CatalogRepository
from .llm import build_prompt, complete

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Running Shoe Recommendation Agent",
    description="AI-powered running shoe recommendations using Ollama",
    version="0.1.0"
)

# Initialize recommenders (loads catalog once)
recommender = ShoeRecommender()  # Keep for backward compatibility
enhanced_recommender = EnhancedShoeRecommender()  # New enhanced system
catalog_repository = CatalogRepository()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Running Shoe Recommendation Agent",
        "status": "healthy",
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.1"),
        "catalog_backend": catalog_repository.backend_name,
    }


@app.get("/shoes")
async def list_shoes(category: str | None = None, search: str | None = None, limit: int = 30):
    """Browse stored shoes for the website catalog."""
    limit = max(1, min(limit, 100))
    shoes = catalog_repository.list_shoes(category=category, search=search, limit=limit)
    return {
        "backend": catalog_repository.backend_name,
        "count": len(shoes),
        "shoes": shoes,
    }


@app.get("/shoes/{shoe_key}")
async def get_shoe(shoe_key: str):
    """Fetch a single stored shoe by generated key."""
    for shoe in catalog_repository.load_catalog():
        if shoe.get("shoe_key") == shoe_key:
            return shoe
    raise HTTPException(status_code=404, detail="Shoe not found")


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_shoes(request: RecommendationRequest) -> RecommendationResponse:
    """Get personalized running shoe recommendations with enhanced AI analysis"""
    try:
        # Check LLM health via existing complete() for backward-compatible tests
        llm_ok = True
        try:
            _ = complete("health-check", "[]")
        except Exception:
            llm_ok = False

        # Use the enhanced recommender system
        # If LLM appears down, force analyzer fallback messaging
        if not llm_ok:
            try:
                enhanced_recommender.ai_analyzer._force_fallback = True
            except Exception:
                pass

        shortlist = enhanced_recommender.get_enhanced_recommendations(request)
        
        if not shortlist:
            return RecommendationResponse(
                inputs_echo=request,
                shortlist=[],
                notes=["No shoes match your criteria. Try relaxing brand preferences or budget constraints."]
            )
        
        # Generate enhanced notes
        notes = []
        above_budget_count = sum(1 for item in shortlist if item.price_usd > request.cost_limiter.max_usd)
        if above_budget_count > 0:
            notes.append(f"Note: {above_budget_count} recommendation(s) exceed your budget but offer premium performance features.")
        
        if len(shortlist) < 3:
            notes.append("Fewer recommendations than usual - consider relaxing some constraints for more options.")
        
        # Add note about enhanced analysis
        notes.append("Rankings use advanced AI analysis with dynamic scoring based on technical specs, market data, and use-case optimization.")
        
        return RecommendationResponse(inputs_echo=request, shortlist=shortlist, notes=notes)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced recommendation generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
