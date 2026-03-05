# Async Document Processing Platform

Production-oriented document processing platform with asynchronous workers, JWT auth, searchable processed content, and Dockerized deployment.

## Tech Stack
- Frontend: React (Vite, responsive UI)
- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Queue/Broker/Cache: Redis
- Async workers: Celery
- API docs: OpenAPI/Swagger (`drf-spectacular`)
- Containerization: Docker + Docker Compose

## Architecture
```mermaid
flowchart LR
    U[User / React Frontend] -->|JWT + REST| API[Django API]
    API -->|Store metadata| PG[(PostgreSQL)]
    API -->|Upload file metadata + task enqueue| RQ[(Redis)]
    API -->|Save files| FS[(Shared Media Volume)]
    CW[Celery Worker] -->|Consume tasks| RQ
    CW -->|Read uploaded files| FS
    CW -->|Extract text + summarize| PG
    API -->|Search processed docs| PG
    API -->|Cache search responses| RQ
```

## Project Structure
```text
async-document-processing-platform/
  backend/
    apps/
      users/         # Custom user model + auth endpoints
      documents/     # Upload/list/detail APIs + document model
      processing/    # Task model + Celery processing task + status API
      search/        # Search API + cache-backed search service
    services/
      extraction.py  # PDF/DOCX text extraction
      summary.py     # Summary generation logic
    config/          # Django settings, URLs, Celery bootstrap
  frontend/
    src/             # Responsive React client for auth/upload/search/status
  docker-compose.yml
  README.md
```

## Features Implemented
- Upload API for `PDF` and `DOCX`
- Background processing with Celery worker
- Text extraction services
- Automatic summary generation
- Metadata persistence in PostgreSQL
- Redis broker and Redis cache-backed search responses
- Task status endpoint
- Search endpoint over processed documents
- JWT authentication (register + token issue/refresh)
- Swagger UI and OpenAPI schema
- Unit tests for auth, upload flow, processing, and search

## API Endpoints
- `POST /api/auth/register/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `GET /api/auth/me/`
- `POST /api/documents/upload/`
- `GET /api/documents/`
- `GET /api/documents/{id}/`
- `GET /api/processing/tasks/{id}/`
- `GET /api/search/documents/?q=<term>`
- `GET /api/schema/`
- `GET /api/docs/`

## Environment Setup
1. Copy `.env.example` to `.env`.
2. Set a secure `DJANGO_SECRET_KEY`.
3. Choose database source:
   - Local compose PostgreSQL (default in `.env.example`) or
   - Neon/PostgreSQL cloud URI.

Neon DB URI provided:
```bash
postgresql://neondb_owner:npg_PcKIg7hQFi9B@ep-autumn-lab-a805z0mz-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require
```
If using Neon, uncomment/update `DATABASE_URL` in `.env` and optionally set `DB_SSL_REQUIRE=True`.

## Run With Docker Compose
```bash
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/api/docs/`
- Frontend: `http://localhost:3000`

## Run Backend Locally (without Docker)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Start worker separately:
```bash
cd backend
celery -A config worker --loglevel=INFO
```

## Test Suite
```bash
cd backend
python manage.py test
```

## Notes
- Files are stored in Django `MEDIA_ROOT` and shared with worker through Docker volume.
- Search is scoped to the authenticated user’s processed documents.
- Search responses are cached (`SEARCH_CACHE_TIMEOUT`).
