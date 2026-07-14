#!/bin/sh
# Self-hosted / Unraid friendly startup.
#
# The data volume is bind-mounted from the host, so its ownership is whatever
# the host share uses (on Unraid, nobody:users = 99:100) — not the image's
# build-time owner. If we ran the app directly as a fixed non-root user it
# couldn't create the SQLite file and startup would fail with
# "unable to open database file". So we start as root, make /data writable for
# the requested user (PUID/PGID, LinuxServer/Unraid convention), then drop
# privileges and exec the app.
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  # Point the bundled 'owlet' account at the requested ids (best effort — a
  # collision or read-only passwd shouldn't stop startup).
  groupmod -o -g "$PGID" owlet 2>/dev/null || true
  usermod  -o -u "$PUID" -g "$PGID" owlet 2>/dev/null || true
  # Make the volume (and any DB copied in by hand) owned by the runtime user.
  # Cheap here: /data holds only the SQLite files and optional backups.
  chown -R "$PUID:$PGID" /data 2>/dev/null || true
  exec gosu "$PUID:$PGID" "$@"
fi

# Already non-root (e.g. the operator passed --user): just run.
exec "$@"
