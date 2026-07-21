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
    /* 16px minimum stops mobile Safari's forced zoom-on-focus */
    input, select {{ width:100%; padding:10px 12px; border:1px solid #d6dee9; border-radius:10px; font-size:16px; }}
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
    # role="alert" makes screen readers announce the failure on page load
    return f'<div class="notice" role="alert">{html.escape(error)}</div>' if error else ""


def desktop_redirect_page(url: str) -> str:
    """Bounce the desktop window to a remote instance. A plain meta/JS redirect
    so the webview lands on the always-on server and behaves as its web app."""
    safe = html.escape(url, quote=True)
    return (
        f'<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={safe}">'
        f'<script>location.replace({html.escape(_json_str(url))})</script>'
        f'<p style="font:15px system-ui;padding:24px;color:#5b6b80">Connecting to {safe}…</p>'
    )


def _json_str(value: str) -> str:
    import json as _json

    return _json.dumps(value)


def desktop_launcher_page(current_backend: str | None = None, error: str | None = None) -> str:
    change = ""
    if current_backend:
        change = (
            f'<p class="alt">Currently connected to '
            f'<b>{html.escape(current_backend)}</b>.</p>'
        )
    prefill = html.escape(current_backend or "", quote=True)
    return _LAUNCHER.format(error=_error(error), change=change, prefill=prefill)


_LAUNCHER = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Owlet Dashboard — get started</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    :root {{ --bg:#f5f7fb; --panel:#fff; --text:#122033; --muted:#5b6b80; --purple:#6d28d9;
             --purple-soft:#ede9fe; --line:#e3e9f2; }}
    * {{ box-sizing:border-box; margin:0; }}
    body {{ font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
      background:radial-gradient(1100px 500px at 15% -10%, var(--purple-soft), transparent 60%), var(--bg);
      color:var(--text); min-height:100vh; display:flex; align-items:center; justify-content:center; padding:32px 20px; }}
    .wrap {{ width:100%; max-width:640px; }}
    .brand {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
    .brand img {{ width:40px; height:40px; }}
    .brand span {{ font-size:19px; font-weight:700; letter-spacing:-.02em; }}
    h1 {{ font-size:26px; letter-spacing:-.02em; margin:14px 0 6px; }}
    .lede {{ color:var(--muted); font-size:15px; line-height:1.55; margin-bottom:22px; }}
    .opt {{ background:var(--panel); border:1px solid var(--line); border-radius:16px;
      box-shadow:0 12px 34px rgba(18,32,51,.08); padding:20px 22px; margin-bottom:16px; }}
    .opt h2 {{ font-size:17px; margin-bottom:4px; }}
    .opt p {{ color:var(--muted); font-size:13.5px; line-height:1.5; margin-bottom:14px; }}
    .opt.primary {{ border:1.5px solid var(--purple); }}
    input {{ width:100%; padding:11px 12px; border:1px solid #d6dee9; border-radius:10px;
      font-size:16px; background:#fbfcfe; margin-bottom:10px; }}
    input:focus {{ outline:2px solid var(--purple); outline-offset:1px; border-color:transparent; }}
    button {{ width:100%; padding:12px; border:0; border-radius:10px; background:var(--purple);
      color:#fff; font-size:15px; font-weight:600; cursor:pointer; }}
    button:hover {{ background:#5b21b6; }}
    button.ghost {{ background:transparent; color:var(--purple); border:1px solid var(--line); }}
    button.ghost:hover {{ background:var(--purple-soft); }}
    button[disabled] {{ opacity:.6; cursor:default; }}
    .alt {{ font-size:13px; color:var(--muted); margin-top:8px; text-align:center; }}
    .notice {{ background:#fef2f2; color:#991b1b; border-radius:10px; padding:10px 12px;
      font-size:13px; margin-bottom:10px; }}
    footer {{ text-align:center; font-size:11.5px; color:var(--muted); margin-top:14px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="brand"><img src="/logo.svg" alt="" /><span>Owlet Dashboard</span></div>
    <h1>How do you want to use this app?</h1>
    <p class="lede">Point this window at an always-on server you run, or collect right here on
      this PC.</p>
    {error}
    <div class="opt primary">
      <h2>Connect to a live server</h2>
      <p>Best if you run the Docker/Unraid version somewhere always-on. This window becomes a
        viewer for it — real 24/7 history, nothing lost when this PC sleeps, and a normal login.</p>
      <input id="serverUrl" type="url" inputmode="url" placeholder="https://owlet.yourdomain.com"
        value="{prefill}" autocomplete="off" />
      <button id="connectBtn" type="button">Connect</button>
    </div>
    <div class="opt">
      <h2>Collect on this PC</h2>
      <p>No server needed. This app collects readings itself — but only while it's open and the PC
        is awake, so expect gaps. Good for trying it out or travel.</p>
      <form method="post" action="/desktop/use-local"><button class="ghost" type="submit">Use this PC</button></form>
    </div>
    {change}
    <footer>You can switch anytime from the Instance menu.</footer>
  </div>
  <script>
    var btn = document.getElementById('connectBtn');
    btn.addEventListener('click', function () {{
      var url = document.getElementById('serverUrl').value.trim();
      if (!/^https?:\\/\\//i.test(url)) {{ alert('Enter a full address starting with http:// or https://'); return; }}
      btn.disabled = true; btn.textContent = 'Connecting…';
      fetch('/desktop/connect', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{ url: url }}) }})
        .then(function (r) {{ return r.json().then(function (d) {{ return {{ ok: r.ok, d: d }}; }}); }})
        .then(function (res) {{ if (!res.ok) throw new Error(res.d.detail || 'Could not connect'); window.location.href = res.d.url; }})
        .catch(function (e) {{ btn.disabled = false; btn.textContent = 'Connect'; alert(e.message); }});
    }});
  </script>
</body>
</html>"""


_LANDING = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#0b1023" />
  <title>Owlet Dashboard — every night, remembered</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    /* Split screen: the story lives on a night-coloured panel (the app's own
       Tonight palette), the sign-in gets an uncontested half of the page. */
    :root {{
      --night:#0b1023; --night-2:#232b5c; --ink-dark:#e8ecf8; --dim-dark:#9aa3c8;
      --line-dark:rgba(139,148,184,.28); --indigo:#a5b4fc; --accent:#4f46e5;
      --paper:#faf7f2; --ink:#1c1917; --dim:#78716c; --faint:#a8a29e; --line:#e7e0d5;
    }}
    * {{ box-sizing:border-box; margin:0; }}
    body {{
      font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; color:var(--ink);
      min-height:100vh; display:grid; grid-template-columns:1.08fr .92fr;
    }}
    /* ---- left: the pitch ------------------------------------------------ */
    .story {{
      background:radial-gradient(900px 600px at 20% -10%, var(--night-2) 0%, transparent 60%),
                 var(--night);
      color:var(--ink-dark); padding:52px 56px 0;
      display:flex; flex-direction:column; overflow:hidden;
    }}
    .brand {{ display:flex; align-items:center; gap:11px; margin-bottom:40px; }}
    .brand img {{ width:32px; height:32px; border-radius:8px; }}
    .brand span {{ font-size:14.5px; font-weight:650; color:#c7cdf0; letter-spacing:.01em; }}
    /* A system serif — editorial voice with no webfont to download, which
       keeps the self-hosted/offline story intact. */
    h1 {{
      font-family:ui-serif,Georgia,'Times New Roman',serif; font-weight:500;
      font-size:clamp(32px,3.5vw,48px); line-height:1.05; letter-spacing:-.025em;
      max-width:13ch; margin-bottom:16px;
    }}
    h1 em {{ font-style:italic; color:var(--indigo); }}
    .lede {{ color:var(--dim-dark); font-size:16px; line-height:1.6; max-width:44ch;
            margin-bottom:24px; }}
    .pills {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .pills span {{ font-size:12.5px; color:#c7cdf0; border:1px solid var(--line-dark);
                  padding:6px 12px; border-radius:999px; }}
    /* the phone runs off the bottom edge — implies there is more below */
    .shot {{ margin:38px auto -2px; width:min(300px,78%); }}
    .shot img {{ width:100%; height:auto; display:block; border-radius:22px 22px 0 0;
                border:1px solid var(--line-dark); border-bottom:0;
                box-shadow:0 -10px 80px rgba(129,140,248,.22); }}
    /* ---- right: sign in -------------------------------------------------- */
    .signin {{ background:var(--paper); display:flex; align-items:center;
              justify-content:center; padding:48px 44px; }}
    .panel {{ width:100%; max-width:352px; }}
    .panel h2 {{ font-size:26px; letter-spacing:-.02em; margin-bottom:5px; }}
    .panel p.sub {{ color:var(--dim); font-size:14px; line-height:1.5; margin-bottom:18px; }}
    label {{ display:block; font-size:12.5px; font-weight:650; margin:14px 0 5px; }}
    /* 16px minimum stops mobile Safari's forced zoom-on-focus */
    input {{ width:100%; padding:12px; border:1px solid var(--line); border-radius:11px;
            font-size:16px; background:#fff; }}
    input:focus {{ outline:2px solid var(--accent); outline-offset:1px; border-color:transparent; }}
    button {{ margin-top:20px; width:100%; padding:13px; border:0; border-radius:11px;
             background:var(--accent); color:#fff; font-size:15px; font-weight:650;
             cursor:pointer; }}
    button:hover {{ background:#4338ca; }}
    .alt {{ margin-top:14px; font-size:13px; color:var(--dim); text-align:center; }}
    .alt a {{ color:var(--accent); font-weight:650; text-decoration:none; }}
    .notice {{ background:#fef2f2; color:#991b1b; border-radius:10px; padding:10px 12px;
              font-size:13px; margin-bottom:6px; }}
    .fine {{ margin-top:28px; padding-top:18px; border-top:1px solid var(--line);
            font-size:11.5px; color:var(--faint); line-height:1.55; }}
    .fine a {{ color:var(--dim); font-weight:600; }}
    .fine p + p {{ margin-top:7px; }}
    /* Side by side, the split owns exactly one screen: the phone clips at the
       bottom edge instead of stretching the page into a scroll. The sign-in
       half scrolls on its own so a short laptop can still reach the button. */
    @media (min-width: 901px) {{
      body {{ height:100vh; }}
      .story {{ overflow:hidden; }}
      .signin {{ overflow-y:auto; }}
    }}
    /* ---- stacked ---------------------------------------------------------- */
    @media (max-width: 900px) {{
      body {{ grid-template-columns:1fr; }}
      .story {{ padding:34px 26px 0; }}
      .brand {{ margin-bottom:26px; }}
      h1 {{ max-width:none; }}
      /* On a phone the mockup earns less than the ~550px of scroll it costs
         before the sign-in form — show the top of the Today view as a peek. */
      .shot {{ margin:26px auto 0; width:min(240px,66%); max-height:210px;
              overflow:hidden; border-radius:18px 18px 0 0; }}
      .signin {{ padding:34px 26px 40px; }}
      .panel {{ max-width:420px; }}
    }}
  </style>
</head>
<body>
  <section class="story">
    <div class="brand"><img src="/logo.svg" alt="" /><span>Owlet Dashboard</span></div>
    <h1>Every night, <em>remembered</em>.</h1>
    <p class="lede">Sign in with your Owlet account and your sock's readings become a private
      history you can explore — live vitals, a plain-language report each night, and the
      rhythms that emerge as your baby grows.</p>
    <div class="pills">
      <span>Live vitals every 30s</span><span>Nightly reports</span>
      <span>Long-term rhythms</span><span>O₂ and feed logging</span><span>Self-hostable</span>
    </div>
    <div class="shot">{preview}</div>
  </section>
  <main class="signin">
    <div class="panel">
      <h2>Sign in</h2>
      <p class="sub">{signin_sub}</p>
      {error}
      <form method="post" action="/auth/login">
        <label for="email">{email_label}</label>
        <input id="email" name="email" type="text" inputmode="email" required
               autocomplete="username" />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" required
               autocomplete="current-password" />
        <button type="submit">Sign in</button>
      </form>
      {signup_line}
      <div class="fine">
        <p>{privacy_copy}</p>
        <p>Free, open source, and unofficial — provided as-is, not affiliated with Owlet Baby
          Care. <a href="https://github.com/pbozzay/owlet-dashboard" rel="noopener">View the
          project on GitHub</a>.</p>
        <p>Retrospective trend viewing only — not a medical monitor or alert replacement.</p>
      </div>
    </div>
  </main>
</body>
</html>"""


# A real capture of the Today view (mobile width, anonymized name), shipped as a
# static asset and served by /preview-today.png. Refresh it by re-shooting the
# page into app/static/preview-today.png whenever the UI meaningfully changes.
_TODAY_PREVIEW_IMG = (
    '<img src="/preview-today.png" width="375" height="790" loading="lazy" '
    'alt="The Today view: live oxygen and heart-rate charts with baseline bands, '
    'sleep and movement tiles, and the day\'s totals" />'
)


HOSTED_PRIVACY_COPY = (
    "Your Owlet password is verified once and never stored. "
    "Your baby's data is only visible to you."
)
DESKTOP_PRIVACY_COPY = (
    "Everything lives on this computer. Your Owlet login is kept locally so "
    "collection can always reconnect - nothing is sent anywhere else."
)


def login_page(error: str | None = None, desktop_mode: bool = False) -> str:
    # Desktop is a purely local login (seeded admin account), not a web
    # account — offering "create a free account" there reads like signing up
    # for a hosted service that doesn't exist.
    if desktop_mode:
        signin_sub = ("This app runs entirely on this computer. Sign in with the local "
                      "account — <b>admin</b> / <b>password</b> until you change it in "
                      "Settings → Sign-in.")
        signup_line = ""
        email_label = "Username"
    else:
        signin_sub = "Welcome back — your charts are waiting."
        signup_line = '<p class="alt">New here? <a href="/signup">Create a free account</a></p>'
        email_label = "Email"
    return _LANDING.format(
        error=_error(error),
        privacy_copy=DESKTOP_PRIVACY_COPY if desktop_mode else HOSTED_PRIVACY_COPY,
        preview=_TODAY_PREVIEW_IMG,
        signin_sub=signin_sub,
        signup_line=signup_line,
        email_label=email_label,
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


def onboarding_page(error: str | None = None, desktop_mode: bool = False) -> str:
    promise = (
        """Your Owlet login is <strong>stored only on this computer</strong> so collection
    can always reconnect, even after weeks powered off."""
        if desktop_mode
        else """We verify it with Owlet once and
    <strong>never store your Owlet password</strong> — only a revocable access token."""
    )
    return _page(
        "Link your Owlet sock",
        f"""<h1>Link your Owlet sock</h1>
    <p class="sub">Enter the login you use in the Owlet app. {promise}</p>
    {_error(error)}
    <form method="post" action="/onboarding/link" onsubmit="const b=this.querySelector('button[type=submit]');b.disabled=true;b.textContent='Linking with Owlet…';">
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
      <button type="submit" style="background:none;color:#5b6b80;margin:0;padding:12px 10px;width:auto;min-height:44px;font-size:13px">
        Sign out</button></form></div>""",
    )
