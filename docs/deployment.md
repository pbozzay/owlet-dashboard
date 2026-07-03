# Owlet Dashboard local deployment

Current durable deployment target:

- Public hostname: `https://owlet.bozzay.app`
- Local app: `http://127.0.0.1:8788`
- GitHub repo: `https://github.com/pbozzay/owlet-dashboard`
- Supervisor: macOS `launchd`
- Tunnel: Cloudflare named tunnel `owlet-dashboard`
- Auth target: Cloudflare Access allowlist for `paulbzzy@gmail.com`

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

`owlet.bozzay.app` has been routed to this tunnel. Start the tunnel only after Cloudflare Access is protecting the hostname.

Tunnel LaunchAgent prepared locally:

```text
~/Library/LaunchAgents/com.paulbozzay.owlet-dashboard-tunnel.plist
```

Start after Access is configured:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.paulbozzay.owlet-dashboard-tunnel.plist
launchctl kickstart -k gui/$(id -u)/com.paulbozzay.owlet-dashboard-tunnel
```

Logs:

```text
~/Library/Logs/owlet-dashboard/tunnel.out.log
~/Library/Logs/owlet-dashboard/tunnel.err.log
```

## Cloudflare Access

Create a self-hosted Access application for:

```text
owlet.bozzay.app
```

Recommended policy:

```text
Decision: Allow
Include: Email = paulbzzy@gmail.com
```

After Access is configured and the tunnel is started, verify unauthenticated requests are blocked by Cloudflare Access before reaching FastAPI.

## Local deployment registry

This deployment is also tracked in:

```text
~/Projects/Personal/local-app-registry/apps.yaml
```
