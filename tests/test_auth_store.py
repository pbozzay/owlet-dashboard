import pytest

from app.auth_store import AuthStore
from app.security import hash_password, hash_token, new_token, verify_password
from app.store import ReadingStore


def test_password_and_token_helpers():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password(hashed, "correct horse") is True
    assert verify_password(hashed, "wrong") is False
    assert verify_password("not-a-hash", "x") is False
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 40
    assert hash_token(a) == hash_token(a) != hash_token(b)


@pytest.mark.asyncio
async def test_user_crud_and_email_normalization(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("Parent@Example.COM", hash_password("hunter22"))
    assert user["email"] == "parent@example.com"
    assert (await auth.get_user_by_email("PARENT@example.com"))["id"] == user["id"]
    with pytest.raises(ValueError):
        await auth.create_user("parent@example.com", hash_password("other"))


@pytest.mark.asyncio
async def test_sessions_create_expire_revoke(tmp_path):
    auth = AuthStore(tmp_path / "owlet.sqlite3")
    user = await auth.create_user("a@b.c", hash_password("hunter22"))
    token = new_token()
    await auth.create_session(user["id"], hash_token(token))
    assert (await auth.get_session_user(hash_token(token)))["id"] == user["id"]
    assert await auth.get_session_user(hash_token("nope")) is None
    expired = new_token()
    await auth.create_session(user["id"], hash_token(expired), ttl_days=-1)
    assert await auth.get_session_user(hash_token(expired)) is None
    await auth.delete_session(hash_token(token))
    assert await auth.get_session_user(hash_token(token)) is None


@pytest.mark.asyncio
async def test_first_user_adopts_orphan_accounts(tmp_path):
    db = tmp_path / "owlet.sqlite3"
    store = ReadingStore(db)
    await store.init()
    orphan = await store.create_account(email="sock@example.com")
    auth = AuthStore(db)
    first = await auth.create_user("first@example.com", hash_password("hunter22"))
    second = await auth.create_user("second@example.com", hash_password("hunter22"))
    assert {a["id"] for a in await store.list_accounts(user_id=first["id"])} == {orphan["id"]}
    assert await store.list_accounts(user_id=second["id"]) == []
