from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_omdb_client, get_tmdb_client, get_tvmaze_client
from app.db.base import Base
from app.db.session import get_db
from app.integrations.errors import ProviderError
from app.jobs import generate_notifications
from app.main import app
from app.models import (
    Episode,
    Media,
    MediaExternalId,
    Notification,
    Season,
    User,
    UserLibrary,
    WatchEvent,
)


class FakeTmdbClient:
    def __init__(self) -> None:
        self.details_calls = 0
        self.episodes: list[dict] = []

    def search(self, query: str, media_type: str | None = None) -> list[dict]:
        return [
            {
                "provider": "tmdb",
                "external_id": "101",
                "media_type": "MOVIE",
                "title": "A Test Film",
                "original_title": "A Test Film",
                "overview": "A test description.",
                "release_date": date(2024, 2, 3) if media_type == "movie" else None,
                "first_air_date": date(2020, 5, 4) if media_type == "tv" else None,
                "poster_path": None,
                "backdrop_path": None,
                "popularity": 1.0,
                "tmdb_rating": 7.8,
                "tmdb_vote_count": 1510,
                "original_language": "en",
            }
        ]

    def get_details(self, media_type: str, external_id: int) -> dict:
        self.details_calls += 1
        return {
            "provider": "tmdb",
            "external_id": str(external_id),
            "media_type": "MOVIE" if media_type == "movie" else "TV",
            "title": "A Test Film",
            "original_title": "A Test Film",
            "overview": "A test description.",
            "release_date": date(2024, 2, 3) if media_type == "movie" else None,
            "first_air_date": date(2020, 5, 4) if media_type == "tv" else None,
            "poster_path": None,
            "backdrop_path": None,
            "runtime": 100,
            "original_language": "en",
            "popularity": 1.0,
            "tmdb_rating": 7.8,
            "tmdb_vote_count": 1510,
            "status": "Released",
            "genres": ["Drama"],
        }

    def get_imdb_id(self, media_type: str, external_id: int) -> None:
        return None

    def get_episodes(self, show_id: int) -> list[dict]:
        assert show_id == 202
        return self.episodes


class FakeTvmazeClient:
    def find_matching_show(
        self, title: str, first_air_date: str | date | None
    ) -> None:
        return None


class FakeOmdbClient:
    configured = False

    def get_ratings(self, imdb_id: str) -> None:
        return None


@pytest.fixture
def api_client() -> Generator[
    tuple[TestClient, sessionmaker[Session], FakeTmdbClient],
    None,
    None,
]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    tmdb = FakeTmdbClient()

    def override_db() -> Generator[Session, None, None]:
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tmdb_client] = lambda: tmdb  # type: ignore[assignment]
    app.dependency_overrides[get_omdb_client] = (
        lambda: FakeOmdbClient()  # type: ignore[assignment]
    )
    app.dependency_overrides[get_tvmaze_client] = (
        lambda: FakeTvmazeClient()  # type: ignore[assignment]
    )
    with TestClient(app) as client:
        yield client, test_session, tmdb
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_search_import_duplicate_status_and_removal(api_client) -> None:
    client, test_session, tmdb = api_client

    search_response = client.get("/api/v1/media/search", params={"q": "A Test"})
    assert search_response.status_code == 200
    assert search_response.json()[0]["title"] == "A Test Film"
    assert search_response.json()[0]["tmdb_rating"] == 7.8

    import_payload = {"provider": "tmdb", "external_id": 101, "media_type": "MOVIE"}
    first_import = client.post("/api/v1/media/import", json=import_payload)
    repeated_import = client.post("/api/v1/media/import", json=import_payload)

    assert first_import.status_code == 201
    assert first_import.json()["watch_status"] == "PLAN_TO_WATCH"
    assert first_import.json()["media"]["release_date"] == "2024-02-03"
    assert first_import.json()["media"]["tmdb_rating"] == 7.8
    assert first_import.json()["media"]["genres"] == ["Drama"]
    assert repeated_import.status_code == 200
    assert repeated_import.json()["already_in_library"] is True
    assert tmdb.details_calls == 2

    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(Media)) == 1
        assert db.scalar(select(func.count()).select_from(MediaExternalId)) == 1
        assert db.scalar(select(func.count()).select_from(UserLibrary)) == 1

    media_id = first_import.json()["media"]["id"]
    library_response = client.get("/api/v1/library", params={"media_type": "MOVIE"})
    assert library_response.status_code == 200
    assert len(library_response.json()) == 1

    status_response = client.patch(
        f"/api/v1/library/{media_id}",
        json={"watch_status": "COMPLETED"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["watch_status"] == "COMPLETED"

    remove_response = client.delete(f"/api/v1/library/{media_id}")
    assert remove_response.status_code == 204
    assert client.get("/api/v1/library").json() == []
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(Media)) == 1


def test_completing_and_reopening_show_updates_all_episode_watch_events(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 404, "media_type": "TV"},
    )
    assert imported.status_code == 201
    media_id = UUID(imported.json()["media"]["id"])

    with test_session() as db:
        user = db.scalar(select(User))
        assert user is not None
        season = Season(media_id=media_id, season_number=1, name="Season 1")
        future_season = Season(media_id=media_id, season_number=2, name="Season 2")
        db.add(season)
        db.add(future_season)
        db.flush()
        db.add_all(
            [
                Episode(
                    season_id=season.id,
                    tvmaze_id=740,
                    episode_number=1,
                    title="Previously watched",
                ),
                Episode(
                    season_id=season.id,
                    tvmaze_id=741,
                    episode_number=2,
                    title="Not watched yet",
                ),
                Episode(
                    season_id=future_season.id,
                    tvmaze_id=742,
                    episode_number=1,
                    title="Future episode",
                    air_date=date(2100, 1, 1),
                ),
            ]
        )
        db.flush()
        previously_watched = db.scalar(
            select(Episode).where(Episode.tvmaze_id == 740)
        )
        assert previously_watched is not None
        db.add(
            WatchEvent(
                user_id=user.id,
                episode_id=previously_watched.id,
                event_type="WATCHED",
                is_current=True,
            )
        )
        db.commit()

    completed = client.patch(
        f"/api/v1/library/{media_id}",
        json={"watch_status": "COMPLETED"},
    )
    assert completed.status_code == 200
    assert completed.json()["watch_status"] == "COMPLETED"
    tracking = client.get(f"/api/v1/library/{media_id}/episodes")
    assert tracking.status_code == 200
    assert tracking.json()["watched_count"] == 3
    assert all(
        episode["watched"]
        for season in tracking.json()["seasons"]
        for episode in season["episodes"]
    )

    reopened = client.patch(
        f"/api/v1/library/{media_id}",
        json={"watch_status": "ON_HOLD"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["watch_status"] == "ON_HOLD"
    tracking = client.get(f"/api/v1/library/{media_id}/episodes")
    assert tracking.status_code == 200
    assert tracking.json()["watched_count"] == 0
    assert all(
        not episode["watched"]
        for season in tracking.json()["seasons"]
        for episode in season["episodes"]
    )


def test_episode_can_mark_unwatched_previous_episodes_across_seasons(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 406, "media_type": "TV"},
    )
    media_id = UUID(imported.json()["media"]["id"])

    with test_session() as db:
        first_season = Season(media_id=media_id, season_number=1, name="Season 1")
        second_season = Season(media_id=media_id, season_number=2, name="Season 2")
        db.add_all([first_season, second_season])
        db.flush()
        previous_episode = Episode(
            season_id=first_season.id,
            tvmaze_id=743,
            episode_number=1,
            title="Earlier episode",
        )
        current_episode = Episode(
            season_id=second_season.id,
            tvmaze_id=744,
            episode_number=1,
            title="Current episode",
        )
        db.add_all([previous_episode, current_episode])
        db.commit()
        current_episode_id = current_episode.id

    response = client.put(
        f"/api/v1/episodes/{current_episode_id}/watched",
        json={"watched": True, "include_previous": True},
    )

    assert response.status_code == 200
    tracking = client.get(f"/api/v1/library/{media_id}/episodes")
    assert tracking.status_code == 200
    assert tracking.json()["watched_count"] == 2
    assert all(
        episode["watched"]
        for season in tracking.json()["seasons"]
        for episode in season["episodes"]
    )


def test_library_last_watched_uses_latest_episode_watch_time(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 407, "media_type": "TV"},
    )
    media_id = UUID(imported.json()["media"]["id"])
    earlier = datetime(2024, 1, 1, tzinfo=UTC)
    latest = datetime(2024, 1, 5, tzinfo=UTC)

    with test_session() as db:
        user = db.scalar(select(User))
        assert user is not None
        season = Season(media_id=media_id, season_number=1, name="Season 1")
        db.add(season)
        db.flush()
        episodes = [
            Episode(season_id=season.id, tvmaze_id=745, title="Earlier"),
            Episode(season_id=season.id, tvmaze_id=746, title="Latest"),
        ]
        db.add_all(episodes)
        db.flush()
        db.add_all(
            [
                WatchEvent(
                    user_id=user.id,
                    episode_id=episodes[0].id,
                    watched_at=earlier,
                    event_type="WATCHED",
                    is_current=True,
                ),
                WatchEvent(
                    user_id=user.id,
                    episode_id=episodes[1].id,
                    watched_at=latest,
                    event_type="REWATCHED",
                    is_current=True,
                ),
            ]
        )
        db.commit()

    library = client.get("/api/v1/library")
    assert library.status_code == 200
    entry = next(item for item in library.json() if item["media"]["id"] == str(media_id))
    assert entry["last_watched_at"].startswith(latest.strftime("%Y-%m-%dT%H:%M:%S"))


def test_calendar_includes_movie_releases_and_localized_episode_airings(api_client) -> None:
    client, test_session, _ = api_client
    movie_import = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 101, "media_type": "MOVIE"},
    )
    tv_import = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 202, "media_type": "TV"},
    )
    assert movie_import.status_code == 201
    assert tv_import.status_code == 201

    with test_session() as db:
        tv_media = db.get(Media, UUID(tv_import.json()["media"]["id"]))
        assert tv_media is not None
        season = Season(media_id=tv_media.id, season_number=1, name="Season 1")
        db.add(season)
        db.flush()
        db.add(
            Episode(
                season_id=season.id,
                tvmaze_id=555,
                episode_number=1,
                title="A New Episode",
                air_at=datetime(2024, 1, 1, 2, tzinfo=UTC),
                air_date=date(2024, 1, 1),
            )
        )
        db.add(
            Episode(
                season_id=season.id,
                tvmaze_id=556,
                episode_number=2,
                title="Date Unknown",
            )
        )
        db.add(
            Episode(
                season_id=season.id,
                tvmaze_id=557,
                episode_number=3,
                title="Date Only",
                air_date=date(2024, 1, 2),
            )
        )
        db.commit()

    movie_response = client.get(
        "/api/v1/calendar",
        params={"start": "2024-02-01", "end": "2024-02-29", "timezone": "UTC"},
    )
    assert movie_response.status_code == 200
    movie_events = movie_response.json()["events"]
    assert [
        (event["event_type"], event["event_date"])
        for event in movie_events
    ] == [("MOVIE_RELEASE", "2024-02-03")]

    episode_response = client.get(
        "/api/v1/calendar",
        params={
            "start": "2023-12-31",
            "end": "2023-12-31",
            "timezone": "America/Los_Angeles",
        },
    )
    assert episode_response.status_code == 200
    episode_event = episode_response.json()["events"][0]
    assert episode_event["event_type"] == "EPISODE_AIRING"
    assert episode_event["title"] == "A Test Film: S01E01"
    assert episode_event["episode_title"] == "A New Episode"
    assert episode_event["event_date"] == "2023-12-31"
    assert episode_event["starts_at"] == "2023-12-31T18:00:00-08:00"
    assert episode_event["season_number"] == 1
    assert episode_event["episode_number"] == 1

    date_only_response = client.get(
        "/api/v1/calendar",
        params={"start": "2024-01-02", "end": "2024-01-02", "timezone": "UTC"},
    )
    assert date_only_response.status_code == 200
    date_only_event = date_only_response.json()["events"][0]
    assert date_only_event["event_date"] == "2024-01-02"
    assert date_only_event["starts_at"] is None


@pytest.mark.parametrize(
    ("params", "detail"),
    [
        (
            {"start": "2024-02-02", "end": "2024-02-01"},
            "Calendar start date must be on or before its end date.",
        ),
        (
            {"start": "2024-02-01", "end": "2024-02-02", "timezone": "Not/A_Timezone"},
            "The requested timezone is not a valid IANA timezone.",
        ),
    ],
)
def test_calendar_rejects_invalid_ranges_and_timezones(api_client, params, detail) -> None:
    client, _, _ = api_client
    response = client.get("/api/v1/calendar", params=params)
    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_catch_up_lists_only_aired_unwatched_episodes(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 303, "media_type": "TV"},
    )
    assert imported.status_code == 201
    media_id = UUID(imported.json()["media"]["id"])
    aired = datetime.now(UTC).date() - timedelta(days=2)

    with test_session() as db:
        user = db.scalar(select(User))
        entry = db.scalar(select(UserLibrary).where(UserLibrary.media_id == media_id))
        assert user is not None
        assert entry is not None
        entry.watch_status = "WATCHING"
        season = Season(media_id=media_id, season_number=1, name="Season 1")
        db.add(season)
        db.flush()
        unwatched_episode = Episode(
            season_id=season.id,
            tvmaze_id=700,
            episode_number=1,
            title="Unwatched",
            air_date=aired,
        )
        watched_episode = Episode(
            season_id=season.id,
            tvmaze_id=701,
            episode_number=2,
            title="Watched",
            air_date=aired,
        )
        db.add_all([unwatched_episode, watched_episode])
        db.flush()
        db.add(
            WatchEvent(
                user_id=user.id,
                episode_id=watched_episode.id,
                event_type="WATCHED",
                is_current=True,
            )
        )
        db.commit()

    response = client.get("/api/v1/catch-up", params={"timezone": "UTC"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    show = response.json()[0]
    assert show["unwatched_count"] == 1
    assert show["episodes"][0]["title"] == "Unwatched"
    assert show["episodes"][0]["air_date"] == aired.isoformat()


def test_scheduled_notifications_are_deduplicated_and_preferences_apply(api_client) -> None:
    client, test_session, _ = api_client
    tv_import = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 405, "media_type": "TV"},
    )
    assert tv_import.status_code == 201
    media_id = UUID(tv_import.json()["media"]["id"])
    run_at = datetime(2024, 2, 3, 12, tzinfo=UTC)

    with test_session() as db:
        watching_entry = db.scalar(select(UserLibrary).where(UserLibrary.media_id == media_id))
        assert watching_entry is not None
        watching_entry.watch_status = "WATCHING"
        season = Season(media_id=media_id, season_number=1, name="Season 1")
        db.add(season)
        db.flush()
        db.add(
            Episode(
                season_id=season.id,
                tvmaze_id=702,
                episode_number=4,
                title="Released episode",
                air_at=datetime(2024, 2, 3, 2, tzinfo=UTC),
                air_date=date(2024, 2, 3),
            )
        )
        db.add(
            Episode(
                season_id=season.id,
                tvmaze_id=703,
                episode_number=5,
                title="Announced episode",
                air_at=datetime(2024, 2, 10, 5, tzinfo=UTC),
                air_date=date(2024, 2, 10),
            )
        )
        planned_show = Media(media_type="TV", title="Not currently watching")
        db.add(planned_show)
        db.flush()
        db.add(UserLibrary(user_id=watching_entry.user_id, media_id=planned_show.id))
        planned_season = Season(
            media_id=planned_show.id,
            season_number=1,
            name="Season 1",
        )
        db.add(planned_season)
        db.flush()
        db.add(
            Episode(
                season_id=planned_season.id,
                tvmaze_id=704,
                episode_number=1,
                title="Planned show episode",
                air_at=datetime(2024, 2, 10, 5, tzinfo=UTC),
                air_date=date(2024, 2, 10),
            )
        )
        db.commit()
        assert generate_notifications(db, run_at) == 2
        assert generate_notifications(db, run_at) == 0
        assert db.scalar(select(func.count()).select_from(Notification)) == 2
        kinds = set(db.scalars(select(Notification.kind)).all())
        assert kinds == {"EPISODE_RELEASE", "EPISODE_ANNOUNCED"}

    preferences = client.get("/api/v1/notification-preferences")
    assert preferences.status_code == 200
    assert preferences.json()["release_notifications_enabled"] is True
    updated = client.patch(
        "/api/v1/notification-preferences",
        json={
            "release_notifications_enabled": False,
            "timezone": "America/Los_Angeles",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["release_notifications_enabled"] is False
    assert updated.json()["timezone"] == "America/Los_Angeles"

    with test_session() as db:
        season = db.scalar(select(Season).where(Season.media_id == media_id))
        assert season is not None
        db.add(
            Episode(
                season_id=season.id,
                tvmaze_id=705,
                episode_number=6,
                title="Notifications disabled",
                air_at=datetime(2024, 2, 11, 5, tzinfo=UTC),
                air_date=date(2024, 2, 11),
            )
        )
        db.commit()
        assert generate_notifications(db, run_at) == 0
        assert db.scalar(select(func.count()).select_from(Notification)) == 2

    notifications = client.get("/api/v1/notifications")
    assert notifications.status_code == 200
    assert len(notifications.json()) == 2
    assert {notification["kind"] for notification in notifications.json()} == {
        "EPISODE_RELEASE",
        "EPISODE_ANNOUNCED",
    }
    with test_session() as db:
        watching_entry = db.scalar(select(UserLibrary).where(UserLibrary.media_id == media_id))
        assert watching_entry is not None
        watching_entry.watch_status = "PLAN_TO_WATCH"
        db.commit()
    assert client.get("/api/v1/notifications").json() == []
    with test_session() as db:
        watching_entry = db.scalar(select(UserLibrary).where(UserLibrary.media_id == media_id))
        assert watching_entry is not None
        watching_entry.watch_status = "WATCHING"
        db.commit()

    notification_id = notifications.json()[0]["id"]
    cleared = client.delete(f"/api/v1/notifications/{notification_id}")
    assert cleared.status_code == 204
    assert len(client.get("/api/v1/notifications").json()) == 1
    cleared_all = client.delete("/api/v1/notifications")
    assert cleared_all.status_code == 200
    assert cleared_all.json()["cleared_count"] == 1
    assert client.get("/api/v1/notifications").json() == []
    assert client.delete(f"/api/v1/notifications/{notification_id}").status_code == 404
    reenabled_preferences = client.patch(
        "/api/v1/notification-preferences",
        json={"release_notifications_enabled": True},
    )
    assert reenabled_preferences.status_code == 200
    with test_session() as db:
        assert generate_notifications(db, run_at) == 0
    assert client.get("/api/v1/notifications").json() == []


def test_provider_failure_does_not_create_library_data(api_client) -> None:
    client, test_session, _ = api_client

    def fail_details(_: str, __: int) -> dict:
        raise ProviderError("TMDB", "TMDB request failed", unavailable=True)

    from app.api.dependencies import get_tmdb_client as tmdb_dependency

    class FailedTmdbClient(FakeTmdbClient):
        get_details = staticmethod(fail_details)

    app.dependency_overrides[tmdb_dependency] = FailedTmdbClient
    response = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 999, "media_type": "MOVIE"},
    )

    assert response.status_code == 503
    assert "TMDB request failed" in response.text
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(Media)) == 0


def test_reimport_preserves_existing_metadata_when_provider_omits_fields(api_client) -> None:
    client, test_session, tmdb = api_client
    payload = {"provider": "tmdb", "external_id": 101, "media_type": "MOVIE"}
    first_import = client.post("/api/v1/media/import", json=payload)
    assert first_import.status_code == 201

    original_get_details = tmdb.get_details

    def incomplete_details(media_type: str, external_id: int) -> dict:
        details = original_get_details(media_type, external_id)
        details["overview"] = None
        details["poster_path"] = None
        return details

    tmdb.get_details = incomplete_details
    reimport = client.post("/api/v1/media/import", json=payload)

    assert reimport.status_code == 200
    assert reimport.json()["media"]["overview"] == "A test description."
    with test_session() as db:
        media = db.scalar(select(Media))
        assert media is not None
        assert media.overview == "A test description."


def test_tv_import_persists_matched_tvmaze_identifier(api_client) -> None:
    client, test_session, _ = api_client

    class MatchingTvmazeClient:
        def find_matching_show(self, title: str, first_air_date: str | date | None) -> dict:
            assert first_air_date == date(2020, 5, 4)
            return {"id": 777}

    app.dependency_overrides[get_tvmaze_client] = lambda: MatchingTvmazeClient()
    response = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 202, "media_type": "TV"},
    )

    assert response.status_code == 201
    assert response.json()["tvmaze_id"] == 777
    with test_session() as db:
        external_id = db.scalar(
            select(MediaExternalId).where(MediaExternalId.provider == "tvmaze")
        )
        assert external_id is not None
        assert external_id.external_id == "777"


def test_episode_sync_falls_back_to_tmdb_when_tvmaze_has_no_match(api_client) -> None:
    client, _, tmdb = api_client
    tmdb.episodes = [
        {
            "tmdb_id": 9001,
            "season_number": 1,
            "season_name": "Season 1",
            "season_overview": "First season",
            "season_poster_path": None,
            "season_air_date": date(2020, 5, 4),
            "episode_number": 1,
            "title": "First Episode",
            "overview": "Episode description",
            "air_at": None,
            "air_date": date(2020, 5, 4),
            "runtime": 24,
            "still_path": None,
        }
    ]
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 202, "media_type": "TV"},
    )
    media_id = imported.json()["media"]["id"]

    response = client.post(f"/api/v1/library/{media_id}/episodes/sync")

    assert response.status_code == 200
    assert response.json()["episode_tracking_available"] is True
    assert response.json()["episode_count"] == 1
    assert response.json()["seasons"][0]["episodes"][0]["title"] == "First Episode"


def test_ratings_endpoint_returns_tmdb_rating_without_omdb(api_client) -> None:
    client, _, _ = api_client

    response = client.get("/api/v1/media/MOVIE/101/ratings")

    assert response.status_code == 200
    assert response.json() == {
        "tmdb_id": "101",
        "tmdb_rating": 7.8,
        "tmdb_vote_count": 1510,
        "imdb_rating": None,
        "rotten_tomatoes_rating": None,
        "imdb_id": None,
        "omdb_configured": False,
        "omdb_available": True,
    }


def test_import_persists_omdb_ratings_when_configured(api_client) -> None:
    client, test_session, _ = api_client

    class RatedTmdbClient(FakeTmdbClient):
        def get_imdb_id(self, media_type: str, external_id: int) -> str:
            return "tt0123456"

    class RatedOmdbClient:
        configured = True

        def get_ratings(self, imdb_id: str) -> dict[str, float | int]:
            assert imdb_id == "tt0123456"
            return {"imdb_rating": 8.4, "rotten_tomatoes_rating": 95}

    app.dependency_overrides[get_tmdb_client] = lambda: RatedTmdbClient()
    app.dependency_overrides[get_omdb_client] = lambda: RatedOmdbClient()
    response = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 101, "media_type": "MOVIE"},
    )

    assert response.status_code == 201
    assert response.json()["media"]["imdb_rating"] == 8.4
    assert response.json()["media"]["rotten_tomatoes_rating"] == 95
    with test_session() as db:
        media = db.scalar(select(Media))
        assert media is not None
        assert media.imdb_rating == 8.4
        assert media.rotten_tomatoes_rating == 95


def test_movie_watch_tracking_is_idempotent_and_can_be_undone(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 101, "media_type": "MOVIE"},
    )
    media_id = imported.json()["media"]["id"]
    watched = client.put(f"/api/v1/library/{media_id}/watched", json={"watched": True})
    repeated = client.put(f"/api/v1/library/{media_id}/watched", json={"watched": True})

    assert watched.status_code == 200
    assert repeated.json()["watched"] is True
    assert repeated.json()["watch_status"] == "COMPLETED"
    library_item = client.get("/api/v1/library").json()[0]
    assert library_item["watched"] is True
    assert library_item["watched_at"] is not None
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(WatchEvent)) == 1

    rewatch_body = {"idempotency_key": str(uuid4())}
    rewatch = client.post(f"/api/v1/library/{media_id}/rewatch", json=rewatch_body)
    repeated_rewatch = client.post(f"/api/v1/library/{media_id}/rewatch", json=rewatch_body)
    assert rewatch.status_code == 200
    assert repeated_rewatch.json()["watched"] is True
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(WatchEvent)) == 2

    unwatched = client.put(f"/api/v1/library/{media_id}/watched", json={"watched": False})
    assert unwatched.status_code == 200
    assert unwatched.json()["watched"] is False
    assert unwatched.json()["watch_status"] == "PLAN_TO_WATCH"
    repeated_unwatch = client.put(
        f"/api/v1/library/{media_id}/watched", json={"watched": False}
    )
    assert repeated_unwatch.json()["watched"] is False
    assert client.get("/api/v1/library").json()[0]["watched"] is False
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(WatchEvent)) == 3


def test_library_feedback_can_be_saved_and_cleared(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 101, "media_type": "MOVIE"},
    )
    media_id = imported.json()["media"]["id"]

    updated = client.patch(
        f"/api/v1/library/{media_id}/feedback",
        json={
            "personal_rating": 8.5,
            "personal_review": "A favorite.",
            "personal_notes": "Watch again with friends.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["personal_rating"] == 8.5
    assert updated.json()["personal_review"] == "A favorite."
    assert updated.json()["personal_notes"] == "Watch again with friends."
    library_entry = client.get("/api/v1/library").json()[0]
    assert library_entry["personal_rating"] == 8.5
    assert library_entry["personal_review"] == "A favorite."
    assert library_entry["personal_notes"] == "Watch again with friends."
    assert client.get(f"/api/v1/library/{media_id}").json()["personal_rating"] == 8.5

    invalid = client.patch(
        f"/api/v1/library/{media_id}/feedback",
        json={"personal_rating": 11},
    )
    assert invalid.status_code == 422
    cleared = client.patch(
        f"/api/v1/library/{media_id}/feedback",
        json={"personal_rating": None, "personal_review": None, "personal_notes": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["personal_rating"] is None
    assert cleared.json()["personal_review"] is None
    assert cleared.json()["personal_notes"] is None
    with test_session() as db:
        entry = db.scalar(select(UserLibrary))
        assert entry is not None
        assert entry.personal_rating is None


def test_episode_sync_preserves_history_and_season_actions_skip_future_episodes(
    api_client,
) -> None:
    client, test_session, _ = api_client

    class EpisodeTvmazeClient:
        def find_matching_show(
            self, title: str, first_air_date: str | date | None
        ) -> dict:
            return {"id": 777}

        def get_episodes(self, show_id: int) -> list[dict]:
            assert show_id == 777
            return [
                {
                    "tvmaze_id": 7001,
                    "season_number": 1,
                    "episode_number": 1,
                    "title": "Already aired",
                    "overview": "Past episode",
                    "air_at": None,
                    "air_date": date(2020, 1, 1),
                    "runtime": 44,
                    "still_path": None,
                },
                {
                    "tvmaze_id": 7002,
                    "season_number": 1,
                    "episode_number": 2,
                    "title": "Not yet aired",
                    "overview": None,
                    "air_at": None,
                    "air_date": date(2100, 1, 1),
                    "runtime": 44,
                    "still_path": None,
                },
                {
                    "tvmaze_id": 7003,
                    "season_number": 2,
                    "episode_number": 1,
                    "title": "Unknown date",
                    "overview": None,
                    "air_at": None,
                    "air_date": None,
                    "runtime": None,
                    "still_path": None,
                },
            ]

    app.dependency_overrides[get_tvmaze_client] = lambda: EpisodeTvmazeClient()
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 202, "media_type": "TV"},
    )
    media_id = imported.json()["media"]["id"]
    synced = client.post(f"/api/v1/library/{media_id}/episodes/sync")
    assert synced.status_code == 200
    assert synced.json()["episode_count"] == 3

    first_episode = next(
        episode
        for season in synced.json()["seasons"]
        for episode in season["episodes"]
        if episode["title"] == "Already aired"
    )
    marked = client.put(
        f"/api/v1/episodes/{first_episode['id']}/watched",
        json={"watched": True},
    )
    repeated = client.put(
        f"/api/v1/episodes/{first_episode['id']}/watched",
        json={"watched": True},
    )
    assert marked.status_code == 200
    assert repeated.json()["watched"] is True
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(WatchEvent)) == 1

    rewatch_body = {"idempotency_key": str(uuid4())}
    rewatch = client.post(
        f"/api/v1/episodes/{first_episode['id']}/rewatch", json=rewatch_body
    )
    repeated_rewatch = client.post(
        f"/api/v1/episodes/{first_episode['id']}/rewatch", json=rewatch_body
    )
    assert rewatch.status_code == 200
    assert repeated_rewatch.json()["watched"] is True
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(WatchEvent)) == 2

    synced_again = client.post(f"/api/v1/library/{media_id}/episodes/sync")
    assert synced_again.status_code == 200
    assert synced_again.json()["watched_count"] == 1
    season_one = next(
        season
        for season in synced_again.json()["seasons"]
        if season["season_number"] == 1
    )
    season_watched = client.put(
        f"/api/v1/seasons/{season_one['id']}/watched",
        json={"watched": True},
    )
    assert season_watched.status_code == 200
    assert season_watched.json()["watched_count"] == 1
    assert season_watched.json()["episode_count"] == 3
    with test_session() as db:
        events = db.scalars(select(WatchEvent)).all()
        assert len(events) == 2

    season_unwatched = client.put(
        f"/api/v1/seasons/{season_one['id']}/watched",
        json={"watched": False},
    )
    assert season_unwatched.status_code == 200
    assert season_unwatched.json()["watched_count"] == 0
    unknown_episode = next(
        episode
        for season in season_unwatched.json()["seasons"]
        for episode in season["episodes"]
        if episode["title"] == "Unknown date"
    )
    manually_watched = client.put(
        f"/api/v1/episodes/{unknown_episode['id']}/watched",
        json={"watched": True},
    )
    assert manually_watched.status_code == 200
    assert client.get(f"/api/v1/library/{media_id}/episodes").json()["watched_count"] == 1
    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(WatchEvent)) == 4


def test_marking_later_season_watched_also_marks_previous_seasons(api_client) -> None:
    client, test_session, _ = api_client
    imported = client.post(
        "/api/v1/media/import",
        json={"provider": "tmdb", "external_id": 408, "media_type": "TV"},
    )
    media_id = UUID(imported.json()["media"]["id"])

    with test_session() as db:
        first_season = Season(media_id=media_id, season_number=1, name="Season 1")
        second_season = Season(media_id=media_id, season_number=2, name="Season 2")
        db.add_all([first_season, second_season])
        db.flush()
        db.add_all(
            [
                Episode(
                    season_id=first_season.id,
                    tvmaze_id=747,
                    episode_number=1,
                    title="Earlier episode with no air date",
                ),
                Episode(
                    season_id=second_season.id,
                    tvmaze_id=748,
                    episode_number=1,
                    title="Aired episode",
                    air_date=date(2020, 1, 1),
                ),
                Episode(
                    season_id=second_season.id,
                    tvmaze_id=749,
                    episode_number=2,
                    title="Future episode",
                    air_date=date(2100, 1, 1),
                ),
            ]
        )
        db.commit()
        second_season_id = second_season.id

    response = client.put(
        f"/api/v1/seasons/{second_season_id}/watched",
        json={"watched": True},
    )

    assert response.status_code == 200
    assert response.json()["watched_count"] == 2
    assert response.json()["episode_count"] == 3
    watched_by_season = {
        season["season_number"]: [episode["watched"] for episode in season["episodes"]]
        for season in response.json()["seasons"]
    }
    assert watched_by_season == {1: [True], 2: [True, False]}
