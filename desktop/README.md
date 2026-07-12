# Owlet Dashboard — Windows desktop app (Tauri)

A native Windows shell around the same app: a frozen `owlet-server.exe` sidecar
(FastAPI + SQLite, data in `%LOCALAPPDATA%\owlet-dashboard\`) plus a Tauri window
pointed at it. Login is preseeded as `admin` / `password` (local machine only).

> **Important limitation — read before relying on it**
> The desktop app only collects readings **while it is running**. If you close it
> or your PC sleeps overnight, those readings are gone for good (Owlet's API has no
> backfill). Gaps are shown honestly in the charts as "collector off" bands.
> For uninterrupted 24/7 history, run the Docker/server version instead and use
> the desktop app or browser as a viewer.

## Build prerequisites (one-time)

1. Rust toolchain: `winget install Rustlang.Rustup` then `rustup default stable-msvc`
2. Visual Studio Build Tools with the "Desktop development with C++" workload:
   `winget install Microsoft.VisualStudio.2022.BuildTools`
3. Tauri CLI: `cargo install tauri-cli --version "^2"`
4. Python deps (repo venv): `.venv\Scripts\python -m pip install -e ".[dev]" pyinstaller`

## Build

From the repository root:

```powershell
.\desktop\build-sidecar.ps1                       # freeze the server -> sidecar exe
cd desktop\src-tauri
cargo tauri icon ..\..\app\static\icon-512.png    # generate icons/ (first build only)
cargo tauri build                                  # NSIS installer in target\release\bundle\nsis\
```

For iterating without an installer: `cargo tauri dev` (spawns the sidecar and opens
the window; it reuses an already-running server on port 8877 if one exists).

## How it fits together

- `server_entry.py` — sidecar entry point; sets desktop defaults (`OWLET_DESKTOP=1`,
  `SEED_DEFAULT_ADMIN=true`, DB in `%LOCALAPPDATA%`) and runs uvicorn on `127.0.0.1:8877`.
- `build-sidecar.ps1` — PyInstaller freeze + copy to `src-tauri/binaries/` with the
  target-triple name Tauri requires.
- `src-tauri/src/main.rs` — spawns the sidecar, waits for the port, opens the window,
  kills the sidecar on window close.
