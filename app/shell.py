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
  // ---- theme: auto | light | dark, segmented control in the profile menu ----
  function currentSetting() { return localStorage.getItem('owletTheme') || 'auto'; }
  function applyTheme(setting) {
    var mode = setting !== 'auto'
      ? setting
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var changed = document.documentElement.dataset.theme !== mode;
    document.documentElement.dataset.theme = mode;
    document.querySelectorAll('[data-theme-set]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.themeSet === setting);
    });
    // Only pages that need a hard restyle (chart re-init) hook this; fire it
    // solely on real mode flips so theme sync never causes reload loops.
    if (changed && typeof window.__onThemeChange === 'function') window.__onThemeChange(mode);
  }
  applyTheme(currentSetting());
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    applyTheme(currentSetting());
  });
  document.querySelectorAll('[data-theme-set]').forEach(function (button) {
    button.addEventListener('click', function () {
      var next = button.dataset.themeSet;
      localStorage.setItem('owletTheme', next);
      applyTheme(next);
      fetch('/api/accounts').then(function (r) { return r.json(); }).then(function (data) {
        var account = (data.accounts || [])[0];
        if (!account) return;
        fetch('/api/accounts/' + account.id, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dashboard_preferences: { theme: next } })
        });
      }).catch(function () {});
    });
  });

  // ---- profile dropdown (the transplanted account & settings menu) ----
  var byId = function (id) { return document.getElementById(id); };
  var profileButton = byId('profileMenuToggle');
  var profileMenu = byId('profileMenu');
  function closeProfile() {
    if (!profileMenu) return;
    profileMenu.hidden = true;
    if (profileButton) profileButton.setAttribute('aria-expanded', 'false');
  }
  if (profileButton && profileMenu) {
    profileButton.addEventListener('click', function (event) {
      event.stopPropagation();
      profileMenu.hidden = !profileMenu.hidden;
      profileButton.setAttribute('aria-expanded', String(!profileMenu.hidden));
    });
    document.addEventListener('click', function (event) {
      if (!profileMenu.hidden && !profileMenu.contains(event.target)) closeProfile();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeProfile();
    });
  }

  var shellAccounts = [];
  function shellSelectedAccount() {
    var select = byId('accountSelect');
    var id = select && select.value;
    return shellAccounts.find(function (a) { return String(a.id) === String(id); }) || shellAccounts[0] || null;
  }
  function renderShellMenu(devices) {
    var account = shellSelectedAccount();
    var device = (devices || [])[0];
    var name = account ? (account.display_name || account.email || 'Owlet profile') : 'Owlet profile';
    var deviceName = device ? (device.baby_name || device.name || 'Owlet sock') : 'Owlet sock';
    var initials = name.replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || 'O';
    ['profileAvatar', 'profileMenuAvatar'].forEach(function (id) {
      var node = byId(id); if (node) node.textContent = initials;
    });
    if (byId('profileAccountName')) byId('profileAccountName').textContent = name;
    if (byId('profileMenuTitle')) byId('profileMenuTitle').textContent = name;
    if (byId('profileDeviceName')) byId('profileDeviceName').textContent = deviceName;
    if (byId('profileMenuSubtitle')) byId('profileMenuSubtitle').textContent = deviceName;
    if (byId('showCryptoSetting')) byId('showCryptoSetting').checked = !!(account && account.show_crypto);
    if (byId('pollIntervalSetting')) byId('pollIntervalSetting').value = String((account && account.poll_interval_seconds) || 5);
  }
  function loadShellAccounts() {
    return Promise.all([
      fetch('/api/accounts').then(function (r) { return r.json(); }),
      fetch('/api/devices').then(function (r) { return r.json(); })
    ]).then(function (results) {
      shellAccounts = results[0].accounts || [];
      var account = shellAccounts[0];
      if (account && account.poll_interval_seconds) pollInterval = account.poll_interval_seconds;
      var saved = account && account.dashboard_preferences && account.dashboard_preferences.theme;
      if (saved && saved !== currentSetting()) { localStorage.setItem('owletTheme', saved); applyTheme(saved); }
      // Pages with their own account-switching logic (the Data workbench) own
      // the select's contents; everywhere else the shell fills it.
      var select = byId('accountSelect');
      if (select && !window.__pageOwnsAccountSelect) {
        var current = select.value;
        select.innerHTML = shellAccounts.map(function (a) {
          return '<option value="' + a.id + '">' + (a.display_name || a.email) + '</option>';
        }).join('');
        if (current && shellAccounts.some(function (a) { return String(a.id) === current; })) select.value = current;
      }
      renderShellMenu(results[1].devices || []);
    }).catch(function () {});
  }
  function patchSelectedAccount(body) {
    var account = shellSelectedAccount();
    if (!account) return Promise.resolve(null);
    return fetch('/api/accounts/' + account.id, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (data.account) {
        var index = shellAccounts.findIndex(function (a) { return String(a.id) === String(data.account.id); });
        if (index >= 0) shellAccounts[index] = data.account;
      }
      document.dispatchEvent(new CustomEvent('owlet:prefs-changed', { detail: data.account || null }));
      return data.account;
    }).catch(function () { return null; });
  }
  if (byId('showCryptoSetting')) byId('showCryptoSetting').addEventListener('change', function (event) {
    patchSelectedAccount({ show_crypto: event.target.checked });
  });
  if (byId('pollIntervalSetting')) byId('pollIntervalSetting').addEventListener('change', function (event) {
    patchSelectedAccount({ poll_interval_seconds: Number(event.target.value) }).then(function (account) {
      if (account && account.poll_interval_seconds) pollInterval = account.poll_interval_seconds;
    });
  });
  if (byId('accountSelect')) byId('accountSelect').addEventListener('change', function () {
    renderShellMenu([]);
  });
  if (byId('addAccount')) byId('addAccount').addEventListener('click', function () {
    var email = prompt('Owlet email');
    if (!email) return;
    var password = prompt('Owlet password (verified once with Owlet)');
    if (!password) return;
    var region = prompt('Owlet region', 'world') || 'world';
    var displayName = prompt('Display name', email) || email;
    fetch('/api/accounts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: password, region: region, display_name: displayName })
    }).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    }).then(function (data) {
      var event = new CustomEvent('owlet:account-added', { detail: data.account || null, cancelable: true });
      var handled = !document.dispatchEvent(event);
      if (!handled) window.location.reload();
    }).catch(function () {
      alert('Could not validate that Owlet account. Check the email/password/region and try again.');
    });
  });

  // ---- install app ----
  var deferredInstall = null;
  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredInstall = event;
  });
  if (byId('installApp')) byId('installApp').addEventListener('click', function () {
    if (deferredInstall) {
      deferredInstall.prompt();
      deferredInstall = null;
    } else {
      alert('To install: open the browser menu and choose "Install app" / "Add to Home Screen".');
    }
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
  function paintStatus() {
    var status = byId('status');
    if (!status) return;
    var fresh = lastReadingAt !== null && (Date.now() - lastReadingAt) < pollInterval * 3000;
    var dotClass = lastReadingAt === null ? '' : (fresh ? 'good' : 'offline');
    var label = lastReadingAt === null
      ? 'Waiting for first reading…'
      : (fresh ? 'Collecting live' : 'No new data for ' + Math.round((Date.now() - lastReadingAt) / 1000) + 's');
    status.innerHTML = '<span class="status-dot ' + dotClass + '"></span>' + label;
  }
  function pollFreshness() {
    fetch('/api/widget?hours=1').then(function (r) { return r.json(); }).then(function (widget) {
      if (widget.updated_at) lastReadingAt = Date.parse(widget.updated_at);
      paintDot();
      paintStatus();
    }).catch(function () {});
  }
  loadShellAccounts();
  pollFreshness();
  setInterval(pollFreshness, 10000);
  setInterval(paintDot, 1000);
  var dot = document.getElementById('shellDot');
  if (dot) dot.addEventListener('click', function () { window.location.reload(); });
})();
</script>"""


def render_shell(
    *, view: str, title: str, head: str = "", body: str, scripts: str = "", wide: bool = False
) -> str:
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
  <meta name="theme-color" content="#122033" />
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-title" content="Owlet" />
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
    <span class="shell-side" id="profileMenuWrap">
      <button id="profileMenuToggle" class="profile-chip" type="button" aria-haspopup="menu"
        aria-expanded="false" title="Account and dashboard settings">
        <span id="profileAvatar" class="pc-avatar" aria-hidden="true">·</span>
        <span class="pc-labels">
          <span id="profileAccountName" class="pc-name">Owlet profile</span>
          <span id="profileDeviceName" class="pc-device">Owlet sock</span>
        </span>
        <span class="pc-caret" aria-hidden="true">▾</span>
      </button>
      <div id="profileMenu" class="profile-pop card" role="menu"
        aria-label="Account and dashboard settings" hidden>
        <div class="pp-id">
          <span id="profileMenuAvatar" class="pp-avatar" aria-hidden="true">·</span>
          <div><b id="profileMenuTitle">…</b><small id="profileMenuSubtitle"></small></div>
        </div>
        <div class="pp-section" id="accountCluster">
          <span class="pp-label">Owlet account</span>
          <div class="pp-row">
            <select id="accountSelect"><option value="">Default</option></select>
            <button id="addAccount" class="pp-link-btn" type="button"
              title="Link another Owlet account">Link</button>
          </div>
        </div>
        <div class="pp-section">
          <label class="pp-toggle" for="showCryptoSetting">
            <span><b>Crypto widget</b><small>BTC card + optional chart line</small></span>
            <input id="showCryptoSetting" type="checkbox" />
          </label>
        </div>
        <div class="pp-section">
          <span class="pp-label">Update every</span>
          <select id="pollIntervalSetting">
            <option value="5">5 sec</option>
            <option value="10">10 sec</option>
            <option value="30">30 sec</option>
            <option value="60">1 min</option>
            <option value="300">5 min</option>
          </select>
        </div>
        <div class="pp-section">
          <span class="pp-label">Theme</span>
          <div class="pp-seg" role="group" aria-label="Theme">
            <button type="button" data-theme-set="auto">Auto</button>
            <button type="button" data-theme-set="light">Light</button>
            <button type="button" data-theme-set="dark">Dark</button>
          </div>
        </div>
        <div class="pp-actions">
          <button id="installApp" class="pp-install" type="button"
            title="Install Owlet as an app">Install app</button>
          <form method="post" action="/auth/logout" class="pp-signout" style="margin:0">
            <button type="submit">Sign out</button>
          </form>
        </div>
        <div class="pp-status" id="status"><span class="status-dot"></span>Checking collector…</div>
      </div>
    </span>
  </header>
  <main class="shell-main{' wide' if wide else ''}">
{body}
  </main>
  <footer class="shell-footer">Retrospective trend viewing only — not a medical monitor or alert
    replacement. Unofficial; not affiliated with Owlet Baby Care.</footer>
  <nav class="shell-bottom" aria-label="Views">{tabs_bottom}</nav>
  {SHELL_JS}
  {scripts}
</body>
</html>"""
