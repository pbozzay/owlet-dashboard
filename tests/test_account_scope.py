import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js required")
def test_account_scope():
    result = subprocess.run(
        ["node", "--test", str(Path(__file__).with_name("account_scope.test.cjs"))],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
