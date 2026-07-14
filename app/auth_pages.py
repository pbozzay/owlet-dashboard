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


_LANDING = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Owlet Dashboard — every night, remembered</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    :root {{
      --bg:#f5f7fb; --panel:#fff; --text:#122033; --muted:#5b6b80;
      --purple:#6d28d9; --purple-soft:#ede9fe; --line:#e3e9f2;
    }}
    * {{ box-sizing:border-box; margin:0; }}
    body {{
      font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
      background:
        radial-gradient(1100px 500px at 15% -10%, var(--purple-soft), transparent 60%),
        radial-gradient(900px 400px at 110% 30%, #e0f2fe, transparent 55%),
        var(--bg);
      color:var(--text); min-height:100vh;
      display:flex; align-items:center; justify-content:center; padding:32px 20px;
    }}
    .wrap {{
      display:grid; grid-template-columns: 1.15fr .85fr; gap:48px;
      width:100%; max-width:980px; align-items:center;
    }}
    .brand {{ display:flex; align-items:center; gap:12px; margin-bottom:22px; }}
    .brand img {{ width:44px; height:44px; }}
    .brand span {{ font-size:20px; font-weight:700; letter-spacing:-.02em; }}
    h1 {{ font-size:clamp(30px, 4.2vw, 42px); line-height:1.12; letter-spacing:-.03em;
         margin-bottom:14px; }}
    h1 em {{ font-style:normal; color:var(--purple); }}
    .lede {{ color:var(--muted); font-size:16px; line-height:1.55; max-width:44ch;
            margin-bottom:14px; }}
    .oss {{ font-size:13.5px; color:var(--muted); margin-bottom:24px; }}
    .oss a {{ color:var(--purple); font-weight:600; text-decoration:none; }}
    ul.features {{ list-style:none; display:grid; gap:13px; }}
    ul.features li {{ display:flex; gap:12px; align-items:flex-start; font-size:14.5px;
                     line-height:1.45; }}
    ul.features b {{ display:block; font-size:14.5px; }}
    ul.features span {{ color:var(--muted); }}
    .dot {{ flex:none; width:30px; height:30px; border-radius:9px; background:var(--purple-soft);
           color:var(--purple); display:flex; align-items:center; justify-content:center;
           margin-top:1px; }}
    .dot svg {{ width:16px; height:16px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:18px;
            box-shadow:0 16px 44px rgba(18,32,51,.10); padding:30px; }}
    .card h2 {{ font-size:19px; margin-bottom:4px; }}
    .card p.sub {{ color:var(--muted); font-size:13.5px; margin-bottom:14px; }}
    .rightcol {{ display:flex; flex-direction:column; gap:18px; }}
    .shot {{ align-self:center; width:100%; max-width:250px; background:var(--panel);
            border:1px solid var(--line); border-radius:20px; padding:9px;
            box-shadow:0 12px 34px rgba(18,32,51,.12); }}
    .shot svg {{ display:block; width:100%; height:auto; border-radius:13px; }}
    .shot-cap {{ text-align:center; font-size:11.5px; color:var(--muted); margin-top:9px; }}
    label {{ display:block; font-size:13px; font-weight:600; margin:14px 0 5px; }}
    /* 16px minimum stops mobile Safari's forced zoom-on-focus */
    input {{ width:100%; padding:11px 12px; border:1px solid #d6dee9; border-radius:10px;
            font-size:16px; background:#fbfcfe; }}
    input:focus {{ outline:2px solid var(--purple); outline-offset:1px; border-color:transparent; }}
    button {{ margin-top:18px; width:100%; padding:12px; border:0; border-radius:10px;
             background:var(--purple); color:#fff; font-size:15px; font-weight:600;
             cursor:pointer; }}
    button:hover {{ background:#5b21b6; }}
    .alt {{ margin-top:14px; font-size:13.5px; color:var(--muted); text-align:center; }}
    .alt a {{ color:var(--purple); font-weight:600; text-decoration:none; }}
    .notice {{ background:#fef2f2; color:#991b1b; border-radius:10px; padding:10px 12px;
              font-size:13px; margin-bottom:6px; }}
    footer {{ grid-column:1 / -1; text-align:center; font-size:11.5px; color:var(--muted);
             margin-top:8px; }}
    @media (max-width: 800px) {{
      .wrap {{ grid-template-columns:1fr; gap:30px; max-width:460px; }}
      body {{ padding:26px 16px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section>
      <div class="brand"><img src="/logo.svg" alt="" /><span>Owlet Dashboard</span></div>
      <h1>A free web client for <em>Owlet</em> users.</h1>
      <p class="lede">Sign in with your Owlet account and Owlet Dashboard turns your sock's
        readings into a private history you can explore — live vitals, nightly sleep
        reports, and long-term rhythms, on any device.</p>
      <p class="oss">Free, open source, and unofficial — provided as-is, not affiliated with
        Owlet Baby Care. <a href="https://github.com/pbozzay/owlet-dashboard"
        rel="noopener">View the project on GitHub</a>.</p>
      <ul class="features">
        <li><span class="dot" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l2-7 4 14 2-7h6"/></svg></span>
          <div><b>Live vitals, kept for good</b>
          <span>Oxygen, heart rate, movement, and sleep every 30 seconds — zoom from the last minute to the last month, or export to CSV.</span></div></li>
        <li><span class="dot" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></span>
          <div><b>A plain-language report every night</b>
          <span>“Tonight” recaps each night in words: sleep stages, wake-ups, and every oxygen dip, with a seven-night trend.</span></div></li>
        <li><span class="dot" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V11M10 20V4M16 20v-6M21 20H3"/></svg></span>
          <div><b>Patterns as your baby grows</b>
          <span>“Rhythms” charts the day-night rhythm, sleep consolidation, and recurring dips across weeks — age-adjusted when you add a birth date.</span></div></li>
        <li><span class="dot" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8.5v7M8.5 12h7"/></svg></span>
          <div><b>Oxygen and feeds, logged in a tap</b>
          <span>Mark supplemental O₂ and its flow, feeds, and oxygen challenges — with real numbers against baseline for pediatrician visits.</span></div></li>
        <li><span class="dot" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.5 21a2 2 0 0 1-3 0"/></svg></span>
          <div><b>Alerts and status at a glance</b>
          <span>Set a low-oxygen threshold and get a toast or phone notification; battery and sock status ride in the top bar.</span></div></li>
        <li><span class="dot" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></span>
          <div><b>Private, and yours to run</b>
          <span>{privacy_copy} Installable as an app, or self-host it with Docker.</span></div></li>
      </ul>
    </section>
    <div class="rightcol">
      <div class="shot">
        {preview}
        <div class="shot-cap">A peek at the Today view</div>
      </div>
      <section class="card">
        <h2>Sign in</h2>
        <p class="sub">Welcome back — your charts are waiting.</p>
        {error}
        <form method="post" action="/auth/login">
          <label for="email">Email</label>
          <input id="email" name="email" type="text" inputmode="email" required
                 autocomplete="username" />
          <label for="password">Password</label>
          <input id="password" name="password" type="password" required autocomplete="current-password" />
          <button type="submit">Sign in</button>
        </form>
        <p class="alt">New here? <a href="/signup">Create a free account</a></p>
      </section>
    </div>
    <footer>Retrospective trend viewing only — not a medical monitor or alert replacement.
      Not affiliated with Owlet Baby Care.</footer>
  </div>
</body>
</html>"""


# A hand-built, on-brand mock of the Today screen — self-contained (no external
# assets, no real baby data), crisp at any size, and cheap to keep current as the
# UI evolves. Inserted into _LANDING as a .format() value, so its own braces (none
# here) don't need escaping.
_TODAY_PREVIEW_SVG = """<svg viewBox="0 0 300 372" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Preview of the Today view: live oxygen and heart-rate charts with sleep status">
  <rect width="300" height="372" rx="14" fill="#f5f7fb"/>
  <g font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">
    <text x="14" y="24" font-size="12.5" font-weight="700" fill="#122033">Owlet Dashboard</text>
    <circle cx="126" cy="20" r="3.2" fill="#f59e0b"/>
    <rect x="236" y="12" width="50" height="17" rx="8.5" fill="#fff" stroke="#e3e9f2"/>
    <text x="261" y="24" font-size="9.5" font-weight="600" fill="#5b6b80" text-anchor="middle">82%</text>
    <text x="14" y="56" font-size="12.5" fill="#5b6b80"><tspan font-weight="700" fill="#122033">The baby</tspan> is asleep</text>
    <rect x="256" y="45" width="30" height="17" rx="8.5" fill="#ede9fe"/>
    <text x="271" y="57" font-size="9.5" font-weight="700" fill="#6d28d9" text-anchor="middle">6h</text>
    <rect x="14" y="70" width="272" height="86" rx="13" fill="#fff" stroke="#e3e9f2"/>
    <text x="26" y="90" font-size="9" letter-spacing="1" font-weight="700" fill="#9aa7b8">OXYGEN</text>
    <text x="26" y="119" font-size="27" font-weight="700" fill="#122033">97<tspan font-size="14" fill="#5b6b80">%</tspan></text>
    <polyline points="150,140 161,133 172,142 183,128 194,139 205,124 216,138 227,130 238,143 249,132 260,139 271,134" fill="none" stroke="#6d28d9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="14" y="166" width="272" height="86" rx="13" fill="#fff" stroke="#e3e9f2"/>
    <text x="26" y="186" font-size="9" letter-spacing="1" font-weight="700" fill="#9aa7b8">HEART RATE</text>
    <text x="26" y="215" font-size="27" font-weight="700" fill="#122033">128<tspan font-size="14" fill="#5b6b80"> bpm</tspan></text>
    <polyline points="150,236 160,230 170,234 180,226 190,232 200,222 210,231 220,224 230,235 240,228 250,233 260,227 271,232" fill="none" stroke="#7c3aed" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="14" y="262" width="84" height="50" rx="11" fill="#fff" stroke="#e3e9f2"/>
    <text x="56" y="288" font-size="13.5" font-weight="700" fill="#122033" text-anchor="middle">8h 20m</text>
    <text x="56" y="303" font-size="8.5" fill="#5b6b80" text-anchor="middle">sleep today</text>
    <rect x="106" y="262" width="84" height="50" rx="11" fill="#fff" stroke="#e3e9f2"/>
    <text x="148" y="288" font-size="13.5" font-weight="700" fill="#122033" text-anchor="middle">2</text>
    <text x="148" y="303" font-size="8.5" fill="#5b6b80" text-anchor="middle">O₂ dips today</text>
    <rect x="198" y="262" width="88" height="50" rx="11" fill="#fff" stroke="#e3e9f2"/>
    <text x="242" y="288" font-size="12.5" font-weight="700" fill="#3b82f6" text-anchor="middle">O₂ off</text>
    <text x="242" y="303" font-size="8.5" fill="#5b6b80" text-anchor="middle">supplemental</text>
    <line x1="14" y1="332" x2="286" y2="332" stroke="#e3e9f2"/>
    <text x="44" y="352" font-size="9" font-weight="700" fill="#6d28d9" text-anchor="middle">Today</text>
    <text x="115" y="352" font-size="9" fill="#8a98ab" text-anchor="middle">Tonight</text>
    <text x="188" y="352" font-size="9" fill="#8a98ab" text-anchor="middle">Rhythms</text>
    <text x="256" y="352" font-size="9" fill="#8a98ab" text-anchor="middle">Data</text>
  </g>
</svg>"""


HOSTED_PRIVACY_COPY = (
    "Your Owlet password is verified once and never stored. "
    "Your baby's data is only visible to you."
)
DESKTOP_PRIVACY_COPY = (
    "Everything lives on this computer. Your Owlet login is kept locally so "
    "collection can always reconnect - nothing is sent anywhere else."
)


def login_page(error: str | None = None, desktop_mode: bool = False) -> str:
    return _LANDING.format(
        error=_error(error),
        privacy_copy=DESKTOP_PRIVACY_COPY if desktop_mode else HOSTED_PRIVACY_COPY,
        preview=_TODAY_PREVIEW_SVG,
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
