import json
from datetime import date

import httpx
import pytest

from app.integrations.errors import ProviderError
from app.integrations.http import get_json
from app.integrations.omdb import OmdbClient
from app.integrations.tmdb import (
    TmdbClient,
    normalize_details,
    normalize_search_result,
    parse_release_date,
)
from app.integrations.tvmaze import TvmazeClient


def test_tmdb_normalizes_movie_and_tv_results() -> None:
    movie = normalize_search_result(
        "movie",
        {
            "id": 123,
            "title": "A Film",
            "original_title": "A Film",
            "release_date": "2024-02-03",
            "poster_path": "/poster.jpg",
        },
    )
    show = normalize_search_result(
        "tv",
        {
            "id": 456,
            "name": "A Show",
            "first_air_date": "2021-08-09",
            "poster_path": None,
        },
    )

    assert movie["media_type"] == "MOVIE"
    assert movie["release_date"].isoformat() == "2024-02-03"
    assert movie["poster_path"] == "https://image.tmdb.org/t/p/w342/poster.jpg"
    assert show["media_type"] == "TV"
    assert show["first_air_date"].isoformat() == "2021-08-09"
    assert show["poster_path"] is None


def test_tmdb_search_uses_bearer_auth_and_merges_categories() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        category = request.url.path.rsplit("/", 1)[-1]
        item = (
            {"id": 1, "title": "Movie", "popularity": 2}
            if category == "movie"
            else {"id": 2, "name": "Show", "popularity": 5}
        )
        return httpx.Response(200, json={"results": [item]})

    client = TmdbClient(
        token="test-token",
        transport=httpx.MockTransport(handle),
    )
    results = client.search("test")

    assert [item["title"] for item in results] == ["Show", "Movie"]
    assert all(request.headers["Authorization"] == "Bearer test-token" for request in requests)
    assert all(request.url.params["query"] == "test" for request in requests)


def test_tmdb_loads_and_normalizes_season_episodes() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/3/tv/42":
            return httpx.Response(
                200,
                json={
                    "seasons": [
                        {
                            "season_number": 1,
                            "name": "Season 1",
                            "overview": "Season summary",
                            "air_date": "2021-01-02",
                            "poster_path": "/season.jpg",
                        }
                    ]
                },
            )
        assert request.url.path == "/3/tv/42/season/1"
        return httpx.Response(
            200,
            json={
                "episodes": [
                    {
                        "id": 4201,
                        "episode_number": 1,
                        "name": "Episode 1",
                        "overview": "Episode summary",
                        "air_date": "2021-01-03",
                        "runtime": 24,
                        "still_path": "/episode.jpg",
                    }
                ]
            },
        )

    episodes = TmdbClient(
        token="test-token",
        transport=httpx.MockTransport(handle),
    ).get_episodes(42)

    assert episodes == [
        {
            "tmdb_id": 4201,
            "season_number": 1,
            "season_name": "Season 1",
            "season_overview": "Season summary",
            "season_poster_path": "https://image.tmdb.org/t/p/w342/season.jpg",
            "season_air_date": date(2021, 1, 2),
            "episode_number": 1,
            "title": "Episode 1",
            "overview": "Episode summary",
            "air_at": None,
            "air_date": date(2021, 1, 3),
            "runtime": 24,
            "still_path": "https://image.tmdb.org/t/p/w300/episode.jpg",
        }
    ]


def test_tvmaze_only_returns_exact_title_and_year_matches() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"show": {"id": 1, "name": "The Office", "premiered": "2001-03-09"}},
                {"show": {"id": 2, "name": "The Office", "premiered": "2005-03-24"}},
            ],
        )

    client = TvmazeClient(transport=httpx.MockTransport(handle))

    match = client.find_matching_show("The Office", date(2005, 1, 1))
    no_match = client.find_matching_show("The Office", "2010-01-01")

    assert match is not None and match["id"] == 2
    assert no_match is None


def test_tvmaze_normalizes_episode_metadata_and_summaries() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/shows/777/episodes"
        assert request.url.params["specials"] == "1"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 11,
                    "season": 1,
                    "number": 2,
                    "name": "Episode",
                    "summary": "<p>A <b>story</b> &amp; a mystery.</p>",
                    "airstamp": "2024-01-02T03:04:00+00:00",
                    "airdate": "2024-01-02",
                    "runtime": 44,
                    "image": {"original": "https://example.test/episode.jpg"},
                },
                {
                    "id": 12,
                    "season": 0,
                    "number": None,
                    "name": "Special",
                    "summary": None,
                    "airstamp": None,
                    "airdate": None,
                    "runtime": None,
                    "image": None,
                },
            ],
        )

    episodes = TvmazeClient(transport=httpx.MockTransport(handle)).get_episodes(777)

    assert episodes[0]["overview"] == "A story & a mystery."
    assert episodes[0]["air_at"].isoformat() == "2024-01-02T03:04:00+00:00"
    assert episodes[0]["air_date"] == date(2024, 1, 2)
    assert episodes[0]["still_path"] == "https://example.test/episode.jpg"
    assert episodes[1]["season_number"] == 0
    assert episodes[1]["episode_number"] is None
    assert episodes[1]["overview"] is None


def test_provider_client_retries_transient_errors() -> None:
    attempts = 0
    delays: list[float] = []

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    result = get_json(
        "test-provider",
        "https://provider.test/retry-case",
        transport=httpx.MockTransport(handle),
        sleep=delays.append,
    )

    assert result == {"ok": True}
    assert attempts == 2
    assert delays == [0.25]


def test_provider_client_honors_retry_after_and_caches_success() -> None:
    attempts = 0
    delays: list[float] = []

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"success": True})

    result = get_json(
        "test-provider",
        "https://provider.test/rate-limit-case",
        transport=httpx.MockTransport(handle),
        sleep=delays.append,
    )
    cached_result = get_json(
        "test-provider",
        "https://provider.test/rate-limit-case",
        transport=httpx.MockTransport(handle),
        sleep=delays.append,
    )

    assert result == {"success": True}
    assert cached_result == result
    assert attempts == 2
    assert delays == [1.0]


def test_tmdb_requires_credentials() -> None:
    with pytest.raises(ProviderError, match="TMDB_READ_ACCESS_TOKEN is not configured"):
        TmdbClient(token="").search("title")


def test_invalid_release_dates_are_not_invented() -> None:
    result = normalize_search_result(
        "movie",
        {"id": 20, "title": "Unknown date", "release_date": "not-a-date"},
    )

    assert result["release_date"] is None


def test_normalized_dates_are_safe_for_import_and_tvmaze_matching() -> None:
    details = normalize_details(
        "tv",
        {
            "id": 88,
            "name": "A Show",
            "first_air_date": "2020-05-04",
            "episode_run_time": [],
            "genres": [
                {"id": 18, "name": "Drama"},
                {"id": 10765, "name": "Sci-Fi & Fantasy"},
            ],
        },
    )

    assert details["first_air_date"] == date(2020, 5, 4)
    assert parse_release_date(details["first_air_date"]) == date(2020, 5, 4)
    assert details["runtime"] is None
    assert details["genres"] == ["Drama", "Sci-Fi & Fantasy"]


def test_tmdb_normalizes_vote_average_only_within_valid_range() -> None:
    result = normalize_search_result(
        "movie",
        {
            "id": 9,
            "title": "Rated film",
            "vote_average": 8.25,
            "vote_count": 42,
        },
    )
    invalid = normalize_search_result(
        "movie",
        {
            "id": 10,
            "title": "Invalid score",
            "vote_average": 11,
            "vote_count": -1,
        },
    )

    assert result["tmdb_rating"] == 8.25
    assert result["tmdb_vote_count"] == 42
    assert invalid["tmdb_rating"] is None
    assert invalid["tmdb_vote_count"] is None


def test_omdb_reads_imdb_and_rotten_tomatoes_ratings() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.params["i"] == "tt0123456"
        assert request.url.params["apikey"] == "test-key"
        return httpx.Response(
            200,
            json={
                "Response": "True",
                "imdbRating": "8.4",
                "Ratings": [{"Source": "Rotten Tomatoes", "Value": "95%"}],
            },
        )

    client = OmdbClient(api_key="test-key", transport=httpx.MockTransport(handle))

    assert client.get_ratings("tt0123456") == {
        "imdb_rating": 8.4,
        "rotten_tomatoes_rating": 95,
    }


def test_omdb_missing_key_disables_optional_ratings() -> None:
    client = OmdbClient(api_key="")

    assert client.configured is False
    assert client.get_ratings("tt0123456") is None


def test_transport_does_not_expose_provider_error_bodies() -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=json.dumps({"secret": "not for clients"}))

    with pytest.raises(ProviderError) as error:
        get_json(
            "test-provider",
            "https://provider.test/server-error-case",
            transport=httpx.MockTransport(handle),
            sleep=lambda _: None,
        )

    assert "secret" not in str(error.value)
