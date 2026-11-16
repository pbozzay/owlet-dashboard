"""Run the page's JavaScript regressions as part of pytest when Node is installed."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for page JavaScript tests")
def test_resolution_switching():
    suite = Path(__file__).with_name("rhythms_resolution.test.cjs")
    result = subprocess.run(
        ["node", "--test", str(suite)], capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr

@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for page JavaScript tests")
def test_missing_dashboard_metrics():
    suite = Path(__file__).with_name("dashboard_metrics.test.cjs")
    result = subprocess.run(["node", "--test", str(suite)], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
