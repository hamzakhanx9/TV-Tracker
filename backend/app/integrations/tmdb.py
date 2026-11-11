from datetime import date
from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.errors import ProviderError
from app.integrations.http import get_json

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"


class TmdbClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._token = token if token is not None else get_settings().tmdb_read_access_token
        self._transport = transport

    def search(self, query: str, media_type: str | None = None) -> list[dict[str, Any]]:
        if not self._token:
            raise ProviderError(
                "TMDB", "TMDB_READ_ACCESS_TOKEN is not configured", unavailable=True
            )
        categories = [media_type] if media_type else ["movie", "tv"]
        results: list[dict[str, Any]] = []
        for category in categories:
            payload = self._get(
                f"/search/{category}",
                params={"query": query, "include_adult": "false"},
            )
            items = payload.get("results")
            if not isinstance(items, list):
                raise ProviderError("TMDB", "TMDB returned an invalid search response")
            for item in items:
                if not isinstance(item, dict):
                    raise ProviderError("TMDB", "TMDB returned an invalid search result")
                results.append(normalize_search_result(category, item))
        return sorted(
            results,
            key=lambda item: (item["popularity"] or 0, item["title"].casefold()),
            reverse=True,
        )

    def get_details(self, media_type: str, external_id: int) -> dict[str, Any]:
        if not self._token:
            raise ProviderError(
                "TMDB", "TMDB_READ_ACCESS_TOKEN is not configured", unavailable=True
            )
        payload = self._get(f"/{media_type}/{external_id}")
        return normalize_details(media_type, payload)

    def get_imdb_id(self, media_type: str, external_id: int) -> str | None:
        if not self._token:
            raise ProviderError(
                "TMDB", "TMDB_READ_ACCESS_TOKEN is not configured", unavailable=True
            )
        payload = self._get(f"/{media_type}/{external_id}/external_ids")
        imdb_id = payload.get("imdb_id")
        return imdb_id if isinstance(imdb_id, str) and imdb_id.startswith("tt") else None

    def get_episodes(self, show_id: int) -> list[dict[str, Any]]:
        if not self._token:
            raise ProviderError(
                "TMDB", "TMDB_READ_ACCESS_TOKEN is not configured", unavailable=True
            )
        show = self._get(f"/tv/{show_id}")
        seasons = show.get("seasons")
        if not isinstance(seasons, list):
            raise ProviderError("TMDB", "TMDB returned an invalid season response")

        episodes: list[dict[str, Any]] = []
        for season in seasons:
            if not isinstance(season, dict):
                raise ProviderError("TMDB", "TMDB returned an invalid season")
            season_number = season.get("season_number")
            season_name = season.get("name")
            if (
                isinstance(season_number, bool)
                or not isinstance(season_number, int)
                or not isinstance(season_name, str)
            ):
                raise ProviderError("TMDB", "TMDB returned an invalid season")
            season_payload = self._get(f"/tv/{show_id}/season/{season_number}")
            items = season_payload.get("episodes")
            if not isinstance(items, list):
                raise ProviderError("TMDB", "TMDB returned an invalid episode response")
            for item in items:
                if not isinstance(item, dict):
                    raise ProviderError("TMDB", "TMDB returned an invalid episode")
                episode_id = item.get("id")
                name = item.get("name")
                if (
                    isinstance(episode_id, bool)
                    or not isinstance(episode_id, int)
                    or not isinstance(name, str)
                    or not name.strip()
                ):
                    raise ProviderError("TMDB", "TMDB returned an invalid episode")
                still = item.get("still_path")
                poster = season.get("poster_path")
                episodes.append(
                    {
                        "tmdb_id": episode_id,
                        "season_number": season_number,
                        "season_name": season_name,
                        "season_overview": season.get("overview"),
                        "season_poster_path": image_url(poster, "w342")
                        if isinstance(poster, str)
                        else None,
                        "season_air_date": parse_release_date(season.get("air_date")),
                        "episode_number": _non_negative_integer(item.get("episode_number")),
                        "title": name,
                        "overview": item.get("overview")
                        if isinstance(item.get("overview"), str)
                        else None,
                        "air_at": None,
                        "air_date": parse_release_date(item.get("air_date")),
                        "runtime": _non_negative_integer(item.get("runtime")),
                        "still_path": image_url(still, "w300") if isinstance(still, str) else None,
                    }
                )
        return episodes

    def _get(
        self, path: str, *, params: dict[str, str | int] | None = None
    ) -> dict[str, Any]:
        payload = get_json(
            "TMDB",
            f"{BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
            transport=self._transport,
        )
        if not isinstance(payload, dict):
            raise ProviderError("TMDB", "TMDB returned an invalid response")
        return payload


def normalize_search_result(category: str, item: dict[str, Any]) -> dict[str, Any]:
    if item.get("id") is None:
        raise ProviderError("TMDB", "TMDB returned a title without an identifier")
    is_movie = category == "movie"
    title = item.get("title" if is_movie else "name")
    if not isinstance(title, str) or not title.strip():
        raise ProviderError("TMDB", "TMDB returned a title without a name")
    return {
        "provider": "tmdb",
        "external_id": str(item["id"]),
        "media_type": "MOVIE" if is_movie else "TV",
        "title": title,
        "original_title": item.get("original_title" if is_movie else "original_name"),
        "overview": item.get("overview"),
        "release_date": parse_release_date(item.get("release_date")) if is_movie else None,
        "first_air_date": parse_release_date(item.get("first_air_date")) if not is_movie else None,
        "poster_path": image_url(item.get("poster_path"), "w342"),
        "backdrop_path": image_url(item.get("backdrop_path"), "w780"),
        "popularity": item.get("popularity"),
        "tmdb_rating": _finite_score(item.get("vote_average"), minimum=0, maximum=10),
        "tmdb_vote_count": _non_negative_integer(item.get("vote_count")),
        "original_language": item.get("original_language"),
    }


def normalize_details(category: str, item: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_search_result(category, item)
    episode_run_times = item.get("episode_run_time") or []
    genres = item.get("genres")
    normalized.update(
        {
            "status": item.get("status"),
            "genres": [
                genre["name"].strip()
                for genre in genres
                if isinstance(genre, dict)
                and isinstance(genre.get("name"), str)
                and genre["name"].strip()
            ]
            if isinstance(genres, list)
            else [],
            "runtime": item.get("runtime")
            if category == "movie"
            else (episode_run_times[0] if episode_run_times else None),
        }
    )
    return normalized


def image_url(path: str | None, size: str) -> str | None:
    return f"{IMAGE_BASE_URL}{size}{path}" if path else None


def _finite_score(value: Any, *, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    score = float(value)
    return score if minimum <= score <= maximum else None


def _non_negative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def parse_release_date(value: str | date | None) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
