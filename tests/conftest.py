import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Tests must not depend on credentials that happen to be set on the developer's machine."""
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)