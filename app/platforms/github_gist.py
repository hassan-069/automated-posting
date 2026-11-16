"""GitHub Gist — https://docs.github.com/en/rest/gists/gists#create-a-gist"""
from app.platforms.base import BasePlatform, PostResult, make_title


class GitHubGistPlatform(BasePlatform):
    name = "GitHub Gist"
    credentials = ("github_token",)

    async def publish(self, message: str) -> PostResult:
        resp = await self.client.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"Bearer {self.settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"description": make_title(message), "public": True, "files": {"post.md": {"content": message}}},
        )
        resp.raise_for_status()
        return PostResult(url=resp.json()["html_url"])
