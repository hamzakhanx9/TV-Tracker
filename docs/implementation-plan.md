# FRAME implementation plan

## Current milestone: Stage 1 — Foundation

- [x] Establish the frontend, backend, database, and worker monorepo structure.
- [x] Add a responsive dark-mode application shell and navigation.
- [x] Add FastAPI health endpoints and database connectivity.
- [x] Add SQLAlchemy configuration, the initial user model, and Alembic migration.
- [x] Add Docker Compose services, persistent PostgreSQL storage, and health checks.
- [x] Document the architecture, database baseline, API baseline, and local setup.
- [ ] Run container builds and tests in an environment with Docker, Node.js, and Python installed.

## Stage 2 — External integrations

- [ ] Add isolated TMDB and TVmaze clients with timeouts, retry/backoff, rate-limit
      handling, caching, and safe metadata synchronization.
- [ ] Normalize provider metadata and persist external IDs, media, seasons, and episodes.
- [ ] Add media search and import endpoints and UI.
- [ ] Add integration tests using mocked provider responses.

## Stage 3 — Library

- [ ] Add user library, status management, ratings, reviews, and notes.
- [ ] Implement movie and TV library views and media detail pages.
- [ ] Test imports, uniqueness constraints, and user-owned data.

## Stage 4 — Episode tracking

- [ ] Add episode-level watch events and transactional season actions.
- [ ] Add progress calculations, rewatches, and spoiler-protected episode details.
- [ ] Test duplicate prevention and episode/season progress.

## Stage 5 — Calendar

- [ ] Synchronize release dates and expose timezone-aware date-range endpoints.
- [ ] Add the calendar and release-detail UI.
- [ ] Test date-only, unknown, and timezone-sensitive release handling.

## Stage 6 — Catch-up and notifications

- [ ] Add catch-up calculations and idempotent scheduled jobs.
- [ ] Generate deduplicated in-app notifications from persisted synchronized data.
- [ ] Add notification preferences and browser push support.

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
