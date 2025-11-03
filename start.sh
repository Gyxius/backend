#!/bin/bash
# Startup script that runs migration before starting the server

echo "🚀 Running database migrations..."
python migrate_add_is_featured.py

echo "🌟 Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000
