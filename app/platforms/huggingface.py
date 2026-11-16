"""Hugging Face Hub — opens a public community discussion on a repo.
Docs: https://huggingface.co/docs/huggingface_hub/package_reference/hf_api (create_discussion)
"""
from app.platforms.base import BasePlatform, PlatformError, PostResult, make_title


class HuggingFacePlatform(BasePlatform):
    name = "Hugging Face"
    credentials = ("hf_token",)

    async def publish(self, message: str) -> PostResult:
        headers = {"Authorization": f"Bearer {self.settings.hf_token}"}

        # 1. Who am I?
        whoami = await self.client.get("https://huggingface.co/api/whoami-v2", headers=headers)
        whoami.raise_for_status()
        username = whoami.json()["name"]

        repo_id = self.settings.hf_repo_id or f"{username}/announcements"
        repo_name = repo_id.split("/")[-1]

        # 2. Make sure a public repo exists (409 = already exists, which is fine)
        created = await self.client.post(
            "https://huggingface.co/api/repos/create",
            headers=headers,
            json={"name": repo_name, "type": "model", "private": False},
        )
        if created.status_code not in (200, 201, 409):
            created.raise_for_status()

        # 3. Open a public discussion with the message
        resp = await self.client.post(
            f"https://huggingface.co/api/models/{repo_id}/discussions",
            headers=headers,
            json={"title": make_title(message), "description": message, "pullRequest": False},
        )
        resp.raise_for_status()
        num = resp.json().get("num")
        if not num:
            raise PlatformError("Hugging Face returned no discussion number")
        return PostResult(url=f"https://huggingface.co/{repo_id}/discussions/{num}")