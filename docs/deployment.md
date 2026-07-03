# Owlet Dashboard local deployment

Current durable deployment target:

- Public hostname: `https://owlet.bozzay.app`
- Local app: `http://127.0.0.1:8788`
- GitHub repo: `https://github.com/pbozzay/owlet-dashboard`
- Supervisor: macOS `launchd`
- Tunnel: Cloudflare named tunnel `owlet-dashboard`
- Auth: Cloudflare Access allowlist for `paulbzzy@gmail.com`

## Local app service

The app is supervised by this LaunchAgent on Paul's Mac:

```text
~/Library/LaunchAgents/com.paulbozzay.owlet-dashboard.plist
```

Useful commands:

```bash
launchctl print gui/$(id -u)/com.paulbozzay.owlet-dashboard
launchctl kickstart -k gui/$(id -u)/com.paulbozzay.owlet-dashboard
curl -fsS http://127.0.0.1:8788/api/health
```

Logs:

```text
~/Library/Logs/owlet-dashboard/app.out.log
~/Library/Logs/owlet-dashboard/app.err.log
```

## Cloudflare Tunnel

The named tunnel exists as:

```text
name: owlet-dashboard
id: 3d14f878-6353-4df0-b217-18d958c3ca01
config: ~/.cloudflared/owlet-dashboard.yml
```

`owlet.bozzay.app` is routed to this tunnel. The tunnel is supervised by this LaunchAgent:

```text
~/Library/LaunchAgents/com.paulbozzay.owlet-dashboard-tunnel.plist
```

Useful commands:

```bash
launchctl print gui/$(id -u)/com.paulbozzay.owlet-dashboard-tunnel
launchctl kickstart -k gui/$(id -u)/com.paulbozzay.owlet-dashboard-tunnel
cloudflared tunnel info owlet-dashboard
```

Logs:

```text
~/Library/Logs/owlet-dashboard/tunnel.out.log
~/Library/Logs/owlet-dashboard/tunnel.err.log
```

## Cloudflare Access

Cloudflare Access is configured as a self-hosted application:

```text
Application: Owlet Dashboard
Domain: owlet.bozzay.app
Policy: Allow email = paulbzzy@gmail.com
```

Verification target:

```bash
curl -L https://owlet.bozzay.app/
```

Unauthenticated requests should redirect to a Cloudflare Access login page at `bozzay.cloudflareaccess.com`, not return the FastAPI dashboard HTML directly.

## Local deployment registry

This deployment is also tracked in:

```text
~/Projects/Personal/local-app-registry/apps.yaml
```
