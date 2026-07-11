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
- Env (all optional): `POLL_INTERVAL_SECONDS` (default 30)

Everything the app stores lives in the `/data` volume (`owlet.sqlite3`).

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
