# Setting up Python Environment with `uv`

This guide shows how to set up and run the Running Shoe Recommendation Agent using `uv`, a fast Python package installer and resolver.

## What is `uv`?

`uv` is a modern Python toolchain that's significantly faster than pip and provides better dependency resolution. It's a great alternative to pip, pipenv, and poetry.

## Installation

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Alternative: pip
```bash
pip install uv
```

## Project Setup

### 1. Navigate to Project Directory
```bash
cd running-shoe-agent
```

### 2. Create Virtual Environment
```bash
uv venv
```

### 3. Activate Virtual Environment

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### 4. Install Dependencies
```bash
uv pip install -r requirements.txt
```

### 5. Install Development Dependencies (Optional)
```bash
uv pip install -e .
```

## Running the Application

### 1. Set up Environment Variables
```bash
cp env.example .env
# Edit .env if needed (e.g., change OLLAMA_MODEL)
```

### 2. Start Ollama (if not already running)
```bash
ollama serve
```

### 3. Run the API
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Test the API
```bash
python demo.py
```

## Alternative: Using `uv run`

You can also run commands directly without activating the virtual environment:

```bash
# Run the API
uv run uvicorn app.main:app --reload --port 8000

# Run tests
uv run pytest tests/ -v

# Run demo
uv run python demo.py
```

## Development Workflow

### Adding New Dependencies
```bash
uv add package-name
uv add --dev package-name  # for dev dependencies
```

### Updating Dependencies
```bash
uv pip install --upgrade -r requirements.txt
```

### Running Tests
```bash
uv run pytest tests/ -v
uv run pytest tests/ --cov=app  # with coverage
```

## Troubleshooting

### Virtual Environment Issues
If you encounter activation problems:
```bash
# Remove and recreate
rm -rf .venv
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt
```

### Port Already in Use
If port 8000 is busy:
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

### Ollama Connection Issues
Make sure Ollama is running:
```bash
# Check status
curl http://localhost:11434/api/tags

# Start if needed
ollama serve
```

## Why `uv`?

- **Speed**: 10-100x faster than pip
- **Reliability**: Better dependency resolution
- **Simplicity**: Single tool for venv + package management
- **Compatibility**: Works with existing requirements.txt and pyproject.toml
- **Modern**: Built with Rust for performance

## Alternative Setup Methods

If you prefer traditional tools:

### pip + venv
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### pipenv
```bash
pipenv install
pipenv run uvicorn app.main:app --reload
```

### poetry
```bash
poetry install
poetry run uvicorn app.main:app --reload
```
