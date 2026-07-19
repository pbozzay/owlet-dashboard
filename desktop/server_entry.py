"""Entry point for the frozen desktop sidecar (owlet-server.exe).

Runs the same FastAPI app as the hosted version, but preconfigured for a
single-user desktop install: local-only bind, data in %LOCALAPPDATA%, and the
admin/password convenience login enabled.
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

DESKTOP_PORT = 8877  # outside Windows' common excluded port ranges


def _opt_out_of_power_throttling() -> None:
    """Windows 11 EcoQoS-throttles background processes: when our window loses
    focus, the 5s poll timers get coalesced into minutes-long gaps. Collection
    is the whole point of this process — explicitly opt out."""
    if sys.platform != "win32":
        return
    try:
        class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
            _fields_ = [
                ("Version", ctypes.c_ulong),
                ("ControlMask", ctypes.c_ulong),
                ("StateMask", ctypes.c_ulong),
            ]

        PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
        PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
        PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION = 0x4
        ProcessPowerThrottling = 4

        state = PROCESS_POWER_THROTTLING_STATE(
            PROCESS_POWER_THROTTLING_CURRENT_VERSION,
            PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            | PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION,
            0,  # StateMask 0 with bits in ControlMask = throttling OFF for those bits
        )
        ctypes.windll.kernel32.SetProcessInformation(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ProcessPowerThrottling,
            ctypes.byref(state),
            ctypes.sizeof(state),
        )
    except Exception:  # never let a throttling opt-out break startup
        pass


def main() -> None:
    _opt_out_of_power_throttling()
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
