#!/bin/bash

# Hooker Start Script
# Usage: ./start.sh [docker|local]

MODE=${1:-local}

if [ "$MODE" == "docker" ]; then
    echo "🐳 Starting Hooker in Docker..."
    if ! command -v docker &> /dev/null; then
        echo "Error: docker could not be found."
        exit 1
    fi
    docker-compose up --build -d
    echo "✅ Hooker is running at http://localhost:8000/static/index.html"
else
    echo "🐍 Starting Hooker locally..."
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Run migration check
    python3 migrate.py
    
    echo "✅ Starting server..."
    uvicorn backend:app --host 0.0.0.0 --port 8000
fi
