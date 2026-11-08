import re
import unicodedata
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

import httpx

from app.integrations.errors import ProviderError
from app.integrations.http import get_json

BASE_URL = "https://api.tvmaze.com"


class TvmazeClient:
    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def find_matching_show(
        self, title: str, first_air_date: str | date | None
    ) -> dict[str, Any] | None:
        payload = get_json(
            "TVmaze",
            f"{BASE_URL}/search/shows",
            params={"q": title},
            headers={"Accept": "application/json"},
            transport=self._transport,
        )
        if not isinstance(payload, list):
            raise ProviderError("TVmaze", "TVmaze returned an invalid response")
        requested_title = normalize_title(title)
        requested_year = date_year(first_air_date)
        exact_title_matches = []
        for result in payload:
            if not isinstance(result, dict) or not isinstance(result.get("show"), dict):
                raise ProviderError("TVmaze", "TVmaze returned an invalid show result")
            show = result["show"]
            show_name = show.get("name")
            if not isinstance(show_name, str) or normalize_title(show_name) != requested_title:
                continue
            if requested_year:
                if date_year(show.get("premiered")) == requested_year:
                    return show
                continue
            exact_title_matches.append(show)
        return exact_title_matches[0] if len(exact_title_matches) == 1 else None

    def get_episodes(self, show_id: int) -> list[dict[str, Any]]:
        payload = get_json(
            "TVmaze",
            f"{BASE_URL}/shows/{show_id}/episodes",
            params={"specials": 1},
            headers={"Accept": "application/json"},
            transport=self._transport,
        )
        if not isinstance(payload, list):
            raise ProviderError("TVmaze", "TVmaze returned an invalid episode response")

        episodes: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ProviderError("TVmaze", "TVmaze returned an invalid episode")
            episode_id = item.get("id")
            season = item.get("season")
            name = item.get("name")
            if (
                not isinstance(episode_id, int)
                or not isinstance(season, int)
                or not isinstance(name, str)
            ):
                raise ProviderError("TVmaze", "TVmaze returned an invalid episode")
            image = item.get("image")
            image_path = (
                image.get("original") or image.get("medium")
                if isinstance(image, dict)
                else None
            )
            episodes.append(
                {
                    "tvmaze_id": episode_id,
                    "season_number": season,
                    "episode_number": item.get("number")
                    if isinstance(item.get("number"), int)
                    else None,
                    "title": name,
                    "overview": _plain_text(item.get("summary")),
                    "air_at": _parse_airstamp(item.get("airstamp")),
                    "air_date": _parse_airdate(item.get("airdate")),
                    "runtime": item.get("runtime")
                    if isinstance(item.get("runtime"), int)
                    else None,
                    "still_path": image_path if isinstance(image_path, str) else None,
                }
            )
        return episodes


def normalize_title(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_title = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_title).strip()


def date_year(value: str | date | None) -> int | None:
    if not value:
        return None
    if isinstance(value, date):
        return value.year
    try:
        return date.fromisoformat(value[:10]).year
    except ValueError:
        return None


class _SummaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _plain_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    parser = _SummaryParser()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip() or None


def _parse_airstamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _parse_airdate(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
