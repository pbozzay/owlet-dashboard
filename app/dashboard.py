DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Owlet History</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: rgba(255, 255, 255, .94);
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
    .shell { width: min(1460px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 48px; }
    .hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; margin-bottom: 18px; }
    h1 { margin: 0; letter-spacing: -.045em; font-size: clamp(2.3rem, 5vw, 4.4rem); line-height: .92; }
    h2 { margin: 0; font-size: 1.06rem; letter-spacing: -.02em; }
    h3 { margin: 0 0 8px; font-size: .88rem; color: var(--muted); text-transform: uppercase; letter-spacing: .07em; }
    .subtitle { color: var(--muted); max-width: 760px; margin: 12px 0 0; font-size: 1.02rem; }
    .status { display: flex; align-items: center; gap: 8px; padding: .55rem .8rem; border-radius: 999px; background: #eef2ff; color: #3730a3; font-weight: 800; font-size: .88rem; white-space: nowrap; }
    .status-dot { width: 9px; height: 9px; border-radius: 50%; background: #94a3b8; display: inline-block; }
    .status-dot.good { background: #22c55e; }
    .toolbar, .panel, .card {
      background: var(--panel);
      border: 1px solid rgba(226, 232, 240, .9);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
      border-radius: 24px;
    }
    .toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; padding: 12px; margin: 18px 0; }
    .control-group { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    label { color: var(--muted); font-size: .9rem; font-weight: 700; }
    select, input, button {
      border: 1px solid var(--line); background: #fff; color: var(--text); border-radius: 13px;
      padding: .62rem .78rem; font: inherit;
    }
    button { cursor: pointer; font-weight: 800; }
    button.primary { background: var(--dark); color: #fff; border-color: var(--dark); }
    .grid { display: grid; gap: 14px; }
    .today-grid { grid-template-columns: 1.1fr 1fr 1fr; margin-bottom: 14px; }
    .metric-grid { grid-template-columns: repeat(4, minmax(140px, 1fr)); }
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
    .charts { grid-template-columns: minmax(0, 1.3fr) minmax(420px, .7fr); align-items: start; }
    .panel-title { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 10px; }
    .small { color: var(--muted); font-size: .88rem; }
    .insight-text { font-size: 1.08rem; font-weight: 750; line-height: 1.35; margin: 12px 0; }
    .drill-grid { grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); margin-top: 14px; }
    table { width: 100%; border-collapse: collapse; font-size: .9rem; }
    th, td { padding: 10px 9px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    th { color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; background: #f8fafc; position: sticky; top: 0; z-index: 1; }
    tr:hover td { background: #f8fafc; }
    .table-wrap { overflow: auto; max-height: 460px; border: 1px solid var(--line); border-radius: 16px; }
    .raw-box { white-space: pre-wrap; word-break: break-word; background: var(--dark); color: #dbeafe; border-radius: 16px; padding: 14px; max-height: 280px; overflow: auto; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; }
    .empty { padding: 28px; text-align: center; color: var(--muted); border: 1px dashed #cbd5e1; border-radius: 18px; background: #f8fafc; }
    .progress { height: 10px; border-radius: 999px; overflow: hidden; background: #e2e8f0; margin-top: 12px; display: flex; }
    .progress span:nth-child(1) { background: var(--purple); }
    .progress span:nth-child(2) { background: var(--blue); }
    .progress span:nth-child(3) { background: var(--amber); }
    @media (max-width: 1080px) {
      .hero { align-items: flex-start; flex-direction: column; }
      .today-grid, .metric-grid, .charts, .drill-grid { grid-template-columns: 1fr; }
      .status { white-space: normal; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <h1>Owlet History</h1>
        <p class="subtitle">
          Live-updated pulse plus historical drill-downs for breathing, sleep, wake time,
          and raw readings. Retrospective trend viewing only — not a medical monitor or alert replacement.
        </p>
      </div>
      <div class="status" id="status"><span class="status-dot"></span>Checking collector…</div>
    </section>

    <section class="toolbar">
      <div class="control-group">
        <label for="window">Window</label>
        <select id="window">
          <option value="6">6 hours</option>
          <option value="12">12 hours</option>
          <option selected value="24">24 hours</option>
          <option value="72">3 days</option>
          <option value="168">7 days</option>
          <option value="720">30 days</option>
          <option value="all">All stored data</option>
        </select>
        <label for="bucket">Drill-down</label>
        <select id="bucket">
          <option selected value="hour">Hourly</option>
          <option value="day">Daily</option>
        </select>
        <label for="search">Search</label>
        <input id="search" placeholder="sleep state, serial, value…" />
      </div>
      <div class="control-group">
        <span class="small" id="refreshNote">Refreshing…</span>
        <button id="refresh" class="primary">Refresh now</button>
        <button id="download">Download CSV</button>
      </div>
    </section>

    <section class="grid today-grid">
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

    <section class="grid charts" style="margin-top: 14px;">
      <div class="panel">
        <div class="panel-title">
          <h2>Live vitals trace</h2>
          <span class="small" id="coverage">—</span>
        </div>
        <canvas id="vitalsChart" height="130"></canvas>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>Sleep / state mix</h2>
          <span class="small">by estimated duration</span>
        </div>
        <canvas id="stateChart" height="220"></canvas>
      </div>
    </section>

    <section class="grid drill-grid">
      <div class="panel">
        <div class="panel-title">
          <h2>Drill-down averages</h2>
          <span class="small" id="rollupLabel">Hourly</span>
        </div>
        <canvas id="rollupChart" height="190"></canvas>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>Drill-down table</h2>
          <span class="small">averages + sleep/awake estimates</span>
        </div>
        <div class="table-wrap"><table id="rollupTable"></table></div>
      </div>
    </section>

    <section class="grid drill-grid">
      <div class="panel">
        <div class="panel-title">
          <h2>Readings table</h2>
          <span class="small" id="tableCount">—</span>
        </div>
        <div class="table-wrap"><table id="readingsTable"></table></div>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>Selected reading</h2>
          <span class="small">click a reading row</span>
        </div>
        <pre id="raw" class="raw-box">No reading selected yet.</pre>
      </div>
    </section>
  </main>

  <script>
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

    const el = (id) => document.getElementById(id);
    const fmt = (value, suffix = '') => value === null || value === undefined ? '—' : `${value}${suffix}`;
    const num = (value, digits = 1) => value === null || value === undefined ? '—' : Number(value).toFixed(digits).replace(/\.0$/, '');
    const hours = (seconds) => seconds ? `${(seconds / 3600).toFixed(1).replace(/\.0$/, '')}h` : '0h';
    const trendClass = (trend) => `trend-${trend || 'unknown'}`;
    const localTime = (iso) => iso ? new Date(iso).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' }) : '—';
    const stateLabel = (value) => ({ '0': 'inactive', '1': 'awake', '8': 'light sleep', '15': 'deep sleep' }[String(value)] || `state ${value ?? 'unknown'}`);

    function queryParams(extra = {}) {
      const window = el('window').value;
      const params = new URLSearchParams({ limit: '100000', ...extra });
      if (window !== 'all') params.set('hours', window);
      return params.toString();
    }

    async function refresh() {
      secondsUntilRefresh = REFRESH_SECONDS;
      const qs = queryParams();
      const rollupQs = queryParams({ bucket: el('bucket').value });
      const [health, rows, stats, insightData, rollupData] = await Promise.all([
        fetch('/api/health').then(r => r.json()),
        fetch(`/api/readings?${qs}`).then(r => r.json()),
        fetch(`/api/summary?${qs}`).then(r => r.json()),
        fetch(`/api/insights?${qs}`).then(r => r.json()),
        fetch(`/api/rollups?${rollupQs}`).then(r => r.json())
      ]);
      readings = rows;
      summary = stats;
      insights = insightData;
      rollups = rollupData.rollups || [];
      renderStatus(health);
      renderInsights();
      applyFilter();
      renderMetricCards();
      renderCharts();
      renderRollups();
    }

    function renderStatus(health) {
      el('status').innerHTML = `<span class="status-dot ${health.collecting ? 'good' : ''}"></span>${health.collecting ? 'Collecting live' : 'Stored data only'} · ${health.database_path}`;
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

    function downsample(rows, maxPoints = 900) {
      if (rows.length <= maxPoints) return rows;
      const step = Math.ceil(rows.length / maxPoints);
      return rows.filter((_, index) => index % step === 0 || index === rows.length - 1);
    }

    function renderCharts() {
      const sampled = downsample(readings);
      if (vitalsChart) vitalsChart.destroy();
      vitalsChart = new Chart(el('vitalsChart'), {
        type: 'line',
        data: {
          labels: sampled.map(r => localTime(r.recorded_at)),
          datasets: [
            { label: 'Heart rate', data: sampled.map(r => r.heart_rate), borderColor: '#dc2626', backgroundColor: '#dc262620', yAxisID: 'hr', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'SpO₂', data: sampled.map(r => r.oxygen_saturation), borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'spo2', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'Movement', data: sampled.map(r => r.movement), borderColor: '#059669', backgroundColor: '#05966920', yAxisID: 'move', spanGaps: true, pointRadius: 0, tension: .2 }
          ]
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { position: 'bottom' } },
          scales: {
            hr: { type: 'linear', position: 'left', title: { display: true, text: 'BPM' } },
            spo2: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'SpO₂' } },
            move: { display: false }
          }
        }
      });

      const sleep = insights.sleep;
      if (stateChart) stateChart.destroy();
      stateChart = new Chart(el('stateChart'), {
        type: 'doughnut',
        data: {
          labels: ['Light sleep', 'Deep sleep', 'Awake'],
          datasets: [{ data: [sleep.light_sleep_seconds, sleep.deep_sleep_seconds, sleep.awake_seconds], backgroundColor: ['#7c3aed', '#2563eb', '#b45309'] }]
        },
        options: { plugins: { legend: { position: 'bottom' } } }
      });
    }

    function renderRollups() {
      el('rollupLabel').textContent = el('bucket').selectedOptions[0].textContent;
      if (rollupChart) rollupChart.destroy();
      rollupChart = new Chart(el('rollupChart'), {
        type: 'bar',
        data: {
          labels: rollups.map(r => r.bucket_label),
          datasets: [
            { type: 'line', label: 'Avg O₂', data: rollups.map(r => r.avg_oxygen_saturation), borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'oxygen', tension: .25 },
            { type: 'bar', label: 'Sleep hrs', data: rollups.map(r => r.sleep_seconds / 3600), backgroundColor: '#7c3aed80', yAxisID: 'hours' },
            { type: 'bar', label: 'Awake hrs', data: rollups.map(r => r.awake_seconds / 3600), backgroundColor: '#b4530980', yAxisID: 'hours' }
          ]
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { position: 'bottom' } },
          scales: {
            oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100, title: { display: true, text: 'Avg O₂' } },
            hours: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Hours' } }
          }
        }
      });
      const rows = rollups.slice().reverse().map(row => `<tr><td>${row.bucket_label}</td><td>${row.samples}</td><td>${fmt(row.avg_oxygen_saturation, '%')}</td><td>${fmt(row.min_oxygen_saturation, '%')}</td><td>${fmt(row.avg_heart_rate, ' bpm')}</td><td>${hours(row.sleep_seconds)}</td><td>${hours(row.awake_seconds)}</td></tr>`).join('');
      el('rollupTable').innerHTML = `<thead><tr><th>Window</th><th>Samples</th><th>Avg O₂</th><th>Min O₂</th><th>Avg HR</th><th>Sleep</th><th>Awake</th></tr></thead><tbody>${rows || '<tr><td colspan="7" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function applyFilter() {
      const q = el('search').value.trim().toLowerCase();
      filtered = q ? readings.filter(row => JSON.stringify(row).toLowerCase().includes(q)) : readings;
      renderReadingsTable();
    }

    function renderReadingsTable() {
      const rows = filtered.slice().reverse().map(row => `
        <tr data-index="${readings.indexOf(row)}">
          <td>${localTime(row.recorded_at)}</td>
          <td>${fmt(row.device_serial)}</td>
          <td>${num(row.heart_rate)}</td>
          <td>${num(row.oxygen_saturation)}%</td>
          <td>${num(row.movement)}</td>
          <td>${stateLabel(row.sleep_state)}</td>
          <td>${fmt(row.battery, '%')}</td>
          <td>${num(row.skin_temperature)}</td>
        </tr>`).join('');
      el('tableCount').textContent = `${filtered.length} shown · ${readings.length} loaded`;
      el('readingsTable').innerHTML = `<thead><tr><th>Time</th><th>Serial</th><th>HR</th><th>O₂</th><th>Move</th><th>State</th><th>Battery</th><th>Temp</th></tr></thead><tbody>${rows || '<tr><td colspan="8" class="empty">No matching readings.</td></tr>'}</tbody>`;
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

    function tickCountdown() {
      secondsUntilRefresh = Math.max(0, secondsUntilRefresh - 1);
      el('refreshNote').textContent = `Auto-refresh in ${secondsUntilRefresh}s`;
      if (secondsUntilRefresh === 0) refresh();
    }

    el('window').addEventListener('change', refresh);
    el('bucket').addEventListener('change', refresh);
    el('search').addEventListener('input', applyFilter);
    el('refresh').addEventListener('click', refresh);
    el('download').addEventListener('click', downloadCsv);
    refresh();
    setInterval(tickCountdown, 1000);
  </script>
</body>
</html>
"""
