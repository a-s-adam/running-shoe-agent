#!/usr/bin/env python3
"""
Enhanced Scraper for Road Runner Sports men's running shoes into a JSON catalog matching catalog.json format.

Features:
- Handles pagination to check ALL pages in the catalog
- Improved plate technology detection with context awareness
- Scrolls each page to load all products
- Collects product cards (name, brand, model, image, product URL)
- Extracts detailed specs from product pages to match catalog.json format
- Saves to JSON in the same structure as catalog.json
- Comprehensive logging and error handling

Usage examples:
    python scrape_roadrunners_mens_running.py --out catalog_roadrunner.json
    python scrape_roadrunners_mens_running.py --max-products 20 --out test_catalog.json
"""

from __future__ import annotations
import argparse
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# You can 'pip install webdriver-manager' and uncomment below to auto-manage ChromeDriver.
# from webdriver_manager.chrome import ChromeDriverManager


BASE = "https://www.roadrunnersports.com"
MENS_RUNNING_URL = "https://www.roadrunnersports.com/category/mens/shoes/running"


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1400,1400")
    opts.add_argument("--disable-dev-shm-usage")
    # Reduce bot friction
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")

    # driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    return driver


def find_pagination_links(driver: webdriver.Chrome) -> List[str]:
    """
    Find all pagination links to ensure we scrape every page.
    Returns list of URLs to visit.
    """
    page_urls = []
    
    try:
        # Start with the current page
        current_url = driver.current_url
        page_urls.append(current_url)
        
        # Look for pagination elements that are actually page numbers
        pagination_selectors = [
            'nav[aria-label="Pagination"] a[href*="page="]',
            '.pagination a[href*="page="]',
            '[data-testid="pagination"] a[href*="page="]',
            'a[href*="page="]'
        ]
        
        for selector in pagination_selectors:
            try:
                links = driver.find_elements(By.CSS_SELECTOR, selector)
                for link in links:
                    href = link.get_attribute("href")
                    if href and "roadrunnersports.com" in href and "page=" in href:
                        # Only add if it's a valid page link
                        if href not in page_urls:
                            page_urls.append(href)
            except:
                continue
        
        # If no pagination found, just return the current page
        if len(page_urls) == 1:
            print(f"🔍 No pagination found, scraping single page")
        else:
            print(f"🔍 Found {len(page_urls)} pages to scrape")
            
        return page_urls
        
    except Exception as e:
        print(f"⚠️ Error finding pagination: {e}")
        # Fallback to current page
        return [driver.current_url]


def gently_scroll_all(driver: webdriver.Chrome, pause: float = 0.6, max_tries: int = 30) -> None:
    """
    Scrolls to the bottom, waiting for lazy-loaded content. Stops when height stops growing.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    stable_count = 0
    for _ in range(200):  # safety cap
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            stable_count += 1
            if stable_count >= max_tries:
                break
        else:
            stable_count = 0
            last_height = new_height


def extract_product_cards(driver: webdriver.Chrome) -> List[Dict]:
    """
    Finds product cards on the listing page. Returns rough dicts with:
    brand, model, title, product_url, image_url
    """
    cards = []

    # Strategy: product anchors contain '/product/...' links. We'll dedup by URL.
    anchors = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/product/"]')

    seen = set()
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            if not href or "/product/" not in href:
                continue
            # Dedup by canonical product path (strip query/fragments)
            canonical = href.split("?")[0].split("#")[0]
            if canonical in seen:
                continue
            seen.add(canonical)

            # Try multiple strategies to extract title
            title = None
            
            # Strategy 1: aria-label
            aria_label = a.get_attribute("aria-label")
            if aria_label and len(aria_label) > 10:
                title = aria_label.strip()
            
            # Strategy 2: text content
            if not title:
                title = a.text.strip()
            
            # Strategy 3: nearby text elements
            if not title or len(title) < 5:
                try:
                    # Look for text in nearby elements
                    nearby_text = a.find_element(By.XPATH, "following-sibling::*[1]").text.strip()
                    if nearby_text and len(nearby_text) > 5:
                        title = nearby_text
                except:
                    pass
            
            # Strategy 4: URL slug as fallback
            if not title or len(title) < 5:
                url_path = urlparse(href).path
                slug = url_path.split("/")[-1]
                if slug and len(slug) > 5:
                    title = slug.replace("-", " ").title()
            
            if not title or len(title) < 5:
                continue

            # Clean up title
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Extract brand and model
            brand, model = guess_brand_model_from_title(title)
            
            if brand and model:
                cards.append({
                    "brand": brand,
                    "model": model,
                    "title": title,
                    "product_url": href,
                    "image_url": None  # We'll get this from product page if needed
                })

        except (StaleElementReferenceException, Exception) as e:
            continue

    return cards


def guess_brand_model_from_title(title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract brand and model from product title.
    """
    # Remove gender prefixes
    title = re.sub(r"^(Men's|Men|Women's|Women|Unisex)\s+", "", title, flags=re.IGNORECASE)
    
    # Known brand patterns
    brand_patterns = {
        "Brooks": r"Brooks\s+([A-Za-z0-9\s\-]+)",
        "ASICS": r"ASICS\s+([A-Za-z0-9\s\-]+)",
        "HOKA": r"HOKA\s+([A-Za-z0-9\s\-]+)",
        "Nike": r"Nike\s+([A-Za-z0-9\s\-]+)",
        "Adidas": r"Adidas\s+([A-Za-z0-9\s\-]+)",
        "Saucony": r"Saucony\s+([A-Za-z0-9\s\-]+)",
        "New Balance": r"New\s+Balance\s+([A-Za-z0-9\s\-]+)",
        "On": r"On\s+([A-Za-z0-9\s\-]+)",
        "Altra": r"Altra\s+([A-Za-z0-9\s\-]+)",
        "Mizuno": r"Mizuno\s+([A-Za-z0-9\s\-]+)",
        "Under Armour": r"Under\s+Armour\s+([A-Za-z0-9\s\-]+)",
        "Puma": r"Puma\s+([A-Za-z0-9\s\-]+)",
        "Reebok": r"Reebok\s+([A-Za-z0-9\s\-]+)"
    }
    
    for brand, pattern in brand_patterns.items():
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            model = match.group(1).strip()
            # Clean up model name
            model = re.sub(r'\s+', ' ', model).strip()
            return brand, model
    
    return None, None


def parse_price_block(driver: webdriver.Chrome) -> Tuple[Optional[float], Optional[float]]:
    """
    Try to locate price elements on a product page.
    Returns (regular_price, sale_price)
    """
    try:
        # More specific price selectors that are likely to contain actual product prices
        price_selectors = [
            '[data-testid="price"]',
            '.product-price',
            '.price-current',
            '.price-regular',
            '.price-sale',
            '[class*="price"]'
        ]
        
        all_prices = []
        
        # Collect all potential prices
        for selector in price_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.strip()
                    if text:
                        # Look for price patterns with better validation
                        # First try to find $XX.XX format
                        price_matches = re.findall(r'\$(\d+\.\d{2})', text)
                        if not price_matches:
                            # Fallback: look for any XX.XX format in price-like context
                            price_matches = re.findall(r'(\d+\.\d{2})', text)
                        
                        for price_str in price_matches:
                            try:
                                price = float(price_str)
                                # Validate price range (running shoes are typically $50-$300)
                                if 50 <= price <= 300:
                                    all_prices.append(price)
                            except ValueError:
                                continue
            except:
                continue
        
        if not all_prices:
            return None, None
        
        # Remove duplicates and sort
        unique_prices = sorted(list(set(all_prices)))
        
        # Logic to determine regular vs sale price
        if len(unique_prices) == 1:
            # Only one price found
            return unique_prices[0], None
        elif len(unique_prices) >= 2:
            # Multiple prices - assume highest is regular, lowest is sale
            regular_price = max(unique_prices)
            sale_price = min(unique_prices)
            
            # If the difference is too small, it might not be a real sale
            if regular_price - sale_price < 10:
                return regular_price, None
            else:
                return regular_price, sale_price
        
        return None, None
        
    except Exception as e:
        print(f"  Error parsing price: {e}")
        return None, None


def extract_product_specs_from_text(page_text: str) -> Dict:
    """
    Extract product specifications from page text with improved accuracy.
    """
    specs = {}
    
    try:
        # Convert to lowercase for consistent matching
        page_text = page_text.lower()
        
        # Extract categories based on intended use
        categories = []
        if any(word in page_text for word in ["race", "racing", "competition"]):
            categories.append("race")
        if any(word in page_text for word in ["tempo", "speed", "fast"]):
            categories.append("tempo")
        if any(word in page_text for word in ["daily", "training", "everyday"]):
            categories.append("daily")
        if any(word in page_text for word in ["easy", "recovery", "long"]):
            categories.append("easy")
        if any(word in page_text for word in ["trail", "off-road"]):
            categories.append("trail")
        
        if categories:
            specs["category"] = categories
        
        # IMPROVED: Extract plate technology with context awareness
        # Look for specific plate mentions in context
        plate_patterns = [
            r'carbon\s+plate',           # "carbon plate"
            r'carbon\s+fiber\s+plate',   # "carbon fiber plate"
            r'nylon\s+plate',            # "nylon plate"
            r'composite\s+plate',        # "composite plate"
            r'pebax\s+plate',            # "pebax plate"
            r'no\s+plate',               # "no plate"
            r'without\s+plate',          # "without plate"
            r'plate\s+technology',       # "plate technology"
        ]
        
        plate_found = False
        for pattern in plate_patterns:
            if re.search(pattern, page_text):
                if "carbon" in pattern:
                    specs["plate"] = "carbon"
                    plate_found = True
                    break
                elif "nylon" in pattern:
                    specs["plate"] = "nylon"
                    plate_found = True
                    break
                elif "composite" in pattern:
                    specs["plate"] = "composite"
                    plate_found = True
                    break
                elif "pebax" in pattern:
                    specs["plate"] = "pebax"
                    plate_found = True
                    break
                elif "no" in pattern or "without" in pattern:
                    specs["plate"] = "none"
                    plate_found = True
                    break
        
        # If no specific plate pattern found, default to "none"
        if not plate_found:
            specs["plate"] = "none"
        
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
        
        # Look for specific specs in the "NUTS & BOLTS" section
        # Note: This section requires driver access, so we'll skip it for now
        # and rely on the main page text analysis
            
    except Exception as e:
        print(f"Error extracting specs: {e}")
    
    return specs


def check_size_available_on_product_page(
    driver: webdriver.Chrome,
    product_url: str,
    size_str: str,
    wait_s: float = 10.0,
    delay_after_load: float = 0.6
) -> Tuple[bool, Optional[float], Optional[float]]:
    """
    Opens product page, tries to detect if desired size is selectable (in-stock).
    Returns (available, price, sale_price)
    """
    try:
        driver.get(product_url)
        WebDriverWait(driver, wait_s).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        time.sleep(delay_after_load)

        # Try to find a size button/option with the desired size text.
        # Common patterns: buttons, li, span with text == size (e.g., "10.5")
        size_el = None
        candidates = driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{size_str}']")
        for el in candidates:
            cls = el.get_attribute("class") or ""
            aria = el.get_attribute("aria-disabled") or ""
            disabled = "disabled" in cls.lower() or aria.lower() in ("true", "aria-disabled")
            # Heuristic: parent may hold disabled state
            parent_cls = (el.find_element(By.XPATH, "..").get_attribute("class") or "").lower()
            parent_disabled = "disabled" in parent_cls or "unavailable" in parent_cls
            if not (disabled or parent_disabled):
                size_el = el
                break

        available = size_el is not None

        price, sale_price = parse_price_block(driver)
        return (available, price, sale_price)

    except (TimeoutException, WebDriverException):
        return (False, None, None)


def extract_product_data_with_retry(
    driver: webdriver.Chrome,
    product_url: str,
    max_retries: int = 3,
    throttle: float = 1.0
) -> Tuple[Optional[float], Optional[float], Dict]:
    """
    Extract product data with retry logic for reliability.
    Returns (price, sale_price, specs)
    """
    for attempt in range(max_retries):
        try:
            print(f"    Attempt {attempt + 1}/{max_retries}: Loading {product_url}")
            driver.get(product_url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            time.sleep(throttle)
            
            # Get page text for analysis
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            price, sale_price = parse_price_block(driver)
            specs = extract_product_specs_from_text(page_text)
            
            return price, sale_price, specs
            
        except (TimeoutException, WebDriverException) as e:
            print(f"    Timeout/connection error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(throttle * 2)  # Longer wait on retry
                continue
            else:
                print(f"    Failed after {max_retries} attempts")
                return None, None, {}
        except Exception as e:
            print(f"    Unexpected error: {e}")
            return None, None, {}
    
    return None, None, {}


def main():
    ap = argparse.ArgumentParser(description="Enhanced Scraper for Road Runner Sports men's running shoes to JSON matching catalog.json format.")
    ap.add_argument("--url", default=MENS_RUNNING_URL, help="Listing URL (default: men's running)")
    ap.add_argument("--size", default=None, help='Target size to check, e.g. "10" or "10.5".')
    ap.add_argument("--verify-size", action="store_true",
                    help="Open each product page to verify size availability (slower).")
    ap.add_argument("--out", default="catalog_roadrunner.json", help="Output JSON path.")
    ap.add_argument("--headful", action="store_true", help="Run browser with UI (non-headless).")
    ap.add_argument("--max-products", type=int, default=None, help="Limit number of products to process.")
    ap.add_argument("--pause", type=float, default=0.6, help="Scroll pause (seconds).")
    ap.add_argument("--throttle", type=float, default=0.6, help="Delay between product checks (seconds).")
    ap.add_argument("--retries", type=int, default=3, help="Number of retries for failed page loads.")
    args = ap.parse_args()

    if args.verify_size and not args.size:
        ap.error("--verify-size requires --size")

    driver = setup_driver(headless=not args.headful)
    all_products = []
    
    try:
        print(f"🚀 Starting enhanced scraper for Road Runner Sports")
        print(f"📍 Base URL: {args.url}")
        print(f"⚙️  Settings: throttle={args.throttle}s, retries={args.retries}")
        
        # Find all pagination links
        print(f"🔍 Loading initial page to find pagination...")
        driver.get(args.url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/product/"]'))
        )
        
        page_urls = find_pagination_links(driver)
        
        # Process each page
        for page_idx, page_url in enumerate(page_urls, 1):
            print(f"\n📄 Processing page {page_idx}/{len(page_urls)}: {page_url}")
            
            try:
                driver.get(page_url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/product/"]'))
                )
                
                print(f"  Scrolling to load all products on this page...")
                gently_scroll_all(driver, pause=args.pause)
                
                print(f"  Extracting product cards from this page...")
                page_cards = extract_product_cards(driver)
                print(f"  Found {len(page_cards)} products on this page")
                
                # Dedup by product_url (defense-in-depth)
                seen = set()
                trimmed = []
                for c in page_cards:
                    if c["product_url"] not in seen:
                        seen.add(c["product_url"])
                        trimmed.append(c)
                page_cards = trimmed
                
                print(f"  After deduplication: {len(page_cards)} unique products")
                
                # Process products on this page
                for idx, card in enumerate(page_cards, start=1):
                    print(f"  Processing {idx}/{len(page_cards)}: {card['brand']} {card['model']}")
                    
                    available_for_size = None
                    price = None
                    sale_price = None
                    specs = {}

                    if args.verify_size and args.size:
                        available_for_size, price, sale_price = check_size_available_on_product_page(
                            driver, card["product_url"], args.size
                        )
                        time.sleep(args.throttle)
                    else:
                        # Always get price and specs for catalog format
                        price, sale_price, specs = extract_product_data_with_retry(
                            driver, card["product_url"], max_retries=args.retries, throttle=args.throttle
                        )
                        
                        time.sleep(args.throttle)

                    # Build output matching catalog.json format
                    output_item = {
                        "brand": card["brand"],
                        "model": card["model"],
                        "category": specs.get("category", ["daily"]),
                        "price_usd": price or 0.0,
                        "plate": specs.get("plate", "none"),
                        "drop_mm": specs.get("drop_mm"),
                        "weight_g": specs.get("weight_g")
                    }
                    
                    # Add additional fields for verification
                    if args.verify_size:
                        output_item.update({
                            "size_checked": args.size,
                            "available_for_size": available_for_size,
                            "sale_price_usd": sale_price
                        })
                    
                    all_products.append(output_item)
                    
                    # Apply max products limit if specified
                    if args.max_products and len(all_products) >= args.max_products:
                        print(f"  Reached max products limit ({args.max_products})")
                        break
                
                # Apply max products limit if specified
                if args.max_products and len(all_products) >= args.max_products:
                    break
                    
            except Exception as e:
                print(f"  ⚠️ Error processing page {page_url}: {e}")
                continue

        # Final deduplication across all pages
        print(f"\n🔄 Final deduplication across all pages...")
        seen_urls = set()
        final_products = []
        for product in all_products:
            # Create a unique key from brand + model
            key = f"{product['brand']}_{product['model']}"
            if key not in seen_urls:
                seen_urls.add(key)
                final_products.append(product)
        
        print(f"📊 Final results: {len(final_products)} unique products from {len(all_products)} total")

        # Save results
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(final_products, f, ensure_ascii=False, indent=2)

        print(f"💾 Saved {len(final_products)} products to {args.out}")
        
        # Show sample of extracted data
        if final_products:
            print("\n📋 Sample extracted data:")
            print(json.dumps(final_products[0], indent=2))
            
        # Show comprehensive statistics
        successful_extractions = sum(1 for item in final_products if item["price_usd"] > 0)
        successful_specs = sum(1 for item in final_products if item["plate"] != "none" or item.get("drop_mm") or item.get("weight_g"))
        
        print(f"\n📊 COMPREHENSIVE EXTRACTION STATISTICS:")
        print(f"  Total pages processed: {len(page_urls)}")
        print(f"  Total products found: {len(all_products)}")
        print(f"  Unique products after deduplication: {len(final_products)}")
        print(f"  Successful price extractions: {successful_extractions}")
        print(f"  Successful spec extractions: {successful_specs}")
        print(f"  Price success rate: {(successful_extractions/len(final_products)*100):.1f}%")
        print(f"  Specs success rate: {(successful_specs/len(final_products)*100):.1f}%")
        
        # Plate technology breakdown
        plate_counts = {}
        for item in final_products:
            plate = item.get("plate", "unknown")
            plate_counts[plate] = plate_counts.get(plate, 0) + 1
        
        print(f"\n🏷️ PLATE TECHNOLOGY BREAKDOWN:")
        for plate, count in sorted(plate_counts.items()):
            percentage = (count / len(final_products)) * 100
            print(f"  {plate}: {count} products ({percentage:.1f}%)")
        
        # Brand distribution
        brand_counts = {}
        for item in final_products:
            brand = item.get("brand", "Unknown")
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        
        print(f"\n🏭 BRAND DISTRIBUTION:")
        for brand, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(final_products)) * 100
            print(f"  {brand}: {count} products ({percentage:.1f}%)")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
