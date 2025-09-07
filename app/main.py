from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from .schemas import RecommendationRequest, RecommendationResponse, RecommendationItem
from .recommender import ShoeRecommender
from .llm import build_prompt, complete

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Running Shoe Recommendation Agent",
    description="AI-powered running shoe recommendations using Ollama",
    version="0.1.0"
)

# Initialize recommender (loads catalog once)
recommender = ShoeRecommender()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Running Shoe Recommendation Agent",
        "status": "healthy",
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.1")
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_shoes(request: RecommendationRequest) -> RecommendationResponse:
    """Get personalized running shoe recommendations"""
    try:
        # Step 1: Filter and score candidates
        candidates = recommender.filter_and_score(request)
        
        if not candidates:
            return RecommendationResponse(
                inputs_echo=request,
                shortlist=[],
                notes=["No shoes match your criteria. Try relaxing brand preferences or budget constraints."]
            )
        
        # Step 2: Get LLM explanations
        try:
            system_str, user_str = build_prompt(request.model_dump(), candidates)
            why_llm_list = complete(system_str, user_str)
        except Exception:
            why_llm_list = ["AI explanation unavailable - using rule-based reasoning"]
        
        # Step 3: Align explanations and build response
        while len(why_llm_list) < len(candidates):
            why_llm_list.append(why_llm_list[-1] if why_llm_list else "Good fit for your needs")
        why_llm_list = why_llm_list[:len(candidates)]
        
        # Step 4: Build initial shortlist with LLM quality scoring and ensure depth
        shortlist = []
        for i, candidate in enumerate(candidates):
            # Get LLM quality multiplier and adjust score
            enriched_why = recommender.ensure_explanation_depth(candidate, request, why_llm_list[i])
            quality_multiplier = recommender.incorporate_llm_quality_score(candidate, enriched_why)
            adjusted_score = min(1.0, candidate["score"] * quality_multiplier)
            
            shortlist.append(RecommendationItem(
                brand=candidate["brand"],
                model=candidate["model"],
                category=candidate["category"],
                price_usd=candidate["price_usd"],
                plate=candidate["plate"],
                drop_mm=candidate.get("drop_mm"),
                weight_g=candidate.get("weight_g"),
                why_rules=recommender.generate_why_rules(candidate, request),
                why_llm=enriched_why,
                score=adjusted_score
            ))
        
        # Step 5: Re-sort by adjusted scores (LLM quality now factored in)
        shortlist.sort(key=lambda x: x.score, reverse=True)
        
        # Generate notes
        notes = []
        above_budget_count = sum(1 for item in shortlist if item.price_usd > request.cost_limiter.max_usd)
        if above_budget_count > 0:
            notes.append(f"Note: {above_budget_count} recommendation(s) exceed your budget but may be worth considering for performance.")
        if len(shortlist) < 3:
            notes.append("Fewer recommendations than usual - consider relaxing some constraints.")
        
        # Add note about LLM quality scoring if applicable
        quality_variations = [item.score for item in shortlist]
        quality_range = max(quality_variations) - min(quality_variations)
        if quality_range > 0.05:
            notes.append("Scores have been adjusted based on AI explanation quality - more detailed explanations receive higher scores.")
        
        return RecommendationResponse(inputs_echo=request, shortlist=shortlist, notes=notes)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
