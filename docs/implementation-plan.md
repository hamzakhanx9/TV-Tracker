# FRAME implementation plan

## Stage 1 — Foundation

- [x] Establish the frontend, backend, database, and worker monorepo structure.
- [x] Add a responsive dark-mode application shell and navigation.
- [x] Add FastAPI health endpoints and database connectivity.
- [x] Add SQLAlchemy configuration, the initial user model, and Alembic migration.
- [x] Add Docker Compose services, persistent PostgreSQL storage, and health checks.
- [x] Document the architecture, database baseline, API baseline, and local setup.
- [ ] Run container builds and tests in an environment with Docker, Node.js, and Python installed.

## Current milestone: Stage 2 — External integrations and first library workflows

- [x] Add isolated TMDB and TVmaze clients with timeouts, retry/backoff, rate-limit
      handling, caching, and safe metadata synchronization.
- [x] Normalize movie/TV metadata and persist media and provider IDs.
- [x] Add media search and import endpoints and UI.
- [x] Add movie/TV library list, status update, and removal workflows.
- [x] Add a mixed movie/TV watchlist for titles marked "Plan to watch".
- [x] Open TV episode tracking in a dedicated, scrollable show dialog.
- [x] Add TMDB aggregate ratings, optional OMDb ratings, and SeriesGraph details panels.
- [x] Add provider and API tests using mocked responses.
- [x] Persist TVmaze episode metadata and synchronize it without overwriting watch history.
- [ ] Run tests and the Docker stack in an environment with dependencies installed.

## Stage 3 — Library

- [x] Add the initial user library and watch-status management.
- [x] Implement movie and TV library views.
- [x] Show TMDB, IMDb, and Rotten Tomatoes aggregate ratings when available.
- [x] Add expandable title details and SeriesGraph links for TV shows.
- [x] Add personal ratings, reviews, notes, and detailed media pages.
- [ ] Test uniqueness constraints and user-owned data on PostgreSQL.

## Stage 4 — Episode tracking

- [x] Add movie/episode watch events, idempotent watched toggles, and transactional season actions.
- [x] Calculate progress from watch events and reveal episode descriptions on demand.
- [x] Add explicit, idempotent rewatch history.
- [ ] Test duplicate prevention and episode/season progress.

## Stage 5 — Calendar

- [x] Expose stored release dates and timezone-aware date-range endpoints.
- [x] Add the calendar and release-detail UI.
- [ ] Run date-only, unknown, and timezone-sensitive release tests.

## Stage 6 — Catch-up and notifications

- [ ] Validate catch-up calculations and idempotent scheduled jobs.
- [ ] Validate deduplicated in-app notifications and clear actions.
- [ ] Validate notification preference workflows.
- [x] Browser push notifications are out of scope.

## Stage 7 — Recommendations and statistics

- [ ] Add explainable content-based recommendations.
- [ ] Add data-backed viewing statistics and charts.
- [ ] Test ranking, exclusions, and aggregates.

## Stage 8 — Production readiness

- [ ] Add authentication and authorization.
- [ ] Add end-to-end testing, accessibility checks, production configuration, and PWA support.
- [ ] Review operational security, performance, and backup/restore procedures.

Stages may be reordered to respect implementation dependencies. A checklist item
is complete only when its behavior is implemented and appropriately validated.
