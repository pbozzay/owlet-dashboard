"""Entry point for the frozen desktop sidecar (owlet-server.exe).

Runs the same FastAPI app as the hosted version, but preconfigured for a
single-user desktop install: local-only bind, data in %LOCALAPPDATA%, and the
admin/password convenience login enabled.
"""
from __future__ import annotations

import os
from pathlib import Path

DESKTOP_PORT = 8877  # outside Windows' common excluded port ranges


def main() -> None:
    data_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "owlet-dashboard"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATABASE_PATH", str(data_dir / "owlet.sqlite3"))
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", str(DESKTOP_PORT))
    os.environ.setdefault("SEED_DEFAULT_ADMIN", "true")
    os.environ.setdefault("OWLET_DESKTOP", "1")

    import uvicorn

    from app.main import create_app

    uvicorn.run(
        create_app(),
        host=os.environ["HOST"],
        port=int(os.environ["PORT"]),
        log_level="info",
    )


if __name__ == "__main__":
    main()
