"""'Rhythms' — a 14-day actogram and pattern reader. Light, editorial, built for
the slower question: "is a schedule forming?" Same data, longer lens."""

from __future__ import annotations

RHYTHMS_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Rhythms · Owlet Dashboard</title>
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <style>
    :root {
      --paper: #faf7f2; --ink: #1c1917; --dim: #78716c; --faint: #a8a29e;
      --sleep-1: #ede9fe; --sleep-2: #c4b5fd; --sleep-3: #8b5cf6; --sleep-4: #5b21b6;
      --awake: #fbbf24; --nodata: #f0ece5; --line: #e7e0d5; --accent: #5b21b6;
    }
    * { box-sizing: border-box; margin: 0; }
    body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
      background: var(--paper); color: var(--ink); min-height: 100vh; padding: 28px 20px 60px; }
    .wrap { max-width: 940px; margin: 0 auto; }
    nav { display: flex; justify-content: space-between; align-items: center;
      font-size: 13px; color: var(--dim); margin-bottom: 40px; }
    nav .links a { color: var(--dim); text-decoration: none; margin-left: 18px; }
    nav .links a:hover { color: var(--ink); }
    nav .brand { font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
      font-size: 11px; color: var(--faint); }
    h1 { font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
      font-size: clamp(34px, 5.4vw, 54px); line-height: 1.06; letter-spacing: -0.015em;
      font-weight: 600; max-width: 18ch; }
    h1 em { font-style: italic; color: var(--accent); }
    .lede { font-size: 16.5px; line-height: 1.6; color: var(--dim); max-width: 58ch;
      margin: 18px 0 40px; }
    section { margin-bottom: 44px; }
    section > h2 { font-size: 12px; letter-spacing: .15em; text-transform: uppercase;
      color: var(--faint); font-weight: 700; margin-bottom: 16px; }
    .acto-card { background: #fff; border: 1px solid var(--line); border-radius: 18px;
      padding: 22px; box-shadow: 0 12px 34px rgba(28, 25, 23, .05); overflow-x: auto; }
    table.acto { border-collapse: collapse; width: 100%; min-width: 680px; }
    table.acto th { font-size: 9.5px; font-weight: 500; color: var(--faint);
      padding: 0 0 8px; text-align: left; }
    table.acto td.day { font-size: 11px; color: var(--dim); padding-right: 12px;
      white-space: nowrap; font-variant-numeric: tabular-nums; }
    table.acto td.cell { height: 20px; padding: 1px; }
    table.acto td.cell i { display: block; width: 100%; height: 100%; border-radius: 3px; }
    .acto-legend { display: flex; flex-wrap: wrap; gap: 18px; font-size: 12px;
      color: var(--dim); margin-top: 16px; }
    .acto-legend i { display: inline-block; width: 11px; height: 11px; border-radius: 3px;
      margin-right: 6px; vertical-align: -1px; }
    .grad { display: inline-flex; vertical-align: -1px; margin-right: 6px; }
    .grad i { width: 11px; height: 11px; margin: 0; border-radius: 0; }
    .grad i:first-child { border-radius: 3px 0 0 3px; }
    .grad i:last-child { border-radius: 0 3px 3px 0; }
    .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }
    .tile { background: #fff; border: 1px solid var(--line); border-radius: 18px;
      padding: 20px; box-shadow: 0 12px 34px rgba(28, 25, 23, .05); }
    .tile h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
      color: var(--faint); font-weight: 700; margin-bottom: 10px; }
    .tile b { font-size: 27px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
    .tile b small { font-size: 14px; color: var(--dim); font-weight: 500; }
    .tile p { font-size: 13px; color: var(--dim); line-height: 1.5; margin-top: 8px; }
    .tile .delta { font-size: 13px; font-weight: 600; margin-left: 8px; }
    .delta.up { color: #15803d; } .delta.down { color: #b45309; } .delta.flat { color: var(--faint); }
    .empty { text-align: center; color: var(--dim); padding: 60px 20px; font-size: 15px;
      background: #fff; border: 1px dashed var(--line); border-radius: 18px; }
    footer { margin-top: 48px; text-align: center; font-size: 11px; color: var(--faint); }
  </style>
</head>
<body>
  <div class="wrap">
    <nav>
      <span class="brand">Owlet · Rhythms</span>
      <span class="links"><a href="/">Dashboard</a><a href="/night">Tonight</a></span>
    </nav>
    <h1 id="title">The shape of <em>the days</em></h1>
    <p class="lede" id="lede">Every row is a day, every column a half-hour. Purple is sleep
      (darker = deeper), amber is awake, blank is no signal. Over weeks, a rhythm emerges —
      this page is where you watch it happen.</p>
    <div id="content"></div>
    <footer>Retrospective trend viewing only — not a medical monitor or alert replacement.</footer>
  </div>
  <script>
    const BUCKET_MIN = 30;
    const BUCKET_SEC = BUCKET_MIN * 60;
    const COLS = 48;
    const el = id => document.getElementById(id);
    const pad = n => String(n).padStart(2, '0');
    const fmtDur = seconds => {
      const h = Math.floor(seconds / 3600), m = Math.round((seconds % 3600) / 60);
      return h ? `${h}h ${pad(m)}m` : `${m}m`;
    };
    const fmtClock = minutesFromMidnight => {
      let h = Math.floor(minutesFromMidnight / 60) % 24; const m = pad(Math.round(minutesFromMidnight % 60));
      const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
      return `${h}:${m} ${ap}`;
    };

    function dayGrid(rollups) {
      // Map bucket rows into day rows x 48 half-hour columns (local time).
      const days = new Map();
      rollups.forEach(row => {
        const t = new Date(row.bucket_start);
        const key = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`;
        if (!days.has(key)) days.set(key, { date: new Date(t.getFullYear(), t.getMonth(), t.getDate()), cells: Array(COLS).fill(null) });
        const col = t.getHours() * 2 + (t.getMinutes() >= 30 ? 1 : 0);
        days.get(key).cells[col] = row;
      });
      return [...days.values()].sort((a, b) => a.date - b.date);
    }

    function cellColor(row) {
      if (!row) return 'var(--nodata)';
      const sleep = row.sleep_seconds || 0, awake = row.awake_seconds || 0;
      if (!sleep && !awake) return 'var(--nodata)';
      if (awake > sleep) return 'var(--awake)';
      const fraction = sleep / BUCKET_SEC;
      if (fraction > .85) return 'var(--sleep-4)';
      if (fraction > .6) return 'var(--sleep-3)';
      if (fraction > .3) return 'var(--sleep-2)';
      return 'var(--sleep-1)';
    }

    function cellTitle(day, col, row) {
      const when = `${day.date.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${fmtClock(col * 30)}`;
      if (!row) return `${when} — no signal`;
      const parts = [];
      if (row.sleep_seconds) parts.push(`${fmtDur(row.sleep_seconds)} asleep`);
      if (row.awake_seconds) parts.push(`${fmtDur(row.awake_seconds)} awake`);
      if (row.avg_oxygen_saturation != null) parts.push(`O₂ ${row.avg_oxygen_saturation.toFixed(1)}%`);
      if (row.avg_heart_rate != null) parts.push(`HR ${Math.round(row.avg_heart_rate)}`);
      return `${when} — ${parts.join(' · ') || 'no signal'}`;
    }

    function renderActogram(days) {
      const headers = ['<th></th>'];
      for (let h = 0; h < 24; h += 3) headers.push(`<th colspan="6">${fmtClock(h * 60)}</th>`);
      const rows = days.map(day => {
        const cells = day.cells.map((row, col) =>
          `<td class="cell"><i style="background:${cellColor(row)}" title="${cellTitle(day, col, row)}"></i></td>`).join('');
        const label = day.date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
        return `<tr><td class="day">${label}</td>${cells}</tr>`;
      }).join('');
      return `<section><h2>Two weeks, half-hour by half-hour</h2>
        <div class="acto-card"><table class="acto">
          <tr>${headers.join('')}</tr>${rows}</table>
        <div class="acto-legend">
          <span><span class="grad"><i style="background:var(--sleep-1)"></i><i style="background:var(--sleep-2)"></i><i style="background:var(--sleep-3)"></i><i style="background:var(--sleep-4)"></i></span>Sleep (light → deep)</span>
          <span><i style="background:var(--awake)"></i>Awake</span>
          <span><i style="background:var(--nodata)"></i>No signal</span>
        </div></div></section>`;
    }

    // ----- pattern analysis -------------------------------------------------

    function nightlyAnalysis(days) {
      // For each night (6 PM day N -> noon day N+1): total sleep, bedtime, longest stretch.
      const byTime = new Map();
      days.forEach(day => day.cells.forEach((row, col) => {
        if (row) byTime.set(day.date.getTime() + col * BUCKET_SEC * 1000, row);
      }));
      const nights = [];
      days.forEach(day => {
        const start = day.date.getTime() + 18 * 3600 * 1000;
        const end = start + 18 * 3600 * 1000;
        let sleep = 0, covered = 0, bedtime = null, stretch = 0, bestStretch = 0;
        for (let t = start; t < end; t += BUCKET_SEC * 1000) {
          const row = byTime.get(t);
          if (!row) { stretch = 0; continue; }
          covered += 1;
          const asleep = (row.sleep_seconds || 0) > BUCKET_SEC * 0.5;
          sleep += row.sleep_seconds || 0;
          if (asleep) {
            stretch += 1; bestStretch = Math.max(bestStretch, stretch);
            if (bedtime === null && stretch >= 2) bedtime = t - BUCKET_SEC * 1000; // stretch began one bucket back
          } else stretch = 0;
        }
        if (covered >= 6) nights.push({ date: day.date, sleep, bedtime, bestStretch: bestStretch * BUCKET_SEC });
      });
      return nights;
    }

    const avg = values => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;

    function bedtimeMinutes(night) {
      if (night.bedtime === null) return null;
      const d = new Date(night.bedtime);
      let minutes = d.getHours() * 60 + d.getMinutes();
      if (minutes < 12 * 60) minutes += 24 * 60; // past-midnight bedtimes sort after evening ones
      return minutes;
    }

    function renderTiles(days, rollups) {
      const nights = nightlyAnalysis(days);
      if (!nights.length) return '';
      const week = nights.slice(-7), prior = nights.slice(-14, -7);

      const sleepNow = avg(week.map(n => n.sleep));
      const sleepBefore = avg(prior.map(n => n.sleep));
      const sleepDelta = sleepNow != null && sleepBefore != null ? sleepNow - sleepBefore : null;

      const bedtimes = week.map(bedtimeMinutes).filter(v => v !== null);
      const bedAvg = avg(bedtimes);
      const bedSpread = bedtimes.length > 1
        ? Math.sqrt(avg(bedtimes.map(v => (v - bedAvg) ** 2))) : null;

      const longest = Math.max(...week.map(n => n.bestStretch), 0);
      const longestNight = week.find(n => n.bestStretch === longest);

      const o2Week = avg(rollups.slice(-336).map(r => r.avg_oxygen_saturation).filter(v => v != null));
      const o2Prior = avg(rollups.slice(0, -336).map(r => r.avg_oxygen_saturation).filter(v => v != null));

      const deltaBadge = (delta, unit, invert = false) => {
        if (delta === null || Math.abs(delta) < 0.05) return '<span class="delta flat">→ steady</span>';
        const good = invert ? delta < 0 : delta > 0;
        const arrow = delta > 0 ? '↑' : '↓';
        return `<span class="delta ${good ? 'up' : 'down'}">${arrow} ${unit}</span>`;
      };

      const tiles = [];
      tiles.push(`<div class="tile"><h3>Sleep per night</h3>
        <b>${sleepNow != null ? fmtDur(sleepNow) : '—'}</b>${deltaBadge(sleepDelta, sleepDelta != null ? fmtDur(Math.abs(sleepDelta)) + ' vs last week' : '')}
        <p>Average over the last ${week.length} night${week.length === 1 ? '' : 's'}${prior.length ? ', compared with the week before' : ''}.</p></div>`);
      tiles.push(`<div class="tile"><h3>Typical bedtime</h3>
        <b>${bedAvg != null ? fmtClock(bedAvg % (24 * 60)) : '—'}</b>
        <p>${bedSpread != null ? (bedSpread <= 30
          ? `Remarkably consistent — within ±${Math.round(bedSpread)} minutes. A rhythm is forming.`
          : `Still drifting by about ±${Math.round(bedSpread)} minutes night to night.`)
          : 'First sustained sleep after 6 PM.'}</p></div>`);
      tiles.push(`<div class="tile"><h3>Longest stretch</h3>
        <b>${longest ? fmtDur(longest) : '—'}</b>
        <p>${longestNight && longest ? `Best unbroken sleep this week, on ${longestNight.date.toLocaleDateString([], { weekday: 'long' })} night.` : 'Longest unbroken sleep this week.'}</p></div>`);
      tiles.push(`<div class="tile"><h3>Oxygen baseline</h3>
        <b>${o2Week != null ? o2Week.toFixed(1) + '<small>%</small>' : '—'}</b>${o2Prior != null && o2Week != null ? deltaBadge(o2Week - o2Prior, Math.abs(o2Week - o2Prior).toFixed(1) + ' pts vs last week') : ''}
        <p>Average SpO₂ across the whole week, day and night.</p></div>`);
      return `<section><h2>What the pattern says</h2><div class="tiles">${tiles.join('')}</div></section>`;
    }

    async function boot() {
      let rollups = [], deviceName = null;
      try {
        const [rollupData, devices] = await Promise.all([
          fetch('/api/rollups?bucket=30m&hours=336&limit=100000').then(r => r.json()),
          fetch('/api/devices').then(r => r.json())
        ]);
        rollups = rollupData.rollups || [];
        const device = (devices.devices || [])[0];
        if (device) deviceName = device.baby_name || device.name;
      } catch (error) {
        el('content').innerHTML = '<div class="empty">Could not load readings — is the collector running?</div>';
        return;
      }
      if (deviceName) el('title').innerHTML = `The shape of <em>${deviceName}’s</em> days`;
      const days = dayGrid(rollups);
      if (!days.length) {
        el('content').innerHTML = `<div class="empty">Nothing to chart yet.<br/>
          Give it a night or two — each day of readings adds a row here.</div>`;
        return;
      }
      el('content').innerHTML = renderActogram(days) + renderTiles(days, rollups);
    }
    boot();
  </script>
</body>
</html>"""


def render_rhythms_page() -> str:
    return RHYTHMS_HTML
