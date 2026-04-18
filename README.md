# Running shoe recommendation agent

Small example app: rule-based shortlisting plus local LLM explanations via [Ollama](https://ollama.com).

## Quick start

### Python environment

```bash
cd running-shoe-agent
uv venv
# Windows PowerShell:
#   .\.venv\Scripts\Activate.ps1
# Windows cmd:
#   .venv\Scripts\activate.bat
# macOS/Linux:
#   source .venv/bin/activate
uv pip install -r requirements.txt
```

If `.venv` exists but `pip` is missing (some minimal venvs), run: `python -m ensurepip --upgrade`, then `pip install -r requirements.txt`.

**Run commands** only after activating `.venv`, or prefix with the venv’s `python` / `uv run`.

**Start the API** (from the project root, with `.venv` active):

```bash
python -m uvicorn app.main:app --reload --port 8000
```

More detail: [SETUP_UV.md](SETUP_UV.md).

### Ollama

```bash
ollama pull llama3.1
# ollama serve  # if needed; often already running on localhost:11434
```

### API

```bash
cp env.example .env
# Optional: set OLLAMA_MODEL, OLLAMA_HOST, PORT
python -m uvicorn app.main:app --reload --port 8000
```

### Try the API

```bash
curl -s -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_preferences": ["Saucony","Adidas"],
    "intended_use": {"easy_runs": true, "tempo_runs": true, "races": ["half_marathon"], "trail": false},
    "cost_limiter": {"enabled": true, "max_usd": 180}
  }'
```

## Models

Set `OLLAMA_MODEL` in `.env`, run `ollama pull <name>`, then restart the API.

## Web UI (optional)

```bash
# Terminal 1: API (see above)
# Terminal 2:
./start_flask.sh
# or: python flask_app.py
```

Open [http://localhost:3000](http://localhost:3000). Flask setup: [FLASK_README.md](FLASK_README.md).

## Layout

```text
running-shoe-agent/
├── README.md
├── env.example
├── pyproject.toml
├── requirements.txt
├── flask_app.py
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── catalog.json
│   ├── recommender.py
│   ├── enhanced_recommender.py
│   ├── llm.py
│   └── prompts/
├── static/css/
│   └── app.css
├── templates/
│   ├── index.html
│   └── results.html
├── tests/
└── scrape_roadrunners_mens_running.py   # see SCRAPER_README.md
```

## Requirements

- Python 3.11+
- Ollama (for LLM text)
