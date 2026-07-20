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


def test_change_email_and_password(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        client.post("/auth/signup", data={"email": "parent@example.com", "password": "hunter22"})

        # wrong current password -> rejected, nothing changes
        rejected = client.post(
            "/auth/change-email",
            json={"current_password": "nope", "email": "new@example.com"},
        )
        assert rejected.status_code == 403

        # email change
        changed = client.post(
            "/auth/change-email",
            json={"current_password": "hunter22", "email": "New@Example.com"},
        )
        assert changed.status_code == 200 and changed.json()["email"] == "new@example.com"
        assert client.get("/api/me").json()["email"] == "new@example.com"

        # a second signed-in device...
        with client_for(app) as other:
            other.post(
                "/auth/login", data={"email": "new@example.com", "password": "hunter22"}
            )
            assert other.get("/api/readings").status_code == 200

            # ...gets signed out when the password changes here
            weak = client.post(
                "/auth/change-password",
                json={"current_password": "hunter22", "new_password": "short"},
            )
            assert weak.status_code == 400
            changed = client.post(
                "/auth/change-password",
                json={"current_password": "hunter22", "new_password": "hunter2222"},
            )
            assert changed.status_code == 200
            assert changed.json()["other_sessions_signed_out"] == 1
            assert other.get("/api/readings").status_code == 401   # kicked
        assert client.get("/api/readings").status_code == 200       # this session survives

        # old password dead, new one works
        with client_for(app) as fresh:
            old = fresh.post(
                "/auth/login",
                data={"email": "new@example.com", "password": "hunter22"},
                follow_redirects=False,
            )
            assert "error" in old.headers["location"]
            good = fresh.post(
                "/auth/login",
                data={"email": "new@example.com", "password": "hunter2222"},
                follow_redirects=False,
            )
            assert good.headers["location"] == "/"

        # duplicate email is a conflict
        with client_for(app) as second_user:
            second_user.post("/auth/signup", data={"email": "b@example.com", "password": "hunter22"})
            conflict = second_user.post(
                "/auth/change-email",
                json={"current_password": "hunter22", "email": "new@example.com"},
            )
            assert conflict.status_code == 409


def test_login_rate_limited(app_bundle):
    app, *_ = app_bundle
    with client_for(app) as client:
        for _ in range(10):
            client.post("/auth/login", data={"email": "x@y.z", "password": "wrong"})
        response = client.post(
            "/auth/login", data={"email": "x@y.z", "password": "wrong"}, follow_redirects=False
        )
        assert response.status_code == 429


def test_desktop_mode_needs_no_login(tmp_path):
    from app.auth_store import AuthStore
    from app.main import create_app
    from app.store import ReadingStore
    from tests.conftest import test_settings

    store = ReadingStore(tmp_path / "owlet.sqlite3")
    auth = AuthStore(store.db_path)
    app = create_app(
        store=store,
        settings=test_settings(desktop_mode=True, database_path=str(tmp_path / "owlet.sqlite3")),
        start_poller=False,
        auth_store=auth,
    )
    with client_for(app) as client:
        client.post("/desktop/use-local", follow_redirects=False)  # past the launcher
        # no session cookie, no login — every request is the local admin
        assert client.get("/api/readings").status_code == 200
        assert client.get("/api/me").json()["email"] == "admin"
        landing = client.get("/login", follow_redirects=False)
        assert landing.status_code == 303 and landing.headers["location"] == "/"
        # local mode -> straight to onboarding, never a sign-in page
        assert "link your owlet sock" in client.get("/").text.lower()


def test_desktop_launcher_and_remote_connect(tmp_path, monkeypatch):
    import app.main as main_module
    from app.auth_store import AuthStore
    from app.main import create_app
    from app.store import ReadingStore
    from tests.conftest import test_settings

    store = ReadingStore(tmp_path / "owlet.sqlite3")
    auth = AuthStore(store.db_path)
    settings = test_settings(desktop_mode=True, database_path=str(tmp_path / "owlet.sqlite3"))
    app = create_app(store=store, settings=settings, start_poller=False, auth_store=auth)

    with client_for(app) as client:
        # first run -> launcher, not onboarding
        home = client.get("/")
        assert "How do you want to use this app?" in home.text

        # unreachable server is rejected, no config written
        async def _fail(url):
            return False

        monkeypatch.setattr(main_module, "_probe_owlet_instance", _fail)
        bad = client.post("/desktop/connect", json={"url": "https://nope.example"})
        assert bad.status_code == 400
        assert "How do you want to use this app?" in client.get("/").text

        # a reachable Owlet instance is saved; home then bounces to it
        async def _ok(url):
            return True

        monkeypatch.setattr(main_module, "_probe_owlet_instance", _ok)
        good = client.post("/desktop/connect", json={"url": "https://owlet.example/"})
        assert good.status_code == 200 and good.json()["url"] == "https://owlet.example"
        redirect = client.get("/")
        assert "owlet.example" in redirect.text and "location.replace" in redirect.text

        # switching to local clears the remote and returns to normal onboarding
        client.post("/desktop/use-local", follow_redirects=False)
        assert "link your owlet sock" in client.get("/").text.lower()


def test_desktop_routes_are_404_off_desktop(app_bundle):
    app, *_ = app_bundle  # hosted mode
    with client_for(app) as client:
        assert client.post("/desktop/connect", json={"url": "https://x"}).status_code == 404
        assert client.post("/desktop/use-local", follow_redirects=False).status_code == 404
        bounced = client.get("/desktop", follow_redirects=False)
        assert bounced.status_code == 303 and bounced.headers["location"] == "/"


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
            settings=test_settings(desktop_mode=True, database_path=str(tmp_path / "owlet.sqlite3")),
            start_poller=False,
            auth_store=auth,
        )
        with client_for(app, session) as client:
            client.post("/desktop/use-local", follow_redirects=False)  # past the launcher
            assert "stored only on this computer" in client.get("/").text
        with client_for(app) as anon:
            # desktop mode has no login at all — /login bounces straight home
            bounced = anon.get("/login", follow_redirects=False)
            assert bounced.status_code == 303 and bounced.headers["location"] == "/"

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
