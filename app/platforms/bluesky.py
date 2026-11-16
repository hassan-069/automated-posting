"""Bluesky (AT Protocol) — https://docs.bsky.app/docs/api/com-atproto-repo-create-record"""
from datetime import datetime, timezone

from app.platforms.base import BasePlatform, PlatformError, PostResult
from app.validators import extract_urls


def _link_facets(text: str) -> list[dict]:
    """Make URLs clickable. Facet offsets are UTF-8 *byte* positions."""
    facets = []
    for url in extract_urls(text):
        start = text.find(url)
        byte_start = len(text[:start].encode("utf-8"))
        facets.append(
            {
                "index": {"byteStart": byte_start, "byteEnd": byte_start + len(url.encode("utf-8"))},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
            }
        )
    return facets


class BlueskyPlatform(BasePlatform):
    name = "Bluesky"
    credentials = ("bluesky_handle", "bluesky_app_password")

    async def publish(self, message: str) -> PostResult:
        pds = self.settings.bluesky_pds_url.rstrip("/")

        session = await self.client.post(
            f"{pds}/xrpc/com.atproto.server.createSession",
            json={"identifier": self.settings.bluesky_handle, "password": self.settings.bluesky_app_password},
        )
        session.raise_for_status()
        s = session.json()

        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "facets": _link_facets(message),
        }
        resp = await self.client.post(
            f"{pds}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {s['accessJwt']}"},
            json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": record},
        )
        resp.raise_for_status()
        at_uri = resp.json().get("uri")
        if not at_uri:
            raise PlatformError("Bluesky did not return a post URI")

        rkey = at_uri.rsplit("/", 1)[-1]
        return PostResult(
            url=f"https://bsky.app/profile/{s['handle']}/post/{rkey}",
            # bsky.app is a SPA that always returns 200, so verify via the public AppView API instead.
            verify_url=f"https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri={at_uri}&depth=0",
        )
