# Flask web UI

HTML form and results pages that call the FastAPI `/recommend` endpoint so you do not need raw JSON or curl.

## Run

Activate this repo’s **`.venv`** first (see [README.md](README.md) or [SETUP_UV.md](SETUP_UV.md)). Do not use unrelated Conda envs unless you have installed `requirements.txt` into them.

```bash
# Terminal 1 — API (from project root, .venv active)
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Flask (same .venv)
python web/app.py
# or: ./start_flask.sh
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

| Variable | Purpose |
| --- | --- |
| `RECOMMEND_API_URL` | FastAPI base URL (default `http://localhost:8000`) |
| `FLASK_PORT` | Port for the UI (default `3000`) |
| `FLASK_SECRET_KEY` | Flask session secret (set in any shared deployment) |

Ollama settings (`OLLAMA_HOST`, `OLLAMA_MODEL`) are read by the **API**, not Flask.

## Flow

```text
Browser  →  Flask (port 3000)  →  FastAPI (port 8000)  →  Ollama (11434)
```

## Customization

- Form options: `RACE_DISTANCES`, `CATEGORIES`, and brand list from `app/catalog.json` in `web/app.py`.
- Styling: `static/css/app.css` (shared by `templates/index.html` and `templates/results.html`).

## Troubleshooting

- **Cannot connect to API** — Ensure FastAPI is up: `curl http://localhost:8000/`
- **Port in use** — Set `FLASK_PORT` or change `DEFAULT_PORT` in `web/app.py`.

## Production notes

Use a real `FLASK_SECRET_KEY`, HTTPS, and a production WSGI server (e.g. gunicorn) instead of `app.run(debug=True)`.
