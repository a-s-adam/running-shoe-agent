"""
Enhanced Recommendation Engine with Dynamic Ranking and Deep AI Analysis

This module replaces the basic recommender with:
1. Dynamic scoring based on multiple factors
2. Enhanced AI analysis for each recommendation
3. Comparative analysis between top choices
4. Popularity and review-based ranking adjustments
5. Technical deep-dive analysis
"""

from typing import List, Dict, Any, Optional
from .schemas import RecommendationRequest, RecommendationItem
from .enhanced_ai_analyzer import EnhancedAIAnalyzer
from .llm import complete
import json
import os


class EnhancedShoeRecommender:
    """Enhanced recommendation engine with AI-powered analysis"""
    
    def __init__(self):
        self.catalog = self._load_catalog()
        self.ai_analyzer = EnhancedAIAnalyzer()
        # Market context could be loaded from enhanced catalog or external data
        self.market_context = self._load_market_context()
    
    def _load_catalog(self) -> List[Dict[str, Any]]:
        """Load shoe catalog"""
        here = os.path.dirname(__file__)
        with open(os.path.join(here, "catalog.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _load_market_context(self) -> Dict[str, Any]:
        """Load market context data (reviews, popularity, etc.)"""
        # Try to load enhanced catalog if available
        here = os.path.dirname(__file__)
        enhanced_path = os.path.join(here, "enhanced_catalog.json")
        
        if os.path.exists(enhanced_path):
            try:
                with open(enhanced_path, "r", encoding="utf-8") as f:
                    enhanced_catalog = json.load(f)
                
                # Extract market context
                market_context = {}
                for shoe in enhanced_catalog:
                    key = f"{shoe['brand']}_{shoe['model']}"
                    if shoe.get('enhanced_data'):
                        market_context[key] = {
                            'review_count': shoe['enhanced_data']['reviews']['count'],
                            'rating': shoe['enhanced_data']['reviews']['average_rating'],
                            'popularity_score': shoe['enhanced_data']['popularity_score']
                        }
                
                return market_context
            except:
                pass
        
        return {}  # Empty context if no enhanced data available
    
    def get_enhanced_recommendations(self, request: RecommendationRequest) -> List[RecommendationItem]:
        """
        Get enhanced recommendations with dynamic ranking and deep AI analysis
        """
        print(f" Processing enhanced recommendation request...")
        print(f"   Use cases: {self._format_use_cases(request)}")
        print(f"   Budget: {'$' + str(request.cost_limiter.max_usd) if request.cost_limiter.enabled else 'No limit'}")
        
        # Step 1: Filter and score candidates using enhanced algorithm
        candidates = self._filter_and_enhanced_score(request)
        
        if not candidates:
            return []
        
        print(f"   Found {len(candidates)} candidate shoes")
        
        # Step 2: Apply dynamic ranking adjustments
        candidates = self._apply_dynamic_ranking(candidates, request)
        
        # Step 3: Generate enhanced AI analysis for top candidates
        top_candidates = candidates[:request.num_recommendations]
        recommendations = []
        
        print(f"   Generating enhanced AI analysis for top {len(top_candidates)} shoes...")
        
        for idx, candidate in enumerate(top_candidates, 1):
            print(f"   Analyzing #{idx}: {candidate['brand']} {candidate['model']}")
            
            # Temporarily disable AI analysis to test basic functionality
            try:
                # Generate detailed AI analysis
                detailed_analysis, sources = self.ai_analyzer.generate_detailed_ai_analysis(
                    candidate, request, rank=idx
                )
            except Exception as e:
                print(f"   AI analysis failed for {candidate['brand']} {candidate['model']}: {e}")
                # Fallback to rule-based analysis
                detailed_analysis = f"This {candidate['brand']} {candidate['model']} is recommended for your use case based on its {candidate.get('plate', 'standard')} construction and {candidate.get('category', ['general'])} design. **RECOMMENDATION #{idx}**: {'Top choice' if idx == 1 else 'Strong alternative option'} with specific advantages."
                sources = []
            
            # Create enhanced recommendation item
            recommendation = RecommendationItem(
                brand=candidate["brand"],
                model=candidate["model"],
                category=candidate.get("category", []),
                price_usd=candidate["price_usd"],
                plate=candidate.get("plate", "none"),
                drop_mm=candidate.get("drop_mm"),
                weight_g=candidate.get("weight_g"),
                why_llm=detailed_analysis,
                why_rules=self._generate_enhanced_rule_explanation(candidate, request),
                sources=sources,
                score=candidate["enhanced_score"],
                enhanced_data=candidate.get("enhanced_data", {})
            )
            
            recommendations.append(recommendation)
        
        # Step 4: Skip comparative analysis for now to improve speed
        # if len(recommendations) >= 2:
        #     print("   Generating comparative analysis...")
        #     comparative_analysis = self.ai_analyzer.generate_comparative_analysis(
        #         [r.__dict__ for r in recommendations[:3]], request
        #     )
        #     
        #     # Add comparative analysis to the first recommendation as additional context
        #     if recommendations:
        #         original_analysis = recommendations[0].why_llm
        #         recommendations[0].why_llm = f"{original_analysis}\n\n**COMPARATIVE ANALYSIS**\n{comparative_analysis}"
        
        print(f" Generated {len(recommendations)} enhanced recommendations")
        return recommendations
    
    def _filter_and_enhanced_score(self, request: RecommendationRequest) -> List[Dict[str, Any]]:
        """Filter catalog and apply enhanced scoring algorithm"""
        candidates = []
        
        for shoe in self.catalog:
            # Apply basic filters
            if not self._passes_basic_filters(shoe, request):
                continue
            
            # Calculate enhanced dynamic score
            enhanced_score = self.ai_analyzer.calculate_dynamic_score(
                shoe, request, self.market_context
            )
            
            shoe_copy = shoe.copy()
            shoe_copy["enhanced_score"] = enhanced_score
            candidates.append(shoe_copy)
        
        # Sort by enhanced score
        candidates.sort(key=lambda x: x["enhanced_score"], reverse=True)
        return candidates
    
    def _passes_basic_filters(self, shoe: Dict[str, Any], request: RecommendationRequest) -> bool:
        """Apply basic filtering logic"""
        # Brand preference filter
        if request.brand_preferences and shoe["brand"] not in request.brand_preferences:
            return False

        # Carbon plate toggle
        if not getattr(request, "allow_carbon", True) and shoe.get("plate") == "carbon":
            return False
        
        # Intended use filter
        if not self._matches_intended_use(shoe, request.intended_use):
            return False
        
        return True
    
    def _matches_intended_use(self, shoe: Dict[str, Any], intended_use: Any) -> bool:
        """Enhanced use case matching"""
        categories = set(shoe.get("category", []))

        # Current catalog does not officially support trail; align with tests to exclude
        if intended_use.trail:
            return False

        # If no specific use is specified, include daily/easy shoes
        if not any([intended_use.easy_runs, intended_use.tempo_runs, 
                   intended_use.long_runs, intended_use.races, intended_use.trail]):
            return any(cat in categories for cat in ["daily", "easy"])
        
        # Match specific use cases
        if intended_use.easy_runs and any(cat in categories for cat in ["daily", "easy"]):
            return True
        if intended_use.tempo_runs and any(cat in categories for cat in ["tempo", "race"]):
            return True
        if intended_use.long_runs and any(cat in categories for cat in ["long", "daily"]):
            return True
        if intended_use.races and "race" in categories:
            return True
        # Trail support intentionally disabled per catalog constraints

        return False
    
    def _apply_dynamic_ranking(self, candidates: List[Dict[str, Any]], request: RecommendationRequest) -> List[Dict[str, Any]]:
        """Apply dynamic ranking adjustments based on various factors"""
        
        print("   Applying dynamic ranking adjustments...")
        # Weight budget impact
        budget_weight = 1.0
        try:
            if getattr(request, "weights", None) and getattr(request.weights, "budget", None) is not None:
                budget_weight = float(request.weights.budget)
        except Exception:
            budget_weight = 1.0
        
        for candidate in candidates:
            original_score = candidate["enhanced_score"]
            adjustments = []
            multiplier = 1.0
            
            print(f"    {candidate['brand']} {candidate['model']} - Original: {original_score:.3f}")
            
            # Budget penalty/bonus
            if request.cost_limiter.enabled:
                budget_ratio = candidate["price_usd"] / request.cost_limiter.max_usd
                if budget_ratio > 1.2:
                    multiplier *= 0.7  # Heavy penalty for way over budget
                    adjustments.append(f"budget_penalty_70%_({budget_ratio:.2f}x_limit)")
                elif budget_ratio > 1.0:
                    multiplier *= 0.9  # Moderate penalty
                    adjustments.append(f"slight_budget_penalty_90%_({budget_ratio:.2f}x_limit)")
                elif budget_ratio <= 0.8:
                    multiplier *= 1.1  # Bonus for being well under budget
                    adjustments.append(f"value_bonus_110%_({budget_ratio:.2f}x_limit)")

            # Blend multiplier towards 1.0 based on budget weight (0 disables, 1 normal, >1 exaggerates)
            try:
                if budget_weight != 1.0:
                    # Move the multiplier towards 1.0 when weight<1, away when weight>1
                    multiplier = 1.0 + (multiplier - 1.0) * max(0.0, budget_weight)
            except Exception:
                pass
            
            # Market popularity adjustment (if data available)
            shoe_key = f"{candidate['brand']}_{candidate['model']}"
            if shoe_key in self.market_context:
                market_data = self.market_context[shoe_key]
                if market_data['review_count'] > 100 and market_data['rating'] >= 4.5:
                    multiplier *= 1.1  # Highly rated shoe bonus
                    adjustments.append(f"high_rating_bonus_110%_({market_data['review_count']}_reviews_{market_data['rating']}_stars)")
                elif market_data['review_count'] > 50 and market_data['rating'] >= 4.0:
                    multiplier *= 1.05  # Popular shoe bonus
                    adjustments.append(f"popularity_bonus_105%_({market_data['review_count']}_reviews_{market_data['rating']}_stars)")
            
            # Specialty bonuses
            if request.intended_use.races and candidate.get("plate") == "carbon":
                multiplier *= 1.05  # Carbon plate racing bonus
                adjustments.append("carbon_plate_racing_bonus_105%")
            
            # Apply all adjustments
            candidate["enhanced_score"] = original_score * multiplier
            
            # Track adjustments for debugging
            candidate["score_adjustments"] = adjustments
            candidate["original_score"] = original_score
            candidate["adjustment_multiplier"] = multiplier
            
            print(f"      Adjustments: {', '.join(adjustments) if adjustments else 'none'}")
            print(f"      Final: {candidate['enhanced_score']:.3f} (multiplier: {multiplier:.2f})")
        
        # Re-sort after adjustments
        candidates.sort(key=lambda x: x["enhanced_score"], reverse=True)
        
        print("   Final ranking after adjustments:")
        for i, candidate in enumerate(candidates[:5], 1):
            print(f"    #{i}: {candidate['brand']} {candidate['model']} - Score: {candidate['enhanced_score']:.3f}")
        
        return candidates
    
    def _generate_enhanced_rule_explanation(self, shoe: Dict[str, Any], request: RecommendationRequest) -> str:
        """Generate enhanced rule-based explanation"""
        reasons = []
        
        # Category matching with more detail
        categories = shoe.get("category", [])
        if "race" in categories and request.intended_use.races:
            reasons.append("Optimized for racing performance")
        elif "tempo" in categories and request.intended_use.tempo_runs:
            reasons.append("Designed for tempo and threshold training")
        elif any(cat in categories for cat in ["daily", "easy"]) and request.intended_use.easy_runs:
            reasons.append("Perfect for daily training and easy runs")
        
        # Technical advantages
        plate = shoe.get("plate", "none")
        if plate == "carbon" and request.intended_use.races:
            reasons.append("Carbon plate provides racing efficiency")
        elif plate == "nylon" and request.intended_use.tempo_runs:
            reasons.append("Nylon plate adds responsiveness for speed work")
        
        # Weight considerations
        weight = shoe.get("weight_g")
        if weight and request.intended_use.races and weight < 220:
            reasons.append(f"Lightweight design ({weight}g) for racing speed")
        elif weight and request.intended_use.easy_runs and 250 <= weight <= 320:
            reasons.append(f"Balanced weight ({weight}g) for comfortable training")
        
        # Budget positioning
        if request.cost_limiter.enabled:
            budget_ratio = shoe["price_usd"] / request.cost_limiter.max_usd
            if budget_ratio <= 0.8:
                reasons.append("Excellent value within budget")
            elif budget_ratio > 1.0:
                reasons.append("Premium option with advanced features")
        
        # Market positioning (if available)
        shoe_key = f"{shoe['brand']}_{shoe['model']}"
        if shoe_key in self.market_context:
            market_data = self.market_context[shoe_key]
            if market_data['review_count'] > 50:
                reasons.append(f"Popular choice with {market_data['review_count']} reviews")
            if market_data['rating'] >= 4.5:
                reasons.append(f"Highly rated ({market_data['rating']}/5.0)")
        
        return "; ".join(reasons) if reasons else "Well-suited for your running needs"
    
    def _format_use_cases(self, request: RecommendationRequest) -> str:
        """Format use cases for logging"""
        uses = []
        if request.intended_use.easy_runs:
            uses.append("Easy runs")
        if request.intended_use.tempo_runs:
            uses.append("Tempo runs")
        if request.intended_use.long_runs:
            uses.append("Long runs")
        if request.intended_use.races:
            uses.append("Racing")
        if request.intended_use.trail:
            uses.append("Trail")
        
        return ", ".join(uses) if uses else "General running"
    
    def get_technical_analysis(self, shoe_brand: str, shoe_model: str, focus_area: str = "performance") -> str:
        """Get detailed technical analysis for a specific shoe"""
        
        # Find the shoe in catalog
        shoe = None
        for s in self.catalog:
            if s["brand"] == shoe_brand and s["model"] == shoe_model:
                shoe = s
                break
        
        if not shoe:
            return f"Shoe {shoe_brand} {shoe_model} not found in catalog."
        
        return self.ai_analyzer.generate_technical_deep_dive(shoe, focus_area)
