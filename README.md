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

### Optional: Persistent image storage (S3/R2/B2)
Event images saved to the container filesystem (`./static/uploads`) are ephemeral on many hosts (e.g., Render) and will disappear on restarts/redeploys. To persist uploads, configure S3-compatible storage:

#### **Free option: Cloudflare R2** (recommended)
- 10 GB free, no egress fees
- Set these env vars on Render:
  ```
  S3_BUCKET=your-bucket-name
  S3_REGION=auto
  S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
  S3_PUBLIC_URL=https://pub-xxxxx.r2.dev  (enable R2.dev subdomain in bucket settings)
  AWS_ACCESS_KEY_ID=<your-r2-access-key>
  AWS_SECRET_ACCESS_KEY=<your-r2-secret>
  ```
- Get credentials from Cloudflare dashboard → R2 → Manage R2 API Tokens

#### AWS S3 (standard)
- `S3_BUCKET` — your bucket name
- `S3_REGION` — region like `eu-west-1`
- `S3_PREFIX` — object key prefix, default `uploads/`
- AWS credentials via `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

#### Backblaze B2 or other S3-compatible
- Set `S3_ENDPOINT_URL` to provider's endpoint
- Use provider's access keys for `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`

When `S3_BUCKET` is set, `/api/upload-image` uploads to the configured storage and returns a public URL. If S3/R2 is not configured or fails, the server falls back to `./static/uploads` (ephemeral).

## Endpoints
- `POST /register` — username + password (hash stored server-side)
- `POST /login` — verifies password (case-insensitive username)
- `GET /events` / `POST /events`
- `POST /join_event`
- `GET /user_joined_events/{user_id}`
- `POST /search_requests` / `GET /search_requests`
- `POST /api/upload-image` — upload an image; with S3 configured returns a public S3 URL; otherwise serves from `/static/uploads/*`.
