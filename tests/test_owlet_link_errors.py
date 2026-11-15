import logging

import aiohttp
import pytest
from pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletCredentialsError,
    OwletDevicesError,
)

from app.auth_store import AuthStore
from app.config import Settings
from app.main import create_app
from app.store import ReadingStore
from tests.conftest import client_for, make_user


@pytest.mark.asyncio
@pytest.mark.parametrize('route', ['/api/accounts', '/onboarding/link'])
@pytest.mark.parametrize(('error', 'status', 'message'), [
    (OwletCredentialsError('SECRET'), 400, 'Owlet rejected the login'),
    (TimeoutError('SECRET'), 504, 'timed out'),
    (aiohttp.ClientConnectionError('SECRET'), 503, 'could not connect'),
    (OwletConnectionError('SECRET'), 503, 'could not connect'),
    (OwletDevicesError('SECRET'), 400, 'no supported Owlet sock'),
    (OwletAuthenticationError('Too many incorrect attempts'), 429, 'limiting sign-in'),
    (OwletAuthenticationError('SECRET'), 502, 'could not complete authentication'),
    (ValueError('SECRET'), 502, 'Could not finish linking'),
])
async def test_link_failures_are_actionable_and_do_not_leak_secrets(
    tmp_path, monkeypatch, caplog, route, error, status, message
):
    import app.main as main_module

    closed = []

    class FailingClient:
        def __init__(self, **kwargs):
            pass

        async def connect(self):
            raise error

        async def close(self):
            closed.append(True)

    monkeypatch.setattr(main_module, 'OwletClient', FailingClient)
    store = ReadingStore(tmp_path / 'test.sqlite3')
    await store.init()
    auth = AuthStore(store.db_path)
    user, session = await make_user(auth, 'owner@example.test')
    app = create_app(store=store, auth_store=auth, start_poller=False, settings=Settings(_env_file=None))
    payload = {'email': 'sock@example.test', 'password': 'SECRET', 'region': 'world'}
    with caplog.at_level(logging.WARNING), client_for(app, session) as client:
        response = client.post(route, **({'json': payload} if route == '/api/accounts' else {'data': payload}))
    assert response.status_code == status
    assert message in response.text
    assert 'SECRET' not in response.text
    assert 'SECRET' not in caplog.text
    assert closed == [True]
    assert await store.list_accounts(user_id=user['id']) == []
