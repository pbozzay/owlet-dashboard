from datetime import date, timedelta

import pytest

from app.auth_store import AuthStore
from app.config import Settings
from app.main import _public_account, create_app
from app.owlet_profiles import (
    effective_preferences,
    normalize_profiles,
    save_profiles,
    sync_profiles,
)
from app.store import ReadingStore
from tests.conftest import client_for, make_user

BIRTH = (date.today() - timedelta(days=100)).isoformat()
P1 = {
    "id": "accounts/a/profiles/one",
    "baby_name": "Baby One",
    "birth_date": BIRTH,
    "baby_pronouns": "he",
}
P2 = {"id": "accounts/a/profiles/two", "baby_name": "Baby Two", "baby_pronouns": "she"}


def test_normalization_keeps_only_supported_fields_and_valid_account_profiles():
    result = normalize_profiles(
        {
            "profiles": [
                {
                    "name": P1["id"],
                    "givenName": " Baby One ",
                    "birthdate": BIRTH,
                    "gender": "MALE",
                    "weight": 9,
                    "secret": "hidden",
                },
                {"name": "accounts/another/profiles/one", "givenName": "Wrong account"},
                {"name": "accounts/a/profiles/../oops"},
                {"name": P2["id"], "birthdate": "3000-01-01", "gender": "unknown"},
            ]
        },
        "a",
    )
    assert result == [P1, {"id": P2["id"]}]


def test_existing_manual_values_including_clears_override_imports():
    prefs = {
        "owlet_profiles": [P1],
        "owlet_profile_id": P1["id"],
        "baby_name": "",
        "birth_date": None,
        "baby_pronouns": "they",
    }
    resolved = effective_preferences(prefs)
    assert (resolved["baby_name"], resolved["birth_date"], resolved["baby_pronouns"]) == (
        "",
        None,
        "they",
    )
    assert _public_account({"dashboard_preferences": prefs})["baby_overrides"] == [
        "baby_name",
        "birth_date",
        "baby_pronouns",
    ]


@pytest.mark.asyncio
async def test_singleton_autoselect_multi_requires_choice_and_saved_choice_survives(tmp_path):
    store = ReadingStore(tmp_path / "test.sqlite3")
    await store.init()
    account = await store.create_account(email="synthetic@example.test")
    aid = account["id"]
    multiple = await save_profiles(store, aid, [P1, P2])
    assert multiple["dashboard_preferences"].get("owlet_profile_id") is None
    assert "baby_name" not in effective_preferences(multiple["dashboard_preferences"])
    single = await save_profiles(store, aid, [P1])
    assert effective_preferences(single["dashboard_preferences"])["baby_name"] == "Baby One"
    again = await save_profiles(store, aid, [P2, P1])
    assert again["dashboard_preferences"]["owlet_profile_id"] == P1["id"]
    removed = await save_profiles(store, aid, [])
    assert removed["dashboard_preferences"].get("owlet_profile_id") is None


@pytest.mark.asyncio
async def test_failed_optional_sync_preserves_existing_settings(tmp_path):
    store = ReadingStore(tmp_path / "test.sqlite3")
    await store.init()
    account = await store.create_account(email="synthetic@example.test")
    await save_profiles(store, account["id"], [P1])

    class BrokenClient:
        async def profiles(self):
            raise ValueError("sensitive upstream detail")

    await sync_profiles(store, account["id"], BrokenClient())
    assert (await store.get_account(account["id"]))["dashboard_preferences"]["owlet_profiles"] == [
        P1
    ]


@pytest.mark.asyncio
async def test_refresh_selection_override_reset_and_tenant_isolation(tmp_path, monkeypatch):
    import app.main as main_module

    calls = []

    async def fake_fetch(region, token):
        calls.append(region)
        return [P1, P2]

    monkeypatch.setattr(main_module, "fetch_profiles", fake_fetch)
    store = ReadingStore(tmp_path / "test.sqlite3")
    await store.init()
    auth = AuthStore(store.db_path)
    user, session = await make_user(auth, "owner@example.test")
    own = await store.create_account(email="sock@example.test", user_id=user["id"])
    other_user, _ = await make_user(auth, "other@example.test")
    other = await store.create_account(email="other-sock@example.test", user_id=other_user["id"])
    app = create_app(
        store=store, auth_store=auth, settings=Settings(_env_file=None), start_poller=False
    )
    base = f"/api/accounts/{own['id']}"
    with client_for(app, session) as client:
        assert client.post(f"/api/accounts/{other['id']}/profiles/refresh").status_code == 404
        assert calls == []
        assert client.post(base + "/profiles/refresh").status_code == 200
        assert (
            client.patch(base, json={"owlet_profile_id": "accounts/other/profiles/id"}).status_code
            == 400
        )
        assert client.patch(base, json={"owlet_profile_id": []}).status_code == 400
        chosen = client.patch(base, json={"owlet_profile_id": P1["id"]}).json()["account"]
        assert chosen["dashboard_preferences"]["baby_name"] == "Baby One"
        manual = client.patch(
            base, json={"dashboard_preferences": {"baby_name": "My name", "baby_pronouns": "they"}}
        ).json()["account"]
        assert manual["dashboard_preferences"]["baby_name"] == "My name"
        refreshed = client.post(base + "/profiles/refresh").json()["account"]
        assert refreshed["dashboard_preferences"]["baby_name"] == "My name"
        reset = client.patch(base, json={"use_owlet_baby_details": True}).json()["account"]
        assert reset["baby_overrides"] == []
        assert reset["dashboard_preferences"]["baby_name"] == "Baby One"
        assert reset["dashboard_preferences"]["baby_pronouns"] == "he"
        assert (
            client.get("/api/accounts").json()["accounts"][0]["dashboard_preferences"]["birth_date"]
            == BIRTH
        )
