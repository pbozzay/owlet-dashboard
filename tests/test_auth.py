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
