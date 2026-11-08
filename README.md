# FRAME

FRAME is a personal TV and movie tracker. This repository is being built in
stages; the current milestone is **Stage 2: Search and library workflows**.

## Current foundation

- Next.js App Router frontend with a responsive dark application shell.
- FastAPI backend with liveness and database-readiness checks.
- PostgreSQL 16 with a persistent Docker volume.
- SQLAlchemy 2.x, Alembic, and migrations for users, normalized media, provider
  IDs, and a personal library.
- TMDB search/import and TVmaze title matching for imported TV shows.
- TMDB ratings, optional OMDb IMDb/Rotten Tomatoes scores, and expandable title
  details with a SeriesGraph panel for TV shows.
- Movie and TV libraries with watch-status updates and removal.
- Separate APScheduler worker process.
- Docker Compose health checks and dependency ordering.

Episode tracking, personal ratings/reviews, calendar, notifications,
recommendations, and statistics are planned but are not implemented yet.

## Run locally with Docker

1. Copy `.env.example` to `.env`. If changing the database password, update it
   in both `POSTGRES_PASSWORD` and `DATABASE_URL`.
2. Set `TMDB_READ_ACCESS_TOKEN` to a TMDB API Read Access Token. The token stays
   in the backend environment and is never sent to the browser. Search and
   import return a clear service-unavailable error if it is not configured.
3. Optionally set `OMDB_API_KEY` to show IMDb and Rotten Tomatoes scores.
   TMDB ratings are available without this key.
4. Start the stack:

   ```sh
   docker compose up --build
   ```

5. Open:
   - Frontend: <http://localhost:3000>
   - API health: <http://localhost:8000/health/ready>
   - OpenAPI docs: <http://localhost:8000/docs>

   Search titles at **Discover**, click a result to expand its details and
   ratings, and add it to your library. Click library posters to expand details;
   TV show details include a link to open the show on SeriesGraph.

The first backend startup applies Alembic migrations before serving requests.
PostgreSQL data persists in the `postgres_data` named volume.
Compose configures the frontend to reach the backend over the internal service
network; when running the frontend outside Compose, set
`FRONTEND_API_URL=http://localhost:8000`.

## Development

Frontend source is in `frontend/`; backend source and tests are in `backend/`.
The development stack runs the Next.js dev server and FastAPI with auto-generated
OpenAPI documentation. Backend tests can be run in the backend environment with:

```sh
pytest
```

Never put provider credentials in frontend variables or commit a real `.env`
file.

## Database backup and restore

Create a compressed backup:

```sh
docker compose exec -T db pg_dump -U frame -d frame -Fc > frame.dump
```

Restore into the running database (this replaces objects in the target database):

```sh
docker compose exec -T db pg_restore -U frame -d frame --clean --if-exists < frame.dump
```

## Project documentation

- [Implementation plan](docs/implementation-plan.md)
- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [API](docs/api.md)
