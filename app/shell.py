"""Shared app shell: theme resolution, top bar / bottom tabs, living dot, footer.

Every authenticated view renders through render_shell() so navigation, theming,
and the freshness dot behave identically across the app.
"""

from __future__ import annotations

import html

TABS = [
    ("now", "Today", "/", "•"),
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
  function persistThemePreference(next, accountId) {
    // keepalive: applyTheme() reloads chart pages immediately, and without it
    // the PATCH gets cancelled mid-flight — the server preference never
    // updates and the shell syncs the old theme right back after reload.
    return fetch('/api/accounts/' + accountId, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dashboard_preferences: { theme: next } }),
      keepalive: true
    }).catch(function () {});
  }
  document.querySelectorAll('[data-theme-set]').forEach(function (button) {
    button.addEventListener('click', function () {
      var next = button.dataset.themeSet;
      localStorage.setItem('owletTheme', next);
      var account = shellAccounts[0];
      if (account) {
        persistThemePreference(next, account.id);
        applyTheme(next);
      } else {
        fetch('/api/accounts').then(function (r) { return r.json(); }).then(function (data) {
          var found = (data.accounts || [])[0];
          if (found) return persistThemePreference(next, found.id);
        }).catch(function () {}).then(function () { applyTheme(next); });
      }
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
      if (typeof closeBell === 'function') closeBell();
      if (typeof closeBatt === 'function') closeBatt();
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
    var babyName = account && account.dashboard_preferences && account.dashboard_preferences.baby_name;
    var deviceName = babyName || (device ? (device.baby_name || device.name || 'Owlet sock') : 'Owlet sock');
    var initials = name.replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || 'O';
    ['profileAvatar', 'profileMenuAvatar'].forEach(function (id) {
      var node = byId(id); if (node) node.textContent = initials;
    });
    if (byId('profileAccountName')) byId('profileAccountName').textContent = name;
    if (byId('profileMenuTitle')) byId('profileMenuTitle').textContent = name;
    if (byId('profileDeviceName')) byId('profileDeviceName').textContent = deviceName;
    if (byId('profileMenuSubtitle')) byId('profileMenuSubtitle').textContent = deviceName;
    if (byId('pollIntervalSetting')) byId('pollIntervalSetting').value = String((account && account.poll_interval_seconds) || 5);
    if (byId('babyNameSetting') && document.activeElement !== byId('babyNameSetting')) {
      byId('babyNameSetting').value = babyName || '';
    }
  }
  function loadShellAccounts() {
    return Promise.all([
      fetch('/api/accounts').then(function (r) {
        if (r.status === 401) { window.location.href = '/login'; throw new Error('unauthenticated'); }
        return r.json();
      }),
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
  if (byId('pollIntervalSetting')) byId('pollIntervalSetting').addEventListener('change', function (event) {
    patchSelectedAccount({ poll_interval_seconds: Number(event.target.value) }).then(function (account) {
      if (account && account.poll_interval_seconds) pollInterval = account.poll_interval_seconds;
    });
  });
  if (byId('babyNameSetting')) byId('babyNameSetting').addEventListener('change', function (event) {
    patchSelectedAccount({ dashboard_preferences: { baby_name: event.target.value.trim() } })
      .then(function () { loadShellAccounts(); });
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

  // ---- notifications: shell bell, unread badge, toasts ----
  var bellButton = byId('shellBell');
  var bellPop = byId('bellPop');
  var unreadCount = 0;
  function escapeHtml(text) {
    return String(text == null ? '' : text).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function notificationTime(iso) {
    var date = new Date(iso);
    var h = date.getHours();
    var minutes = String(date.getMinutes()).padStart(2, '0');
    var ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
    var label = h + ':' + minutes + ' ' + ap;
    if (date.toDateString() !== new Date().toDateString()) {
      label = (date.getMonth() + 1) + '/' + date.getDate() + ' ' + label;
    }
    return label;
  }
  function focusLink(notification) {
    return '/data?focus=' + encodeURIComponent(notification.recorded_at) + '&span=30';
  }
  function paintBell() {
    var badge = byId('shellBellCount');
    if (!badge) return;
    badge.hidden = unreadCount <= 0;
    badge.textContent = unreadCount > 99 ? '99+' : String(unreadCount);
  }
  function closeBell() {
    if (!bellPop) return;
    bellPop.hidden = true;
    if (bellButton) bellButton.setAttribute('aria-expanded', 'false');
  }
  function openBell() {
    closeProfile(); closeBatt();
    bellPop.hidden = false;
    bellButton.setAttribute('aria-expanded', 'true');
    byId('bellList').innerHTML = '<div class="bell-empty">Loading…</div>';
    fetch('/api/notifications?hours=168&limit=25')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var items = data.items || [];
        byId('bellList').innerHTML = items.length
          ? items.map(function (n) {
              return '<a class="bell-item ' + (n.severity || 'info') + (n.read_at ? '' : ' unread') + '"'
                + ' href="' + focusLink(n) + '">'
                + '<b>' + escapeHtml(n.title) + '</b>'
                + '<span>' + notificationTime(n.recorded_at) + ' · ' + escapeHtml(n.message) + '</span>'
                + '</a>';
            }).join('')
          : '<div class="bell-empty">Nothing yet — alerts from the sock land here.</div>';
        // Opening the panel is reading it.
        if (unreadCount > 0) fetch('/api/notifications/read', { method: 'POST' }).catch(function () {});
        unreadCount = 0;
        paintBell();
      })
      .catch(function () {
        byId('bellList').innerHTML = '<div class="bell-empty">Could not load notifications.</div>';
      });
  }
  if (bellButton && bellPop) {
    bellButton.addEventListener('click', function (event) {
      event.stopPropagation();
      if (bellPop.hidden) openBell(); else closeBell();
    });
    document.addEventListener('click', function (event) {
      if (!bellPop.hidden && !bellPop.contains(event.target) && !bellButton.contains(event.target)) closeBell();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeBell();
    });
  }

  // ---- battery: top-bar glyph + charge/drain detail popover ----
  var battButton = byId('shellBattery');
  var battPop = byId('battPop');
  var battLevel = null;
  function paintBattery() {
    if (!battButton) return;
    var pct = byId('shellBattPct'), fill = byId('shellBattFill');
    if (battLevel == null) {
      pct.textContent = '—';
      fill.style.width = '0%';
      battButton.className = 'shell-batt';
      return;
    }
    var level = Math.round(battLevel);
    pct.textContent = level + '%';
    fill.style.width = Math.max(6, Math.min(100, level)) + '%';
    battButton.className = 'shell-batt ' + (level <= 20 ? 'low' : level <= 50 ? 'mid' : 'good');
    battButton.title = 'Battery ' + level + '%';
  }
  function closeBatt() {
    if (!battPop) return;
    battPop.hidden = true;
    if (battButton) battButton.setAttribute('aria-expanded', 'false');
  }
  function openBatt() {
    closeProfile(); closeBell();
    battPop.hidden = false;
    battButton.setAttribute('aria-expanded', 'true');
    byId('battBody').innerHTML = '<div class="bell-empty">Reading the last few hours…</div>';
    fetch('/api/rollups?bucket=5m&hours=6&limit=200')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var series = (data.rollups || [])
          .map(function (row) { return { t: Date.parse(row.bucket_start), y: row.avg_battery }; })
          .filter(function (pt) { return pt.y != null; });
        if (series.length < 3) {
          byId('battBody').innerHTML = '<div class="bell-empty">Not enough recent readings to measure a trend.</div>';
          return;
        }
        // slope over the most recent ~45 minutes
        var tail = series.slice(-9);
        var hours = (tail[tail.length - 1].t - tail[0].t) / 3600000;
        var rate = hours > 0 ? (tail[tail.length - 1].y - tail[0].y) / hours : 0;
        var state = rate > 1 ? 'charging' : rate < -0.5 ? 'draining' : 'holding steady';
        var lines = [
          '<div class="batt-row"><span>Charge now</span><b>' + (battLevel != null ? Math.round(battLevel) + '%' : '—') + '</b></div>',
          '<div class="batt-row"><span>State</span><b>' + state + '</b></div>',
          '<div class="batt-row"><span>Rate</span><b>' + (rate > 0 ? '+' : '') + rate.toFixed(1) + '%/h</b></div>',
        ];
        if (state === 'charging' && battLevel != null && rate > 0) {
          lines.push('<div class="batt-row"><span>Full in</span><b>~' + Math.max(1, Math.round(((100 - battLevel) / rate) * 60)) + ' min</b></div>');
        } else if (state === 'draining' && battLevel != null && rate < 0) {
          lines.push('<div class="batt-row"><span>Empty in</span><b>~' + (battLevel / -rate).toFixed(1) + ' h</b></div>');
        }
        byId('battBody').innerHTML = lines.join('')
          + '<p class="batt-note">Rate is measured over the last 45 minutes of readings.</p>';
      })
      .catch(function () {
        byId('battBody').innerHTML = '<div class="bell-empty">Could not load battery history.</div>';
      });
  }
  if (battButton && battPop) {
    battButton.addEventListener('click', function (event) {
      event.stopPropagation();
      if (battPop.hidden) openBatt(); else closeBatt();
    });
    document.addEventListener('click', function (event) {
      if (!battPop.hidden && !battPop.contains(event.target) && !battButton.contains(event.target)) closeBatt();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeBatt();
    });
  }

  var TOAST_FRESH_MS = 15 * 60 * 1000;
  function showToast(notification) {
    var rack = byId('toastRack');
    if (!rack) return;
    var toast = document.createElement('a');
    toast.className = 'toast card ' + (notification.severity || 'info');
    toast.href = focusLink(notification);
    toast.innerHTML = '<b>' + escapeHtml(notification.title) + '</b>'
      + '<span>' + notificationTime(notification.recorded_at) + ' · tap to inspect</span>';
    rack.appendChild(toast);
    while (rack.children.length > 3) rack.removeChild(rack.firstChild);
    setTimeout(function () { toast.classList.add('leaving'); }, 6000);
    setTimeout(function () { toast.remove(); }, 6500);
  }
  function maybeToast(widget) {
    var latest = widget && widget.latest_notification;
    if (!latest || !latest.id || latest.read_at) return;
    var age = Date.now() - Date.parse(latest.recorded_at);
    if (!(age >= 0) || age > TOAST_FRESH_MS) return;
    // localStorage so a page switch doesn't replay the same alert
    var lastToasted = Number(localStorage.getItem('owletLastToastId') || 0);
    if (latest.id <= lastToasted) return;
    localStorage.setItem('owletLastToastId', String(latest.id));
    if (bellPop && !bellPop.hidden) return;   // already looking at the list
    showToast(latest);
  }

  // ---- living dot: freshness of the newest reading ----
  var pollInterval = 5;
  var lastReadingAt = null;
  var sockReporting = true;
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
    // The collector is alive but the sock itself has nothing to say
    // (off, charging, out of range) — amber, not green.
    if (!sockReporting && intervals <= 4) {
      dot.style.backgroundColor = 'rgb(245,158,11)';
      dot.title = 'Sock not reporting — it may be off or charging · click to refresh';
      return;
    }
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
    var dotClass = lastReadingAt === null ? '' : (fresh ? (sockReporting ? 'good' : 'warn') : 'offline');
    var label = lastReadingAt === null
      ? 'Waiting for first reading…'
      : (fresh
        ? (sockReporting ? 'Collecting live' : 'Collector live — sock not reporting')
        : 'No new data for ' + Math.round((Date.now() - lastReadingAt) / 1000) + 's');
    status.innerHTML = '<span class="status-dot ' + dotClass + '"></span>' + label;
  }
  function pollFreshness() {
    fetch('/api/widget?hours=1').then(function (r) { return r.json(); }).then(function (widget) {
      if (widget.updated_at) lastReadingAt = Date.parse(widget.updated_at);
      sockReporting = widget.sock_reporting !== false;
      if (typeof widget.battery === 'number') { battLevel = widget.battery; paintBattery(); }
      if (typeof widget.unread_notifications === 'number' && (bellPop == null || bellPop.hidden)) {
        unreadCount = widget.unread_notifications;
        paintBell();
      }
      maybeToast(widget);
      paintDot();
      paintStatus();
    }).catch(function () {});
  }
  loadShellAccounts();
  pollFreshness();
  setInterval(pollFreshness, 10000);
  setInterval(paintDot, 1000);

  // Warm the other tabs into the service-worker cache so the first switch
  // paints instantly too.
  setTimeout(function () {
    if (!('serviceWorker' in navigator) || !navigator.serviceWorker.controller) return;
    ['/', '/night', '/rhythms', '/data'].forEach(function (path) {
      if (window.location.pathname !== path) fetch(path, { credentials: 'same-origin' }).catch(function () {});
    });
  }, 2500);
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
      <span class="bell-wrap">
        <button id="shellBell" class="shell-bell" type="button" aria-haspopup="true"
          aria-expanded="false" title="Notifications" aria-label="Notifications">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.7 21a2 2 0 0 1-3.4 0" />
          </svg>
          <span id="shellBellCount" class="bell-badge" hidden></span>
        </button>
        <div id="bellPop" class="bell-pop card" role="menu" aria-label="Notifications" hidden>
          <div class="bp-head"><b>Notifications</b><span class="bp-meta">newest first · opening marks read</span></div>
          <div id="bellList" class="bell-list"></div>
        </div>
      </span>
      <span class="batt-wrap">
        <button id="shellBattery" class="shell-batt" type="button" aria-haspopup="true"
          aria-expanded="false" title="Battery">
          <span class="batt-shell" aria-hidden="true"><span id="shellBattFill" class="batt-fill"></span></span>
          <span id="shellBattPct" class="batt-pct">—</span>
        </button>
        <div id="battPop" class="bell-pop card" role="menu" aria-label="Battery" hidden>
          <div class="bp-head"><b>Battery</b><span class="bp-meta" id="battMeta"></span></div>
          <div id="battBody" class="batt-body"></div>
        </div>
      </span>
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
          <span class="pp-label">Baby's name</span>
          <input id="babyNameSetting" type="text" maxlength="40" placeholder="e.g. Hazel"
            autocomplete="off" />
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
  <div id="toastRack" class="toast-rack" aria-live="polite"></div>
  {SHELL_JS}
  {scripts}
</body>
</html>"""
