DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#122033" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-title" content="Owlet" />
  <link rel="manifest" href="/manifest.webmanifest" />
  <link rel="apple-touch-icon" href="/icon-192.png" />
  <title>Owlet Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.2.0/dist/chartjs-plugin-zoom.min.js"></script>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: rgba(255, 255, 255, .95);
      --text: #122033;
      --muted: #64748b;
      --line: #e2e8f0;
      --red: #dc2626;
      --blue: #2563eb;
      --green: #059669;
      --amber: #b45309;
      --purple: #7c3aed;
      --dark: #0f172a;
      --shadow: 0 18px 50px rgba(15, 23, 42, .10);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(37, 99, 235, .16), transparent 34rem),
        radial-gradient(circle at top right, rgba(168, 85, 247, .12), transparent 32rem),
        var(--bg);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .shell { width: min(1500px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 48px; }
    .hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; margin-bottom: 14px; }
    h1 { margin: 0; letter-spacing: -.045em; font-size: clamp(2.1rem, 5vw, 4.2rem); line-height: .92; }
    h2 { margin: 0; font-size: 1.03rem; letter-spacing: -.02em; }
    h3 { margin: 0 0 8px; font-size: .84rem; color: var(--muted); text-transform: uppercase; letter-spacing: .07em; }
    .subtitle { color: var(--muted); max-width: 760px; margin: 10px 0 0; font-size: 1rem; }
    .status { display: flex; align-items: center; gap: 8px; padding: .5rem .75rem; border-radius: 999px; background: #eef2ff; color: #3730a3; font-weight: 800; font-size: .85rem; white-space: nowrap; }
    .status-dot { width: 9px; height: 9px; border-radius: 50%; background: #94a3b8; display: inline-block; }
    .status-dot.good { background: #22c55e; }
    .status-dot.offline { background: #ef4444; }
    .toolbar, .panel, .card {
      background: var(--panel);
      border: 1px solid rgba(226, 232, 240, .9);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
      border-radius: 22px;
      min-width: 0;
    }
    .toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; padding: 10px; margin: 14px 0; position: sticky; top: 8px; z-index: 10; }
    .control-group { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .refresh-cluster { margin-left: auto; justify-content: flex-end; }
    .toolbar-right { position: relative; }
    .install-button { display: none; }
    .install-button.show { display: inline-flex; align-items: center; gap: 6px; }
    label { color: var(--muted); font-size: .86rem; font-weight: 800; }
    select, input, button {
      border: 1px solid var(--line); background: #fff; color: var(--text); border-radius: 12px;
      padding: .55rem .7rem; font: inherit;
    }
    button { cursor: pointer; font-weight: 800; }
    button.primary { background: var(--dark); color: #fff; border-color: var(--dark); }
    button.icon-button { width: 38px; height: 38px; padding: 0; display: inline-grid; place-items: center; border-radius: 999px; background: #f8fafc; }
    .grid { display: grid; gap: 14px; }
    .grid > * { min-width: 0; }
    .chart-stack { display: grid; gap: 14px; }
    .chart-panel { padding: 14px; }
    .chart-frame { position: relative; width: 100%; }
    .chart-frame.main { height: 455px; }
    .chart-frame.secondary { height: 240px; }
    .chart-frame canvas { display: block; width: 100% !important; height: 100% !important; }
    .chart-actions { display: flex; gap: 8px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
    .chart-hint { color: var(--muted); font-size: .8rem; }
    .update-chip { opacity: 0; transform: translateY(-2px); color: var(--green); font-size: .8rem; font-weight: 900; transition: opacity .45s ease, transform .45s ease; }
    .update-chip.show { opacity: 1; transform: translateY(0); }
    .pulse-new { animation: pulseNew .9s ease; }
    @keyframes pulseNew { 0% { background: #dcfce7; } 100% { background: transparent; } }
    .glance-strip { display: grid; grid-template-columns: 1.15fr repeat(4, minmax(150px, .75fr)); gap: 10px; margin: 10px 0 14px; }
    .glance-card { min-height: 92px; padding: 12px 13px; }
    .glance-card strong { display: block; font-size: clamp(1.45rem, 3vw, 2.25rem); line-height: 1; letter-spacing: -.045em; margin: 4px 0; }
    .glance-card small { display: block; color: var(--muted); line-height: 1.25; }
    .glance-card .inline-stat { color: var(--text); font-weight: 850; }
    .glance-progress { height: 7px; margin-top: 7px; }
    .notification-button { position: relative; }
    .notification-count { display: inline-grid; place-items: center; min-width: 20px; height: 20px; padding: 0 6px; margin-left: 4px; border-radius: 999px; background: #fef2f2; color: #b91c1c; font-size: .72rem; font-weight: 900; }
    .notifications-popover { position: absolute; right: 0; top: calc(100% + 8px); width: min(420px, calc(100vw - 28px)); background: #fff; border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: 12px; z-index: 30; }
    .notifications-popover.hidden { display: none; }
    .notification-list { display: grid; gap: 8px; max-height: 360px; overflow: auto; }
    .notification-item { border: 1px solid var(--line); border-left: 5px solid var(--amber); border-radius: 13px; padding: 9px 10px; background: #fffaf0; }
    .notification-item.critical { border-left-color: var(--red); background: #fff1f2; }
    .notification-item.info { border-left-color: var(--blue); background: #eff6ff; }
    .notification-title { font-weight: 900; }
    .notification-meta { color: var(--muted); font-size: .78rem; margin-top: 3px; line-height: 1.3; }
    .metric-grid { grid-template-columns: repeat(4, minmax(140px, 1fr)); margin-top: 14px; }
    .card, .panel { padding: 16px; }
    .hero-card { min-height: 172px; }
    .eyebrow { color: var(--muted); font-size: .77rem; font-weight: 850; text-transform: uppercase; letter-spacing: .08em; }
    .big { font-size: clamp(2.1rem, 5vw, 4.1rem); line-height: .92; font-weight: 900; letter-spacing: -.05em; margin: 9px 0; }
    .sub { color: var(--muted); font-size: .94rem; line-height: 1.35; }
    .mini-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .mini { background: #f8fafc; border: 1px solid var(--line); border-radius: 14px; padding: 9px 10px; min-width: 98px; }
    .mini b { display: block; font-size: 1.15rem; }
    .metric-value { font-size: 2.1rem; line-height: 1; font-weight: 900; letter-spacing: -.04em; margin: 8px 0 5px; }
    .trend-improving, .trend-up { color: var(--green); }
    .trend-worsening, .trend-down { color: var(--red); }
    .trend-stable, .trend-flat { color: var(--blue); }
    .trend-unknown { color: var(--muted); }
    .panel-title { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 8px; }
    .small { color: var(--muted); font-size: .86rem; }
    .insight-text { font-size: 1.08rem; font-weight: 750; line-height: 1.35; margin: 12px 0; }
    .details-grid { grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); margin-top: 14px; }
    table { width: 100%; border-collapse: collapse; font-size: .9rem; }
    th, td { padding: 10px 9px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    th { color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; background: #f8fafc; position: sticky; top: 0; z-index: 1; }
    tr:hover td { background: #f8fafc; }
    tr.offline-row td { background: #fff1f2; color: #991b1b; }
    tr.offline-row:hover td { background: #ffe4e6; }
    .table-wrap { overflow: auto; max-width: 100%; max-height: 460px; border: 1px solid var(--line); border-radius: 16px; }
    .raw-box { white-space: pre-wrap; word-break: break-word; background: var(--dark); color: #dbeafe; border-radius: 16px; padding: 14px; max-height: 280px; overflow: auto; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; }
    .empty { padding: 28px; text-align: center; color: var(--muted); border: 1px dashed #cbd5e1; border-radius: 18px; background: #f8fafc; }
    .progress { height: 10px; border-radius: 999px; overflow: hidden; background: #e2e8f0; margin-top: 12px; display: flex; }
    .progress span:nth-child(1) { background: var(--purple); }
    .progress span:nth-child(2) { background: var(--blue); }
    .progress span:nth-child(3) { background: var(--amber); }
    @media (max-width: 1080px) {
      .hero { align-items: flex-start; flex-direction: column; }
      .glance-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .glance-card:first-child { grid-column: span 2; }
      .metric-grid, .details-grid { grid-template-columns: 1fr; }
      .status { white-space: normal; }
      .toolbar { position: static; }
      .chart-frame.main { height: 360px; }
      .chart-frame.secondary { height: 230px; }
    }
    @media (max-width: 640px) {
      .shell { width: min(100% - 14px, 1500px); padding: 10px 0 24px; }
      .hero { gap: 8px; margin-bottom: 8px; }
      h1 { font-size: clamp(1.75rem, 12vw, 2.7rem); }
      .subtitle { display: none; }
      .toolbar, .panel, .card { border-radius: 16px; box-shadow: 0 10px 26px rgba(15, 23, 42, .08); }
      .toolbar { padding: 7px; gap: 7px; margin: 8px 0; }
      .control-group { gap: 6px; width: 100%; }
      .filter-cluster { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; }
      .filter-cluster select { width: 100%; }
      .refresh-cluster { width: 100%; justify-content: space-between; }
      .install-button.show { display: inline-flex; }
      label { font-size: .76rem; }
      select, button { padding: .45rem .55rem; border-radius: 10px; font-size: .86rem; }
      button.icon-button { width: 34px; height: 34px; }
      .chart-stack, .grid { gap: 8px; }
      .glance-strip { gap: 7px; margin: 8px 0; }
      .glance-card { min-height: 66px; padding: 8px 9px; }
      .glance-card:first-child { grid-column: span 1; }
      .glance-card strong { font-size: 1.35rem; margin: 2px 0; }
      .glance-card small { font-size: .75rem; }
      .chart-panel, .panel, .card { padding: 9px; }
      .panel-title { gap: 8px; margin-bottom: 5px; align-items: flex-start; }
      .panel-title { flex-wrap: wrap; }
      .details-grid .panel-title .small { flex-basis: 100%; }
      .chart-hint { display: none; }
      .chart-frame.main { height: 430px; }
      .chart-frame.secondary { height: 295px; }
      .small { font-size: .76rem; }
      .big { font-size: 2rem; }
      .mini-row { gap: 6px; }
      .mini { min-width: 0; flex: 1 1 30%; padding: 7px; }
      th, td { padding: 8px 7px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <h1>Owlet Dashboard</h1>
        <p class="subtitle">
          Live-updated pulse plus historical drill-downs for breathing, sleep, wake time,
          and raw readings. Retrospective trend viewing only — not a medical monitor or alert replacement.
        </p>
      </div>
      <div class="status" id="status"><span class="status-dot"></span>Checking collector…</div>
    </section>

    <section class="toolbar" aria-label="Date and data controls">
      <div class="control-group filter-cluster">
        <label for="window">Range</label>
        <select id="window">
          <option value="6">6 hours</option>
          <option value="12">12 hours</option>
          <option selected value="24">24 hours</option>
          <option value="72">3 days</option>
          <option value="168">7 days</option>
          <option value="720">30 days</option>
          <option value="all">All stored data</option>
        </select>
        <label for="bucket">Averages</label>
        <select id="bucket">
          <option value="5m">5 minutes</option>
          <option value="15m">15 minutes</option>
          <option value="30m">30 minutes</option>
          <option selected value="hour">1 hour</option>
          <option value="6h">6 hours</option>
          <option value="12h">12 hours</option>
          <option value="day">Daily</option>
        </select>
      </div>
      <div class="control-group refresh-cluster toolbar-right">
        <button id="notificationsToggle" class="notification-button" type="button" aria-expanded="false">Notifications <span id="notificationCount" class="notification-count">0</span></button>
        <button id="installApp" class="install-button" type="button" title="Install Owlet as an app">Install app</button>
        <span class="small" id="refreshNote">Refreshing…</span>
        <button id="refresh" class="primary">Refresh</button>
        <div id="notificationsPanel" class="notifications-popover hidden" role="dialog" aria-label="Notifications">
          <div class="panel-title">
            <h2>Notifications</h2>
            <span class="small" id="notificationPage">—</span>
          </div>
          <div id="notificationList" class="notification-list"></div>
          <div class="control-group" style="justify-content: space-between; margin-top: 10px;">
            <button id="notificationsPrev" type="button">Previous</button>
            <button id="notificationsNext" type="button">Next</button>
          </div>
        </div>
      </div>
    </section>

    <section class="glance-strip" aria-label="At a glance">
      <article class="card glance-card">
        <span class="eyebrow">O₂ now</span>
        <strong id="latestOxygen">—</strong>
        <small id="latestSummary">Waiting for latest reading…</small>
      </article>
      <article class="card glance-card">
        <span class="eyebrow">O₂ today</span>
        <strong id="todayOxygen">—</strong>
        <small>Recent <span class="inline-stat" id="recentOxygen">—</span> · Prior <span class="inline-stat" id="priorOxygen">—</span> · Low <span class="inline-stat" id="lowOxygen">—</span></small>
      </article>
      <article class="card glance-card">
        <span class="eyebrow">Heart rate</span>
        <strong id="latestHr">—</strong>
        <small>State <span class="inline-stat" id="latestState">—</span> · Move <span class="inline-stat" id="latestMove">—</span></small>
      </article>
      <article class="card glance-card">
        <span class="eyebrow">Trend</span>
        <strong id="breathingDirection">—</strong>
        <small id="breathingSentence">Not enough data yet.</small>
      </article>
      <article class="card glance-card">
        <span class="eyebrow">Sleep</span>
        <strong id="sleepTotal">—</strong>
        <small id="sleepSummary">Estimated from intervals.</small>
        <div class="progress glance-progress" title="Light sleep / deep sleep / awake">
          <span id="lightBar"></span><span id="deepBar"></span><span id="awakeBar"></span>
        </div>
        <small>Light <span class="inline-stat" id="lightSleep">—</span> · Deep <span class="inline-stat" id="deepSleep">—</span> · Awake <span class="inline-stat" id="awakeTime">—</span></small>
      </article>
    </section>

    <section class="chart-stack" aria-label="Primary charts">
      <div class="panel chart-panel primary-chart">
        <div class="panel-title">
          <div>
            <h2>Main vitals trace</h2>
            <span class="chart-hint">Drag across any chart to zoom. Double-click to reset.</span>
          </div>
          <div class="chart-actions">
            <span class="update-chip" id="updateChip">New data</span>
            <span class="small" id="coverage">—</span>
            <button id="resetZoom" type="button">Reset zoom</button>
            <button id="download" class="icon-button" title="Download CSV" aria-label="Download CSV">CSV</button>
          </div>
        </div>
        <div class="chart-frame main"><canvas id="vitalsChart"></canvas></div>
      </div>
      <div class="panel chart-panel secondary-chart">
        <div class="panel-title">
          <h2 id="rollupLabel">Hourly averages</h2>
          <span class="small">Avg O₂, min O₂, and avg heart rate</span>
        </div>
        <div class="chart-frame secondary"><canvas id="rollupChart"></canvas></div>
      </div>
      <div class="panel chart-panel secondary-chart">
        <div class="panel-title">
          <h2>Sleep / wake by period</h2>
          <span class="small">light sleep, deep sleep, awake estimates</span>
        </div>
        <div class="chart-frame secondary"><canvas id="stateChart"></canvas></div>
      </div>
    </section>

    <section class="grid metric-grid" id="metricCards"></section>

    <section class="grid details-grid">
      <div class="panel">
        <div class="panel-title">
          <h2>Drill-down table</h2>
          <span class="small">averages + sleep/awake estimates</span>
        </div>
        <div class="table-wrap"><table id="rollupTable"></table></div>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>Selected reading</h2>
          <span class="small">click a reading row</span>
        </div>
        <pre id="raw" class="raw-box">No reading selected yet.</pre>
      </div>
    </section>

    <section class="panel" style="margin-top: 14px;">
      <div class="panel-title">
        <h2>Readings table</h2>
        <span class="small" id="tableCount">—</span>
      </div>
      <div class="table-wrap"><table id="readingsTable"></table></div>
    </section>
  </main>

  <script>
    const API_BASE = "__API_BASE__";
    const SHARE_MODE = __SHARE_MODE__;
    const REFRESH_SECONDS = 15;
    let readings = [];
    let filtered = [];
    let summary = null;
    let insights = null;
    let rollups = [];
    let notifications = { items: [], total: 0, limit: 500, offset: 0 };
    let notificationPageOffset = 0;
    const NOTIFICATION_PAGE_SIZE = 10;
    let vitalsChart = null;
    let stateChart = null;
    let rollupChart = null;
    let secondsUntilRefresh = REFRESH_SECONDS;
    let syncInProgress = false;
    let zoomWindow = null;
    let lastLatestTimestamp = null;
    let deferredInstallPrompt = null;

    const offlineBandsPlugin = {
      id: 'offlineBands',
      beforeDatasetsDraw(chart, _args, options) {
        const intervals = options?.intervals || [];
        if (!intervals.length || !chart.scales?.x) return;
        const { ctx, chartArea, scales } = chart;
        ctx.save();
        ctx.fillStyle = 'rgba(239, 68, 68, 0.12)';
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.28)';
        intervals.forEach(({ start, end }) => {
          const left = Math.max(chartArea.left, scales.x.getPixelForValue(start));
          const right = Math.min(chartArea.right, scales.x.getPixelForValue(end));
          if (!Number.isFinite(left) || !Number.isFinite(right) || right <= chartArea.left || left >= chartArea.right) return;
          const width = Math.max(2, right - left);
          ctx.fillRect(left, chartArea.top, width, chartArea.bottom - chartArea.top);
          ctx.strokeRect(left, chartArea.top, width, chartArea.bottom - chartArea.top);
        });
        ctx.restore();
      }
    };
    const notificationGlyphsPlugin = {
      id: 'notificationGlyphs',
      afterDatasetsDraw(chart) {
        const index = chart.data.datasets.findIndex(dataset => dataset.id === 'notifications');
        if (index < 0) return;
        const meta = chart.getDatasetMeta(index);
        const dataset = chart.data.datasets[index];
        const { ctx } = chart;
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = 'bold 12px system-ui, sans-serif';
        meta.data.forEach((point, i) => {
          const raw = dataset.data[i];
          if (!raw) return;
          ctx.fillStyle = raw.severity === 'critical' ? '#991b1b' : '#92400e';
          ctx.fillText('!', point.x, point.y + 1);
        });
        ctx.restore();
      }
    };
    Chart.register(offlineBandsPlugin, notificationGlyphsPlugin);

    const el = (id) => document.getElementById(id);
    const fmt = (value, suffix = '') => value === null || value === undefined ? '—' : `${value}${suffix}`;
    const num = (value, digits = 1) => value === null || value === undefined ? '—' : Number(value).toFixed(digits).replace(/\.0$/, '');
    const hours = (seconds) => seconds ? `${(seconds / 3600).toFixed(1).replace(/\.0$/, '')}h` : '0h';
    const trendClass = (trend) => `trend-${trend || 'unknown'}`;
    const stateLabel = (value) => ({ '0': 'inactive', '1': 'awake', '8': 'light sleep', '15': 'deep sleep' }[String(value)] || `state ${value ?? 'unknown'}`);
    const zeroOrNegative = (value) => value !== null && value !== undefined && Number(value) <= 0;
    const isOffline = (row) => zeroOrNegative(row?.heart_rate) || zeroOrNegative(row?.oxygen_saturation);
    const chartList = () => [vitalsChart, rollupChart, stateChart].filter(Boolean);

    function selectedHours() {
      const value = el('window').value;
      return value === 'all' ? null : Number(value);
    }

    function localTime(iso, compact = false) {
      if (!iso) return '—';
      const date = new Date(iso);
      if (compact) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      return date.toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' });
    }

    function average(values) {
      const clean = values.filter(value => value !== null && value !== undefined && Number.isFinite(Number(value))).map(Number);
      if (!clean.length) return null;
      return clean.reduce((sum, value) => sum + value, 0) / clean.length;
    }

    function todayAverageOxygen() {
      const latest = readings[readings.length - 1];
      if (!latest) return null;
      const latestDate = new Date(latest.recorded_at);
      const sameLocalDay = readings.filter(row => {
        const date = new Date(row.recorded_at);
        return !isOffline(row) && date.toDateString() === latestDate.toDateString();
      });
      return average(sameLocalDay.map(row => row.oxygen_saturation));
    }

    function timeTick(value) {
      const date = new Date(value);
      const hours = selectedHours();
      if (hours && hours <= 24) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      return date.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric' });
    }

    function rollupLabel(row) {
      const date = new Date(row.bucket_start);
      const bucket = row.bucket;
      if (bucket === 'day') return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
      if (selectedHours() && selectedHours() <= 24) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      return date.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    }

    function queryParams(extra = {}) {
      const window = el('window').value;
      const params = new URLSearchParams({ limit: '100000', ...extra });
      if (window !== 'all') params.set('hours', window);
      return params.toString();
    }

    async function fetchJson(url) {
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText} while fetching ${url}`);
      return response.json();
    }

    async function refresh({ resetZoom = false } = {}) {
      secondsUntilRefresh = REFRESH_SECONDS;
      const previousLatest = lastLatestTimestamp;
      const qs = queryParams();
      const rollupQs = queryParams({ bucket: el('bucket').value });
      const notificationQs = queryParams({ limit: '500', offset: '0' });
      const [health, rows, stats, insightData, rollupData, notificationData] = await Promise.all([
        fetchJson(`${API_BASE}/api/health`),
        fetchJson(`${API_BASE}/api/readings?${qs}`),
        fetchJson(`${API_BASE}/api/summary?${qs}`),
        fetchJson(`${API_BASE}/api/insights?${qs}`),
        fetchJson(`${API_BASE}/api/rollups?${rollupQs}`),
        fetchJson(`${API_BASE}/api/notifications?${notificationQs}`)
      ]);
      readings = rows;
      summary = stats;
      insights = insightData;
      rollups = rollupData.rollups || [];
      notifications = notificationData;
      lastLatestTimestamp = readings.length ? readings[readings.length - 1].recorded_at : null;
      if (resetZoom) zoomWindow = null;
      renderStatus(health);
      renderInsights();
      applyFilter();
      renderMetricCards();
      renderCharts();
      renderRollups();
      renderNotifications();
      if (previousLatest && lastLatestTimestamp && lastLatestTimestamp !== previousLatest) showNewDataPulse();
    }

    function renderStatus(health) {
      const mode = SHARE_MODE ? 'Shared read-only view' : health.database_path;
      const latest = readings[readings.length - 1];
      const offlineNow = latest && isOffline(latest);
      const label = offlineNow ? 'Device offline / sock off' : (health.collecting ? 'Collecting live' : 'Stored data only');
      const dotClass = offlineNow ? 'offline' : (health.collecting ? 'good' : '');
      el('status').innerHTML = `<span class="status-dot ${dotClass}"></span>${label} · ${mode}`;
    }

    function renderInsights() {
      const latest = insights.latest;
      el('latestOxygen').textContent = latest ? fmt(latest.oxygen_saturation, '% O₂') : '—';
      const todayO2 = todayAverageOxygen();
      el('todayOxygen').textContent = todayO2 === null ? '—' : `${todayO2.toFixed(1).replace(/\.0$/, '')}%`;
      el('latestHr').textContent = latest ? fmt(latest.heart_rate, ' bpm') : '—';
      el('latestState').textContent = latest ? latest.sleep_state_label : '—';
      el('latestMove').textContent = latest ? num(latest.movement) : '—';
      el('latestSummary').textContent = latest ? `Latest reading ${localTime(latest.recorded_at)} · battery ${fmt(latest.battery, '%')}` : 'Waiting for latest reading…';

      const breathing = insights.breathing;
      el('breathingDirection').textContent = breathing.direction;
      el('breathingDirection').className = `big ${trendClass(breathing.direction)}`;
      el('breathingSentence').textContent = breathing.plain_language;
      el('recentOxygen').textContent = fmt(breathing.recent_avg_oxygen, '%');
      el('priorOxygen').textContent = fmt(breathing.previous_avg_oxygen, '%');
      el('lowOxygen').textContent = breathing.low_oxygen_samples;

      const sleep = insights.sleep;
      el('sleepTotal').textContent = hours(sleep.sleep_seconds);
      el('sleepSummary').textContent = `${hours(sleep.awake_seconds)} awake · current state: ${sleep.sleep_state_label}`;
      el('lightSleep').textContent = hours(sleep.light_sleep_seconds);
      el('deepSleep').textContent = hours(sleep.deep_sleep_seconds);
      el('awakeTime').textContent = hours(sleep.awake_seconds);
      const total = Math.max(1, sleep.light_sleep_seconds + sleep.deep_sleep_seconds + sleep.awake_seconds);
      el('lightBar').style.width = `${(sleep.light_sleep_seconds / total) * 100}%`;
      el('deepBar').style.width = `${(sleep.deep_sleep_seconds / total) * 100}%`;
      el('awakeBar').style.width = `${(sleep.awake_seconds / total) * 100}%`;
    }

    function renderMetricCards() {
      const cards = [
        ['Avg oxygen', fmt(summary.oxygen_saturation.avg, '%'), `min ${fmt(summary.oxygen_saturation.min, '%')} · ${summary.oxygen_saturation.trend}`, summary.oxygen_saturation.trend],
        ['Avg heart rate', fmt(summary.heart_rate.avg, ' bpm'), `latest ${fmt(summary.heart_rate.latest, ' bpm')}`, summary.heart_rate.trend],
        ['Avg movement', num(summary.movement.avg), `latest ${num(summary.movement.latest)} · ${summary.movement.trend}`, summary.movement.trend],
        ['Coverage', `${summary.valid_count ?? summary.count}/${summary.count}`, `${summary.offline_count || 0} offline/zero readings · ${localTime(summary.first_recorded_at)} → ${localTime(summary.last_recorded_at)}`, summary.offline_count ? 'down' : 'unknown'],
      ];
      el('metricCards').innerHTML = cards.map(([label, value, foot, trend]) => `
        <article class="card">
          <div class="eyebrow">${label}</div>
          <div class="metric-value ${trendClass(trend)}">${value}</div>
          <div class="sub">${foot}</div>
        </article>`).join('');
      el('coverage').textContent = `${summary.window} · ${summary.count} readings`;
    }

    function downsample(rows, maxPoints = 1200) {
      if (rows.length <= maxPoints) return rows;
      const step = Math.ceil(rows.length / maxPoints);
      return rows.filter((_, index) => index % step === 0 || index === rows.length - 1 || isOffline(rows[index]));
    }

    function offlineIntervals() {
      const intervals = [];
      let activeStart = null;
      readings.forEach((row, index) => {
        const current = Date.parse(row.recorded_at);
        const next = readings[index + 1] ? Date.parse(readings[index + 1].recorded_at) : current + 60 * 1000;
        if (isOffline(row)) {
          if (activeStart === null) activeStart = current;
        } else if (activeStart !== null) {
          intervals.push({ start: activeStart, end: current });
          activeStart = null;
        }
        if (isOffline(row) && index === readings.length - 1) {
          intervals.push({ start: activeStart, end: Math.max(next, current + 60 * 1000) });
          activeStart = null;
        }
      });
      return intervals;
    }

    function nearestReadingIndex(timestamp) {
      let bestIndex = -1;
      let bestDelta = Infinity;
      readings.forEach((row, index) => {
        const delta = Math.abs(Date.parse(row.recorded_at) - timestamp);
        if (delta < bestDelta) {
          bestDelta = delta;
          bestIndex = index;
        }
      });
      return bestIndex;
    }

    function surroundingDataLines(timestamp) {
      const index = nearestReadingIndex(timestamp);
      if (index < 0) return [];
      return readings.slice(Math.max(0, index - 1), Math.min(readings.length, index + 2)).map(row => `${localTime(row.recorded_at, true)} · O₂ ${fmt(row.oxygen_saturation, '%')} · HR ${fmt(row.heart_rate, ' bpm')}`);
    }

    function notificationPoints() {
      return (notifications.items || []).slice().reverse().map(item => {
        const timestamp = Date.parse(item.recorded_at);
        const y = item.oxygen_saturation && item.oxygen_saturation > 0 ? item.oxygen_saturation : 89;
        return {
          x: timestamp,
          y,
          severity: item.severity,
          tooltipLines: [
            `${item.title} · ${localTime(item.recorded_at)}`,
            item.message,
            `O₂ ${fmt(item.oxygen_saturation, '%')} · HR ${fmt(item.heart_rate, ' bpm')} · battery ${fmt(item.battery, '%')}`,
            ...surroundingDataLines(timestamp)
          ]
        };
      });
    }

    function tooltipLabel(context) {
      if (context.dataset.id === 'notifications') return context.raw.tooltipLines;
      const value = context.parsed.y;
      return `${context.dataset.label}: ${value === null || value === undefined ? '—' : value}`;
    }

    function legendOptions() {
      const mobile = window.matchMedia('(max-width: 640px)').matches;
      return {
        position: mobile ? 'chartArea' : 'bottom',
        align: 'start',
        labels: { boxWidth: mobile ? 8 : 12, boxHeight: mobile ? 8 : 12, padding: mobile ? 6 : 12, usePointStyle: true, font: { size: mobile ? 10 : 12 } }
      };
    }

    function xScaleOptions() {
      return {
        type: 'linear',
        min: zoomWindow?.min,
        max: zoomWindow?.max,
        ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: window.matchMedia('(max-width: 640px)').matches ? 6 : 14, callback: timeTick }
      };
    }

    function zoomOptions() {
      return {
        limits: { x: { min: 'original', max: 'original' } },
        pan: { enabled: true, mode: 'x' },
        zoom: {
          drag: { enabled: true, backgroundColor: 'rgba(37, 99, 235, .12)', borderColor: 'rgba(37, 99, 235, .55)', borderWidth: 1 },
          mode: 'x',
          onZoomComplete: ({ chart }) => syncZoomFrom(chart)
        }
      };
    }

    function chartOptions(extraScales) {
      const mobile = window.matchMedia('(max-width: 640px)').matches;
      const scales = { x: xScaleOptions(), ...extraScales };
      if (mobile) {
        Object.entries(scales).forEach(([key, scale]) => {
          if (key !== 'x' && scale.title) scale.title.display = false;
          scale.ticks = { ...(scale.ticks || {}), font: { size: 10 }, padding: 2, maxTicksLimit: 6 };
        });
      }
      return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 450 },
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: legendOptions(), tooltip: { callbacks: { label: tooltipLabel } }, zoom: zoomOptions(), offlineBands: { intervals: offlineIntervals() } },
        scales
      };
    }

    function syncZoomFrom(sourceChart) {
      if (syncInProgress) return;
      const scale = sourceChart.scales.x;
      if (!Number.isFinite(scale.min) || !Number.isFinite(scale.max)) return;
      zoomWindow = { min: scale.min, max: scale.max };
      syncInProgress = true;
      chartList().forEach(chart => {
        if (chart === sourceChart) return;
        chart.options.scales.x.min = zoomWindow.min;
        chart.options.scales.x.max = zoomWindow.max;
        chart.update('none');
      });
      syncInProgress = false;
    }

    function resetZoom() {
      zoomWindow = null;
      chartList().forEach(chart => {
        if (typeof chart.resetZoom === 'function') chart.resetZoom('none');
        chart.options.scales.x.min = undefined;
        chart.options.scales.x.max = undefined;
        chart.update('none');
      });
    }

    function upsertChart(existing, canvasId, config) {
      if (!existing) return new Chart(el(canvasId), config);
      existing.data = config.data;
      existing.options.plugins = config.options.plugins;
      existing.options.scales = config.options.scales;
      existing.update();
      return existing;
    }

    function renderCharts() {
      const sampled = downsample(readings);
      const dataPoint = (row, key) => ({ x: Date.parse(row.recorded_at), y: row[key] });
      vitalsChart = upsertChart(vitalsChart, 'vitalsChart', {
        type: 'line',
        data: {
          datasets: [
            { label: 'Heart rate', data: sampled.map(r => dataPoint(r, 'heart_rate')), borderColor: '#dc2626', backgroundColor: '#dc262620', yAxisID: 'hr', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'SpO₂', data: sampled.map(r => dataPoint(r, 'oxygen_saturation')), borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'spo2', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'Movement', data: sampled.map(r => dataPoint(r, 'movement')), borderColor: '#059669', backgroundColor: '#05966920', yAxisID: 'move', spanGaps: true, pointRadius: 0, tension: .2 },
            { id: 'notifications', type: 'scatter', label: 'Notifications', data: notificationPoints(), yAxisID: 'spo2', pointStyle: 'triangle', pointRadius: 8, pointHoverRadius: 11, showLine: false, borderWidth: 2, borderColor: '#92400e', backgroundColor: '#f59e0b' }
          ]
        },
        options: chartOptions({
          hr: { type: 'linear', position: 'left', title: { display: true, text: 'BPM' } },
          spo2: { type: 'linear', position: 'right', suggestedMin: 88, suggestedMax: 100, grid: { drawOnChartArea: false }, title: { display: true, text: 'SpO₂' } },
          move: { display: false }
        })
      });
    }

    function renderRollups() {
      el('rollupLabel').textContent = `${el('bucket').selectedOptions[0].textContent} averages`;
      const labels = rollups.map(rollupLabel);
      const rollupPoint = (row, key) => ({ x: Date.parse(row.bucket_start), y: row[key] });
      rollupChart = upsertChart(rollupChart, 'rollupChart', {
        type: 'line',
        data: {
          datasets: [
            { label: 'Avg O₂', data: rollups.map(r => rollupPoint(r, 'avg_oxygen_saturation')), borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'oxygen', tension: .25, pointRadius: 2 },
            { label: 'Min O₂', data: rollups.map(r => rollupPoint(r, 'min_oxygen_saturation')), borderColor: '#7c3aed', backgroundColor: '#7c3aed20', yAxisID: 'oxygen', tension: .25, pointRadius: 2 },
            { label: 'Avg HR', data: rollups.map(r => rollupPoint(r, 'avg_heart_rate')), borderColor: '#dc2626', backgroundColor: '#dc262620', yAxisID: 'hr', tension: .25, pointRadius: 2 }
          ]
        },
        options: chartOptions({
          oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100, title: { display: true, text: 'O₂' } },
          hr: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'BPM' } }
        })
      });

      stateChart = upsertChart(stateChart, 'stateChart', {
        type: 'bar',
        data: {
          datasets: [
            { label: 'Light sleep', data: rollups.map(r => ({ x: Date.parse(r.bucket_start), y: r.light_sleep_seconds / 3600 })), backgroundColor: '#7c3aed80', stack: 'sleep' },
            { label: 'Deep sleep', data: rollups.map(r => ({ x: Date.parse(r.bucket_start), y: r.deep_sleep_seconds / 3600 })), backgroundColor: '#2563eb80', stack: 'sleep' },
            { label: 'Awake', data: rollups.map(r => ({ x: Date.parse(r.bucket_start), y: r.awake_seconds / 3600 })), backgroundColor: '#b4530980', stack: 'sleep' }
          ]
        },
        options: chartOptions({
          y: { stacked: true, title: { display: true, text: 'Hours' } }
        })
      });
      stateChart.options.scales.x.stacked = true;
      stateChart.update('none');

      const rows = rollups.slice().reverse().map((row, index) => `<tr class="${index === 0 ? 'newest-rollup' : ''}"><td>${rollupLabel(row)}</td><td>${row.samples}/${row.total_samples ?? row.samples}</td><td>${fmt(row.avg_oxygen_saturation, '%')}</td><td>${fmt(row.min_oxygen_saturation, '%')}</td><td>${fmt(row.avg_heart_rate, ' bpm')}</td><td>${hours(row.sleep_seconds)}</td><td>${hours(row.awake_seconds)}</td><td>${row.offline_samples || 0}</td></tr>`).join('');
      el('rollupTable').innerHTML = `<thead><tr><th>Window</th><th>Valid/total</th><th>Avg O₂</th><th>Min O₂</th><th>Avg HR</th><th>Sleep</th><th>Awake</th><th>Offline</th></tr></thead><tbody>${rows || '<tr><td colspan="8" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function applyFilter() {
      filtered = readings;
      renderReadingsTable();
    }

    function renderReadingsTable() {
      const rows = filtered.slice().reverse().map((row, index) => `
        <tr data-index="${readings.indexOf(row)}" class="${index === 0 ? 'latest-row' : ''} ${isOffline(row) ? 'offline-row' : ''}">
          <td>${localTime(row.recorded_at)}</td>
          <td>${fmt(row.device_serial)}</td>
          <td>${num(row.heart_rate)}</td>
          <td>${num(row.oxygen_saturation)}%</td>
          <td>${num(row.movement)}</td>
          <td>${isOffline(row) ? 'offline / sock off' : stateLabel(row.sleep_state)}</td>
          <td>${fmt(row.battery, '%')}</td>
          <td>${num(row.skin_temperature)}</td>
        </tr>`).join('');
      el('tableCount').textContent = `${filtered.length} loaded`;
      el('readingsTable').innerHTML = `<thead><tr><th>Time</th><th>Serial</th><th>HR</th><th>O₂</th><th>Move</th><th>State</th><th>Battery</th><th>Temp</th></tr></thead><tbody>${rows || '<tr><td colspan="8" class="empty">No readings yet.</td></tr>'}</tbody>`;
      [...el('readingsTable').querySelectorAll('tbody tr[data-index]')].forEach(tr => {
        tr.addEventListener('click', () => {
          const row = readings[Number(tr.dataset.index)];
          el('raw').textContent = JSON.stringify(row, null, 2);
        });
      });
    }

    function renderNotifications() {
      const items = notifications.items || [];
      const total = notifications.total ?? items.length;
      notificationPageOffset = Math.min(notificationPageOffset, Math.max(0, items.length - NOTIFICATION_PAGE_SIZE));
      const pageItems = items.slice(notificationPageOffset, notificationPageOffset + NOTIFICATION_PAGE_SIZE);
      el('notificationCount').textContent = total;
      el('notificationPage').textContent = total ? `${notificationPageOffset + 1}-${Math.min(notificationPageOffset + NOTIFICATION_PAGE_SIZE, items.length)} of ${total}` : 'none';
      el('notificationsPrev').disabled = notificationPageOffset === 0;
      el('notificationsNext').disabled = notificationPageOffset + NOTIFICATION_PAGE_SIZE >= items.length;
      el('notificationList').innerHTML = pageItems.map(item => `
        <article class="notification-item ${item.severity}">
          <div class="notification-title">⚠ ${item.title}</div>
          <div>${item.message}</div>
          <div class="notification-meta">${localTime(item.recorded_at)} · O₂ ${fmt(item.oxygen_saturation, '%')} · HR ${fmt(item.heart_rate, ' bpm')} · battery ${fmt(item.battery, '%')}</div>
        </article>`).join('') || '<div class="empty">No Owlet notifications in this window.</div>';
    }

    function downloadCsv() {
      const columns = ['recorded_at', 'device_serial', 'heart_rate', 'oxygen_saturation', 'movement', 'sleep_state', 'battery', 'skin_temperature'];
      const lines = [columns.join(',')].concat(filtered.map(row => columns.map(col => JSON.stringify(row[col] ?? '')).join(',')));
      const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `owlet-readings-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }

    function showNewDataPulse() {
      const chip = el('updateChip');
      chip.classList.add('show');
      document.querySelectorAll('.latest-row, .newest-rollup').forEach(node => {
        node.classList.remove('pulse-new');
        void node.offsetWidth;
        node.classList.add('pulse-new');
      });
      setTimeout(() => chip.classList.remove('show'), 1800);
    }

    function tickCountdown() {
      secondsUntilRefresh = Math.max(0, secondsUntilRefresh - 1);
      el('refreshNote').textContent = `Auto-refresh in ${secondsUntilRefresh}s`;
      if (secondsUntilRefresh === 0) refresh();
    }

    function updateInstallButton() {
      const button = el('installApp');
      if (SHARE_MODE || window.matchMedia('(display-mode: standalone)').matches) {
        button.classList.remove('show');
        return;
      }
      button.classList.add('show');
      button.textContent = deferredInstallPrompt ? 'Install app' : 'Install help';
    }

    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      deferredInstallPrompt = event;
      updateInstallButton();
    });

    window.addEventListener('appinstalled', () => {
      deferredInstallPrompt = null;
      el('installApp').classList.remove('show');
    });

    el('installApp').addEventListener('click', async () => {
      if (deferredInstallPrompt) {
        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice.catch(() => null);
        deferredInstallPrompt = null;
        updateInstallButton();
        return;
      }
      alert('Chrome may hide the install shortcut after the app is already installed, before the page finishes loading, or behind Cloudflare Access until you are logged in. Use Chrome menu → Cast, save, and share → Install page as app.');
    });

    el('window').addEventListener('change', () => { notificationPageOffset = 0; refresh({ resetZoom: true }); });
    el('bucket').addEventListener('change', () => refresh({ resetZoom: true }));
    el('refresh').addEventListener('click', () => refresh());
    el('download').addEventListener('click', downloadCsv);
    el('resetZoom').addEventListener('click', resetZoom);
    el('notificationsToggle').addEventListener('click', () => {
      const panel = el('notificationsPanel');
      const hidden = panel.classList.toggle('hidden');
      el('notificationsToggle').setAttribute('aria-expanded', String(!hidden));
    });
    el('notificationsPrev').addEventListener('click', () => { notificationPageOffset = Math.max(0, notificationPageOffset - NOTIFICATION_PAGE_SIZE); renderNotifications(); });
    el('notificationsNext').addEventListener('click', () => { notificationPageOffset += NOTIFICATION_PAGE_SIZE; renderNotifications(); });
    ['vitalsChart', 'rollupChart', 'stateChart'].forEach(id => {
      el(id).addEventListener('dblclick', resetZoom);
    });
    window.addEventListener('resize', () => chartList().forEach(chart => { chart.options.plugins.legend = legendOptions(); chart.update('none'); }));
    if ('serviceWorker' in navigator && !SHARE_MODE) {
      window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').then(updateInstallButton).catch(updateInstallButton));
    }
    updateInstallButton();
    refresh({ resetZoom: true });
    setInterval(tickCountdown, 1000);
  </script>
</body>
</html>
"""


def render_dashboard(api_base: str = "", *, share_mode: bool = False) -> str:
    return (
        DASHBOARD_HTML.replace("__API_BASE__", api_base)
        .replace("__SHARE_MODE__", "true" if share_mode else "false")
    )
