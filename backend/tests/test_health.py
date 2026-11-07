from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_does_not_require_database() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "not_checked"}


def test_api_v1_root() -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"name": "FRAME API", "version": "v1"}
