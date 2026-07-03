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
      --panel: rgba(255, 255, 255, .92);
      --panel-solid: #ffffff;
      --text: #122033;
      --muted: #64748b;
      --line: #e2e8f0;
      --red: #dc2626;
      --blue: #2563eb;
      --green: #059669;
      --amber: #b45309;
      --purple: #7c3aed;
      --shadow: 0 18px 50px rgba(15, 23, 42, .10);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(59, 130, 246, .14), transparent 32rem),
        radial-gradient(circle at top right, rgba(236, 72, 153, .10), transparent 30rem),
        var(--bg);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .shell { width: min(1440px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 48px; }
    .hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; margin-bottom: 20px; }
    h1 { margin: 0; letter-spacing: -.04em; font-size: clamp(2rem, 5vw, 4.2rem); line-height: .95; }
    .subtitle { color: var(--muted); max-width: 720px; margin: 12px 0 0; font-size: 1.02rem; }
    .toolbar {
      display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between;
      background: var(--panel); border: 1px solid rgba(226, 232, 240, .75); box-shadow: var(--shadow);
      backdrop-filter: blur(14px); padding: 12px; border-radius: 22px; margin: 18px 0;
    }
    .control-group { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    label { color: var(--muted); font-size: .9rem; font-weight: 650; }
    select, input, button {
      border: 1px solid var(--line); background: #fff; color: var(--text); border-radius: 12px;
      padding: .62rem .75rem; font: inherit;
    }
    button { cursor: pointer; font-weight: 750; }
    button.primary { background: #111827; color: #fff; border-color: #111827; }
    .pill { padding: .45rem .7rem; border-radius: 999px; background: #eef2ff; color: #3730a3; font-weight: 750; font-size: .86rem; }
    .grid { display: grid; gap: 14px; }
    .cards { grid-template-columns: repeat(5, minmax(150px, 1fr)); margin-bottom: 14px; }
    .card, .panel {
      background: var(--panel-solid); border: 1px solid rgba(226, 232, 240, .9); border-radius: 22px;
      box-shadow: 0 8px 28px rgba(15, 23, 42, .07); padding: 16px;
    }
    .metric-label { color: var(--muted); font-size: .82rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
    .metric-value { font-size: clamp(1.7rem, 3vw, 2.7rem); line-height: 1; font-weight: 850; letter-spacing: -.04em; margin: 9px 0 6px; }
    .metric-foot { color: var(--muted); font-size: .9rem; }
    .trend-up { color: var(--amber); }
    .trend-down { color: var(--blue); }
    .trend-flat { color: var(--green); }
    .trend-unknown { color: var(--muted); }
    .charts { grid-template-columns: minmax(0, 1.35fr) minmax(360px, .65fr); align-items: start; }
    .panel-title { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 10px; }
    h2 { margin: 0; font-size: 1.05rem; letter-spacing: -.01em; }
    .small { color: var(--muted); font-size: .88rem; }
    canvas { width: 100%; }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }
    table { width: 100%; border-collapse: collapse; font-size: .9rem; }
    th, td { padding: 10px 9px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    th { color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; background: #f8fafc; position: sticky; top: 0; z-index: 1; }
    tr:hover td { background: #f8fafc; }
    .table-wrap { overflow: auto; max-height: 520px; border: 1px solid var(--line); border-radius: 16px; }
    .raw-box { white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #dbeafe; border-radius: 16px; padding: 14px; max-height: 360px; overflow: auto; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; }
    .empty { padding: 28px; text-align: center; color: var(--muted); border: 1px dashed #cbd5e1; border-radius: 18px; background: #f8fafc; }
    .status-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 7px; background: #94a3b8; }
    .status-dot.good { background: #22c55e; }
    @media (max-width: 1000px) {
      .hero { align-items: flex-start; flex-direction: column; }
      .cards, .charts, .split { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <h1>Owlet History</h1>
        <p class="subtitle">
          All stored data from the local Owlet collector, organized into current vitals,
          trends, daily rollups, and a searchable readings table. Retrospective trend viewing only —
          not a medical monitor or alerting replacement.
        </p>
      </div>
      <div class="pill" id="status"><span class="status-dot"></span>Checking collector…</div>
    </section>

    <section class="toolbar">
      <div class="control-group">
        <label for="window">Window</label>
        <select id="window">
          <option selected value="all">All stored data</option>
          <option value="6">6 hours</option>
          <option value="12">12 hours</option>
          <option value="24">24 hours</option>
          <option value="72">3 days</option>
          <option value="168">7 days</option>
          <option value="720">30 days</option>
        </select>
        <label for="search">Search</label>
        <input id="search" placeholder="sleep state, serial, value…" />
      </div>
      <div class="control-group">
        <button id="refresh" class="primary">Refresh</button>
        <button id="download">Download CSV</button>
      </div>
    </section>

    <section class="grid cards" id="cards"></section>

    <section class="grid charts">
      <div class="panel">
        <div class="panel-title">
          <h2>Vitals over time</h2>
          <span class="small" id="coverage">—</span>
        </div>
        <canvas id="vitalsChart" height="128"></canvas>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>Sleep / state mix</h2>
          <span class="small">by sample count</span>
        </div>
        <canvas id="stateChart" height="220"></canvas>
      </div>
    </section>

    <section class="split">
      <div class="panel">
        <div class="panel-title">
          <h2>Daily rollups</h2>
          <span class="small">local date buckets</span>
        </div>
        <div class="table-wrap"><table id="dailyTable"></table></div>
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
    let readings = [];
    let filtered = [];
    let summary = null;
    let vitalsChart = null;
    let stateChart = null;

    const el = (id) => document.getElementById(id);
    const fmt = (value, suffix = '') => value === null || value === undefined ? '—' : `${value}${suffix}`;
    const num = (value, digits = 1) => value === null || value === undefined ? '—' : Number(value).toFixed(digits).replace(/\.0$/, '');
    const trendClass = (trend) => `trend-${trend || 'unknown'}`;
    const localTime = (iso) => iso ? new Date(iso).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' }) : '—';
    const localDate = (iso) => iso ? new Date(iso).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }) : '—';

    function queryString() {
      const window = el('window').value;
      const params = new URLSearchParams({ limit: '100000' });
      if (window !== 'all') params.set('hours', window);
      return params.toString();
    }

    async function refresh() {
      const qs = queryString();
      const [health, rows, stats] = await Promise.all([
        fetch('/api/health').then(r => r.json()),
        fetch(`/api/readings?${qs}`).then(r => r.json()),
        fetch(`/api/summary?${qs}`).then(r => r.json())
      ]);
      readings = rows;
      summary = stats;
      renderStatus(health);
      applyFilter();
      renderCards();
      renderCharts();
      renderDailyTable();
    }

    function renderStatus(health) {
      el('status').innerHTML = `<span class="status-dot ${health.collecting ? 'good' : ''}"></span>${health.collecting ? 'Collecting live' : 'Stored data only'} · ${health.database_path}`;
    }

    function renderCards() {
      const cards = [
        ['Heart rate', fmt(summary.heart_rate.latest, ' bpm'), `avg ${num(summary.heart_rate.avg)} · ${summary.heart_rate.trend}`, summary.heart_rate.trend],
        ['Oxygen', fmt(summary.oxygen_saturation.latest, '%'), `avg ${num(summary.oxygen_saturation.avg)} · min ${num(summary.oxygen_saturation.min)}`, summary.oxygen_saturation.trend],
        ['Movement', num(summary.movement.latest), `avg ${num(summary.movement.avg)} · ${summary.movement.trend}`, summary.movement.trend],
        ['Battery', fmt(summary.battery.latest, '%'), `avg ${num(summary.battery.avg)} · ${summary.battery.trend}`, summary.battery.trend],
        ['Samples', summary.count, `${localTime(summary.first_recorded_at)} → ${localTime(summary.last_recorded_at)}`, 'unknown'],
      ];
      el('cards').innerHTML = cards.map(([label, value, foot, trend]) => `
        <article class="card">
          <div class="metric-label">${label}</div>
          <div class="metric-value ${trendClass(trend)}">${value}</div>
          <div class="metric-foot">${foot}</div>
        </article>`).join('');
      el('coverage').textContent = summary.count ? `${summary.window} · ${summary.count} readings` : 'No stored readings yet';
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
            { label: 'Movement', data: sampled.map(r => r.movement), borderColor: '#059669', backgroundColor: '#05966920', yAxisID: 'spo2', spanGaps: true, pointRadius: 0, tension: .2 }
          ]
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { position: 'bottom' } },
          scales: {
            hr: { type: 'linear', position: 'left', title: { display: true, text: 'BPM' } },
            spo2: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'SpO₂ / movement' } }
          }
        }
      });

      const states = countBy(readings, r => r.sleep_state || 'unknown');
      if (stateChart) stateChart.destroy();
      stateChart = new Chart(el('stateChart'), {
        type: 'doughnut',
        data: {
          labels: Object.keys(states),
          datasets: [{ data: Object.values(states), backgroundColor: ['#2563eb', '#7c3aed', '#059669', '#f59e0b', '#64748b', '#dc2626'] }]
        },
        options: { plugins: { legend: { position: 'bottom' } } }
      });
    }

    function countBy(rows, fn) {
      return rows.reduce((acc, row) => {
        const key = fn(row);
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {});
    }

    function avg(values) {
      const clean = values.filter(v => v !== null && v !== undefined).map(Number);
      return clean.length ? clean.reduce((a, b) => a + b, 0) / clean.length : null;
    }

    function renderDailyTable() {
      const buckets = {};
      readings.forEach(row => {
        const day = localDate(row.recorded_at);
        buckets[day] ||= [];
        buckets[day].push(row);
      });
      const rows = Object.entries(buckets).reverse().map(([day, items]) => {
        const minSpo2 = Math.min(...items.map(r => r.oxygen_saturation).filter(v => v !== null && v !== undefined));
        return `<tr><td>${day}</td><td>${items.length}</td><td>${num(avg(items.map(r => r.heart_rate)))}</td><td>${num(avg(items.map(r => r.oxygen_saturation)))}%</td><td>${Number.isFinite(minSpo2) ? num(minSpo2) + '%' : '—'}</td><td>${num(avg(items.map(r => r.movement)))}</td></tr>`;
      }).join('');
      el('dailyTable').innerHTML = `<thead><tr><th>Date</th><th>Samples</th><th>Avg HR</th><th>Avg O₂</th><th>Min O₂</th><th>Avg move</th></tr></thead><tbody>${rows || '<tr><td colspan="6" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function applyFilter() {
      const q = el('search').value.trim().toLowerCase();
      filtered = q ? readings.filter(row => JSON.stringify(row).toLowerCase().includes(q)) : readings;
      renderReadingsTable();
    }

    function renderReadingsTable() {
      const rows = filtered.slice().reverse().map((row, index) => `
        <tr data-index="${readings.indexOf(row)}">
          <td>${localTime(row.recorded_at)}</td>
          <td>${fmt(row.device_serial)}</td>
          <td>${num(row.heart_rate)}</td>
          <td>${num(row.oxygen_saturation)}%</td>
          <td>${num(row.movement)}</td>
          <td>${fmt(row.sleep_state)}</td>
          <td>${num(row.battery)}%</td>
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

    el('window').addEventListener('change', refresh);
    el('search').addEventListener('input', applyFilter);
    el('refresh').addEventListener('click', refresh);
    el('download').addEventListener('click', downloadCsv);
    refresh();
    setInterval(refresh, 30000);
  </script>
</body>
</html>
"""
