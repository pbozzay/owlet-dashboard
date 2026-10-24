"""The pages embed their JavaScript in Python strings, where a stray quote or backslash
silently produces a script the browser refuses to run (blank page). Parse every inline
script with Node, which GitHub's Ubuntu runners ship."""

import re
import shutil
import subprocess

import pytest
from fastapi.routing import APIRoute

from tests.conftest import client_for, make_user

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def get_routes(app):
    for route in app.routes:
        if isinstance(route, APIRoute) and "GET" in route.methods and "{" not in route.path:
            yield route.path


@pytest.mark.asyncio
async def test_every_inline_script_parses(app_bundle, tmp_path):
    app, _store, auth_store = app_bundle
    _user, session = await make_user(auth_store, "parent@example.test")
    client = client_for(app, session)
    checked, failures = 0, []
    for path in get_routes(app):
        response = client.get(path, follow_redirects=True)
        if not response.headers.get("content-type", "").startswith("text/html"):
            continue
        for i, script in enumerate(
            re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", response.text, re.S)
        ):
            if not script.strip():
                continue
            file = tmp_path / f"{path.strip('/').replace('/', '_') or 'root'}_{i}.js"
            file.write_text(script)
            result = subprocess.run(["node", "--check", str(file)], capture_output=True, text=True)
            checked += 1
            if result.returncode != 0:
                lines = result.stderr.strip().splitlines()
                reason = next((line for line in lines if "Error" in line), lines[-1])
                failures.append(f"{path} script #{i}: {reason}")
    assert checked > 0
    assert not failures, "\n".join(failures)
