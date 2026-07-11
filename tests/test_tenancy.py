import pytest

from app.auth_store import AuthStore
from app.main import create_app
from app.models import normalize_reading
from app.store import ReadingStore
from tests.conftest import client_for, make_user, test_settings


@pytest.fixture
async def two_tenants(tmp_path):
    db_path = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db_path)
    await store.init()
    auth = AuthStore(db_path)
    alice, alice_session = await make_user(auth, "alice@example.test")
    bob, _bob_session = await make_user(auth, "bob@example.test")
    alice_acc = await store.create_account(email="alice-sock@x.y", user_id=alice["id"])
    bob_acc = await store.create_account(email="bob-sock@x.y", user_id=bob["id"])
    for acc, hr in ((alice_acc, 110), (bob_acc, 155)):
        await store.insert_reading(
            normalize_reading(
                {"heart_rate": hr, "oxygen_saturation": 95, "last_updated": "2026-07-02T01:00:00Z"},
                f"SOCK{acc['id']}",
            ),
            account_id=acc["id"],
        )
    challenge = await store.create_oxygen_challenge(
        "2026-07-02T00:00:00Z", end_time="2026-07-02T00:30:00Z", account_id=bob_acc["id"]
    )
    app = create_app(store=store, settings=test_settings(), start_poller=False, auth_store=auth)
    return app, alice_session, alice_acc, bob_acc, challenge


@pytest.mark.asyncio
async def test_data_endpoints_scoped_to_session_user(two_tenants):
    app, alice_session, alice_acc, bob_acc, _challenge = two_tenants
    with client_for(app, alice_session) as client:
        assert [a["id"] for a in client.get("/api/accounts").json()["accounts"]] == [alice_acc["id"]]
        assert {r["heart_rate"] for r in client.get("/api/readings").json()} == {110}
        assert {d["account_id"] for d in client.get("/api/devices").json()["devices"]} == {alice_acc["id"]}
        assert client.get("/api/summary").json()["count"] == 1
        for path in ("readings", "devices", "summary", "insights", "rollups",
                     "notifications", "oxygen-challenges", "widget"):
            assert client.get(f"/api/{path}?account={bob_acc['id']}").status_code == 404, path


@pytest.mark.asyncio
async def test_mutations_on_foreign_resources_return_404(two_tenants):
    app, alice_session, _alice_acc, bob_acc, challenge = two_tenants
    with client_for(app, alice_session) as client:
        assert client.patch(f"/api/accounts/{bob_acc['id']}", json={"display_name": "hi"}).status_code == 404
        assert client.get(f"/api/oxygen-challenges/{challenge['id']}").status_code == 404
        assert client.patch(f"/api/oxygen-challenges/{challenge['id']}", json={"label": "x"}).status_code == 404
        assert client.delete(f"/api/oxygen-challenges/{challenge['id']}").status_code == 404
        assert client.post(
            "/api/oxygen-challenges",
            json={"start_time": "2026-07-02T02:00:00Z", "account_id": bob_acc["id"]},
        ).status_code == 404
