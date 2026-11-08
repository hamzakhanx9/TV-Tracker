# Database

## Current schema

PostgreSQL is the persistence layer. SQLAlchemy 2.x models live under
`backend/app/models/`, and all schema changes are managed with Alembic.

The migrations create `users`, `media`, `media_external_ids`, `user_library`,
`seasons`, `episodes`, `watch_events`, `notification_preferences`, and
`notifications`.

The `users` table has:

- UUID primary key.
- Unique, indexed email address.
- UTC-aware creation and update timestamps.

The `media` table holds normalized title metadata and distinguishes movies from
TV. `media_external_ids` stores provider IDs with a unique provider/ID constraint.
`user_library` links a user and media title once, with a constrained watch
status, personal timestamps/notes, a personal rating, and a review. A local
development user is created on the first import using `DEFAULT_USER_EMAIL`.

`seasons` and `episodes` store TVmaze episode metadata. `watch_events` stores
the viewing history for a movie or an individual episode and enforces exactly
one target per event. A partial unique index allows only one current event for
each user's movie or episode. Rewatch request keys are unique per user, making
retries idempotent. Episode progress is derived from the current watch event;
synchronization does not remove existing history.

`notification_preferences` stores the episode-alert toggle and an IANA
timezone. `notifications` stores in-app episode announcements/releases with a
per-user deduplication key, optional media/episode targets, and a read
timestamp; `cleared_at` records user dismissals so jobs do not re-create them.
Notifications are generated only for shows marked `WATCHING`;
browser push subscriptions are intentionally out of scope.

The ratings migration adds cached TMDB score/vote count, IMDb score, and Rotten
Tomatoes percentage to `media`. Provider ratings are metadata; personal ratings
remain a separate feature.

Authentication is not implemented. Do not expose this unauthenticated
development deployment to untrusted networks.

## Planned domain tables

The schema may grow incrementally to include genres, TV show details, streaming
providers, push subscriptions, sync jobs, and recommendation runs/reasons.
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
