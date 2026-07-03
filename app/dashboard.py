DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Owlet History</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; background: #f7fafc; color: #172033; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0 2rem; }
    .card { background: white; border-radius: 14px; padding: 1rem; box-shadow: 0 2px 18px rgba(15,23,42,.08); }
    .label { color: #637083; font-size: .85rem; }
    .value { font-size: 2rem; font-weight: 750; }
    .trend-up { color: #b45309; }
    .trend-down { color: #2563eb; }
    .trend-flat { color: #059669; }
    .chart-wrap { background: white; border-radius: 14px; padding: 1rem; box-shadow: 0 2px 18px rgba(15,23,42,.08); }
    select { padding: .4rem .6rem; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>Owlet History</h1>
  <p>Local historical view for Dream Sock / Smart Sock vitals. This is not a medical monitor; use the Owlet app/base station for alerts.</p>
  <label>Window:
    <select id="hours">
      <option value="6">6 hours</option>
      <option value="12">12 hours</option>
      <option selected value="24">24 hours</option>
      <option value="72">3 days</option>
      <option value="168">7 days</option>
    </select>
  </label>
  <div class="cards" id="cards"></div>
  <div class="chart-wrap"><canvas id="chart" height="110"></canvas></div>
  <script>
    let chart;
    function trendClass(t) { return `trend-${t || 'flat'}`; }
    function fmt(x, suffix='') { return x === null || x === undefined ? '—' : `${x}${suffix}`; }
    async function refresh() {
      const hours = document.getElementById('hours').value;
      const [readings, summary] = await Promise.all([
        fetch(`/api/readings?hours=${hours}`).then(r => r.json()),
        fetch(`/api/summary?hours=${hours}`).then(r => r.json())
      ]);
      const cards = document.getElementById('cards');
      cards.innerHTML = `
        <div class="card"><div class="label">Heart Rate</div><div class="value ${trendClass(summary.heart_rate.trend)}">${fmt(summary.heart_rate.latest, ' bpm')}</div><div>avg ${fmt(summary.heart_rate.avg)} · ${summary.heart_rate.trend}</div></div>
        <div class="card"><div class="label">Oxygen</div><div class="value ${trendClass(summary.oxygen_saturation.trend)}">${fmt(summary.oxygen_saturation.latest, '%')}</div><div>avg ${fmt(summary.oxygen_saturation.avg)} · ${summary.oxygen_saturation.trend}</div></div>
        <div class="card"><div class="label">Movement</div><div class="value ${trendClass(summary.movement.trend)}">${fmt(summary.movement.latest)}</div><div>avg ${fmt(summary.movement.avg)} · ${summary.movement.trend}</div></div>
        <div class="card"><div class="label">Samples</div><div class="value">${summary.count}</div><div>stored locally</div></div>`;
      const labels = readings.map(r => new Date(r.recorded_at).toLocaleString());
      const data = {
        labels,
        datasets: [
          { label: 'Heart rate', data: readings.map(r => r.heart_rate), borderColor: '#dc2626', yAxisID: 'y' },
          { label: 'SpO₂', data: readings.map(r => r.oxygen_saturation), borderColor: '#2563eb', yAxisID: 'y1' },
          { label: 'Movement', data: readings.map(r => r.movement), borderColor: '#059669', yAxisID: 'y1' }
        ]
      };
      if (chart) chart.destroy();
      chart = new Chart(document.getElementById('chart'), {
        type: 'line', data,
        options: { responsive: true, interaction: { mode: 'index', intersect: false },
          scales: { y: { type: 'linear', position: 'left' }, y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } } } }
      });
    }
    document.getElementById('hours').addEventListener('change', refresh);
    refresh();
    setInterval(refresh, 30000);
  </script>
</body>
</html>
"""
