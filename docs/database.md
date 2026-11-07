# Database

## Current schema

PostgreSQL is the persistence layer. SQLAlchemy 2.x models live under
`backend/app/models/`, and all schema changes are managed with Alembic.

The initial migration creates `users`, with:

- UUID primary key.
- Unique, indexed email address.
- UTC-aware creation and update timestamps.

The initial user table is an architectural foundation. Authentication and
additional user profile fields are not implemented in Stage 1.

## Planned domain tables

The schema will grow incrementally to include normalized media, provider
identifiers, genres, TV show details, seasons, episodes, user library entries,
watch events, ratings, reviews, streaming providers, notifications, user
preferences, push subscriptions, sync jobs, and recommendation runs/reasons.
Constraints and indexes will enforce ownership, provider-ID uniqueness, one
library entry per user/title, and valid watch-event targets.

## Data conventions

- Persist timestamps in UTC using timezone-aware database columns.
- Store provider identifiers separately from internal UUIDs.
- Keep personal library/watch/rating/review data separate from synchronized
  provider metadata.
- Preserve known-good metadata when provider synchronization fails.
- Treat watch events as the source of truth for viewing history and progress.

## Local operations

Compose persists the database in the `postgres_data` volume. Backup and restore
commands are documented in the root README. Destructive restore operations
should only target a database whose contents may be replaced.
