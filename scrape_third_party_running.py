#!/usr/bin/env python3
"""
Scrape third-party running shoe retailers into the catalog/database format.

Examples:
    python scrape_third_party_running.py --list-sources
    python scrape_third_party_running.py --source rei_mens_road --max-products 20 --out rei_catalog.json
    SHOE_CATALOG_BACKEND=sqlite python scrape_third_party_running.py --source all --store --compress-images

Before scraping, review each site's terms/robots policy and keep throttles conservative.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from app.catalog_repository import CatalogRepository, normalize_shoe
from app.image_utils import fetch_and_compress_image


KNOWN_BRANDS = [
    "New Balance",
    "Under Armour",
    "Road Runner",
    "The North Face",
    "ASICS",
    "Brooks",
    "HOKA",
    "Hoka",
    "Nike",
    "Adidas",
    "Saucony",
    "On",
    "Altra",
    "Mizuno",
    "Puma",
    "Reebok",
    "Topo",
    "Norda",
    "Salomon",
    "Craft",
    "Karhu",
    "Merrell",
]


@dataclass(frozen=True)
class SourceProfile:
    key: str
    name: str
    listing_url: str
    base_url: str
    product_path_markers: Tuple[str, ...]
    default_pages: int = 1
    supports_thumbnail_fetch: bool = True


SOURCES: Dict[str, SourceProfile] = {
    # Source profiles keep retailer-specific URL patterns out of the scraper logic.
    "roadrunner_mens": SourceProfile(
        key="roadrunner_mens",
        name="Road Runner Sports",
        listing_url="https://www.roadrunnersports.com/category/mens/shoes/running",
        base_url="https://www.roadrunnersports.com",
        product_path_markers=("/product/",),
        default_pages=1,
    ),
    "rei_mens_road": SourceProfile(
        key="rei_mens_road",
        name="REI",
        listing_url="https://www.rei.com/c/mens-road-running-shoes",
        base_url="https://www.rei.com",
        product_path_markers=("/product/",),
        default_pages=1,
        supports_thumbnail_fetch=False,
    ),
    "sports_basement_mens": SourceProfile(
        key="sports_basement_mens",
        name="Sports Basement",
        listing_url="https://www.sportsbasement.com/collections/mens-running-shoes",
        base_url="https://www.sportsbasement.com",
        product_path_markers=("/products/",),
        default_pages=2,
    ),
    "runners_mind_footwear": SourceProfile(
        key="runners_mind_footwear",
        name="A Runner's Mind",
        listing_url="https://shop.arunnersmind.com/category/26043/footwear",
        base_url="https://shop.arunnersmind.com",
        product_path_markers=("/product/", "/products/", "/item/"),
        default_pages=1,
    ),
}


def load_selenium() -> None:
    """Import Selenium only when scraping so docs/status commands work without it."""
    global webdriver, Options, StaleElementReferenceException, TimeoutException, WebDriverException
    global By, EC, WebDriverWait

    try:
        from selenium import webdriver as selenium_webdriver
        from selenium.common.exceptions import StaleElementReferenceException as SeleniumStaleElementReferenceException
        from selenium.common.exceptions import TimeoutException as SeleniumTimeoutException
        from selenium.common.exceptions import WebDriverException as SeleniumWebDriverException
        from selenium.webdriver.chrome.options import Options as SeleniumOptions
        from selenium.webdriver.common.by import By as SeleniumBy
        from selenium.webdriver.support import expected_conditions as SeleniumEC
        from selenium.webdriver.support.ui import WebDriverWait as SeleniumWebDriverWait
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install scraper dependencies with `pip install -r requirements.txt`.") from exc

    webdriver = selenium_webdriver
    Options = SeleniumOptions
    StaleElementReferenceException = SeleniumStaleElementReferenceException
    TimeoutException = SeleniumTimeoutException
    WebDriverException = SeleniumWebDriverException
    By = SeleniumBy
    EC = SeleniumEC
    WebDriverWait = SeleniumWebDriverWait


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    load_selenium()
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1440,1600")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    return driver


def gently_scroll(driver: webdriver.Chrome, pause: float = 0.6, rounds: int = 8) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    title = re.sub(r"^(top rated|outlet|new arrival|sale)\s+", "", title, flags=re.I)
    return title


def guess_brand_model(title: str) -> Tuple[Optional[str], Optional[str]]:
    text = clean_title(title)
    text = re.sub(r"^(men's|mens|men|women's|womens|women|unisex)\s+", "", text, flags=re.I)
    text = re.sub(r"\s+(road-)?running shoes?\s*-\s*men'?s?.*$", "", text, flags=re.I)
    text = re.sub(r"\s+shoes?\s*-\s*men'?s?.*$", "", text, flags=re.I)
    text = re.sub(r"\s+men'?s?.*$", "", text, flags=re.I)

    for brand in KNOWN_BRANDS:
        pattern = re.compile(rf"^{re.escape(brand)}\b\s*(.+)$", re.I)
        match = pattern.search(text)
        if match:
            model = clean_title(match.group(1))
            return canonical_brand(brand), model or None

    # Some retailers concatenate brand and model in text, e.g. "BrooksGhost 17".
    for brand in KNOWN_BRANDS:
        if text.lower().startswith(brand.lower()):
            model = clean_title(text[len(brand):])
            return canonical_brand(brand), model or None

    return None, None


def canonical_brand(brand: str) -> str:
    mapping = {
        "asics": "ASICS",
        "hoka": "HOKA",
        "adidas": "Adidas",
    }
    return mapping.get(brand.lower(), brand)


def is_product_url(url: str, profile: SourceProfile) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.netloc and urlparse(profile.base_url).netloc not in parsed.netloc:
        return False
    return any(marker in parsed.path for marker in profile.product_path_markers)


def first_image_near_anchor(anchor: Any, profile: SourceProfile) -> Optional[str]:
    try:
        img = anchor.find_element(By.CSS_SELECTOR, "img")
        src = img.get_attribute("src") or img.get_attribute("data-src")
        if not src:
            srcset = img.get_attribute("srcset") or ""
            src = srcset.split(",")[0].strip().split(" ")[0] if srcset else None
        return urljoin(profile.base_url, src) if src else None
    except Exception:
        return None


def extract_product_cards(driver: webdriver.Chrome, profile: SourceProfile) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    seen_urls = set()

    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    for anchor in anchors:
        try:
            href = urljoin(profile.base_url, anchor.get_attribute("href") or "")
            if not is_product_url(href, profile):
                continue
            canonical_url = href.split("?")[0].split("#")[0]
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)

            title = clean_title(anchor.get_attribute("aria-label") or anchor.text)
            if not title:
                try:
                    img = anchor.find_element(By.CSS_SELECTOR, "img")
                    title = clean_title(img.get_attribute("alt") or "")
                except Exception:
                    title = ""

            if not title:
                title = clean_title(urlparse(canonical_url).path.split("/")[-1].replace("-", " "))

            brand, model = guess_brand_model(title)
            if not brand or not model:
                continue

            cards.append({
                "brand": brand,
                "model": model,
                "title": title,
                "source_url": canonical_url,
                "image_url": first_image_near_anchor(anchor, profile),
                "source_name": profile.name,
            })
        except (StaleElementReferenceException, Exception):
            continue

    return cards


def parse_price(text: str) -> Tuple[Optional[float], Optional[float]]:
    values = []
    for match in re.findall(r"\$([0-9]{2,3}(?:\.[0-9]{2})?)", text or ""):
        try:
            value = float(match)
        except ValueError:
            continue
        if 40 <= value <= 400:
            values.append(value)
    unique = sorted(set(values))
    if not unique:
        return None, None
    if len(unique) == 1:
        return unique[0], None
    return min(unique), max(unique)


def parse_specs(text: str) -> Dict[str, Any]:
    """Infer catalog fields from retailer page copy and specs text."""
    lower = (text or "").lower()
    specs: Dict[str, Any] = {}

    categories = []
    if any(word in lower for word in ["race day", "racing", "competition", "marathon"]):
        categories.append("race")
    if any(word in lower for word in ["tempo", "speed", "threshold", "interval", "fast"]):
        categories.append("tempo")
    if any(word in lower for word in ["daily trainer", "daily training", "everyday", "road-running"]):
        categories.append("daily")
    if any(word in lower for word in ["easy run", "max cushion", "plush"]):
        categories.append("easy")
    if any(word in lower for word in ["trail", "off-road"]):
        categories.append("trail")
    specs["category"] = sorted(set(categories)) or ["daily"]

    if re.search(r"carbon(?:\s+fiber)?\s+plate", lower):
        specs["plate"] = "carbon"
    elif re.search(r"nylon\s+plate", lower):
        specs["plate"] = "nylon"
    elif re.search(r"composite\s+plate", lower):
        specs["plate"] = "composite"
    else:
        specs["plate"] = "none"

    drop_match = re.search(r"(?:drop|heel\s*to\s*toe\s*drop|offset)[:\s-]*(\d+(?:\.\d+)?)\s*mm", lower)
    if not drop_match:
        drop_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:drop|offset)", lower)
    if drop_match:
        specs["drop_mm"] = float(drop_match.group(1))

    weight_match = re.search(r"(?:weight|approximate weight)[:\s-]*(\d+(?:\.\d+)?)\s*(?:oz|ounces)", lower)
    if not weight_match:
        weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:oz|ounces)", lower)
    if weight_match:
        specs["weight_g"] = round(float(weight_match.group(1)) * 28.3495)

    heel_match = re.search(r"heel stack[:\s-]*(\d+(?:\.\d+)?)\s*mm", lower)
    forefoot_match = re.search(r"forefoot stack[:\s-]*(\d+(?:\.\d+)?)\s*mm", lower)
    if heel_match:
        specs["heel_stack_mm"] = float(heel_match.group(1))
    if forefoot_match:
        specs["forefoot_stack_mm"] = float(forefoot_match.group(1))

    if any(term in lower for term in ["maximum cushioning", "max cushioning", "plush cushioning", "maximum"]):
        specs["cushioning_level"] = "plush"
    elif any(term in lower for term in ["moderate cushioning", "balanced cushioning", "moderate"]):
        specs["cushioning_level"] = "moderate"
    elif any(term in lower for term in ["minimal cushioning", "firm ride", "firm cushioning"]):
        specs["cushioning_level"] = "firm"

    if any(term in lower for term in ["stability", "guide rails", "pronation", "support shoe"]):
        specs["support_type"] = "stability"
    elif "neutral" in lower:
        specs["support_type"] = "neutral"

    if any(term in lower for term in ["wide", "2e", "4e"]):
        specs["has_wide_options"] = True

    distances = []
    if re.search(r"\b5k\b", lower):
        distances.append("5k")
    if re.search(r"\b10k\b", lower):
        distances.append("10k")
    if "half marathon" in lower:
        distances.append("half_marathon")
    if "marathon" in lower:
        distances.append("marathon")
    if distances:
        specs["best_for_distances"] = sorted(set(distances))

    return specs


def parse_rating(text: str) -> Tuple[Optional[int], Optional[float]]:
    review_count = None
    rating = None

    count_match = re.search(r"([0-9,]+)\s+reviews?", text or "", flags=re.I)
    if count_match:
        review_count = int(count_match.group(1).replace(",", ""))

    rating_match = re.search(r"average rating of\s+([0-9.]+)\s+out of\s+5", text or "", flags=re.I)
    if not rating_match:
        rating_match = re.search(r"([0-9.]+)\s*(?:out of|/)\s*5", text or "", flags=re.I)
    if rating_match:
        rating = float(rating_match.group(1))

    return review_count, rating


def iter_json_ld(driver: webdriver.Chrome) -> Iterable[Dict[str, Any]]:
    scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
    for script in scripts:
        raw = script.get_attribute("innerHTML") or ""
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in flatten_json_ld(payload):
            if isinstance(item, dict):
                yield item


def flatten_json_ld(payload: Any) -> Iterable[Any]:
    if isinstance(payload, list):
        for item in payload:
            yield from flatten_json_ld(item)
    elif isinstance(payload, dict):
        if "@graph" in payload:
            yield from flatten_json_ld(payload["@graph"])
        else:
            yield payload


def extract_product_json_ld(driver: webdriver.Chrome) -> Dict[str, Any]:
    """Prefer structured product metadata when a retailer exposes JSON-LD."""
    for item in iter_json_ld(driver):
        item_type = item.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if "Product" not in types:
            continue

        out: Dict[str, Any] = {}
        name = item.get("name")
        if name:
            brand, model = guess_brand_model(name)
            if brand and model:
                out.update({"brand": brand, "model": model})
            out["title"] = name

        brand_value = item.get("brand")
        if isinstance(brand_value, dict) and brand_value.get("name"):
            out["brand"] = canonical_brand(str(brand_value["name"]))
        elif isinstance(brand_value, str):
            out["brand"] = canonical_brand(brand_value)

        image = item.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        if isinstance(image, dict):
            image = image.get("url")
        if image:
            out["image_url"] = image

        if item.get("description"):
            out["description"] = item["description"]

        offers = item.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice")
            try:
                out["price_usd"] = float(price)
            except (TypeError, ValueError):
                pass

        aggregate = item.get("aggregateRating") or {}
        if isinstance(aggregate, dict):
            if aggregate.get("reviewCount"):
                out["review_count"] = int(float(aggregate["reviewCount"]))
            if aggregate.get("ratingValue"):
                out["average_rating"] = float(aggregate["ratingValue"])

        return out

    return {}


def read_meta_content(driver: webdriver.Chrome, selector: str) -> Optional[str]:
    try:
        return driver.find_element(By.CSS_SELECTOR, selector).get_attribute("content")
    except Exception:
        return None


def extract_product_details(
    driver: webdriver.Chrome,
    card: Dict[str, Any],
    profile: SourceProfile,
    compress_images: bool = False,
    image_max_bytes: int = 45_000,
) -> Dict[str, Any]:
    driver.get(card["source_url"])
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
    time.sleep(0.8)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    price, regular_price = parse_price(body_text)
    review_count, rating = parse_rating(body_text)
    json_ld = extract_product_json_ld(driver)
    specs = parse_specs(body_text)

    image_url = (
        json_ld.get("image_url")
        or read_meta_content(driver, 'meta[property="og:image"]')
        or card.get("image_url")
    )
    description = (
        json_ld.get("description")
        or read_meta_content(driver, 'meta[name="description"]')
        or read_meta_content(driver, 'meta[property="og:description"]')
    )

    item = {
        **card,
        **specs,
        **json_ld,
        "brand": json_ld.get("brand") or card["brand"],
        "model": json_ld.get("model") or card["model"],
        "price_usd": json_ld.get("price_usd") or price or 0.0,
        "sale_price_usd": price if regular_price and price and price < regular_price else None,
        "regular_price_usd": regular_price,
        "review_count": json_ld.get("review_count") or review_count,
        "average_rating": json_ld.get("average_rating") or rating,
        "popularity_score": calculate_popularity_score(review_count, rating),
        "description": description,
        "image_url": image_url,
        "source_name": profile.name,
        "source_url": card["source_url"],
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    if compress_images and image_url and profile.supports_thumbnail_fetch:
        try:
            thumb, mime = fetch_and_compress_image(image_url, max_bytes=image_max_bytes)
            if thumb:
                item["image_thumbnail_data_uri"] = thumb
                item["image_mime_type"] = mime
        except Exception as exc:
            print(f"    Image compression skipped: {exc}")

    return normalize_shoe(item)


def calculate_popularity_score(review_count: Optional[int], rating: Optional[float]) -> float:
    if not review_count and not rating:
        return 0.0
    import math

    normalized_reviews = min(math.log10((review_count or 0) + 1) / math.log10(2000), 1.0)
    normalized_rating = (rating or 0) / 5.0
    return round((normalized_reviews * 0.55 + normalized_rating * 0.45) * 100, 2)


def listing_urls_for(profile: SourceProfile, max_pages: int) -> List[str]:
    urls = [profile.listing_url]
    for page in range(2, max_pages + 1):
        separator = "&" if "?" in profile.listing_url else "?"
        urls.append(f"{profile.listing_url}{separator}page={page}")
    return urls


def scrape_source(
    profile: SourceProfile,
    max_products: Optional[int],
    max_pages: Optional[int],
    headless: bool,
    throttle: float,
    scroll_pause: float,
    compress_images: bool,
    image_max_bytes: int,
) -> List[Dict[str, Any]]:
    """Scrape one configured retailer source into normalized shoe records."""
    print(f"\n== {profile.name} ==")
    driver = setup_driver(headless=headless)
    products: List[Dict[str, Any]] = []
    seen_keys = set()

    try:
        page_count = max_pages or profile.default_pages
        for listing_url in listing_urls_for(profile, page_count):
            if max_products and len(products) >= max_products:
                break

            print(f"Loading listing: {listing_url}")
            try:
                driver.get(listing_url)
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                gently_scroll(driver, pause=scroll_pause)
                cards = extract_product_cards(driver, profile)
                print(f"  Found {len(cards)} product candidates")
            except (TimeoutException, WebDriverException) as exc:
                print(f"  Listing failed: {exc}")
                continue

            for index, card in enumerate(cards, 1):
                if max_products and len(products) >= max_products:
                    break
                try:
                    print(f"  {index}/{len(cards)} {card['brand']} {card['model']}")
                    item = extract_product_details(
                        driver,
                        card,
                        profile,
                        compress_images=compress_images,
                        image_max_bytes=image_max_bytes,
                    )
                    if item["shoe_key"] not in seen_keys:
                        seen_keys.add(item["shoe_key"])
                        products.append(item)
                    time.sleep(throttle)
                except Exception as exc:
                    print(f"    Product skipped: {exc}")
                    time.sleep(throttle)
    finally:
        driver.quit()

    print(f"Collected {len(products)} unique shoes from {profile.name}")
    return products


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape third-party running shoe retailers.")
    parser.add_argument("--source", default="roadrunner_mens", help="'all' or one source key.")
    parser.add_argument("--list-sources", action="store_true")
    parser.add_argument("--max-products", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--out", default="catalog_third_party.json")
    parser.add_argument("--store", action="store_true", help="Upsert results into configured SQLite/Supabase backend.")
    parser.add_argument("--compress-images", action="store_true", help="Store small WebP thumbnails as data URIs.")
    parser.add_argument("--image-max-bytes", type=int, default=int(os.getenv("SHOE_IMAGE_MAX_BYTES", "45000")))
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--throttle", type=float, default=1.2)
    parser.add_argument("--scroll-pause", type=float, default=0.6)
    args = parser.parse_args()

    if args.list_sources:
        for key, source in SOURCES.items():
            print(f"{key}: {source.name} - {source.listing_url}")
        return

    if args.source != "all" and args.source not in SOURCES:
        available = ", ".join(["all", *SOURCES.keys()])
        raise SystemExit(f"Unknown source '{args.source}'. Available sources: {available}")

    selected = list(SOURCES.values()) if args.source == "all" else [SOURCES[args.source]]
    all_products: List[Dict[str, Any]] = []

    for profile in selected:
        products = scrape_source(
            profile=profile,
            max_products=args.max_products,
            max_pages=args.max_pages,
            headless=not args.headful,
            throttle=args.throttle,
            scroll_pause=args.scroll_pause,
            compress_images=args.compress_images,
            image_max_bytes=args.image_max_bytes,
        )
        all_products.extend(products)

    # Final dedup across sources by shoe key, keeping the first source seen.
    deduped: Dict[str, Dict[str, Any]] = {}
    for item in all_products:
        deduped.setdefault(item["shoe_key"], item)

    output = list(deduped.values())
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(output)} shoes to {args.out}")

    if args.store:
        repo = CatalogRepository()
        stored = repo.upsert_many(output)
        print(f"Stored {stored} shoes in {repo.backend_name}")


if __name__ == "__main__":
    main()
