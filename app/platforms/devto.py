"""Dev.to (Forem API v1) — https://developers.forem.com/api/v1"""
from app.platforms.base import BasePlatform, PostResult, make_title


class DevToPlatform(BasePlatform):
    name = "Dev.to"
    credentials = ("devto_api_key",)

    async def publish(self, message: str) -> PostResult:
        resp = await self.client.post(
            "https://dev.to/api/articles",
            headers={
                "api-key": self.settings.devto_api_key,
                "Accept": "application/vnd.forem.api-v1+json",
            },
            json={"article": {"title": make_title(message), "body_markdown": message, "published": True}},
        )
        resp.raise_for_status()
        return PostResult(url=resp.json()["url"])
