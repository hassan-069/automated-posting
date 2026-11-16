"""Orchestrates publishing a message to every platform, independently and concurrently."""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.platforms.base import BasePlatform, PlatformError
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)

_VERIFY_ATTEMPTS = 3
_VERIFY_DELAY_SECONDS = 1.0


def describe_error(exc: BaseException) -> str:
    """Turn an exception into a short, client-safe message (never leaks URLs/tokens)."""
    if isinstance(exc, PlatformError):
        return str(exc)
    if isinstance(exc, (asyncio.TimeoutError, httpx.TimeoutException)):
        return "Request timed out"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return f"Authentication failed (HTTP {code})"
        if code == 429:
            return "Rate limited by platform (HTTP 429)"
        return f"HTTP {code}: {exc.response.text[:200].strip()}"
    if isinstance(exc, httpx.RequestError):
        return f"Network error ({type(exc).__name__})"
    return f"Unexpected error ({type(exc).__name__})"


class PostingService:
    def __init__(
        self,
        platforms: list[BasePlatform],
        client: httpx.AsyncClient,
        platform_timeout: float = 30.0,
        verify_delay: float = _VERIFY_DELAY_SECONDS,
    ) -> None:
        self.platforms = platforms
        self.client = client
        self.platform_timeout = platform_timeout
        self.verify_delay = verify_delay

    async def publish_all(self, message: str) -> list[PlatformResult]:
        """Post to all platforms concurrently; one platform failing never affects the others."""
        return list(await asyncio.gather(*(self._publish_one(p, message) for p in self.platforms)))

    async def _publish_one(self, platform: BasePlatform, message: str) -> PlatformResult:
        missing = platform.missing_credentials()
        if missing:
            return self._failed(platform.name, f"Missing credentials: {', '.join(missing)}")

        try:
            post = await asyncio.wait_for(platform.publish(message), timeout=self.platform_timeout)
        except Exception as exc:  # noqa: BLE001 - isolation boundary: never let one platform break the rest
            error = describe_error(exc)
            logger.warning("%s failed: %s", platform.name, error)
            return self._failed(platform.name, error)

        posted_at = datetime.now(timezone.utc)
        public = await self._is_public(post.verify_url or post.url)
        logger.info("%s posted: %s (public=%s)", platform.name, post.url, public)
        return PlatformResult(
            platform=platform.name,
            status="success",
            posted_url=post.url,
            public_access=public,
            date=posted_at.strftime("%Y-%m-%d"),
            time=posted_at.strftime("%H:%M:%S"),
            error=None,
        )

    async def _is_public(self, url: str) -> bool:
        """Fetch ``url`` anonymously (no credentials) and check it is reachable."""
        for attempt in range(_VERIFY_ATTEMPTS):
            try:
                resp = await self.client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
            if attempt < _VERIFY_ATTEMPTS - 1:
                await asyncio.sleep(self.verify_delay)  # new posts can take a moment to appear
        return False

    @staticmethod
    def _failed(platform: str, error: str) -> PlatformResult:
        return PlatformResult(platform=platform, status="failed", public_access=False, error=error)
