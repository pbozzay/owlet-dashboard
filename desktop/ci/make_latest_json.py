"""Emit the Tauri updater manifest (latest.json) for a release.

The desktop app polls the newest release's copy of this file; when its
`version` is higher than the running app, the app downloads `url`, verifies it
against the `signature` using the public key baked into tauri.conf.json, and
installs it. Inputs come from the environment so there is no shell-quoting of
the base64 signature.

    VER=0.1.7 OUT=Owlet-Dashboard-0.1.7-windows-setup.exe \
        SIGFILE=path/to/installer.sig python make_latest_json.py > latest.json
"""
from __future__ import annotations

import datetime
import json
import os

REPO = "pbozzay/owlet-dashboard"


def main() -> None:
    ver = os.environ["VER"]
    out = os.environ["OUT"]
    signature = open(os.environ["SIGFILE"], encoding="utf-8").read().strip()
    manifest = {
        "version": ver,
        "notes": f"Owlet Dashboard {ver}. See the release notes on GitHub.",
        "pub_date": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "platforms": {
            "windows-x86_64": {
                "signature": signature,
                "url": f"https://github.com/{REPO}/releases/download/v{ver}/{out}",
            }
        },
    }
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
