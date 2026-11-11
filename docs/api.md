# API

## Current endpoints

The API is versioned under `/api/v1` for product endpoints. Operational health
endpoints are intentionally outside that prefix:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness; does not depend on PostgreSQL. |
| `GET` | `/health/ready` | Readiness check including a database query. |
| `GET` | `/api/v1/media/search?q=...` | Search TMDB; optional `media_type=MOVIE\|TV`. |
| `POST` | `/api/v1/media/import` | Import a TMDB movie/show into the local library. |
| `GET` | `/api/v1/library` | List titles; optional `media_type=MOVIE\|TV`. |
| `GET` | `/api/v1/library/{media_id}` | Get a library title and its personal feedback. |
| `PATCH` | `/api/v1/library/{media_id}/feedback` | Save or clear a personal rating, review, or notes. |
| `GET` | `/api/v1/media/{media_type}/{external_id}/ratings` | Load provider ratings for a search result. |
| `GET` | `/api/v1/library/{media_id}/ratings` | Refresh ratings for a library title. |
| `PATCH` | `/api/v1/library/{media_id}` | Change a title's watch status. |
| `PUT` | `/api/v1/library/{media_id}/watched` | Mark a movie watched or unwatched. |
| `POST` | `/api/v1/library/{media_id}/rewatch` | Record a movie rewatch with an idempotency key. |
| `GET` | `/api/v1/library/{media_id}/episodes` | Read TV episode and watch progress. |
| `POST` | `/api/v1/library/{media_id}/episodes/sync` | Sync a TV episode list from TVmaze or TMDB. |
| `GET` | `/api/v1/calendar?start=...&end=...&timezone=...` | List library movie releases and episode airings in an inclusive date range and IANA timezone. |
| `GET` | `/api/v1/catch-up?timezone=...` | List aired, unwatched episodes by show for titles marked "Watching". |
| `GET` | `/api/v1/notifications?limit=...` | List in-app episode announcements and release notifications. |
| `PUT` | `/api/v1/notifications/{notification_id}/read` | Mark one notification as read. |
| `DELETE` | `/api/v1/notifications/{notification_id}` | Clear one notification without allowing it to be regenerated. |
| `DELETE` | `/api/v1/notifications` | Clear all notifications for the local user; returns `cleared_count`. |
| `GET` | `/api/v1/notification-preferences` | Read episode notification settings and timezone. |
| `PATCH` | `/api/v1/notification-preferences` | Update notification preferences. |
| `PUT` | `/api/v1/episodes/{episode_id}/watched` | Mark one TV episode watched or unwatched. |
| `POST` | `/api/v1/episodes/{episode_id}/rewatch` | Record an episode rewatch with an idempotency key. |
| `PUT` | `/api/v1/seasons/{season_id}/watched` | Mark aired episodes in a season watched or mark the season unwatched. |
| `DELETE` | `/api/v1/library/{media_id}` | Remove the user-library entry. |

Interactive OpenAPI documentation is available at `/docs` and the schema at
`/openapi.json`.

## API conventions

FastAPI/Pydantic define and validate request and response contracts. Product
routers will be grouped by domain under `/api/v1` (media, library, episodes,
watch history, calendar, notifications, recommendations, ratings, reviews,
statistics, and settings). List endpoints will use explicit pagination and
filters. Errors should use appropriate HTTP status codes and must not expose
credentials or internal database details.

## Initial browser integration

The frontend proxies `/api/v1/*` through Next.js to the backend using the
server-only `FRONTEND_API_URL` setting. `TMDB_READ_ACCESS_TOKEN` is backend-only.
TV imports use TVmaze exact-title/year matching to add a secondary provider ID;
missing matches do not prevent import. TMDB vote averages are always returned.
When `OMDB_API_KEY` is configured, the backend looks up IMDb and Rotten
Tomatoes scores by TMDB's IMDb identifier. That key is optional and backend-only.

Episode lists are synchronized from TVmaze when it has data, with TMDB as a
fallback for shows TVmaze does not match or does not list episodes for. Repeated
syncs update provider metadata without deleting existing watch events. Movie
and episode watched updates are idempotent; rewatch calls
require a client-generated UUID `idempotency_key`. Watch and unwatch actions
append events, preserving viewing history. Bulk season watch actions include
only episodes with a known air date/time that has passed when marking watched;
mark-unwatched applies to watched episodes in that season. Individual episodes
with unknown or future dates can still be marked manually. Episode progress is
computed from each title's current watch event.

Library entries include `last_watched_at`, using the latest currently watched
episode for shows and the current movie watch event for films. Marking a show
`COMPLETED` marks all its synchronized episodes watched. Episode watch requests
may include `include_previous: true` to mark unwatched episodes up to and
including the selected episode, ordered across seasons.
Marking a season watched also marks all episodes from earlier seasons; future
episodes in the selected season remain unwatched.

The calendar uses movie release dates and stored TV episode air dates/timestamps
for titles in the local library. `start` and `end` are inclusive ISO dates;
`timezone` is an IANA timezone (defaults to `UTC`). Timed episode airings are
converted to that timezone before date-range filtering, while date-only events
remain all-day events.

Catch-up progress includes past episodes with known air dates/times that are not
currently marked watched, for shows whose library status is `WATCHING`. The
background worker checks persisted library and episode data every 15 minutes.
Episode announcements and recently aired episodes for shows marked `WATCHING`
are stored in-app and deduplicated per user and episode. Clearing notifications
persists a dismissal timestamp, so a later background run does not recreate
them. Notification settings control the episode alerts and the timezone used
to display release dates.
Browser push notifications are intentionally out of scope.

Personal ratings use a 1–10 scale. The feedback endpoint accepts partial
updates; send `null` to clear a rating, review, or note.

As product endpoints are added, their response schemas and corresponding
frontend types/tests should be updated together.
