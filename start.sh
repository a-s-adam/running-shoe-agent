#!/bin/bash
# Quick start script for Running Shoe Recommendation Agent

echo "🏃‍♂️ Starting Running Shoe Recommendation Agent..."
echo ""

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from env.example..."
    cp env.example .env
    echo "✅ .env created. Edit OLLAMA_MODEL if needed."
    echo ""
fi

# Check if Ollama is running
echo "🔍 Checking Ollama status..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running on localhost:11434"
else
    echo "⚠️  Ollama not running. Please start it first:"
    echo "   ollama serve"
    echo ""
fi

echo ""
echo "🚀 Starting API server..."
echo "   API will be available at: http://localhost:8000"
echo "   Health check: http://localhost:8000/"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the API
uvicorn app.main:app --reload --port 8000
