#!/usr/bin/env python3
"""
Enhanced Scraper Module for gathering additional shoe data like reviews, descriptions, and popularity metrics.
This module extends the existing catalog with dynamic data from the web.
"""

import json
import time
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """Setup Chrome WebDriver with optimal settings for scraping"""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1400,1400")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    return driver


def search_shoe_on_roadrunner(driver: webdriver.Chrome, brand: str, model: str) -> Optional[str]:
    """
    Search for a specific shoe on Road Runner Sports and return the product URL.
    """
    try:
        # Create search query
        search_query = f"{brand} {model}".replace(" ", "+")
        search_url = f"https://www.roadrunnersports.com/search?q={search_query}"
        
        print(f"  Searching for: {brand} {model}")
        driver.get(search_url)
        
        # Wait for search results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(1)
        
        # Look for product links that match our brand/model
        product_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/product/"]')
        
        for link in product_links:
            href = link.get_attribute("href")
            link_text = link.text.lower()
            
            # Check if the link contains both brand and model
            if (brand.lower() in link_text and 
                any(word in link_text for word in model.lower().split())):
                print(f"  Found product URL: {href}")
                return href
        
        print(f"  No matching product found for {brand} {model}")
        return None
        
    except Exception as e:
        print(f"  Error searching for {brand} {model}: {e}")
        return None


def extract_enhanced_shoe_data(driver: webdriver.Chrome, product_url: str) -> Dict:
    """
    Extract enhanced data from a shoe product page including reviews, descriptions, and popularity metrics.
    """
    enhanced_data = {
        "reviews": {
            "count": 0,
            "average_rating": 0.0,
            "recent_reviews": []
        },
        "description": "",
        "features": [],
        "popularity_score": 0,
        "availability_score": 0
    }
    
    try:
        print(f"    Loading product page: {product_url}")
        driver.get(product_url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(2)
        
        # Extract product description
        description_selectors = [
            '[data-testid="product-description"]',
            '.product-description',
            '.description',
            '.product-details',
            '.product-info'
        ]
        
        for selector in description_selectors:
            try:
                desc_element = driver.find_element(By.CSS_SELECTOR, selector)
                enhanced_data["description"] = desc_element.text.strip()
                break
            except:
                continue
        
        # Extract review information
        try:
            # Look for review count
            review_count_selectors = [
                '[data-testid="review-count"]',
                '.review-count',
                '.reviews-count',
                '*[text()*="review" i]'
            ]
            
            for selector in review_count_selectors:
                try:
                    review_element = driver.find_element(By.CSS_SELECTOR, selector)
                    review_text = review_element.text
                    # Extract number from text like "145 reviews" or "(23)"
                    numbers = re.findall(r'(\d+)', review_text)
                    if numbers:
                        enhanced_data["reviews"]["count"] = int(numbers[0])
                        break
                except:
                    continue
            
            # Look for star rating
            rating_selectors = [
                '[data-testid="rating"]',
                '.rating',
                '.stars',
                '.star-rating'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = driver.find_element(By.CSS_SELECTOR, selector)
                    rating_text = rating_element.text
                    # Look for patterns like "4.5 out of 5" or "4.5/5"
                    rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*5', rating_text)
                    if rating_match:
                        enhanced_data["reviews"]["average_rating"] = float(rating_match.group(1))
                        break
                except:
                    continue
        
        except Exception as e:
            print(f"    Error extracting review data: {e}")
        
        # Extract key features
        try:
            feature_selectors = [
                '.product-features li',
                '.features li',
                '.bullet-points li',
                '.key-features li'
            ]
            
            for selector in feature_selectors:
                try:
                    feature_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    features = [elem.text.strip() for elem in feature_elements if elem.text.strip()]
                    if features:
                        enhanced_data["features"] = features[:5]  # Limit to top 5 features
                        break
                except:
                    continue
        
        except Exception as e:
            print(f"    Error extracting features: {e}")
        
        # Calculate popularity score based on review count and rating
        review_count = enhanced_data["reviews"]["count"]
        avg_rating = enhanced_data["reviews"]["average_rating"]
        
        if review_count > 0:
            # Normalize review count (log scale) and combine with rating
            import math
            normalized_reviews = min(math.log10(review_count + 1) / math.log10(1000), 1.0)  # Max at 1000 reviews
            normalized_rating = avg_rating / 5.0 if avg_rating > 0 else 0
            enhanced_data["popularity_score"] = (normalized_reviews * 0.6 + normalized_rating * 0.4) * 100
        
        print(f"    Enhanced data extracted: {review_count} reviews, {avg_rating} rating, {len(enhanced_data['features'])} features")
        
    except Exception as e:
        print(f"    Error extracting enhanced data: {e}")
    
    return enhanced_data


def enhance_catalog_with_web_data(catalog_file: str = "catalog.json", output_file: str = "enhanced_catalog.json", max_items: int = None) -> Dict:
    """
    Enhance the existing catalog with web-scraped data for better AI analysis.
    """
    print("Starting catalog enhancement with web data...")
    
    # Load existing catalog
    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    
    if max_items:
        catalog = catalog[:max_items]
        print(f"Processing first {max_items} items for testing")
    
    driver = setup_driver(headless=True)
    enhanced_catalog = []
    
    try:
        for idx, shoe in enumerate(catalog, 1):
            print(f"\nProcessing {idx}/{len(catalog)}: {shoe['brand']} {shoe['model']}")
            
            # Search for the shoe on Road Runner Sports
            product_url = search_shoe_on_roadrunner(driver, shoe["brand"], shoe["model"])
            
            if product_url:
                # Extract enhanced data
                enhanced_data = extract_enhanced_shoe_data(driver, product_url)
                
                # Combine original data with enhanced data
                enhanced_shoe = shoe.copy()
                enhanced_shoe.update({
                    "enhanced_data": enhanced_data,
                    "web_source_url": product_url,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                enhanced_catalog.append(enhanced_shoe)
                
                # Add delay to be respectful
                time.sleep(2)
            else:
                # Keep original data even if we can't enhance it
                enhanced_shoe = shoe.copy()
                enhanced_shoe.update({
                    "enhanced_data": {
                        "reviews": {"count": 0, "average_rating": 0.0, "recent_reviews": []},
                        "description": "",
                        "features": [],
                        "popularity_score": 0,
                        "availability_score": 0
                    },
                    "web_source_url": None,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                enhanced_catalog.append(enhanced_shoe)
    
    except Exception as e:
        print(f"Error during enhancement: {e}")
    
    finally:
        driver.quit()
    
    # Save enhanced catalog
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced_catalog, f, ensure_ascii=False, indent=2)
    
    print(f"\nEnhanced catalog saved to {output_file}")
    print(f"Successfully enhanced {len([s for s in enhanced_catalog if s.get('web_source_url')])} out of {len(enhanced_catalog)} shoes")
    
    return enhanced_catalog


if __name__ == "__main__":
    # Test with a small sample
    enhanced_catalog = enhance_catalog_with_web_data(
        catalog_file="catalog.json",
        output_file="test_enhanced_catalog.json",
        max_items=2  # Test with 2 items
    )