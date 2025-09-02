#!/bin/bash
# Start script for Flask Web Interface

echo "🌐 Starting Flask Web Interface for Running Shoe Recommendations..."
echo ""

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from env.example..."
    cp env.example .env
    echo "✅ .env created. Edit OLLAMA_MODEL if needed."
    echo ""
fi

# Check if the recommendation API is running
echo "🔍 Checking if recommendation API is running..."
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Recommendation API is running on localhost:8000"
else
    echo "⚠️  Recommendation API not running on localhost:8000"
    echo "   Please start it first with: uvicorn app.main:app --reload --port 8000"
    echo "   Or use: ./start.sh"
    echo ""
fi

echo ""
echo "🚀 Starting Flask web interface..."
echo "   Web interface will be available at: http://localhost:3000"
echo "   Make sure the recommendation API is running on: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start Flask app
python flask_app.py
