Automated Multi-Platform Posting

A FastAPI service that takes one short message (with a single CTA link) and publishes it to several third-party platforms through their official APIs. Platforms are called concurrently and each one is isolated, so a failure on one platform never blocks the others.

Stack: Python 3.x · FastAPI · Uvicorn · Pydantic v2 · HTTPX · environment-based configuration

Platforms
Platform	Type	API used	Auth	Output
Dev.to	Developer blogging	Forem API v1 POST /api/articles	API key	Article URL
Mastodon	Social network	POST /api/v1/statuses	OAuth access token	Status URL
Bluesky	Social network	AT Protocol createSession + createRecord	App password	bsky.app post URL
Hugging Face	AI / LLM platform	Hub API: create public repo + POST /discussions	Access token (write)	Discussion URL
GitHub Gist	Code / text hosting	POST /gists (public)	Token with gist scope	Gist URL

All five are free to use. Any platform without credentials is reported as failed ("Missing credentials: …") and skipped, so the app runs with whichever subset is configured.

Platforms evaluated but not included
Hashnode: since 13 May 2026 its GraphQL API requires a paid Pro plan, and the free endpoint (gql.hashnode.com) redirects to an announcement page.
Telegram: the Bot API works, but Telegram is not reachable from Pakistan without a VPN, so it could not be tested reliably.
Known platform behaviour
Hugging Face limits how fast new discussions can be created. Rapid repeated requests can return 429; the app reports this as a failed platform and still posts to the others (see the sample run below).
Dev.to may hide posts from new accounts when identical test posts are published repeatedly. The app detects this: public_access is false if the posted URL is not reachable anonymously.
Quick start
bash
git clone https://github.com/hassan-069/automated-posting.git
cd automated-posting
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
# fill in your credentials in .env
uvicorn app.main:app --host 0.0.0.0 --port 4000

Swagger UI: http://localhost:4000/docs

Configuration

All credentials come from environment variables (.env is git-ignored; .env.example contains no real values).

Variable	Where to get it
DEVTO_API_KEY	dev.to → Settings → Extensions → Generate API key
MASTODON_BASE_URL, MASTODON_ACCESS_TOKEN	Mastodon → Preferences → Development → New application (scope write:statuses)
BLUESKY_HANDLE, BLUESKY_APP_PASSWORD	Bluesky → Settings → Privacy and Security → App Passwords (use the full handle, e.g. name.bsky.social)
HF_TOKEN, HF_REPO_ID (optional)	huggingface.co → Settings → Access Tokens (write access). HF_REPO_ID defaults to <username>/announcements and is created automatically if missing
GITHUB_TOKEN	GitHub → Settings → Developer settings → Tokens (scope gist)
API
POST /posting
json
{ "message": "Wrote a small FastAPI service that shares one short update across several platforms through their official APIs: https://fastapi.tiangolo.com" }

Validation (failures return 422):

message is non-empty and at most 200 characters
exactly one link is present
the link is a valid http(s) URL (real hostname with a valid TLD, no embedded credentials, valid port)

Response (200): one entry per platform.

Field	Meaning
platform	Platform name
status	success or failed
posted_url	URL of the published content (null on failure)
public_access	true if the URL is reachable anonymously (checked with an unauthenticated request)
date / time	Posting date and time in UTC
error	Short, safe error message (null on success)

success at the top level is true if at least one platform succeeded. (Bluesky's public access is verified through its public AppView API, because bsky.app is a client-rendered SPA that always returns 200.)

Validation error (422):

bash
curl -X POST http://localhost:4000/posting -H "Content-Type: application/json" \
  -d '{"message": "no link here"}'
json
{"success": false, "errors": [{"field": "message", "message": "Message must contain exactly one CTA link (found 0)"}]}
GET /health

Returns {"status": "ok"}.

Sample run (real output)

Request:

bash
curl -X POST 'http://localhost:4000/posting' \
  -H 'Content-Type: application/json' \
  -d '{"message": "Wrote a small FastAPI service that shares one short update across several platforms through their official APIs: https://fastapi.tiangolo.com"}'

Response. Four platforms succeeded; Hugging Face was rate limited (429) and the others were unaffected:

json
{
  "success": true,
  "results": [
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/hassan069/wrote-a-small-fastapi-service-that-shares-one-short-update-across-sev-4m8",
      "public_access": true,
      "date": "2026-11-16",
      "time": "10:18:25",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@hassan069/117625605768577090",
      "public_access": true,
      "date": "2026-11-16",
      "time": "10:18:25",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/hassan069.bsky.social/post/3n2gcgom7hl27",
      "public_access": true,
      "date": "2026-11-16",
      "time": "10:18:26",
      "error": null
    },
    {
      "platform": "Hugging Face",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Rate limited by platform (HTTP 429)"
    },
    {
      "platform": "GitHub Gist",
      "status": "success",
      "posted_url": "https://gist.github.com/hassan-069/b801bb1d3b1ebd9da6e569fcea5de253",
      "public_access": true,
      "date": "2026-11-16",
      "time": "10:18:27",
      "error": null
    }
  ]
}

A separate run with only Hugging Face enabled succeeded:

json
{
  "success": true,
  "results": [
    {
      "platform": "Hugging Face",
      "status": "success",
      "posted_url": "https://huggingface.co/hassan069/announcements/discussions/1",
      "public_access": true,
      "date": "2026-11-16",
      "time": "10:15:14",
      "error": null
    }
  ]
}
Screenshots and logs

Everything is in docs/.

Evidence	File
Swagger UI with the POST /posting endpoint	docs/swagger-ui.png
Swagger UI: request and response of a real run	docs/swagger-run.png
Server logs of the same run (Hugging Face 429 isolated, the other platforms posted)	docs/terminal-logs.png
Test suite passing	docs/pytest.png
A published post opened while logged out	docs/live-post.png

Swagger run Server logs

Design notes
One adapter per platform (app/platforms/*.py) implementing BasePlatform.publish(). Adding a platform means one new file and one line in app/platforms/__init__.py.
Isolation and concurrency: PostingService runs all adapters with asyncio.gather; each is wrapped in its own try/except and a per-platform timeout, so one slow or failing platform cannot affect the rest.
Safe errors: exceptions are translated by describe_error() into short messages. Raw exception text and request URLs are never returned (some APIs put tokens in the URL).
Public access check: after posting, the service fetches the URL anonymously (with a short retry) and reports whether the content is actually publicly reachable.
Secrets live only in environment variables / .env.
Validation lives in app/validators.py as pure functions, wired in through a Pydantic v2 validator, with a custom handler that returns clean 422 responses.
Tests
bash
pytest

Covers input validation (length, zero or multiple links, malformed URLs), failure isolation, timeouts, missing credentials, public-access checks, error sanitisation, and adapter request/response parsing against mocked HTTP. No network access or real credentials are needed.

Project structure
app/
  main.py                    FastAPI app, /posting endpoint, error handler
  schemas.py                 Request / response models
  validators.py              Message + URL validation
  config.py                  Env-based settings
  platforms/                 base.py + one module per platform
  services/posting_service.py
tests/
docs/                        Screenshots and logs
.env.example  requirements.txt  README.md