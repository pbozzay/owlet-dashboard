DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
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
    .insight-grid { grid-template-columns: 1.1fr 1fr 1fr; margin-top: 14px; }
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
    .table-wrap { overflow: auto; max-width: 100%; max-height: 460px; border: 1px solid var(--line); border-radius: 16px; }
    .raw-box { white-space: pre-wrap; word-break: break-word; background: var(--dark); color: #dbeafe; border-radius: 16px; padding: 14px; max-height: 280px; overflow: auto; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; }
    .empty { padding: 28px; text-align: center; color: var(--muted); border: 1px dashed #cbd5e1; border-radius: 18px; background: #f8fafc; }
    .progress { height: 10px; border-radius: 999px; overflow: hidden; background: #e2e8f0; margin-top: 12px; display: flex; }
    .progress span:nth-child(1) { background: var(--purple); }
    .progress span:nth-child(2) { background: var(--blue); }
    .progress span:nth-child(3) { background: var(--amber); }
    @media (max-width: 1080px) {
      .hero { align-items: flex-start; flex-direction: column; }
      .insight-grid, .metric-grid, .details-grid { grid-template-columns: 1fr; }
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
      label { font-size: .76rem; }
      select, button { padding: .45rem .55rem; border-radius: 10px; font-size: .86rem; }
      button.icon-button { width: 34px; height: 34px; }
      .chart-stack, .grid { gap: 8px; }
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
      <div class="control-group refresh-cluster">
        <span class="small" id="refreshNote">Refreshing…</span>
        <button id="refresh" class="primary">Refresh</button>
      </div>
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

    <section class="grid insight-grid">
      <article class="card hero-card">
        <h3>Today at a glance</h3>
        <div class="big" id="latestOxygen">—</div>
        <div class="sub" id="latestSummary">Waiting for latest reading…</div>
        <div class="mini-row">
          <div class="mini"><span class="eyebrow">Heart</span><b id="latestHr">—</b></div>
          <div class="mini"><span class="eyebrow">State</span><b id="latestState">—</b></div>
          <div class="mini"><span class="eyebrow">Move</span><b id="latestMove">—</b></div>
        </div>
      </article>
      <article class="card hero-card">
        <h3>Breathing trend</h3>
        <div class="big" id="breathingDirection">—</div>
        <div class="insight-text" id="breathingSentence">Not enough data yet.</div>
        <div class="mini-row">
          <div class="mini"><span class="eyebrow">Recent avg O₂</span><b id="recentOxygen">—</b></div>
          <div class="mini"><span class="eyebrow">Prior avg O₂</span><b id="priorOxygen">—</b></div>
          <div class="mini"><span class="eyebrow">Low O₂ samples</span><b id="lowOxygen">—</b></div>
        </div>
      </article>
      <article class="card hero-card">
        <h3>Sleep / awake estimate</h3>
        <div class="big" id="sleepTotal">—</div>
        <div class="sub" id="sleepSummary">Estimated from reading intervals in this window.</div>
        <div class="progress" title="Light sleep / deep sleep / awake">
          <span id="lightBar"></span><span id="deepBar"></span><span id="awakeBar"></span>
        </div>
        <div class="mini-row">
          <div class="mini"><span class="eyebrow">Light</span><b id="lightSleep">—</b></div>
          <div class="mini"><span class="eyebrow">Deep</span><b id="deepSleep">—</b></div>
          <div class="mini"><span class="eyebrow">Awake</span><b id="awakeTime">—</b></div>
        </div>
      </article>
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
    let vitalsChart = null;
    let stateChart = null;
    let rollupChart = null;
    let secondsUntilRefresh = REFRESH_SECONDS;
    let syncInProgress = false;
    let zoomWindow = null;
    let lastLatestTimestamp = null;

    const el = (id) => document.getElementById(id);
    const fmt = (value, suffix = '') => value === null || value === undefined ? '—' : `${value}${suffix}`;
    const num = (value, digits = 1) => value === null || value === undefined ? '—' : Number(value).toFixed(digits).replace(/\.0$/, '');
    const hours = (seconds) => seconds ? `${(seconds / 3600).toFixed(1).replace(/\.0$/, '')}h` : '0h';
    const trendClass = (trend) => `trend-${trend || 'unknown'}`;
    const stateLabel = (value) => ({ '0': 'inactive', '1': 'awake', '8': 'light sleep', '15': 'deep sleep' }[String(value)] || `state ${value ?? 'unknown'}`);
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
      const [health, rows, stats, insightData, rollupData] = await Promise.all([
        fetchJson(`${API_BASE}/api/health`),
        fetchJson(`${API_BASE}/api/readings?${qs}`),
        fetchJson(`${API_BASE}/api/summary?${qs}`),
        fetchJson(`${API_BASE}/api/insights?${qs}`),
        fetchJson(`${API_BASE}/api/rollups?${rollupQs}`)
      ]);
      readings = rows;
      summary = stats;
      insights = insightData;
      rollups = rollupData.rollups || [];
      lastLatestTimestamp = readings.length ? readings[readings.length - 1].recorded_at : null;
      if (resetZoom) zoomWindow = null;
      renderStatus(health);
      renderInsights();
      applyFilter();
      renderMetricCards();
      renderCharts();
      renderRollups();
      if (previousLatest && lastLatestTimestamp && lastLatestTimestamp !== previousLatest) showNewDataPulse();
    }

    function renderStatus(health) {
      const mode = SHARE_MODE ? 'Shared read-only view' : health.database_path;
      el('status').innerHTML = `<span class="status-dot ${health.collecting ? 'good' : ''}"></span>${health.collecting ? 'Collecting live' : 'Stored data only'} · ${mode}`;
    }

    function renderInsights() {
      const latest = insights.latest;
      el('latestOxygen').textContent = latest ? fmt(latest.oxygen_saturation, '% O₂') : '—';
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
        ['Coverage', summary.count, `${localTime(summary.first_recorded_at)} → ${localTime(summary.last_recorded_at)}`, 'unknown'],
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
      return rows.filter((_, index) => index % step === 0 || index === rows.length - 1);
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
        plugins: { legend: legendOptions(), zoom: zoomOptions() },
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
      existing.options.plugins.legend = legendOptions();
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
            { label: 'Movement', data: sampled.map(r => dataPoint(r, 'movement')), borderColor: '#059669', backgroundColor: '#05966920', yAxisID: 'move', spanGaps: true, pointRadius: 0, tension: .2 }
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

      const rows = rollups.slice().reverse().map((row, index) => `<tr class="${index === 0 ? 'newest-rollup' : ''}"><td>${rollupLabel(row)}</td><td>${row.samples}</td><td>${fmt(row.avg_oxygen_saturation, '%')}</td><td>${fmt(row.min_oxygen_saturation, '%')}</td><td>${fmt(row.avg_heart_rate, ' bpm')}</td><td>${hours(row.sleep_seconds)}</td><td>${hours(row.awake_seconds)}</td></tr>`).join('');
      el('rollupTable').innerHTML = `<thead><tr><th>Window</th><th>Samples</th><th>Avg O₂</th><th>Min O₂</th><th>Avg HR</th><th>Sleep</th><th>Awake</th></tr></thead><tbody>${rows || '<tr><td colspan="7" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function applyFilter() {
      filtered = readings;
      renderReadingsTable();
    }

    function renderReadingsTable() {
      const rows = filtered.slice().reverse().map((row, index) => `
        <tr data-index="${readings.indexOf(row)}" class="${index === 0 ? 'latest-row' : ''}">
          <td>${localTime(row.recorded_at)}</td>
          <td>${fmt(row.device_serial)}</td>
          <td>${num(row.heart_rate)}</td>
          <td>${num(row.oxygen_saturation)}%</td>
          <td>${num(row.movement)}</td>
          <td>${stateLabel(row.sleep_state)}</td>
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

    el('window').addEventListener('change', () => refresh({ resetZoom: true }));
    el('bucket').addEventListener('change', () => refresh({ resetZoom: true }));
    el('refresh').addEventListener('click', () => refresh());
    el('download').addEventListener('click', downloadCsv);
    el('resetZoom').addEventListener('click', resetZoom);
    ['vitalsChart', 'rollupChart', 'stateChart'].forEach(id => {
      el(id).addEventListener('dblclick', resetZoom);
    });
    window.addEventListener('resize', () => chartList().forEach(chart => { chart.options.plugins.legend = legendOptions(); chart.update('none'); }));
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
