"""Common interface every platform integration implements."""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

import httpx

from app.config import Settings
from app.validators import URL_CANDIDATE


class PlatformError(Exception):
    """A platform-specific failure with a message that is safe to show to API clients."""


@dataclass(frozen=True)
class PostResult:
    url: str                       # public URL of the published content
    verify_url: str | None = None  # optional URL to probe instead of ``url`` for public access


def make_title(message: str, limit: int = 70) -> str:
    """Derive a short title (for blog-style platforms) from the message."""
    text = re.sub(r"\s+", " ", URL_CANDIDATE.sub("", message)).strip(" -–—:")
    text = text or "Update"
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class BasePlatform(ABC):
    name: ClassVar[str]
    #: Names of Settings attributes that must be set for this platform to run.
    credentials: ClassVar[tuple[str, ...]] = ()

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    def missing_credentials(self) -> list[str]:
        """Env-var names (upper case) of any credentials that are not configured."""
        return [attr.upper() for attr in self.credentials if not getattr(self.settings, attr)]

    @abstractmethod
    async def publish(self, message: str) -> PostResult:
        """Publish ``message`` and return its public URL. Raise on failure."""
