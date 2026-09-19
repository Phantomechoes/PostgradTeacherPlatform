from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app

client = TestClient(app)


def test_health_returns_http_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_json():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_health_does_not_call_get_db():
    def _boom():
        raise AssertionError("GET /health must not depend on get_db")

    app.dependency_overrides[get_db] = _boom
    try:
        response = TestClient(app).get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
