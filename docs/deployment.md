# Deployment (Unraid + nginx)

Image: `ghcr.io/pbozzay/owlet-dashboard:latest` — published by GitHub Actions on every
push to `main` (tests must pass first).

Current durable deployment target:

- Public hostname: `https://owlet.bozzay.app`
- Host: Unraid, single Docker container behind the existing nginx reverse proxy

## Unraid container

- Repository: `ghcr.io/pbozzay/owlet-dashboard:latest`
- Volume: `/mnt/user/appdata/owlet-dashboard` -> `/data`
- Port: `8888` -> host port of your choice
- Env (all optional): `POLL_INTERVAL_SECONDS` (default 30); `PUID`/`PGID` to set
  the user that owns the data files (default `1000:1000` — set `99`/`100` to match
  Unraid's `nobody:users`)

Everything the app stores lives in the `/data` volume (`owlet.sqlite3`).

### Ownership / "unable to open database file"

The container starts as root, chowns `/data` to `PUID:PGID`, then drops privileges
before launching the app. This means a **fresh install initializes its own database
even when the appdata share is owned by `nobody:users`** — no manual `chown` needed.
If you saw `sqlite3.OperationalError: unable to open database file` on an older image,
that was the fixed-uid container being unable to write the host-owned mount; pull the
current image. Set `PUID=99`/`PGID=100` if you want the SQLite files owned by
`nobody:users` for easy SMB browsing.

## nginx reverse proxy

```nginx
location / {
    proxy_pass http://UNRAID_IP:8888;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $remote_addr;
}
```

The container runs uvicorn with `--proxy-headers`, so session cookies get the
`Secure` flag when the request arrives as https.

## First run

1. Open the site — you land on the sign-in page.
2. Create an account. The **first** user created adopts any accounts/readings from a
   pre-multi-user database, so migrate an old `owlet.sqlite3` into `/data` *before*
   signing up if you have one.
3. Link your Owlet login on the onboarding page (verified once with Owlet; only
   access tokens are stored). Polling starts immediately.

## Updates

Push to `main` -> Actions runs tests, builds, publishes -> Unraid "check for update"
pulls the new image.

## Data & backups

Back up the `/data` folder with your normal appdata backup. For a
guaranteed-consistent copy of the SQLite file, stop the container first (raw copies
of a live database can be mid-write).
