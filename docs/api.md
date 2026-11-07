# API

## Current endpoints

The API is versioned under `/api/v1` for product endpoints. Operational health
endpoints are intentionally outside that prefix:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness; does not depend on PostgreSQL. |
| `GET` | `/health/ready` | Readiness check including a database query. |

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

The frontend reads the backend readiness endpoint using the server-only
`FRONTEND_API_URL` environment setting. Provider credentials and other secrets
must remain backend-only.

As product endpoints are added, their response schemas and corresponding
frontend types/tests should be updated together.
