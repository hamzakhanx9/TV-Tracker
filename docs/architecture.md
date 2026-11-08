# Architecture

## Current structure

FRAME is a modular monolith with deployable frontend, API, database, and worker
processes:

- `frontend/`: Next.js App Router application.
- `backend/app/api/`: FastAPI endpoints.
- `backend/app/models/` and `backend/app/db/`: SQLAlchemy models and database setup.
- `backend/alembic/`: versioned schema migrations.
- `backend/app/worker.py`: separate APScheduler process.
- `docker-compose.yml`: local development orchestration.

The frontend talks to the backend over HTTP. The API owns validation, business
logic, and persistence. PostgreSQL is the source of truth for user-owned data.
The worker is a separate process so scheduled work can evolve independently of
API request handling without introducing a microservice architecture.
It runs idempotent notification generation against persisted movie and episode
release data every 15 minutes.

## Boundaries and future integrations

External providers will be accessed only through backend integration clients.
Provider IDs and normalized internal records will be separate, so metadata
providers can be changed without coupling the UI or domain model to one API.
Synchronization must preserve user-owned state and last-known valid metadata.
Search and import currently use TMDB; TVmaze is queried during TV imports and
only linked when title and premiere year match. TMDB vote averages are included
in search and library data. The optional OMDb client uses the TMDB-provided IMDb
ID to retrieve IMDb and Rotten Tomatoes scores when configured. TV details link
to the corresponding SeriesGraph show page in a new browser tab.

The initial app is suitable for local development and does not implement
authentication. User records and user-scoped domain tables provide a foundation
for future authentication; production deployment must not expose personal data
without adding and testing that layer.

## Runtime and configuration

Docker Compose starts PostgreSQL, the API, the worker, and the frontend. The API
waits for database health and applies Alembic migrations before startup. The
frontend and worker wait for API readiness. Configuration is environment-based;
`.env.example` contains local development defaults, not production credentials.

The API exposes `/health/live` for process liveness and `/health/ready` for
database-backed readiness. OpenAPI is available at `/docs`.

## Planned quality attributes

- UTC timestamps for persisted event data; user timezone applied at presentation
  and calendar boundaries.
- Explicit provider timeouts, retries, rate-limit handling, and safe cache policy.
- Idempotent background jobs and uniqueness constraints for duplicate prevention.
- Request/response schemas and tests at API boundaries.
- No provider secrets in browser code.
