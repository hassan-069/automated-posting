import pytest
from fastapi.testclient import TestClient

from app.main import app, get_service


class _NoopService:
    async def publish_all(self, message):
        return []


@pytest.fixture
def client():
    app.dependency_overrides[get_service] = lambda: _NoopService()
    yield TestClient(app)
    app.dependency_overrides.clear()


def post(client, message):
    return client.post("/posting", json={"message": message})


@pytest.mark.parametrize(
    "message",
    [
        "Check out our platform https://example.com",
        "Visit https://example.com/path?a=1&b=2#frag today",
        "See (https://sub.example.co.uk/page).",
        "x" * 160 + " https://example.com",  # exactly <= 200
    ],
)
def test_valid_messages(client, message):
    assert len(message) <= 200
    assert post(client, message).status_code == 200


def _msg(resp):
    return resp.json()["errors"][0]["message"]


def test_too_long(client):
    resp = post(client, "x" * 190 + " https://example.com")
    assert resp.status_code == 422
    assert "200 characters" in _msg(resp)


def test_no_link(client):
    resp = post(client, "Hello world, no link here")
    assert resp.status_code == 422
    assert "exactly one CTA link (found 0)" in _msg(resp)


def test_two_links(client):
    resp = post(client, "https://a.com and https://b.com")
    assert resp.status_code == 422
    assert "found 2" in _msg(resp)


@pytest.mark.parametrize(
    "bad_url",
    ["ftp://example.com", "www.example.com", "https://localhost", "https://exa_mple.com", "https://-bad.com", "https://example.c0m"],
)
def test_invalid_urls(client, bad_url):
    resp = post(client, f"Check this {bad_url}")
    assert resp.status_code == 422, bad_url


def test_empty_and_missing_message(client):
    assert post(client, "   ").status_code == 422
    resp = client.post("/posting", json={})
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "message"


def test_wrong_type(client):
    assert client.post("/posting", json={"message": 123}).status_code == 422
