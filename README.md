# Running Shoe Recommendation Agent

A minimal, beginner-friendly repository demonstrating basic LLM usage for running shoe recommendations using Ollama (local).

## Quick Start

### 0. Setup Python Environment
```bash
# Using uv (recommended - faster)
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt

# Or traditional pip
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Detailed setup instructions: [SETUP_UV.md](SETUP_UV.md)**

### 1. Install & Run Ollama

```bash
# macOS / Linux: https://ollama.com/download
ollama pull llama3.1
ollama serve   # usually auto-starts; ensures localhost:11434
```

### 2. Run the API

```bash
cp .env.example .env
# optionally edit OLLAMA_MODEL in .env
# To enable web-enriched analysis, set FIRECRAWL_API_KEY in .env
uvicorn app.main:app --reload --port ${PORT:-8000}
```

### 3. Try It

```bash
curl -s -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_preferences": ["Saucony","Adidas"],
    "intended_use": {"easy_runs": true, "tempo_runs": true, "races": ["half_marathon"], "trail": false},
    "cost_limiter": {"enabled": true, "max_usd": 180}
  }' | jq
```

## Swap Models

Change `OLLAMA_MODEL` in your `.env` file (e.g., `phi3`, `qwen2.5:7b-instruct`, `mistral`), then:

```bash
ollama pull <model>
```

## Web Interface (Optional)

Instead of curl commands, use the beautiful Flask web interface:

```bash
# Terminal 1: Start the API backend
./start.sh

# Terminal 2: Start the Flask frontend  
./start_flask.sh

# Open browser to: http://localhost:3000
```

**Detailed Flask setup: [FLASK_README.md](FLASK_README.md)**

## Project Structure

```
running-shoe-agent/
|-- README.md
|-- env.example
|-- pyproject.toml
|-- requirements.txt
|-- start.sh
|-- start_flask.sh
|-- app/
|   |-- main.py
|   |-- schemas.py
|   |-- catalog.json
|   |-- catalog_repository.py
|   |-- recommender.py
|   `-- prompts/
|-- web/
|   |-- app.py
|   `-- templates/
`-- tests/
```

## Features

- **Local LLM**: Uses Ollama via `http://localhost:11434`
- **Smart Filtering**: Brand preferences, intended use, and budget constraints
- **LLM Explanations**: AI-generated justifications for each recommendation
- **Web Enrichment (Firecrawl)**: When `FIRECRAWL_API_KEY` is set, the model will crawl reviews and product pages for each shoe and incorporate findings into the analysis
- **Catalog Database**: Use JSON, local SQLite, or Supabase Free for stored shoe data
- **Catalog Website**: Browse stored shoes, specs, source links, and compressed thumbnails at `/catalog`
- **Third-Party Scrapers**: Pull catalog snapshots from retailer sources such as REI, Road Runner Sports, Sports Basement, and A Runner's Mind
- **Simple Scoring**: Rule-based ranking with configurable weights
- **FastAPI**: Clean REST API with automatic validation
- **Web Interface**: Beautiful Flask frontend (optional) for easy form input

## Requirements

- Python 3.11+
- Ollama running locally
- (Optional) Firecrawl API key for web enrichment
- ~300 LOC (excluding catalog and tests)

## Firecrawl Setup (Optional)

To incorporate live web context in the AI explanations:

- Get an API key from Firecrawl
- Set `FIRECRAWL_API_KEY` in `.env`

The enhanced analyzer will search for <brand> <model> running shoe review 2024, extract brief context from top sources, and include summaries + source links in the prompt it sends to the LLM.

## Catalog Database and Scrapers

The default catalog still comes from `app/catalog.json`. To use a free database backend:

```bash
# Local zero-cost database
SHOE_CATALOG_BACKEND=sqlite python -m app.catalog_repository init --backend sqlite
SHOE_CATALOG_BACKEND=sqlite python -m app.catalog_repository seed --backend sqlite --from-json app/catalog.json
```

For hosted storage, create a Supabase Free project, run `db/supabase_schema.sql`, then set `SHOE_CATALOG_BACKEND=supabase`, `SUPABASE_URL`, and your Supabase API keys in `.env`.

Third-party scraper examples:

```bash
python scrape_third_party_running.py --list-sources
python scrape_third_party_running.py --source rei_mens_road --max-products 10 --out rei_catalog.json
SHOE_CATALOG_BACKEND=sqlite python scrape_third_party_running.py --source all --store --compress-images
```

See [DATABASE_README.md](DATABASE_README.md) for the full setup.
