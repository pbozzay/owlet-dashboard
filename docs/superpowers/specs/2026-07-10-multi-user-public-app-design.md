# Owlet Dashboard — Multi-User Public App

- **Date:** 2026-07-10
- **Status:** Approved design, pre-implementation
- **Owner:** Paul (pbozzay)

## Context

Owlet Dashboard is currently a single-family local app: a FastAPI server polls the
unofficial Owlet cloud API every 30 seconds, stores readings in SQLite, and serves a
private dashboard. This design turns it into a public multi-user product: strangers
sign up, link their own Owlet accounts, and see only their own data.

## Decisions (settled during design review)

| Question | Decision |
|---|---|
| Audience | Real public product (not invite-only) |
| App login | Email + password with email-based password reset (magic links and OAuth deferred) |
| Owlet credential handling | Entered once at link time, validated live, password discarded; only refresh/API tokens stored (existing behavior, now encrypted at rest) |
| Polling fidelity | High — 30s while sock is worn; adaptive back-off otherwise |
| Hosting | Single Docker container on Paul's Unraid box |
| Ingress | Paul's existing nginx reverse proxy provides domain + TLS; no cloudflared, no port mapping beyond the container port |
| Database | SQLite stays (WAL). No Postgres in v1 |
| Monitoring | None in v1 (heartbeat surfaces collector staleness in-app) |
| Email | Resend (free tier) for verification + password reset |
| `.env` Owlet credentials | Removed as a concept; all account linking via UI |

## Goals

1. Anonymous visitors see a sign-in/sign-up page, never the dashboard.
2. Users only ever see their own linked Owlet accounts and data — enforced
   server-side on every endpoint.
3. Owlet passwords are never persisted; stored tokens are encrypted at rest.
4. 30-second data fidelity while a sock is in use.
5. Ships as one Docker image Paul can pull into Unraid like his other apps.

## Non-Goals (v1)

- Google/Apple OAuth, Postgres, horizontal scaling, native mobile apps,
  push/email alerting on vitals, admin panel, billing.

## Architecture

One container, one process:

```
[user browser] → [Paul's nginx: TLS + domain] → [container: uvicorn/FastAPI]
                                                    ├─ web routes (session-gated)
                                                    ├─ per-account poller tasks (asyncio)
                                                    ├─ daily SQLite snapshot task
                                                    └─ SQLite (WAL) on /data volume
                                                          ↑ outbound HTTPS to Owlet cloud
```

Uvicorn runs with proxy-header trust so client IPs (rate limiting) and scheme
(secure cookies) are correct behind nginx.

## Auth & Sessions

**Sign-up:** email + password → account created unverified → verification email
(Resend) → clicking link verifies. Unverified users can log in but see a
"verify your email" gate instead of the dashboard (prevents typo'd-email lockouts
while keeping unverified accounts inert).

**Sign-in:** email + password.

**Password reset:** "forgot password?" on the login page → reset email (same
token mechanism as verification) → landing page sets a new password and
invalidates all of the user's existing sessions.

**Tokens (verification + password reset):** random 256-bit values, stored
**hashed** (SHA-256) in `auth_tokens`, single-use, 15-minute expiry, scoped by
purpose.

**Passwords:** argon2id via `argon2-cffi`. No composition rules; minimum length 8;
maximum 128.

**Sessions:** server-side `sessions` rows (random 256-bit id, hashed in DB),
referenced by an `owlet_session` cookie — `HttpOnly`, `Secure`, `SameSite=Lax`,
30-day rolling expiry. Server-side sessions give revocation ("log out everywhere"
button in settings deletes all the user's sessions).

**CSRF:** `SameSite=Lax` cookie plus origin/referer check on state-changing
requests (the API is same-origin JSON; no cross-site POST surface is needed).

**Rate limits (per IP + per identifier, in-process):** login 10/min, signup 5/hour,
password-reset request 3/15min per email, Owlet link attempts 5/hour per user.
Basic-auth middleware and `OWLET_BASIC_AUTH_*` are removed.

## Data Model Changes

New tables:

- `users` — id, email (unique, citext-style lowercased), password_hash,
  email_verified_at, created_at, updated_at.
- `sessions` — id (hashed), user_id, created_at, last_seen_at, expires_at,
  user_agent.
- `auth_tokens` — token_hash, user_id, purpose (`verify` | `password_reset`),
  expires_at, used_at.

Changed tables:

- `accounts` gains `user_id` (FK → users, NOT NULL after migration). Existing
  columns (email, region, display_name, api_token, refresh_token, status,
  show_crypto, dashboard_preferences) stay.
- `accounts.api_token` / `accounts.refresh_token` become Fernet-encrypted blobs
  (key from `TOKEN_ENCRYPTION_KEY` env). Encryption/decryption lives in the store
  layer so callers are unchanged.
- `users` gains `share_token` (nullable, hashed): the existing `/share/<token>`
  feature moves from a global env value to per-user opt-in, generated/revoked in
  settings. Share routes resolve token → user and expose only that user's data,
  read-only.
- `metadata` keyed heartbeat: poller loop updates `poller_heartbeat_at` each cycle.

**Migration:** startup migration (existing pattern in `store.py`). Legacy rows:
any `accounts` without `user_id` are attached to the **first user created** after
migration (covers Paul's local instance; a fresh public DB has no legacy rows).
Plaintext tokens found during migration are encrypted in place.

## Tenancy Enforcement

Every data endpoint (`/api/accounts`, `/api/devices`, `/api/readings`,
`/api/summary`, `/api/insights`, `/api/rollups`, `/api/notifications`,
`/api/oxygen-challenges`, `/api/widget`, CSV export) requires a session and is
filtered to `account.user_id == session.user_id`. Requests for another user's
account id return **404** (not 403 — no existence oracle). The store layer already
threads `account_id` through queries; queries gain the user join/filter so scoping
is enforced at the data layer, not per-route by convention. `POST /api/accounts`
(Owlet link) attaches the new account to the session user. The account-switcher UI
is unchanged but lists only the session user's accounts.

`/api/crypto` (CoinGecko proxy) requires a session but is not tenant-scoped
(public market data). `show_crypto` defaults **off** for new users.

## Sign-in & Onboarding UX

- `/login` — single page: email+password form, "forgot password?" link, and
  sign-up. Unauthenticated requests to the dashboard redirect here;
  unauthenticated API calls get 401 JSON.
- First login lands on an empty-state screen: "Link your Owlet sock" → existing
  Link flow (Owlet email/password + region dropdown world/europe). Copy states:
  *"We verify with Owlet once and never store your Owlet password."*
- `/settings` — change password, log out everywhere, manage share link, delete
  account, CSV export links.
- Legal: `/terms` and `/privacy` static pages; footer on every page repeats the
  "not a medical device, not an alerting system" disclaimer from the README.
- PWA service worker stays network-first for navigations (already is), so
  login/logout state is never served stale.

## Poller Changes

- **Adaptive interval:** 30s while readings indicate the sock is worn/streaming;
  ~5min when charging/off/disconnected (states already normalized by
  `app/quality.py` logic). First reading after linking is immediate.
- **Jitter:** per-account start offset spreads N accounts across the interval.
- **Backoff:** exponential (30s → 8min cap) on Owlet errors per account;
  auth failures set the existing `needs_reauth` status, which the UI already
  surfaces; polling for that account pauses until relink.
- **Heartbeat:** loop stamps `poller_heartbeat_at`; dashboard shows a
  "collector offline since …" banner when stale (> 3× interval).
- Pollers for new/linked accounts start without restart (existing behavior).

## Security & Privacy

- Owlet tokens encrypted at rest (Fernet); key lives only in container env.
- Owlet link endpoint strictly rate-limited (it relays credentials to Owlet).
- Security headers: `X-Content-Type-Options`, `Referrer-Policy`,
  `X-Frame-Options: DENY`, conservative CSP allowing jsdelivr (charts) —
  dashboard already depends on cdn.jsdelivr.net.
- **Account deletion:** self-serve in settings; cascades users → sessions,
  auth_tokens, accounts → readings, notifications, oxygen_challenges. Immediate
  hard delete.
- **Retention:** raw JSON payload column nulled after 7 days (dashboard uses
  normalized columns); readings older than 180 days are replaced in place by
  5-minute-averaged reading rows, so charts/rollups keep working unchanged on
  sparser history (config: `RETENTION_RAW_DAYS`, `RETENTION_FULL_DAYS`). Runs in
  the daily maintenance task.
- **Backups:** daily consistent snapshot via SQLite backup API to
  `/data/backups/owlet-YYYYMMDD.sqlite3`, keep 7. Unraid appdata backup then
  always captures a consistent file (raw copies of a live WAL DB are unsafe).

## Email (Resend)

- Templates: verify-email, password-reset. Plain, no tracking.
- From address on Paul's domain (Resend domain verification required at deploy).
- `APP_BASE_URL` env builds absolute links.
- Send failures surface as a friendly "couldn't send, try again" and are logged.

## Configuration (final env surface)

| Var | Purpose |
|---|---|
| `SECRET_KEY` | session/cookie signing |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for Owlet tokens |
| `RESEND_API_KEY` | email sending |
| `APP_BASE_URL` | absolute URLs in emails |
| `DATABASE_PATH` | default `/data/owlet.sqlite3` |
| `HOST` / `PORT` | bind (default 0.0.0.0:8888 in container) |
| `POLL_INTERVAL_SECONDS` / `POLL_IDLE_SECONDS` | 30 / 300 defaults |
| `RETENTION_RAW_DAYS` / `RETENTION_FULL_DAYS` | 7 / 180 defaults |

Removed: `OWLET_EMAIL`, `OWLET_PASSWORD`, `OWLET_REGION`,
`OWLET_BASIC_AUTH_USERNAME/PASSWORD`, `OWLET_SHARE_TOKEN`.

## Packaging & Deploy

- **Dockerfile:** `python:3.12-slim`, non-root user, `pip install .`,
  `VOLUME /data`, `CMD uvicorn app.main:app --host 0.0.0.0 --port 8888
  --proxy-headers --forwarded-allow-ips=*`.
- **CI:** GitHub Actions on push to main → build → push
  `ghcr.io/pbozzay/owlet-dashboard:latest` (+ sha tag), linux/amd64.
- **Unraid:** add container from GHCR image, map `/data` to appdata share and
  container port to a host port; Paul's nginx proxies the subdomain to it.
  Update flow = Unraid's normal image-update pull.
- Local dev keeps working uncontainerized (uvicorn + `.env`), Windows included.

## Testing

Extends existing pytest/httpx suite (`create_app(start_poller=False)` pattern):

1. Auth flows — signup, verify, login, password reset (happy path, expiry,
   reuse, wrong purpose, sessions invalidated), logout-everywhere, rate-limit
   responses.
2. **Tenancy isolation** — dedicated test class: user A vs user B across every
   data endpoint, including share tokens and CSV export; expects 404.
3. Store — encryption round-trip, migration on a fixture legacy DB (accounts
   without user_id, plaintext tokens), retention/downsample job, snapshot job.
4. Poller — adaptive interval + backoff with fake clock and stubbed client.
5. Config — app boots with only the new env surface.

## Risks

- **Owlet API fragility:** unofficial API; an upstream auth change breaks all
  polling at once. Mitigated by adapter isolation (`owlet_client.py`) — accepted
  product risk.
- **Home hosting:** box/ISP downtime gaps *all* users' history permanently
  (no backfill API). Heartbeat banner makes it visible — accepted for v1.
- **Owlet rate limiting:** many accounts polled from one IP. Jitter + adaptive
  intervals + backoff reduce footprint; residential IP is a mild advantage.
- **Email deliverability:** verification and reset emails depend on Resend +
  domain reputation; normal login is unaffected.
- **SQLite ceiling:** single-writer is fine for hundreds of accounts; Postgres
  is the designated escape hatch if the product outgrows one box.

## Out of Scope (v1)

Email magic-link login, OAuth providers, Postgres, alerting/notifications
delivery, admin tooling, billing, multi-node polling, Apple/Google sign-in,
mobile apps.
