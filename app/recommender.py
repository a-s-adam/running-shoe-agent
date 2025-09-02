from __future__ import annotations
import json
import os
from typing import List, Dict, Any
from .schemas import RecommendationRequest, RecommendationItem


class ShoeRecommender:
    """Core recommendation engine with filtering and scoring"""
    
    def __init__(self):
        self.catalog = self._load_catalog()
    
    def _load_catalog(self) -> List[Dict[str, Any]]:
        """Load shoe catalog once at startup"""
        here = os.path.dirname(__file__)
        with open(os.path.join(here, "catalog.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def filter_and_score(self, request: RecommendationRequest) -> List[Dict[str, Any]]:
        """Filter catalog by constraints and score candidates"""
        candidates = []
        
        for shoe in self.catalog:
            # Brand preference filter
            if request.brand_preferences and shoe["brand"] not in request.brand_preferences:
                continue
            
            # Intended use filter
            if not self._matches_intended_use(shoe, request.intended_use):
                continue
            
            # Budget filter (allow max 2 above-budget)
            if request.cost_limiter.enabled and shoe["price_usd"] > request.cost_limiter.max_usd:
                if len([c for c in candidates if c["price_usd"] > request.cost_limiter.max_usd]) >= 2:
                    continue
            
            # Calculate score and add candidate
            shoe_copy = shoe.copy()
            shoe_copy["score"] = self._calculate_score(shoe, request)
            candidates.append(shoe_copy)
        
        # Sort by score (highest first) and return requested number
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:request.num_recommendations]
    
    def _matches_intended_use(self, shoe: Dict[str, Any], intended_use: Any) -> bool:
        """Check if shoe matches user's intended activities"""
        categories = set(shoe.get("category", []))
        
        # Easy runs - any daily/easy shoe
        if intended_use.easy_runs and any(cat in categories for cat in ["daily", "easy"]):
            return True
        
        # Tempo runs - tempo or race shoes
        if intended_use.tempo_runs and any(cat in categories for cat in ["tempo", "race"]):
            return True
        
        # Long runs - long or daily shoes
        if intended_use.long_runs and any(cat in categories for cat in ["long", "daily"]):
            return True
        
        # Races - race shoes only
        if intended_use.races and "race" in categories:
            return True
        
        # Trail - would need trail category (not in current catalog)
        if intended_use.trail and "trail" in categories:
            return True
        
        # If no specific use specified, include daily/easy shoes
        if not any([intended_use.easy_runs, intended_use.tempo_runs, 
                   intended_use.long_runs, intended_use.races, intended_use.trail]):
            return any(cat in categories for cat in ["daily", "easy"])
        
        return False
    
    def _calculate_score(self, shoe: Dict[str, Any], request: RecommendationRequest) -> float:
        """Calculate recommendation score 0-1 based on simple weights"""
        score = 0.5  # Base score
        
        # Race preference bonus
        if request.intended_use.races and "race" in shoe.get("category", []):
            score += 0.3
        
        # Plate preference for races
        if request.intended_use.races and shoe.get("plate") != "none":
            score += 0.2
        
        # Budget penalty
        if request.cost_limiter.enabled:
            budget_ratio = shoe["price_usd"] / request.cost_limiter.max_usd
            if budget_ratio > 1.0:
                score -= 0.3 * (budget_ratio - 1.0)
        
        # Weight preference (lighter = better for races)
        if request.intended_use.races and shoe.get("weight_g"):
            if shoe["weight_g"] < 200:
                score += 0.1
            elif shoe["weight_g"] < 220:
                score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def generate_why_rules(self, shoe: Dict[str, Any], request: RecommendationRequest) -> str:
        """Generate rule-based explanation for why shoe was selected"""
        reasons = []
        
        # Category match
        categories = shoe.get("category", [])
        if "race" in categories and request.intended_use.races:
            reasons.append("Race-focused design")
        elif "tempo" in categories and request.intended_use.tempo_runs:
            reasons.append("Tempo run optimized")
        elif any(cat in categories for cat in ["daily", "easy"]) and request.intended_use.easy_runs:
            reasons.append("Daily training suitable")
        
        # Plate technology
        if shoe.get("plate") == "carbon" and request.intended_use.races:
            reasons.append("Carbon plate for speed")
        elif shoe.get("plate") == "nylon" and request.intended_use.tempo_runs:
            reasons.append("Nylon plate for tempo")
        
        # Budget note
        if request.cost_limiter.enabled and shoe["price_usd"] > request.cost_limiter.max_usd:
            reasons.append("Above budget but high-performance")
        
        return "; ".join(reasons) if reasons else "Matches your criteria"

    def incorporate_llm_quality_score(self, shoe: Dict[str, Any], why_llm: str) -> float:
        """
        Analyze LLM output quality and adjust the score accordingly.
        Returns a quality multiplier (0.8 to 1.2) based on explanation quality.
        """
        if not why_llm or why_llm.strip() == "":
            return 0.8  # Penalty for empty explanations
        
        # Check for generic/fallback responses
        generic_phrases = [
            "solid fit for the stated use",
            "consider feel and budget tradeoffs",
            "good fit for your needs",
            "ai explanation unavailable"
        ]
        
        if any(phrase.lower() in why_llm.lower() for phrase in generic_phrases):
            return 0.9  # Small penalty for generic responses
        
        # Check for detailed, specific explanations
        detailed_indicators = [
            "carbon plate",
            "nylon plate",
            "drop",
            "weight",
            "cushioning",
            "responsive",
            "stable",
            "lightweight",
            "durable"
        ]
        
        detailed_count = sum(1 for indicator in detailed_indicators if indicator.lower() in why_llm.lower())
        
        if detailed_count >= 3:
            return 1.2  # Bonus for detailed explanations
        elif detailed_count >= 2:
            return 1.1  # Small bonus for moderately detailed explanations
        elif detailed_count >= 1:
            return 1.0  # No change for basic explanations
        
        return 0.95  # Small penalty for very basic explanations
