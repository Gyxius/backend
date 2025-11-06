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

### Optional: Persistent image storage (S3)
Event images saved to the container filesystem (`./static/uploads`) are ephemeral on many hosts (e.g., Render) and will disappear on restarts/redeploys. To persist uploads, configure S3:

- `S3_BUCKET` — your bucket name (enables S3 path)
- `S3_REGION` — region like `eu-west-1` (optional but recommended)
- `S3_PREFIX` — object key prefix, default `uploads/`
- AWS credentials — provide via environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_SESSION_TOKEN`) or an attached role.

When `S3_BUCKET` is set, `/api/upload-image` uploads directly to S3 with `public-read` ACL and returns a public URL. If S3 is not configured or fails, the server falls back to saving under `./static/uploads` and returns an absolute URL under `/static/uploads/*`.

## Endpoints
- `POST /register` — username + password (hash stored server-side)
- `POST /login` — verifies password (case-insensitive username)
- `GET /events` / `POST /events`
- `POST /join_event`
- `GET /user_joined_events/{user_id}`
- `POST /search_requests` / `GET /search_requests`
- `POST /api/upload-image` — upload an image; with S3 configured returns a public S3 URL; otherwise serves from `/static/uploads/*`.
