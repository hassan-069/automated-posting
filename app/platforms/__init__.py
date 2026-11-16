"""Platform registry. To add a platform: create a BasePlatform subclass and list it here."""
import httpx

from app.config import Settings
from app.platforms.base import BasePlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.github_gist import GitHubGistPlatform
from app.platforms.huggingface import HuggingFacePlatform
from app.platforms.mastodon import MastodonPlatform

ALL_PLATFORMS: tuple[type[BasePlatform], ...] = (
     DevToPlatform,
     MastodonPlatform,
     BlueskyPlatform,
     HuggingFacePlatform,
     GitHubGistPlatform,
)


def build_platforms(settings: Settings, client: httpx.AsyncClient) -> list[BasePlatform]:
    return [cls(settings, client) for cls in ALL_PLATFORMS]