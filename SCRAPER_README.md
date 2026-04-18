# Road Runner Sports scraper

Python scraper for men’s running shoes on [Road Runner Sports](https://www.roadrunnersports.com/category/mens/shoes/running). Output is JSON aligned with `app/catalog.json`.

## Features

- Pulls brand, model, price, and key specs where available
- Output shape matches the catalog entries used by the recommender
- Retries, timeouts, and throttling to reduce flaky runs
- Heuristics for category, plate, drop, and weight
- Optional size verification (slower)

## Quick start

### Dependencies

```bash
pip install selenium
# or
pip install -r requirements.txt
```

Use a current Chrome install; Selenium 4+ typically resolves the driver for you.

### Run

```bash
# Small test run
python scrape_roadrunners_mens_running.py --max-products 5 --out test_catalog.json

# Full pass
python scrape_roadrunners_mens_running.py --out full_catalog.json

# Size check (example)
python scrape_roadrunners_mens_running.py --size "10.5" --verify-size --out size_10p5_catalog.json
```

## Output shape

Example object:

```json
{
  "brand": "Brooks",
  "model": "Ghost 17",
  "category": ["daily", "easy"],
  "price_usd": 164.95,
  "plate": "carbon",
  "drop_mm": 3.0,
  "weight_g": 286
}
```

| Field | Meaning |
| --- | --- |
| `brand` | Manufacturer |
| `model` | Model name |
| `category` | Use tags (daily, easy, race, tempo, trail, etc.) |
| `price_usd` | Price in USD |
| `plate` | `carbon`, `nylon`, or `none` (heuristic) |
| `drop_mm` | Heel-to-toe drop (mm) |
| `weight_g` | Weight in grams |

## CLI options

```text
python scrape_roadrunners_mens_running.py [OPTIONS]

  --url URL           Listing URL (default: men’s running)
  --size SIZE         Size to check, e.g. "10.5"
  --verify-size       Verify stock for that size (slower)
  --out FILE          Output JSON (default: catalog_roadrunner.json)
  --headful           Show the browser
  --max-products N    Cap number of product pages
  --pause SECONDS     Scroll pause (default: 0.6)
  --throttle SECONDS  Delay between products (default: 0.6)
  --retries N         Retries per failed page (default: 2)
```

## Examples

**Quick test**

```bash
python scrape_roadrunners_mens_running.py --max-products 10 --out test_run.json --throttle 1.0
```

**More conservative**

```bash
python scrape_roadrunners_mens_running.py --out production_catalog.json --throttle 1.2 --retries 3 --pause 0.8
```

**Debug in headed mode**

```bash
python scrape_roadrunners_mens_running.py --headful --max-products 3 --out debug_catalog.json
```

## Operations notes

- Expect roughly a few seconds per product with default throttling; site changes can break selectors.
- If ChromeDriver errors appear, `webdriver-manager` is a common fix (see script comments if present).
- Validate a new file before swapping production `catalog.json`:

```bash
python -c "import json; d=json.load(open('app/catalog.json')); print(len(d), d[0])"
```

## Legal and ethics

Scraping may be restricted by the site’s terms. Use polite delays, do not overload their servers, and prefer official APIs or data partnerships for production or commercial use.
