"""Shared app shell: theme resolution, top bar / bottom tabs, living dot, footer.

Every authenticated view renders through render_shell() so navigation, theming,
and the freshness dot behave identically across the app.
"""

from __future__ import annotations

import html

TABS = [
    ("now", "Now", "/", "•"),
    ("night", "Tonight", "/night", "☾"),
    ("rhythms", "Rhythms", "/rhythms", "▦"),
    ("data", "Data", "/data", "≡"),
]

# Runs before first paint so the page never flashes the wrong theme.
THEME_RESOLVER = """<script>
(function () {
  try {
    var saved = localStorage.getItem('owletTheme');
    var mode = saved && saved !== 'auto'
      ? saved
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = mode;
  } catch (e) { document.documentElement.dataset.theme = 'light'; }
})();
</script>"""

SHELL_JS = """<script>
(function () {
  // ---- theme toggle: auto -> light -> dark -> auto ----
  var ICONS = { auto: '◐', light: '☀', dark: '☾' };
  function currentSetting() { return localStorage.getItem('owletTheme') || 'auto'; }
  function applyTheme(setting) {
    var mode = setting !== 'auto'
      ? setting
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = mode;
    var button = document.getElementById('themeToggle');
    if (button) {
      button.textContent = ICONS[setting];
      button.title = 'Theme: ' + setting + ' — click to change';
    }
  }
  applyTheme(currentSetting());
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    applyTheme(currentSetting());
  });
  var toggle = document.getElementById('themeToggle');
  if (toggle) toggle.addEventListener('click', function () {
    var order = ['auto', 'light', 'dark'];
    var next = order[(order.indexOf(currentSetting()) + 1) % order.length];
    localStorage.setItem('owletTheme', next);
    applyTheme(next);
    // Write-through to the account so other devices follow (best effort).
    fetch('/api/accounts').then(function (r) { return r.json(); }).then(function (data) {
      var account = (data.accounts || [])[0];
      if (!account) return;
      fetch('/api/accounts/' + account.id, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dashboard_preferences: { chart_settings: {}, theme: next } })
      });
    }).catch(function () {});
  });

  // ---- living dot: freshness of the newest reading ----
  var pollInterval = 5;
  var lastReadingAt = null;
  function paintDot() {
    var dot = document.getElementById('shellDot');
    if (!dot) return;
    if (lastReadingAt === null) {
      dot.style.backgroundColor = '';
      dot.title = 'No readings yet';
      return;
    }
    var totalMs = pollInterval * 1000;
    var age = Date.now() - lastReadingAt;
    var intervals = age / totalMs;
    var mix = function (from, to, fade) { return Math.round(from + (to - from) * fade); };
    if (intervals <= 1.5) {
      var f = intervals / 1.5;
      dot.style.backgroundColor = 'rgb(' + mix(16, 148, f) + ',' + mix(220, 163, f) + ',' + mix(96, 184, f) + ')';
      dot.title = 'Live — data ' + Math.round(age / 1000) + 's old · click to refresh';
    } else {
      var g = Math.min(1, (intervals - 1.5) / 2.5);
      dot.style.backgroundColor = 'rgb(' + mix(148, 239, g) + ',' + mix(163, 68, g) + ',' + mix(184, 68, g) + ')';
      dot.title = 'No new data for ' + Math.round(age / 1000) + 's · click to refresh';
    }
  }
  function pollFreshness() {
    fetch('/api/widget?hours=1').then(function (r) { return r.json(); }).then(function (widget) {
      if (widget.updated_at) lastReadingAt = Date.parse(widget.updated_at);
      paintDot();
    }).catch(function () {});
  }
  fetch('/api/accounts').then(function (r) { return r.json(); }).then(function (data) {
    var account = (data.accounts || [])[0];
    if (account && account.poll_interval_seconds) pollInterval = account.poll_interval_seconds;
    var saved = account && account.dashboard_preferences && account.dashboard_preferences.theme;
    if (saved && saved !== currentSetting()) { localStorage.setItem('owletTheme', saved); applyTheme(saved); }
  }).catch(function () {});
  pollFreshness();
  setInterval(pollFreshness, 10000);
  setInterval(paintDot, 1000);
  var dot = document.getElementById('shellDot');
  if (dot) dot.addEventListener('click', function () { window.location.reload(); });
})();
</script>"""


def render_shell(*, view: str, title: str, head: str = "", body: str, scripts: str = "") -> str:
    tabs_top = "".join(
        f'<a href="{href}" class="{"active" if key == view else ""}">{label}</a>'
        for key, label, href, _icon in TABS
    )
    tabs_bottom = "".join(
        f'<a href="{href}" class="{"active" if key == view else ""}">'
        f"<span>{icon}</span>{label}</a>"
        for key, label, href, icon in TABS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} · Owlet Dashboard</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  {THEME_RESOLVER}
  <link rel="stylesheet" href="/theme.css" />
  {head}
</head>
<body class="themed">
  <header class="shell-top">
    <a class="shell-brand" href="/">Owlet Dashboard<span id="shellDot" class="shell-dot"
      role="button" tabindex="0" aria-label="Data freshness — click to refresh"></span></a>
    <nav class="shell-tabs" aria-label="Views">{tabs_top}</nav>
    <span class="shell-side">
      <button id="themeToggle" class="theme-toggle" type="button" aria-label="Switch theme">◐</button>
    </span>
  </header>
  <main class="shell-main">
{body}
  </main>
  <footer class="shell-footer">Retrospective trend viewing only — not a medical monitor or alert
    replacement. Unofficial; not affiliated with Owlet Baby Care.</footer>
  <nav class="shell-bottom" aria-label="Views">{tabs_bottom}</nav>
  {SHELL_JS}
  {scripts}
</body>
</html>"""
