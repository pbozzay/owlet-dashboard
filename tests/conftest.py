import pytest
from fastapi.testclient import TestClient

from app.auth_store import AuthStore
from app.config import Settings
from app.main import create_app
from app.security import hash_password, hash_token, new_token
from app.store import ReadingStore


def test_settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


@pytest.fixture
def app_bundle(tmp_path):
    """(app, store, auth_store) wired against a tmp SQLite file."""
    store = ReadingStore(tmp_path / "owlet.sqlite3")
    auth_store = AuthStore(tmp_path / "owlet.sqlite3")
    app = create_app(store=store, settings=test_settings(), start_poller=False, auth_store=auth_store)
    return app, store, auth_store


async def make_user(auth_store: AuthStore, email: str) -> tuple[dict, str]:
    """Create a user + session directly; returns (user, raw_session_token)."""
    user = await auth_store.create_user(email, hash_password("hunter22"))
    raw = new_token()
    await auth_store.create_session(user["id"], hash_token(raw))
    return user, raw


def client_for(app, session_token: str | None = None) -> TestClient:
    client = TestClient(app)
    if session_token:
        client.cookies.set("owlet_session", session_token)
    return client
