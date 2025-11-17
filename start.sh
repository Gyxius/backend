#!/bin/bash
# Startup script that runs migration before starting the server

echo "🚀 Running database migrations..."
python migrate_add_is_featured.py || echo "⚠️  Migration failed or already applied - continuing anyway"
python migrate_add_is_archived.py || echo "⚠️  Migration failed or already applied - continuing anyway"

echo "🌟 Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
# Force rebuild
