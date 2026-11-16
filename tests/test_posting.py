import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_service
from app.platforms.base import BasePlatform, PostResult
from app.platforms.devto import DevToPlatform
from app.platforms.huggingface import HuggingFacePlatform
from app.platforms.mastodon import MastodonPlatform
from app.services.posting_service import PostingService

MESSAGE = "Grow your online visibility https://example.com"


class FakeOK(BasePlatform):
    name = "FakeOK"

    async def publish(self, message):
        return PostResult(url="https://ok.test/post/1")


class FakeBoom(BasePlatform):
    name = "FakeBoom"

    async def publish(self, message):
        raise RuntimeError("secret-token-123 exploded")


class FakeAuth(BasePlatform):
    name = "FakeAuth"

    async def publish(self, message):
        req = httpx.Request("POST", "https://x.test/?token=secret")
        raise httpx.HTTPStatusError("nope", request=req, response=httpx.Response(401, request=req))


class FakeNoCreds(BasePlatform):
    name = "FakeNoCreds"
    credentials = ("devto_api_key",)

    async def publish(self, message):
        raise AssertionError("must not be called without credentials")


class FakeSlow(BasePlatform):
    name = "FakeSlow"

    async def publish(self, message):
        await asyncio.sleep(5)


def make_service(platforms, status=200, timeout=30.0):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(status)))
    settings = Settings(_env_file=None)
    return PostingService([p(settings, client) for p in platforms], client, timeout, verify_delay=0)


def run(service, message=MESSAGE):
    return asyncio.run(service.publish_all(message))


def test_one_failure_does_not_stop_the_others():
    results = run(make_service([FakeBoom, FakeOK, FakeAuth, FakeNoCreds]))
    by_name = {r.platform: r for r in results}

    assert by_name["FakeOK"].status == "success"
    assert by_name["FakeOK"].public_access is True
    assert by_name["FakeOK"].posted_url == "https://ok.test/post/1"
    assert by_name["FakeOK"].date and by_name["FakeOK"].time

    assert by_name["FakeBoom"].status == "failed"
    assert "secret-token" not in by_name["FakeBoom"].error  # no leaking of exception text
    assert by_name["FakeAuth"].error == "Authentication failed (HTTP 401)"
    assert by_name["FakeNoCreds"].error == "Missing credentials: DEVTO_API_KEY"
    assert by_name["FakeNoCreds"].posted_url is None and by_name["FakeNoCreds"].date is None


def test_public_access_false_when_url_not_reachable():
    results = run(make_service([FakeOK], status=404))
    assert results[0].status == "success"
    assert results[0].public_access is False


def test_platform_timeout():
    results = run(make_service([FakeSlow], timeout=0.05))
    assert results[0].status == "failed"
    assert results[0].error == "Request timed out"


def test_endpoint_success_flag(monkeypatch):
    app.dependency_overrides[get_service] = lambda: make_service([FakeBoom, FakeOK])
    try:
        client = TestClient(app)
        body = client.post("/posting", json={"message": MESSAGE}).json()
        assert body["success"] is True and len(body["results"]) == 2

        app.dependency_overrides[get_service] = lambda: make_service([FakeBoom])
        assert client.post("/posting", json={"message": MESSAGE}).json()["success"] is False
    finally:
        app.dependency_overrides.clear()


# --- adapter-level tests against mocked HTTP -------------------------------------------------

def adapter(cls, handler, **settings):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return cls(Settings(_env_file=None, **settings), client)


def test_devto_adapter():
    def handler(req):
        assert req.headers["api-key"] == "k"
        return httpx.Response(201, json={"url": "https://dev.to/me/post-1"})

    result = asyncio.run(adapter(DevToPlatform, handler, devto_api_key="k").publish(MESSAGE))
    assert result.url == "https://dev.to/me/post-1"


def test_mastodon_adapter():
    def handler(req):
        assert req.url.path == "/api/v1/statuses"
        return httpx.Response(200, json={"url": "https://mastodon.social/@me/1"})

    p = adapter(MastodonPlatform, handler, mastodon_access_token="t")
    assert asyncio.run(p.publish(MESSAGE)).url == "https://mastodon.social/@me/1"


def test_huggingface_adapter():
    def handler(req):
        if req.url.path == "/api/whoami-v2":
            return httpx.Response(200, json={"name": "me"})
        if req.url.path == "/api/repos/create":
            return httpx.Response(409, json={"error": "already exists"})
        if req.url.path == "/api/models/me/announcements/discussions":
            body = json.loads(req.content)
            assert body["description"] == MESSAGE
            return httpx.Response(200, json={"num": 3})
        return httpx.Response(404)

    p = adapter(HuggingFacePlatform, handler, hf_token="t", hf_repo_id=None)
    assert asyncio.run(p.publish(MESSAGE)).url == "https://huggingface.co/me/announcements/discussions/3"