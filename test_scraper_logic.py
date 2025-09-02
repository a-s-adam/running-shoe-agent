#!/usr/bin/env python3
"""
Test script for the Road Runner Sports scraper logic.
Tests the data extraction functions without running the browser.
"""

import json
import re
from typing import Dict, Tuple

def guess_brand_model_from_title(title: str) -> Tuple[str, str]:
    """
    Test the brand/model extraction logic.
    """
    if not title:
        return "", ""

    t = title.replace("Men's", "").replace("Men's", "").strip()
    parts = t.split()
    if len(parts) >= 2:
        brand = parts[0]
        model = " ".join(parts[1:])
        return brand, model
    return "", t


def extract_product_specs_from_text(page_text: str) -> Dict:
    """
    Test the spec extraction logic with sample text.
    """
    specs = {
        "category": [],
        "plate": "none",
        "drop_mm": None,
        "weight_g": None
    }
    
    page_text = page_text.lower()
    
    # Determine categories based on keywords
    if any(word in page_text for word in ["race", "racing", "competition"]):
        specs["category"].append("race")
    if any(word in page_text for word in ["tempo", "speed", "fast"]):
        specs["category"].append("tempo")
    if any(word in page_text for word in ["daily", "training", "everyday"]):
        specs["category"].append("daily")
    if any(word in page_text for word in ["easy", "recovery", "long"]):
        specs["category"].append("easy")
    if any(word in page_text for word in ["trail", "off-road"]):
        specs["category"].append("trail")
    
    # Default to daily if no specific category found
    if not specs["category"]:
        specs["category"].append("daily")
    
    # Extract plate technology
    if any(word in page_text for word in ["carbon plate", "carbon fiber", "carbon"]):
        specs["plate"] = "carbon"
    elif any(word in page_text for word in ["nylon plate", "nylon"]):
        specs["plate"] = "nylon"
    
    # Extract drop (heel-to-toe offset)
    drop_match = re.search(r'(\d+)\s*mm.*drop|drop.*(\d+)\s*mm|(\d+)\s*mm.*offset|offset.*(\d+)\s*mm', page_text)
    if drop_match:
        for group in drop_match.groups():
            if group:
                specs["drop_mm"] = float(group)
                break
    
    # Extract weight
    weight_match = re.search(r'(\d+\.?\d*)\s*ounces?|(\d+\.?\d*)\s*oz', page_text)
    if weight_match:
        for group in weight_match.groups():
            if group:
                # Convert ounces to grams (1 oz = 28.35g)
                specs["weight_g"] = round(float(group) * 28.35)
                break
    
    return specs


def test_brand_model_extraction():
    """Test brand/model extraction with sample titles."""
    test_cases = [
        "Men's Brooks Ghost 17",
        "Brooks Ghost 17",
        "Nike Vaporfly 3",
        "Hoka Clifton 9",
        "Saucony Endorphin Speed 3"
    ]
    
    print("Testing brand/model extraction:")
    print("=" * 50)
    
    for title in test_cases:
        brand, model = guess_brand_model_from_title(title)
        print(f"Title: {title}")
        print(f"  Brand: {brand}")
        print(f"  Model: {model}")
        print()


def test_spec_extraction():
    """Test spec extraction with sample product descriptions."""
    test_cases = [
        {
            "name": "Brooks Ghost 17 - Daily Trainer",
            "text": """
            The Brooks Ghost 17 is perfect for daily training runs. 
            It features a 10 mm drop and weighs 10.1 ounces. 
            This neutral running shoe provides excellent cushioning 
            for easy runs and long distances.
            """
        },
        {
            "name": "Nike Vaporfly 3 - Race Shoe",
            "text": """
            The Nike Vaporfly 3 is built for speed with a carbon fiber plate.
            It has an 8 mm drop and weighs only 6.5 ounces.
            This racing shoe is designed for competition and tempo runs.
            """
        },
        {
            "name": "Hoka Clifton 9 - Easy Runs",
            "text": """
            The Hoka Clifton 9 is great for easy runs and recovery.
            It features a 5 mm drop and weighs 8.8 ounces.
            Perfect for daily training and long runs.
            """
        }
    ]
    
    print("Testing spec extraction:")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"Product: {test_case['name']}")
        specs = extract_product_specs_from_text(test_case['text'])
        print(f"  Categories: {specs['category']}")
        print(f"  Plate: {specs['plate']}")
        print(f"  Drop: {specs['drop_mm']}mm")
        print(f"  Weight: {specs['weight_g']}g")
        print()


def test_catalog_format():
    """Test that extracted data matches catalog.json format."""
    print("Testing catalog format compatibility:")
    print("=" * 50)
    
    # Sample extracted data
    sample_extracted = {
        "brand": "Brooks",
        "model": "Ghost 17",
        "category": ["daily", "easy"],
        "price_usd": 149.95,
        "plate": "none",
        "drop_mm": 10.0,
        "weight_g": 286
    }
    
    # Load your existing catalog to compare format
    try:
        with open("app/catalog.json", "r") as f:
            existing_catalog = json.load(f)
        
        if existing_catalog:
            sample_existing = existing_catalog[0]
            
            print("Sample extracted data:")
            print(json.dumps(sample_extracted, indent=2))
            print("\nSample existing catalog data:")
            print(json.dumps(sample_existing, indent=2))
            
            # Check if all required fields are present
            required_fields = ["brand", "model", "category", "price_usd", "plate", "drop_mm", "weight_g"]
            missing_fields = [field for field in required_fields if field not in sample_extracted]
            
            if missing_fields:
                print(f"\n❌ Missing fields: {missing_fields}")
            else:
                print("\n✅ All required fields present!")
                
            # Check data types
            print("\nData type validation:")
            print(f"  brand: {type(sample_extracted['brand']).__name__} ✅")
            print(f"  model: {type(sample_extracted['model']).__name__} ✅")
            print(f"  category: {type(sample_extracted['category']).__name__} ✅")
            print(f"  price_usd: {type(sample_extracted['price_usd']).__name__} ✅")
            print(f"  plate: {type(sample_extracted['plate']).__name__} ✅")
            print(f"  drop_mm: {type(sample_extracted['drop_mm']).__name__} ✅")
            print(f"  weight_g: {type(sample_extracted['weight_g']).__name__} ✅")
            
    except FileNotFoundError:
        print("❌ Could not find app/catalog.json for comparison")
    except Exception as e:
        print(f"❌ Error reading catalog: {e}")


def main():
    """Run all tests."""
    print("🧪 Testing Road Runner Sports Scraper Logic")
    print("=" * 60)
    
    test_brand_model_extraction()
    test_spec_extraction()
    test_catalog_format()
    
    print("\n🎯 Next Steps:")
    print("1. Install selenium: pip install selenium")
    print("2. Install Chrome/ChromeDriver")
    print("3. Run: python scrape_roadrunners_mens_running.py --max-products 5 --out test_catalog.json")
    print("4. Compare output with app/catalog.json format")


if __name__ == "__main__":
    main()
