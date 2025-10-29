# Lemi Backend (FastAPI)

FastAPI backend for Lemi. Includes password-auth endpoints, events, joined events, and search requests.

## Run locally (Docker)

- docker build -t lemi-backend -f Dockerfile .
- docker run -p 8000:8000 lemi-backend

Or via the project’s docker-compose at the root of the monorepo.

## Deploy to Render

Option A — Blueprint (this folder contains `render.yaml`)
1. Push this backend folder as its own GitHub repository (recommended name: `lemi-backend`).
2. In Render, New → Blueprint → select the repo. Render will read `render.yaml` and create a Web Service.
3. Set environment variables:
   - `PYTHONUNBUFFERED=1`
   - `FRONTEND_ORIGINS=https://YOUR_FRONTEND_DOMAIN`  (comma-separated supported)
4. Deploy. Health check path can be `/users`.

Option B — Manual Web Service with Docker
1. New → Web Service → Connect your repo.
2. Environment: Docker
3. Dockerfile path: `Dockerfile.render`
4. Env vars as above.
5. Deploy.

## Environment variables
- `FRONTEND_ORIGINS` — limits CORS to one or more frontend origins (comma-separated). If unset, defaults to `*` (dev).

## Endpoints
- `POST /register` — username + password (hash stored server-side)
- `POST /login` — verifies password (case-insensitive username)
- `GET /events` / `POST /events`
- `POST /join_event`
- `GET /user_joined_events/{user_id}`
- `POST /search_requests` / `GET /search_requests`
