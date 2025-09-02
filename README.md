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

**📖 Detailed setup instructions: [SETUP_UV.md](SETUP_UV.md)**

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

## 🌐 Web Interface (Optional)

Instead of curl commands, use the beautiful Flask web interface:

```bash
# Terminal 1: Start the API backend
./start.sh

# Terminal 2: Start the Flask frontend  
./start_flask.sh

# Open browser to: http://localhost:3000
```

**📖 Detailed Flask setup: [FLASK_README.md](FLASK_README.md)**

## Project Structure

```
running-shoe-agent/
├── README.md
├── .env.example
├── pyproject.toml
├── requirements.txt
├── start.sh                 # API startup script
├── start_flask.sh           # Flask startup script
├── flask_app.py             # Flask web interface
├── FLASK_README.md          # Flask setup guide
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── catalog.json
│   ├── recommender.py
│   ├── llm.py              # Ollama chat wrapper
│   └── prompts/
│       ├── system.txt
│       └── user_template.txt
├── templates/               # Flask HTML templates
│   ├── index.html          # Main form page
│   └── results.html        # Results display page
└── tests/
    ├── test_recommender.py
    └── test_api.py
```

## Features

- **Local LLM**: Uses Ollama via `http://localhost:11434`
- **Smart Filtering**: Brand preferences, intended use, and budget constraints
- **LLM Explanations**: AI-generated justifications for each recommendation
- **Simple Scoring**: Rule-based ranking with configurable weights
- **FastAPI**: Clean REST API with automatic validation
- **Web Interface**: Beautiful Flask frontend (optional) for easy form input

## Requirements

- Python 3.11+
- Ollama running locally
- ~300 LOC (excluding catalog and tests)
