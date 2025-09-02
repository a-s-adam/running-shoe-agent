from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

    
class IntendedUse(BaseModel):
    """User's intended running activities"""
    easy_runs: bool = False
    tempo_runs: bool = False
    long_runs: bool = False
    races: List[str] = Field(default_factory=list)  # e.g., ["5k", "half_marathon"]
    trail: bool = False


class CostLimiter(BaseModel):
    """Budget constraints for recommendations"""
    enabled: bool = True
    max_usd: float = Field(gt=0, description="Maximum price in USD")


class RecommendationRequest(BaseModel):
    """Input for shoe recommendations"""
    brand_preferences: Optional[List[str]] = None
    intended_use: IntendedUse
    cost_limiter: CostLimiter
    num_recommendations: int = Field(default=5, ge=1, le=20, description="Number of recommendations to return (1-20)")


class RecommendationItem(BaseModel):
    """Individual shoe recommendation"""
    brand: str
    model: str
    category: List[str]
    price_usd: float
    plate: str
    drop_mm: Optional[float] = None
    weight_g: Optional[float] = None
    why_rules: str = Field(description="Why this shoe matches the rules")
    why_llm: str = Field(description="LLM-generated explanation")
    score: float = Field(ge=0, le=1, description="Recommendation score 0-1")


class RecommendationResponse(BaseModel):
    """API response with recommendations"""
    inputs_echo: RecommendationRequest
    shortlist: List[RecommendationItem]
    notes: List[str] = Field(default_factory=list)
