"""Mastodon — https://docs.joinmastodon.org/methods/statuses/#create"""
import uuid

from app.platforms.base import BasePlatform, PostResult


class MastodonPlatform(BasePlatform):
    name = "Mastodon"
    credentials = ("mastodon_access_token",)

    async def publish(self, message: str) -> PostResult:
        base = self.settings.mastodon_base_url.rstrip("/")
        resp = await self.client.post(
            f"{base}/api/v1/statuses",
            headers={
                "Authorization": f"Bearer {self.settings.mastodon_access_token}",
                "Idempotency-Key": str(uuid.uuid4()),
            },
            data={"status": message, "visibility": "public"},
        )
        resp.raise_for_status()
        return PostResult(url=resp.json()["url"])
