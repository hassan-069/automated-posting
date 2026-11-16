"""Pure validation helpers for the incoming message and its CTA link."""
import re
from urllib.parse import urlparse

MAX_MESSAGE_LENGTH = 200

# Matches "scheme://..." or "www...." tokens that are not glued to a preceding word.
URL_CANDIDATE = re.compile(r"(?<![\w.\-])(?:[a-zA-Z][a-zA-Z0-9+.\-]*://|www\.)\S+")
_TRAILING_PUNCTUATION = ".,;:!?)]}>\"'"
_HOST_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
_TLD = re.compile(r"^[a-z]{2,63}$", re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    """Return every URL-looking token in ``text`` (trailing punctuation removed)."""
    return [m.rstrip(_TRAILING_PUNCTUATION) for m in URL_CANDIDATE.findall(text)]


def validate_url(url: str) -> str:
    """Raise ValueError unless ``url`` is a well-formed public http(s) URL."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("CTA link must start with http:// or https://")
    try:
        _ = parsed.port  # raises ValueError on an invalid port
    except ValueError:
        raise ValueError("CTA link has an invalid port") from None
    if parsed.username or parsed.password:
        raise ValueError("CTA link must not contain credentials")

    host = parsed.hostname
    if not host:
        raise ValueError("CTA link has no hostname")
    labels = host.split(".")
    if len(labels) < 2 or not all(_HOST_LABEL.match(label) for label in labels):
        raise ValueError(f"CTA link has an invalid hostname: '{host}'")
    if not _TLD.match(labels[-1]):
        raise ValueError(f"CTA link has an invalid domain extension: '.{labels[-1]}'")
    return url


def validate_message(message: str) -> str:
    """Enforce: non-empty, <= 200 chars, exactly one valid CTA link."""
    message = message.strip()
    if not message:
        raise ValueError("Message must not be empty")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message must not exceed {MAX_MESSAGE_LENGTH} characters (got {len(message)})"
        )
    urls = extract_urls(message)
    if len(urls) != 1:
        raise ValueError(f"Message must contain exactly one CTA link (found {len(urls)})")
    validate_url(urls[0])
    return message
