"""'Tonight' — a narrative night report. Dark, calm, built for the 7am question:
"how was last night?" Same data as the dashboard, different lens."""

from __future__ import annotations

NIGHT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tonight · Owlet Dashboard</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    :root {
      --ink: #e8ecf8; --dim: #8b94b8; --faint: #4a5378;
      --deep: #6366f1; --light-sleep: #a78bfa; --awake: #f59e0b;
      --good: #34d399; --warn: #f87171; --card: rgba(30, 38, 74, .5);
      --line: rgba(139, 148, 184, .18);
    }
    * { box-sizing: border-box; margin: 0; }
    body {
      font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
      color: var(--ink); min-height: 100vh; padding: 28px 20px 60px;
      background:
        radial-gradient(1200px 600px at 80% -20%, #232b5c 0%, transparent 60%),
        radial-gradient(900px 500px at -10% 110%, #1a2150 0%, transparent 55%),
        #0b1023;
    }
    .stars { position: fixed; inset: 0; pointer-events: none; opacity: .5;
      background-image:
        radial-gradient(1px 1px at 12% 22%, #fff 50%, transparent 50%),
        radial-gradient(1px 1px at 78% 12%, #fff 50%, transparent 50%),
        radial-gradient(1.5px 1.5px at 55% 8%, #cdd6ff 50%, transparent 50%),
        radial-gradient(1px 1px at 32% 6%, #fff 50%, transparent 50%),
        radial-gradient(1px 1px at 90% 38%, #cdd6ff 50%, transparent 50%),
        radial-gradient(1.5px 1.5px at 8% 52%, #fff 50%, transparent 50%); }
    .wrap { max-width: 880px; margin: 0 auto; position: relative; }
    nav { display: flex; justify-content: space-between; align-items: center;
      font-size: 13px; color: var(--dim); margin-bottom: 34px; }
    nav .links a { color: var(--dim); text-decoration: none; margin-left: 18px; }
    nav .links a:hover { color: var(--ink); }
    nav .brand { font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
      font-size: 11px; color: var(--faint); }
    .night-nav { display: flex; align-items: baseline; gap: 14px; margin-bottom: 6px; }
    .night-nav button { all: unset; cursor: pointer; color: var(--dim); font-size: 22px;
      padding: 0 6px; border-radius: 8px; }
    .night-nav button:hover:not(:disabled) { color: var(--ink); }
    .night-nav button:disabled { opacity: .25; cursor: default; }
    h1 { font-size: clamp(34px, 6vw, 52px); letter-spacing: -0.025em; line-height: 1.04; }
    h1 small { display: block; font-size: 15px; letter-spacing: 0; color: var(--dim);
      font-weight: 400; margin-top: 10px; }
    .lede { font-size: 17px; line-height: 1.55; color: var(--dim); max-width: 60ch;
      margin: 18px 0 34px; }
    .lede b { color: var(--ink); font-weight: 600; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px; margin-bottom: 34px; }
    .stat { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
      padding: 18px 18px 15px; backdrop-filter: blur(14px); }
    .stat b { display: block; font-size: clamp(24px, 3.4vw, 32px); letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums; }
    .stat span { font-size: 12px; color: var(--dim); }
    .stat .sub { font-size: 11.5px; color: var(--faint); margin-top: 4px; display: block; }
    .stat.alert b { color: var(--warn); }
    .stat.calm b { color: var(--good); }
    section h2 { font-size: 13px; letter-spacing: .14em; text-transform: uppercase;
      color: var(--faint); margin: 0 0 14px; font-weight: 600; }
    .timeline-card { background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; padding: 20px; backdrop-filter: blur(14px); margin-bottom: 34px; }
    .timeline { display: flex; height: 44px; border-radius: 10px; overflow: hidden;
      background: rgba(15, 20, 45, .8); }
    .timeline span { height: 100%; }
    .tl-axis { display: flex; justify-content: space-between; font-size: 11px;
      color: var(--faint); margin-top: 8px; font-variant-numeric: tabular-nums; }
    .legend { display: flex; gap: 18px; font-size: 12px; color: var(--dim); margin-top: 14px; }
    .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px;
      margin-right: 6px; vertical-align: -1px; }
    .events { display: grid; gap: 10px; margin-bottom: 34px; }
    .event { display: flex; align-items: baseline; gap: 14px; background: var(--card);
      border: 1px solid var(--line); border-radius: 14px; padding: 14px 18px;
      backdrop-filter: blur(14px); font-size: 14px; }
    .event time { color: var(--dim); font-variant-numeric: tabular-nums; flex: 0 0 76px; }
    .event .depth { margin-left: auto; color: var(--warn); font-weight: 600;
      font-variant-numeric: tabular-nums; }
    .event.fine { color: var(--dim); }
    .event.fine .tick { color: var(--good); margin-right: 4px; }
    .week { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
      padding: 20px; backdrop-filter: blur(14px); }
    .week-bars { display: flex; align-items: flex-end; gap: 10px; height: 92px; margin-top: 6px; }
    .wb { flex: 1; display: flex; flex-direction: column; justify-content: flex-end;
      align-items: center; gap: 6px; height: 100%; }
    .wb i { display: block; width: 100%; max-width: 46px; border-radius: 6px 6px 2px 2px;
      background: linear-gradient(180deg, var(--light-sleep), var(--deep)); min-height: 3px; }
    .wb.tonight i { background: linear-gradient(180deg, #c4b5fd, #818cf8);
      box-shadow: 0 0 18px rgba(129, 140, 248, .45); }
    .wb span { font-size: 10.5px; color: var(--faint); }
    .wb b { font-size: 11px; color: var(--dim); font-weight: 500;
      font-variant-numeric: tabular-nums; }
    .empty { text-align: center; color: var(--dim); padding: 70px 20px; font-size: 15px; }
    footer { margin-top: 46px; text-align: center; font-size: 11px; color: var(--faint); }
    @media (prefers-reduced-transparency: reduce) {
      .stat, .timeline-card, .event, .week { backdrop-filter: none; background: #171d3d; }
    }
  </style>
</head>
<body>
  <div class="stars" aria-hidden="true"></div>
  <div class="wrap">
    <nav>
      <span class="brand">Owlet · Tonight</span>
      <span class="links"><a href="/">Dashboard</a><a href="/rhythms">Rhythms</a></span>
    </nav>
    <div class="night-nav">
      <button id="prevNight" aria-label="Previous night">‹</button>
      <h1 id="nightTitle">Tonight<small id="nightSub">loading…</small></h1>
      <button id="nextNight" aria-label="Next night">›</button>
    </div>
    <p class="lede" id="lede"></p>
    <div id="content"></div>
    <footer>Retrospective trend viewing only — not a medical monitor or alert replacement.</footer>
  </div>
  <script>
    const BUCKET_MIN = 5;
    const BUCKET_SEC = BUCKET_MIN * 60;
    let rollups = [];
    let deviceName = 'your little one';
    let nightOffset = 0; // 0 = most recent night

    const el = id => document.getElementById(id);
    const pad = n => String(n).padStart(2, '0');
    const fmtClock = date => {
      let h = date.getHours(); const m = pad(date.getMinutes());
      const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
      return `${h}:${m} ${ap}`;
    };
    const fmtDur = seconds => {
      const h = Math.floor(seconds / 3600), m = Math.round((seconds % 3600) / 60);
      return h ? `${h}h ${pad(m)}m` : `${m}m`;
    };

    function nightWindow(offset) {
      // A "night" runs 6 PM -> noon the next day, local time.
      const now = new Date();
      const anchor = new Date(now);
      if (now.getHours() < 12) anchor.setDate(anchor.getDate() - 1);
      anchor.setDate(anchor.getDate() - offset);
      const start = new Date(anchor); start.setHours(18, 0, 0, 0);
      const end = new Date(start); end.setDate(end.getDate() + 1); end.setHours(12, 0, 0, 0);
      return { start, end, inProgress: offset === 0 && now < end };
    }

    function bucketsIn({ start, end }) {
      return rollups.filter(row => {
        const t = new Date(row.bucket_start);
        return t >= start && t < end;
      });
    }

    function classify(row) {
      const active = (row.sleep_seconds || 0) + (row.awake_seconds || 0);
      if (!active && (row.avg_heart_rate === null || row.avg_heart_rate === undefined)) return 'nodata';
      if ((row.offline_seconds || 0) > BUCKET_SEC * 0.7) return 'nodata';
      if ((row.sleep_seconds || 0) >= (row.awake_seconds || 0) && (row.sleep_seconds || 0) > 60) {
        return (row.deep_sleep_seconds || 0) >= (row.light_sleep_seconds || 0) ? 'deep' : 'light';
      }
      if ((row.awake_seconds || 0) > 60) return 'awake';
      return 'nodata';
    }

    function nightStats(buckets) {
      let sleep = 0, deep = 0, awake = 0;
      let o2sum = 0, o2n = 0, hrSum = 0, hrN = 0, minO2 = null, minO2At = null;
      buckets.forEach(row => {
        sleep += row.sleep_seconds || 0;
        deep += row.deep_sleep_seconds || 0;
        awake += row.awake_seconds || 0;
        if (row.avg_oxygen_saturation != null) { o2sum += row.avg_oxygen_saturation; o2n++; }
        if (row.avg_heart_rate != null) { hrSum += row.avg_heart_rate; hrN++; }
        if (row.min_oxygen_saturation != null && (minO2 === null || row.min_oxygen_saturation < minO2)) {
          minO2 = row.min_oxygen_saturation; minO2At = new Date(row.bucket_start);
        }
      });
      return { sleep, deep, awake,
        avgO2: o2n ? o2sum / o2n : null, avgHr: hrN ? hrSum / hrN : null,
        minO2, minO2At, coveredSec: (o2n + 0) * BUCKET_SEC };
    }

    function dipEvents(buckets) {
      // Cluster consecutive buckets whose min O2 dropped below 90%.
      const dips = [];
      let current = null;
      buckets.forEach(row => {
        const low = row.min_oxygen_saturation != null && row.min_oxygen_saturation < 90;
        if (low) {
          if (!current) current = { start: new Date(row.bucket_start), min: row.min_oxygen_saturation };
          else current.min = Math.min(current.min, row.min_oxygen_saturation);
          current.end = new Date(new Date(row.bucket_start).getTime() + BUCKET_SEC * 1000);
        } else if (current) { dips.push(current); current = null; }
      });
      if (current) dips.push(current);
      return dips;
    }

    function narrative(stats, dips, inProgress) {
      if (!stats.coveredSec || stats.coveredSec < 1800) {
        return `Not enough readings for this night — the sock may not have been on.`;
      }
      const name = `<b>${deviceName}</b>`;
      const sleepText = `<b>${fmtDur(stats.sleep)}</b> of sleep` +
        (stats.deep ? ` (${fmtDur(stats.deep)} deep)` : '');
      let mood;
      if (!dips.length) mood = 'a smooth night — oxygen held steady the whole way';
      else if (dips.length === 1) mood = `one brief dip to <b>${Math.round(dips[0].min)}%</b> around ${fmtClock(dips[0].start)}, otherwise steady`;
      else mood = `<b>${dips.length}</b> dips below 90%, the lowest at <b>${Math.round(Math.min(...dips.map(d => d.min)))}%</b>`;
      const opener = inProgress ? `So far tonight, ${name} has logged` : `${name} logged`;
      return `${opener} ${sleepText}, with ${mood}.`;
    }

    function renderTimeline(window, buckets) {
      const total = (window.end - window.start) / 1000;
      const byTime = new Map(buckets.map(row => [new Date(row.bucket_start).getTime(), row]));
      const colors = { deep: 'var(--deep)', light: 'var(--light-sleep)', awake: 'var(--awake)', nodata: 'transparent' };
      let spans = '';
      for (let t = window.start.getTime(); t < window.end.getTime(); t += BUCKET_SEC * 1000) {
        const row = byTime.get(t);
        const cls = row ? classify(row) : 'nodata';
        spans += `<span style="flex:1;background:${colors[cls]}"></span>`;
      }
      const axis = [];
      for (let h = 18; h <= 36; h += 3) {
        const d = new Date(window.start); d.setHours(h, 0, 0, 0);
        axis.push(`<span>${fmtClock(d)}</span>`);
      }
      return `<div class="timeline-card"><h2>The night, minute by minute</h2>
        <div class="timeline">${spans}</div>
        <div class="tl-axis">${axis.join('')}</div>
        <div class="legend">
          <span><i style="background:var(--deep)"></i>Deep sleep</span>
          <span><i style="background:var(--light-sleep)"></i>Light sleep</span>
          <span><i style="background:var(--awake)"></i>Awake</span>
          <span><i style="background:rgba(15,20,45,.8);border:1px solid var(--line)"></i>No signal</span>
        </div></div>`;
    }

    function renderStats(stats, dips) {
      const minO2Text = stats.minO2 != null
        ? `<b>${Math.round(stats.minO2)}%</b><span>lowest O₂</span><span class="sub">${stats.minO2At ? 'at ' + fmtClock(stats.minO2At) : ''}</span>` : `<b>—</b><span>lowest O₂</span>`;
      return `<div class="stats">
        <div class="stat"><b>${fmtDur(stats.sleep)}</b><span>total sleep</span>
          <span class="sub">${fmtDur(stats.deep)} deep · ${fmtDur(stats.awake)} awake</span></div>
        <div class="stat"><b>${stats.avgO2 != null ? stats.avgO2.toFixed(1) + '%' : '—'}</b><span>average O₂</span></div>
        <div class="stat ${stats.minO2 != null && stats.minO2 < 88 ? 'alert' : ''}">${minO2Text}</div>
        <div class="stat"><b>${stats.avgHr != null ? Math.round(stats.avgHr) : '—'}</b><span>avg heart rate (bpm)</span></div>
        <div class="stat ${dips.length ? 'alert' : 'calm'}"><b>${dips.length}</b><span>O₂ dips below 90%</span></div>
      </div>`;
    }

    function renderEvents(dips) {
      if (!dips.length) {
        return `<section><h2>Oxygen events</h2><div class="events">
          <div class="event fine"><span class="tick">✓</span>No dips below 90% — nothing to review.</div>
        </div></section>`;
      }
      const items = dips.map(dip => `<div class="event">
        <time>${fmtClock(dip.start)}</time>
        <span>Dip lasting about ${fmtDur(Math.max(60, (dip.end - dip.start) / 1000))}</span>
        <span class="depth">↓ ${Math.round(dip.min)}%</span></div>`).join('');
      return `<section><h2>Oxygen events</h2><div class="events">${items}</div></section>`;
    }

    function renderWeek() {
      const bars = [];
      let maxSleep = 1;
      const nights = [];
      for (let offset = 6; offset >= 0; offset--) {
        const win = nightWindow(offset);
        const stats = nightStats(bucketsIn(win));
        nights.push({ offset, win, stats });
        maxSleep = Math.max(maxSleep, stats.sleep);
      }
      nights.forEach(({ offset, win, stats }) => {
        const height = Math.round((stats.sleep / maxSleep) * 100);
        const label = offset === 0 ? 'tonight'
          : win.start.toLocaleDateString([], { weekday: 'short' });
        bars.push(`<div class="wb ${offset === 0 ? 'tonight' : ''}">
          <b>${stats.sleep ? fmtDur(stats.sleep) : ''}</b>
          <i style="height:${Math.max(3, height)}%"></i><span>${label}</span></div>`);
      });
      return `<section><div class="week"><h2>Sleep, the last seven nights</h2>
        <div class="week-bars">${bars.join('')}</div></div></section>`;
    }

    function render() {
      const win = nightWindow(nightOffset);
      const buckets = bucketsIn(win);
      const stats = nightStats(buckets);
      const dips = dipEvents(buckets);
      const label = win.start.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
      el('nightTitle').childNodes[0].textContent = nightOffset === 0 ? (win.inProgress ? 'Tonight' : 'Last night') : 'The night of';
      el('nightSub').textContent = `${label}${win.inProgress ? ' · still collecting' : ''}`;
      el('lede').innerHTML = narrative(stats, dips, win.inProgress);
      el('nextNight').disabled = nightOffset === 0;
      el('prevNight').disabled = nightOffset >= 6;
      if (!stats.coveredSec || stats.coveredSec < 1800) {
        el('content').innerHTML = `<div class="empty">No night to report here yet.<br/>
          Readings appear once the sock has been worn overnight.</div>` + renderWeek();
        return;
      }
      el('content').innerHTML = renderStats(stats, dips) + renderTimeline(win, buckets)
        + renderEvents(dips) + renderWeek();
    }

    async function boot() {
      try {
        const [rollupData, devices] = await Promise.all([
          fetch('/api/rollups?bucket=5m&hours=192&limit=100000').then(r => r.json()),
          fetch('/api/devices').then(r => r.json())
        ]);
        rollups = rollupData.rollups || [];
        const device = (devices.devices || [])[0];
        if (device) deviceName = device.baby_name || device.name || deviceName;
      } catch (error) {
        el('lede').textContent = 'Could not load readings — is the collector running?';
        return;
      }
      render();
      el('prevNight').addEventListener('click', () => { nightOffset = Math.min(6, nightOffset + 1); render(); });
      el('nextNight').addEventListener('click', () => { nightOffset = Math.max(0, nightOffset - 1); render(); });
      setInterval(async () => {   // keep "still collecting" nights fresh
        if (nightOffset !== 0) return;
        const data = await fetch('/api/rollups?bucket=5m&hours=192&limit=100000').then(r => r.json()).catch(() => null);
        if (data) { rollups = data.rollups || rollups; render(); }
      }, 60000);
    }
    boot();
  </script>
</body>
</html>"""


def render_night_page() -> str:
    return NIGHT_HTML
