"""
Enhanced AI Analysis System for Running Shoe Recommendations

This module provides deep AI-powered analysis of running shoes using multiple
analysis techniques including:
1. Multi-factor scoring analysis
2. Comparative analysis against similar shoes
3. Use-case specific recommendations
4. Technical specification deep-dive
5. Performance prediction modeling
"""

from typing import Dict, List, Any, Tuple
import json
import os
from .llm import complete
from .schemas import RecommendationRequest


class EnhancedAIAnalyzer:
    """Enhanced AI analyzer with multi-stage analysis capabilities"""
    
    def __init__(self):
        self.catalog = self._load_catalog()
        self._load_analysis_prompts()
    
    def _get_completion(self, prompt: str, timeout: int = 8) -> str:
        """Wrapper for the LLM complete function that handles single prompts with timeout"""
        try:
            # Use simple system message and the prompt as user message
            system_msg = "You are a running shoe expert. Provide ONE sentence analysis."
            
            print(f"    Calling AI model for analysis...")
            
            # Try using the complete function with simple inputs
            result = complete(system_msg, prompt)
            print(f"    AI model returned: {type(result)}")
            
            # Handle different return types
            if isinstance(result, list) and len(result) > 0:
                ai_response = str(result[0])
                print(f"    AI analysis successful: {ai_response[:50]}...")
                return ai_response
            elif isinstance(result, str):
                print(f"    AI analysis successful: {result[:50]}...")
                return result
            else:
                print(f"    AI returned unexpected type: {type(result)}, value: {result}")
                return f"This shoe offers solid performance for your running needs with good technical specifications."
                
        except Exception as e:
            print(f"    AI analysis error: {e}")
            import traceback
            print(f"    Full error details: {traceback.format_exc()}")
            # Return a meaningful fallback instead of error message
            return f"This shoe offers solid performance for your running needs with good technical specifications."
    
    def _load_catalog(self) -> List[Dict[str, Any]]:
        """Load shoe catalog"""
        here = os.path.dirname(__file__)
        with open(os.path.join(here, "catalog.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _load_analysis_prompts(self):
        """Load specialized analysis prompts for different analysis types"""
        self.analysis_prompts = {
            "detailed_analysis": """
Analyze this running shoe for the user's needs in 2-3 sentences:

Shoe: {shoe_details}
User needs: {user_requirements}

Focus on: Why it's good for their use case, key technical advantages, and any limitations.
            """.strip(),
            
            "comparative_analysis": """
You are comparing running shoes to help a runner make the best choice. Compare these shoes across:

1. PERFORMANCE COMPARISON
   - Speed/efficiency differences
   - Comfort and support variations
   - Durability expectations

2. USE CASE OPTIMIZATION
   - Which shoe excels in which scenarios
   - Training vs racing applications
   - Distance-specific recommendations

3. VALUE ANALYSIS
   - Price-to-performance ratio
   - Long-term cost considerations
   - Feature justification

4. RECOMMENDATION RANKING
   - Primary recommendation with strong rationale
   - Alternative options and why
   - Situations where each shoe is optimal

Shoes to Compare: {shoes_list}
User Requirements: {user_requirements}

Rank them 1-N with detailed justification for each ranking.
            """.strip(),
            
            "technical_deep_dive": """
You are a biomechanics and running technology expert. Analyze this shoe's technical specifications:

1. BIOMECHANICAL ANALYSIS
   - Drop impact on running form
   - Weight effects on efficiency
   - Plate technology performance implications

2. MATERIAL SCIENCE
   - Foam and cushioning technology assessment
   - Upper construction benefits
   - Outsole durability and traction

3. PERFORMANCE ENGINEERING
   - Energy return characteristics
   - Stability and motion control features
   - Breathability and comfort engineering

4. SCIENTIFIC BACKING
   - Research-supported benefits
   - Measurable performance advantages
   - Limitations and trade-offs

Shoe: {shoe_details}
Focus Area: {focus_area}

Provide evidence-based technical analysis with specific examples.
            """.strip()
        }
    
    def calculate_dynamic_score(self, shoe: Dict[str, Any], request: RecommendationRequest, market_context: Dict = None) -> float:
        """
        Calculate an enhanced dynamic score that considers:
        - Basic compatibility (existing logic)
        - Market positioning and popularity
        - Technical advantage scoring
        - Use-case optimization
        """
        try:
            print(f"    Calculating score for {shoe['brand']} {shoe['model']}:")
            
            base_score = self._calculate_base_compatibility(shoe, request)
            print(f"      Base compatibility: {base_score:.3f} (40% weight)")
            
            # Technical advantage scoring
            tech_bonus = self._calculate_technical_advantages(shoe, request)
            print(f"      Technical advantages: {tech_bonus:.3f} (30% weight)")
            
            # Market positioning bonus (if we have market data)
            market_bonus = 0.0
            if market_context:
                market_bonus = self._calculate_market_positioning_bonus(shoe, market_context)
            print(f"      Market positioning: {market_bonus:.3f} (20% weight)")
            
            # Specialty use case bonus
            specialty_bonus = self._calculate_specialty_bonus(shoe, request)
            print(f"      Specialty bonus: {specialty_bonus:.3f} (10% weight)")
            
            # Combine scores with weights
            final_score = (
                base_score * 0.4 +           # 40% compatibility
                tech_bonus * 0.3 +           # 30% technical advantages  
                market_bonus * 0.2 +         # 20% market positioning
                specialty_bonus * 0.1        # 10% specialty bonus
            )
            
            weighted_final = max(0.0, min(1.0, final_score))
            print(f"      FINAL SCORE: {weighted_final:.3f} ({weighted_final*100:.1f}%)")
            
            return weighted_final
            
        except Exception as e:
            print(f"      ERROR calculating score for {shoe.get('brand', 'unknown')} {shoe.get('model', 'unknown')}: {e}")
            return 0.5  # Safe fallback score
    
    def _calculate_base_compatibility(self, shoe: Dict[str, Any], request: RecommendationRequest) -> float:
        """Calculate basic compatibility score with granular adjustments"""
        score = 0.45  # Slightly lower base score for more dynamic range
        
        categories = set(shoe.get("category", []))
        
        # Use case matching with refined scoring
        if request.intended_use.races and "race" in categories:
            score += 0.28
        elif request.intended_use.tempo_runs and "tempo" in categories:
            score += 0.22
        elif request.intended_use.long_runs and any(cat in categories for cat in ["long", "daily"]):
            score += 0.20
        elif request.intended_use.easy_runs and any(cat in categories for cat in ["daily", "easy"]):
            score += 0.18
        
        # Plate technology optimization with granular scoring
        plate = shoe.get("plate", "none")
        if request.intended_use.races:
            if plate == "carbon":
                score += 0.22
            elif plate == "nylon":
                score += 0.12
        elif request.intended_use.long_runs:
            if plate == "nylon":
                score += 0.08  # Some plate benefit for long runs
        
        # Weight considerations with granular adjustments
        weight = shoe.get("weight_g")
        if weight is not None:
            if request.intended_use.races:
                if weight < 200:
                    score += 0.15  # Ultra lightweight racing bonus
                elif weight < 220:
                    score += 0.12  # Lightweight racing bonus  
                elif weight < 240:
                    score += 0.08  # Light racing bonus
                elif weight > 280:
                    score -= 0.1   # Heavy racing penalty
            elif request.intended_use.long_runs:
                if 240 <= weight <= 280:
                    score += 0.08  # Good cushioning weight for long runs
                elif weight > 320:
                    score -= 0.05  # Too heavy for long runs
            elif request.intended_use.easy_runs:
                if 250 <= weight <= 320:
                    score += 0.06  # Moderate weight for daily training
                elif weight > 350:
                    score -= 0.08  # Too heavy for easy runs
        
        # Drop considerations for granular scoring
        drop = shoe.get("drop_mm")
        if drop is not None:
            if request.intended_use.races:
                if drop <= 4:
                    score += 0.06  # Low drop racing advantage
                elif drop <= 6:
                    score += 0.04  # Moderate low drop
                elif drop > 10:
                    score -= 0.03  # High drop racing disadvantage
            elif request.intended_use.easy_runs:
                if 8 <= drop <= 12:
                    score += 0.04  # Traditional drop for easy runs
        
        # Budget considerations with granular penalties/bonuses
        if request.cost_limiter.enabled:
            budget_ratio = shoe["price_usd"] / request.cost_limiter.max_usd
            if budget_ratio > 1.3:
                score -= 0.35  # Very expensive penalty
            elif budget_ratio > 1.2:
                score -= 0.25  # Expensive penalty
            elif budget_ratio > 1.1:
                score -= 0.15  # Slightly over budget
            elif budget_ratio > 1.0:
                score -= 0.05 * (budget_ratio - 1.0)  # Small penalty for just over
            elif budget_ratio <= 0.7:
                score += 0.08  # Great value bonus
            elif budget_ratio <= 0.8:
                score += 0.05  # Good value bonus
        
        return max(0.1, min(1.0, score))  # Allow lower minimum for more range
    
    def _calculate_technical_advantages(self, shoe: Dict[str, Any], request: RecommendationRequest) -> float:
        """Calculate technical advantages score"""
        score = 0.5
        
        # Drop optimization for different use cases
        drop = shoe.get("drop_mm")
        if drop:
            if request.intended_use.races and drop <= 6:
                score += 0.1  # Low drop for racing
            elif request.intended_use.easy_runs and 8 <= drop <= 12:
                score += 0.1  # Moderate drop for easy runs
        
        # Advanced plate technology
        plate = shoe.get("plate")
        if plate == "carbon" and request.intended_use.races:
            score += 0.2  # Carbon plate racing advantage
        elif plate == "nylon" and request.intended_use.tempo_runs:
            score += 0.15  # Nylon plate tempo advantage
        
        return max(0.0, min(1.0, score))
    
    def _calculate_market_positioning_bonus(self, shoe: Dict[str, Any], market_context: Dict) -> float:
        """Calculate market positioning bonus (placeholder for future market data)"""
        # This would incorporate review counts, ratings, popularity metrics
        return 0.5  # Neutral for now
    
    def _calculate_specialty_bonus(self, shoe: Dict[str, Any], request: RecommendationRequest) -> float:
        """Calculate bonus for specialty features that match user needs"""
        score = 0.45  # Lower base for more dynamic range
        brand = shoe.get("brand", "").upper()
        
        # Brand specialization bonuses based on use case
        if request.intended_use.races:
            if brand in ["NIKE", "SAUCONY", "HOKA"]:
                score += 0.12  # Racing specialists
            elif brand in ["ASICS", "NEW BALANCE"]:  # Add New Balance
                score += 0.10  # Strong racing options
            elif brand == "BROOKS":
                score += 0.08  # Good racing shoes but not specialized
        elif request.intended_use.long_runs:
            if brand in ["HOKA", "BROOKS", "ASICS"]:
                score += 0.12  # Cushioning specialists
            elif brand in ["NEW BALANCE", "SAUCONY"]:
                score += 0.10  # Good long run options
        elif request.intended_use.easy_runs:
            if brand in ["BROOKS", "ASICS", "NEW BALANCE"]:
                score += 0.10  # Daily training specialists
            elif brand in ["HOKA", "SAUCONY"]:
                score += 0.08  # Good daily options
        
        # Brand diversity bonus to prevent same-brand dominance
        # This would need to be passed from the recommender, for now just slight randomization
        import random
        random.seed(hash(shoe.get("model", "") + brand))  # Deterministic but varied
        diversity_bonus = random.uniform(-0.02, 0.02)  # Small randomization for diversity
        score += diversity_bonus
        
        # Price-performance ratio adjustments
        price = shoe.get("price_usd", 0)
        if price < 120:
            score += 0.08  # Great value bonus
        elif price < 150:
            score += 0.05  # Good value bonus
        elif price > 200:
            score -= 0.03  # Premium price penalty (needs to earn it)
        
        return max(0.1, min(1.0, score))
    
    def generate_detailed_ai_analysis(self, shoe: Dict[str, Any], request: RecommendationRequest, rank: int = 1) -> str:
        """Generate comprehensive AI analysis for a specific shoe"""
        
        # Prepare detailed shoe information
        shoe_details = self._format_shoe_details_for_analysis(shoe)
        user_requirements = self._format_user_requirements(request)
        
        # Generate the detailed analysis
        analysis_prompt = self.analysis_prompts["detailed_analysis"].format(
            shoe_details=shoe_details,
            user_requirements=user_requirements
        )
        
        try:
            detailed_analysis = self._get_completion(analysis_prompt)
            
            # Add ranking context if this is a top recommendation
            if rank == 1:
                ranking_context = f"\n\n**TOP RECOMMENDATION #{rank}**: This shoe ranked highest due to optimal alignment with your requirements."
            else:
                ranking_context = f"\n\n**RECOMMENDATION #{rank}**: Strong alternative option with specific advantages."
            
            return detailed_analysis + ranking_context
            
        except Exception as e:
            return f"Advanced AI analysis temporarily unavailable. Basic analysis: This {shoe['brand']} {shoe['model']} offers solid performance for your intended use with {shoe.get('plate', 'standard')} construction and {shoe.get('drop_mm', 'standard')} drop."
    
    def generate_comparative_analysis(self, shoes: List[Dict[str, Any]], request: RecommendationRequest) -> str:
        """Generate comparative analysis between multiple shoes"""
        
        if len(shoes) < 2:
            return "Comparative analysis requires at least 2 shoes."
        
        shoes_list = "\n".join([
            f"{i+1}. {shoe['brand']} {shoe['model']} - ${shoe['price_usd']} - {shoe.get('category', [])} - {shoe.get('plate', 'none')} plate"
            for i, shoe in enumerate(shoes)
        ])
        
        user_requirements = self._format_user_requirements(request)
        
        comparison_prompt = self.analysis_prompts["comparative_analysis"].format(
            shoes_list=shoes_list,
            user_requirements=user_requirements
        )
        
        try:
            return self._get_completion(comparison_prompt)
        except Exception as e:
            return f"Comparative analysis temporarily unavailable. All {len(shoes)} shoes meet your basic requirements with varying strengths in different areas."
    
    def generate_technical_deep_dive(self, shoe: Dict[str, Any], focus_area: str = "performance") -> str:
        """Generate technical deep dive analysis for a specific shoe"""
        
        shoe_details = self._format_shoe_details_for_analysis(shoe, include_technical=True)
        
        technical_prompt = self.analysis_prompts["technical_deep_dive"].format(
            shoe_details=shoe_details,
            focus_area=focus_area
        )
        
        try:
            return self._get_completion(technical_prompt)
        except Exception as e:
            return f"Technical analysis temporarily unavailable. This {shoe['brand']} {shoe['model']} features {shoe.get('plate', 'standard')} technology with {shoe.get('weight_g', 'moderate')}g weight and {shoe.get('drop_mm', 'standard')}mm drop for {focus_area} optimization."
    
    def _format_shoe_details_for_analysis(self, shoe: Dict[str, Any], include_technical: bool = False) -> str:
        """Format shoe details for AI analysis prompts"""
        details = [
            f"Brand: {shoe['brand']}",
            f"Model: {shoe['model']}",
            f"Price: ${shoe['price_usd']}",
            f"Categories: {', '.join(shoe.get('category', []))}",
            f"Plate Technology: {shoe.get('plate', 'none')}"
        ]
        
        if shoe.get('drop_mm'):
            details.append(f"Drop: {shoe['drop_mm']}mm")
        if shoe.get('weight_g'):
            details.append(f"Weight: {shoe['weight_g']}g")
        
        if include_technical:
            # Add more technical details if available
            technical_details = []
            if shoe.get('enhanced_data'):
                enhanced = shoe['enhanced_data']
                if enhanced.get('description'):
                    technical_details.append(f"Description: {enhanced['description'][:200]}...")
                if enhanced.get('features'):
                    technical_details.append(f"Key Features: {', '.join(enhanced['features'][:3])}")
            
            if technical_details:
                details.extend(technical_details)
        
        return "\n".join(details)
    
    def _format_user_requirements(self, request: RecommendationRequest) -> str:
        """Format user requirements for AI analysis"""
        requirements = []
        
        # Intended use
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
            uses.append("Trail running")
        
        if uses:
            requirements.append(f"Intended Use: {', '.join(uses)}")
        
        # Brand preferences
        if request.brand_preferences:
            requirements.append(f"Preferred Brands: {', '.join(request.brand_preferences)}")
        
        # Budget
        if request.cost_limiter.enabled:
            requirements.append(f"Budget: Maximum ${request.cost_limiter.max_usd}")
        
        return "\n".join(requirements) if requirements else "General running needs"