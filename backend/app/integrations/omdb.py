from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.errors import ProviderError
from app.integrations.http import get_json

BASE_URL = "https://www.omdbapi.com/"


class OmdbClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else get_settings().omdb_api_key
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def get_ratings(self, imdb_id: str) -> dict[str, float | int | None] | None:
        if not self._api_key:
            return None
        payload = get_json(
            "OMDb",
            BASE_URL,
            params={"i": imdb_id, "apikey": self._api_key},
            headers={"Accept": "application/json"},
            transport=self._transport,
        )
        if not isinstance(payload, dict):
            raise ProviderError("OMDb", "OMDb returned an invalid response")
        if payload.get("Response") == "False":
            raise ProviderError("OMDb", "OMDb could not find or rate this title")

        ratings = payload.get("Ratings", [])
        if not isinstance(ratings, list):
            raise ProviderError("OMDb", "OMDb returned invalid ratings")
        values: dict[str, Any] = {
            "imdb_rating": _parse_score(payload.get("imdbRating"), maximum=10),
            "rotten_tomatoes_rating": None,
        }
        for rating in ratings:
            if not isinstance(rating, dict) or rating.get("Source") != "Rotten Tomatoes":
                continue
            value = rating.get("Value")
            if isinstance(value, str) and value.endswith("%"):
                values["rotten_tomatoes_rating"] = _parse_score(
                    value[:-1], maximum=100, integer=True
                )
        return values


def _parse_score(value: Any, *, maximum: int, integer: bool = False) -> float | int | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    try:
        score = float(value)
    except ValueError:
        return None
    if not 0 <= score <= maximum:
        return None
    return int(score) if integer else score
