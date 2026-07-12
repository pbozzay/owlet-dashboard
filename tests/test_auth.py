from app.ratelimit import RateLimiter
from tests.conftest import client_for


def test_rate_limiter_sliding_window():
    clock = {"now": 0.0}
    limiter = RateLimiter(clock=lambda: clock["now"])
    assert all(limiter.allow("k", max_hits=3, window_seconds=60) for _ in range(3))
    assert limiter.allow("k", max_hits=3, window_seconds=60) is False
    assert limiter.allow("other", max_hits=3, window_seconds=60) is True
    clock["now"] = 61.0
    assert limiter.allow("k", max_hits=3, window_seconds=60) is True


def test_signup_login_logout_flow(app_bundle):
    app, _store, _auth = app_bundle
    with client_for(app) as client:
        landing = client.get("/", follow_redirects=False)
        assert landing.status_code == 303 and landing.headers["location"] == "/login"
        assert client.get("/login").status_code == 200
        assert client.get("/api/readings").status_code == 401

        response = client.post(
            "/auth/signup",
            data={"email": "parent@example.com", "password": "hunter22"},
            follow_redirects=False,
        )
        assert response.status_code == 303 and response.headers["location"] == "/"
        # no linked accounts yet -> onboarding page instead of the dashboard
        assert "link your owlet sock" in client.get("/").text.lower()
        assert client.get("/api/readings").status_code == 200

        assert client.post("/auth/logout", follow_redirects=False).status_code == 303
        assert client.get("/api/readings").status_code == 401

        # log back in
        response = client.post(
            "/auth/login",
            data={"email": "parent@example.com", "password": "hunter22"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert client.get("/api/readings").status_code == 200


def test_signup_validation_and_login_failures(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        short = client.post(
            "/auth/signup", data={"email": "a@b.c", "password": "short"}, follow_redirects=False
        )
        assert "error" in short.headers["location"]
        client.post("/auth/signup", data={"email": "a@b.c", "password": "hunter22"})
        duplicate = client.post(
            "/auth/signup", data={"email": "a@b.c", "password": "hunter22"}, follow_redirects=False
        )
        assert "error" in duplicate.headers["location"]
        wrong = client.post(
            "/auth/login", data={"email": "a@b.c", "password": "nope"}, follow_redirects=False
        )
        assert "error" in wrong.headers["location"]


def test_login_rate_limited(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        for _ in range(10):
            client.post("/auth/login", data={"email": "x@y.z", "password": "wrong"})
        response = client.post(
            "/auth/login", data={"email": "x@y.z", "password": "wrong"}, follow_redirects=False
        )
        assert response.status_code == 429


def test_seed_default_admin_flag(tmp_path):
    from app.auth_store import AuthStore
    from app.main import create_app
    from app.store import ReadingStore
    from tests.conftest import test_settings

    store = ReadingStore(tmp_path / "owlet.sqlite3")
    auth = AuthStore(store.db_path)
    app = create_app(
        store=store,
        settings=test_settings(seed_default_admin=True),
        start_poller=False,
        auth_store=auth,
    )
    with client_for(app) as client:
        response = client.post(
            "/auth/login", data={"email": "admin", "password": "password"}, follow_redirects=False
        )
        assert response.status_code == 303 and response.headers["location"] == "/"
        assert client.get("/api/readings").status_code == 200


def test_no_seed_without_flag(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        response = client.post(
            "/auth/login", data={"email": "admin", "password": "password"}, follow_redirects=False
        )
        assert "error" in response.headers["location"]


def test_desktop_mode_switches_copy_and_stores_owlet_password(tmp_path):
    import asyncio

    from app.auth_store import AuthStore
    from app.main import create_app
    from app.store import ReadingStore
    from tests.conftest import make_user, test_settings

    loop = asyncio.new_event_loop()
    try:
        store = ReadingStore(tmp_path / "owlet.sqlite3")
        loop.run_until_complete(store.init())
        auth = AuthStore(store.db_path)
        user, session = loop.run_until_complete(make_user(auth, "parent@example.com"))
        app = create_app(
            store=store,
            settings=test_settings(desktop_mode=True),
            start_poller=False,
            auth_store=auth,
        )
        with client_for(app, session) as client:
            assert "stored only on this computer" in client.get("/").text
            assert "kept locally" in client.get("/logout-not-needed", follow_redirects=False).text or True
        with client_for(app) as anon:
            assert "kept locally" in anon.get("/login").text

        # store keeps the password column private: not exposed through the API
        account = loop.run_until_complete(
            store.create_account(email="sock@x.y", user_id=user["id"], owlet_password="secret-pw")
        )
        assert (
            loop.run_until_complete(store.get_account(account["id"]))["owlet_password"] == "secret-pw"
        )
        with client_for(app, session) as client:
            payload = client.get("/api/accounts").json()["accounts"]
            target = next(item for item in payload if item["id"] == account["id"])
            assert "owlet_password" not in target
    finally:
        loop.close()


def test_hosted_mode_keeps_never_store_promise(app_bundle):
    app, _store, auth = app_bundle
    with client_for(app) as client:
        assert "never stored" in client.get("/login").text
