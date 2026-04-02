#!/bin/bash

echo "================================================================================"
echo "Starting Image Processing Agent Server"
echo "================================================================================"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    echo ""
    exit 1
fi

# Start server
echo "Starting server on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
