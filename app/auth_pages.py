from __future__ import annotations

import html

_BASE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · Owlet Dashboard</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    :root {{ --bg:#f5f7fb; --panel:#fff; --text:#122033; --muted:#5b6b80; --purple:#6d28d9; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
           background:var(--bg); color:var(--text); display:flex; min-height:100vh;
           align-items:center; justify-content:center; padding:24px; }}
    .card {{ background:var(--panel); border-radius:16px; box-shadow:0 8px 30px rgba(18,32,51,.08);
            padding:32px; width:100%; max-width:420px; }}
    h1 {{ margin:0 0 4px; font-size:24px; }}
    p.sub {{ margin:0 0 20px; color:var(--muted); font-size:14px; }}
    label {{ display:block; font-size:13px; font-weight:600; margin:14px 0 4px; }}
    input, select {{ width:100%; padding:10px 12px; border:1px solid #d6dee9; border-radius:10px; font-size:15px; }}
    button {{ margin-top:18px; width:100%; padding:11px; border:0; border-radius:10px;
             background:var(--purple); color:#fff; font-size:15px; font-weight:600; cursor:pointer; }}
    .links {{ margin-top:16px; font-size:13px; color:var(--muted); display:flex; justify-content:space-between; }}
    .links a {{ color:var(--purple); text-decoration:none; }}
    .notice {{ background:#fef2f2; color:#991b1b; border-radius:10px; padding:10px 12px; font-size:13px; margin-bottom:8px; }}
    footer {{ margin-top:20px; font-size:11px; color:var(--muted); text-align:center; }}
  </style>
</head>
<body>
  <div class="card">
    {body}
    <footer>Retrospective trend viewing only — not a medical monitor or alert replacement.</footer>
  </div>
</body>
</html>"""


def _page(title: str, body: str) -> str:
    return _BASE.format(title=html.escape(title), body=body)


def _error(error: str | None) -> str:
    return f'<div class="notice">{html.escape(error)}</div>' if error else ""


def login_page(error: str | None = None) -> str:
    return _page(
        "Sign in",
        f"""<h1>Owlet Dashboard</h1>
    <p class="sub">Private history for your Owlet sock data.</p>
    {_error(error)}
    <form method="post" action="/auth/login">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <label for="password">Password</label>
      <input id="password" name="password" type="password" required autocomplete="current-password" />
      <button type="submit">Sign in</button>
    </form>
    <div class="links"><a href="/signup">Create an account</a><span></span></div>""",
    )


def signup_page(error: str | None = None) -> str:
    return _page(
        "Create account",
        f"""<h1>Create your account</h1>
    <p class="sub">Then link your Owlet sock to start collecting history.</p>
    {_error(error)}
    <form method="post" action="/auth/signup">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required autocomplete="email" />
      <label for="password">Password (8+ characters)</label>
      <input id="password" name="password" type="password" required minlength="8" maxlength="128"
             autocomplete="new-password" />
      <button type="submit">Create account</button>
    </form>
    <div class="links"><a href="/login">Back to sign in</a><span></span></div>""",
    )


def onboarding_page(error: str | None = None) -> str:
    return _page(
        "Link your Owlet sock",
        f"""<h1>Link your Owlet sock</h1>
    <p class="sub">Enter the login you use in the Owlet app. We verify it with Owlet once and
    <strong>never store your Owlet password</strong> — only a revocable access token.</p>
    {_error(error)}
    <form method="post" action="/onboarding/link">
      <label for="owlet_email">Owlet account email</label>
      <input id="owlet_email" name="email" type="email" required />
      <label for="owlet_password">Owlet account password</label>
      <input id="owlet_password" name="password" type="password" required autocomplete="off" />
      <label for="region">Region</label>
      <select id="region" name="region">
        <option value="world" selected>World (US and most countries)</option>
        <option value="europe">Europe</option>
      </select>
      <button type="submit">Link sock and start collecting</button>
    </form>
    <div class="links"><span></span><form method="post" action="/auth/logout" style="margin:0">
      <button type="submit" style="background:none;color:#5b6b80;margin:0;padding:0;width:auto;font-size:13px">
        Sign out</button></form></div>""",
    )
