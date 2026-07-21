"""'Rhythms' — a 14-day actogram and pattern reader, rendered through the shared
app shell. Editorial in light theme; the same structure holds up in dark.

Sections (each renders only when its data exists):
  actogram · O₂ dip map · pattern tiles · desat burden · baseline drift ·
  deep-sleep gap · on/off-O₂ report · feed response · challenge ledger ·
  battery wear
"""

from __future__ import annotations

from app.shell import render_shell

RHYTHMS_HEAD = """<style>
    h1 { font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
      font-size: clamp(34px, 5.4vw, 54px); line-height: 1.06; letter-spacing: -0.015em;
      font-weight: 600; max-width: 30ch; margin: 0; }
    h1 em { font-style: italic; color: var(--accent); }
    .lede { font-size: 16.5px; line-height: 1.6; color: var(--dim);
      margin: 18px 0 40px; }
    section { margin-bottom: 44px; }
    .acto-card { padding: 22px; overflow-x: auto; }
    table.acto { border-collapse: collapse; width: 100%; min-width: 680px; }
    table.acto th { font-size: 9.5px; font-weight: 500; color: var(--faint);
      padding: 0 0 8px; text-align: left; }
    table.acto td.day { font-size: 11px; color: var(--dim); padding-right: 12px;
      white-space: nowrap; font-variant-numeric: tabular-nums; }
    table.acto td.cell { height: 20px; padding: 1px; }
    table.acto td.cell i { display: block; width: 100%; height: 100%; border-radius: 3px; }
    tr.ribbon-row td { padding: 0 1px 3px; }
    .o2ribbon { position: relative; height: 3px; }
    .o2ribbon b { position: absolute; top: 0; height: 3px; border-radius: 2px;
      background: var(--accent); opacity: .55; }
    .acto-legend { display: flex; flex-wrap: wrap; gap: 18px; font-size: 12px;
      color: var(--dim); margin-top: 16px; }
    .acto-legend i { display: inline-block; width: 11px; height: 11px; border-radius: 3px;
      margin-right: 6px; vertical-align: -1px; }
    .acto-legend .rib { display: inline-block; width: 14px; height: 3px; border-radius: 2px;
      background: var(--accent); opacity: .55; margin-right: 6px; vertical-align: 2px; }
    .grad { display: inline-flex; vertical-align: -1px; margin-right: 6px; }
    .grad i { width: 11px; height: 11px; margin: 0; border-radius: 0; }
    .grad i:first-child { border-radius: 3px 0 0 3px; }
    .grad i:last-child { border-radius: 0 3px 3px 0; }
    .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }
    .wear-bars { display: flex; align-items: flex-end; gap: 8px; margin: 12px 0 4px;
      min-height: 96px; overflow-x: auto; padding-bottom: 4px; }
    .wear-bars .wb { flex: 1 0 auto; min-width: 34px; display: grid; justify-items: center;
      gap: 4px; align-content: end; }
    .wear-bars i { display: block; width: 100%; max-width: 34px;
      border-radius: 5px 5px 2px 2px; background: var(--accent-soft);
      border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); }
    .wear-bars b { font-size: 10.5px; color: var(--dim); font-weight: 500;
      font-variant-numeric: tabular-nums; }
    .wear-bars span { font-size: 10px; color: var(--faint); white-space: nowrap; }
    .wear-bars em.dip-floor { font-style: normal; font-size: 9.5px; color: var(--faint);
      font-variant-numeric: tabular-nums; white-space: nowrap; }
    .floor-warn { color: var(--warn) !important; font-weight: 700 !important; }
    .floor-bad { color: var(--bad) !important; font-weight: 700 !important; }

    /* day-prep vs night pairs */
    .prep-head { display: grid; grid-template-columns: 52px 1fr 1fr; gap: 10px;
      font-size: 10px; letter-spacing: .06em; text-transform: uppercase;
      color: var(--faint); margin-top: 12px; }
    .prep-rows { display: grid; gap: 9px; margin-top: 8px; }
    .prep-row { display: grid; grid-template-columns: 52px 1fr 1fr; gap: 10px;
      align-items: center; font-size: 11px; }
    .prep-day { color: var(--dim); white-space: nowrap; font-variant-numeric: tabular-nums; }
    .prep-cell { display: grid; gap: 3px; }
    .prep-track { position: relative; height: 8px; border-radius: 4px;
      background: color-mix(in srgb, var(--surface-line) 55%, transparent); overflow: hidden; }
    .prep-track i { position: absolute; top: 0; bottom: 0; left: 0; border-radius: 4px; }
    .prep-track.day i { background: color-mix(in srgb, var(--awake) 60%, var(--surface)); }
    .prep-track.night i { background: var(--accent); opacity: .72; }
    .prep-val { color: var(--faint); font-size: 10px; font-variant-numeric: tabular-nums; }
    .tile { padding: 20px; }
    .tile h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
      color: var(--faint); font-weight: 700; margin: 0 0 10px; }
    .tile b { font-size: 27px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
    .tile b small { font-size: 14px; color: var(--dim); font-weight: 500; }
    .tile p { font-size: 13px; color: var(--dim); line-height: 1.5; margin-top: 8px; }
    .tile .delta { font-size: 13px; font-weight: 600; margin-left: 8px; }
    .delta.up { color: var(--good); } .delta.down { color: var(--warn); } .delta.flat { color: var(--faint); }

    /* drift band */
    .drift-wrap { position: relative; margin-top: 12px; }
    .drift-wrap svg { display: block; width: 100%; height: 104px; }
    .drift-band { fill: var(--accent-soft); stroke: none; }
    .drift-line { fill: none; stroke: var(--accent); stroke-width: 1.7;
      vector-effect: non-scaling-stroke; stroke-linejoin: round; }
    .drift-hair { stroke: var(--faint); stroke-width: 1; stroke-dasharray: 3 4;
      vector-effect: non-scaling-stroke; }
    .drift-ylab { position: absolute; right: 3px; font-size: 10px; color: var(--faint);
      font-variant-numeric: tabular-nums; pointer-events: none; }
    .drift-axis { display: flex; justify-content: space-between; color: var(--faint);
      font-size: 10.5px; margin-top: 5px; font-variant-numeric: tabular-nums; }

    /* deep-sleep gap dumbbells */
    .gap-rows { display: grid; gap: 9px; margin-top: 12px; }
    .gap-row { display: grid; grid-template-columns: 64px 1fr 44px; gap: 12px;
      align-items: center; font-size: 11.5px; }
    .gap-day { color: var(--dim); white-space: nowrap; font-variant-numeric: tabular-nums; }
    .gap-track { position: relative; height: 14px; }
    .gap-track::before { content: ''; position: absolute; left: 0; right: 0; top: 6.5px;
      height: 1px; background: var(--surface-line); }
    .gap-line { position: absolute; top: 6px; height: 2px; background: var(--faint);
      opacity: .6; border-radius: 1px; }
    .gap-dot { position: absolute; top: 3px; width: 8px; height: 8px; border-radius: 50%;
      transform: translateX(-50%); }
    .gap-dot.awake { background: var(--awake); }
    .gap-dot.deep { background: var(--sleep-deep); }
    .gap-row b { text-align: right; font-size: 12px; color: var(--dim);
      font-variant-numeric: tabular-nums; font-weight: 600; }

    /* on/off O₂ report */
    .report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 640px) { .report-grid { grid-template-columns: 1fr; } }
    .report-row { display: flex; justify-content: space-between; gap: 12px;
      padding: 8px 0; border-bottom: 1px solid var(--surface-line); font-size: 13px; }
    .report-row:last-of-type { border-bottom: 0; }
    .report-row b { font-size: 14px; font-variant-numeric: tabular-nums; }

    /* feed response */
    .feed-wrap { position: relative; margin-top: 12px; }
    .feed-wrap svg { display: block; width: 100%; height: 104px; }

    /* challenge ledger */
    .ledger { display: grid; gap: 10px; margin-top: 12px; }
    .ledger-row { display: grid; grid-template-columns: 72px 1fr; gap: 4px 12px;
      align-items: center; font-size: 11.5px; }
    .ledger-date { color: var(--dim); white-space: nowrap; font-variant-numeric: tabular-nums; }
    .ledger-track { position: relative; height: 10px; }
    .ledger-track i { display: block; height: 10px; border-radius: 5px;
      background: var(--accent-soft);
      border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent); }
    .ledger-meta { grid-column: 2; color: var(--faint); font-size: 10.5px;
      font-variant-numeric: tabular-nums; }
    .ledger-meta em { font-style: normal; font-weight: 700; }
    .ledger-meta em.up { color: var(--good); }
    .ledger-meta em.down { color: var(--warn); }

    /* feed rhythm dot map */
    .feedmap { display: grid; gap: 3px; margin-top: 4px; }
    .feedmap-row { display: grid; grid-template-columns: 52px 1fr 56px; gap: 10px;
      align-items: center; }
    .feedmap-row svg { display: block; width: 100%; height: 20px; }
    .feedmap-head { margin-top: 10px; color: var(--faint); }
    .feedmap-day { font-size: 10.5px; color: var(--dim); white-space: nowrap;
      font-variant-numeric: tabular-nums; }
    .feedmap-total { font-size: 11px; text-align: right; font-variant-numeric: tabular-nums;
      color: var(--dim); font-weight: 600; }
    .fs-track { stroke: var(--surface-line); stroke-width: 1.2; }
    .fm-bottle { fill: var(--accent); opacity: .85; }
    .fm-nurse { fill: none; stroke: var(--accent); stroke-width: 1.8; }
    .fm-solid { fill: var(--awake); opacity: .9; }
    .empty { text-align: center; color: var(--dim); padding: 60px 20px; font-size: 15px;
      border: 1px dashed var(--surface-line); border-radius: var(--radius-card); }
    /* sleep scale + cell colors come straight from theme tokens */
  </style>"""

RHYTHMS_BODY = """<h1 id="title">The shape of <em>the days</em></h1>
    <p class="lede" id="lede">Every row is a day, every column a half-hour. Purple is sleep
      (darker = deeper), amber is awake, blank is no signal. Over weeks, a rhythm emerges —
      this page is where you watch it happen.</p>
    <div id="content"></div>"""

RHYTHMS_SCRIPTS = """<script>
    const BUCKET_MIN = 30;
    const BUCKET_SEC = BUCKET_MIN * 60;
    const COLS = 48;
    const el = id => document.getElementById(id);
    const pad = n => String(n).padStart(2, '0');
    const fmtDur = seconds => {
      const totalMinutes = Math.round(seconds / 60);
      const h = Math.floor(totalMinutes / 60), m = totalMinutes % 60;
      return h ? `${h}h ${pad(m)}m` : `${m}m`;
    };
    const fmtClock = minutesFromMidnight => {
      let h = Math.floor(minutesFromMidnight / 60) % 24; const m = pad(Math.round(minutesFromMidnight % 60));
      const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
      return `${h}:${m} ${ap}`;
    };
    const avg = values => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    const median = values => {
      if (!values.length) return null;
      const s = [...values].sort((a, b) => a - b); const m = s.length >> 1;
      return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
    };
    const section = (title, inner) => `<section><h2 class="section-title">${title}</h2>${inner}</section>`;
    const DOW = 'SMTWTFS';

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
      if (fraction > .85) return 'var(--sleep-deep)';
      if (fraction > .6) return 'var(--accent)';
      if (fraction > .3) return 'var(--sleep-light)';
      return 'var(--accent-soft)';
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

    // ----- supplemental-O₂ intervals from care events -------------------------
    function o2Intervals(events, t0, t1) {
      const marks = events
        .filter(e => e.kind === 'O₂ on' || e.kind === 'O₂ off')
        .map(e => ({ t: e.t, on: e.kind === 'O₂ on' }))
        .sort((a, b) => a.t - b.t);
      const out = [];
      let openStart = null;
      for (const mark of marks) {
        if (mark.on) { if (openStart == null) openStart = mark.t; }
        else if (openStart != null) { out.push({ start: openStart, end: mark.t }); openStart = null; }
        else out.push({ start: t0, end: mark.t });   // 'off' whose 'on' predates the window
      }
      if (openStart != null) out.push({ start: openStart, end: t1 });
      return out.filter(iv => iv.end > iv.start);
    }
    const onO2At = (ivs, t) => ivs.some(iv => t >= iv.start && t <= iv.end);

    function ribbonRow(day, ivs) {
      const d0 = day.date.getTime(), d1 = d0 + 86400e3;
      const segs = ivs.filter(iv => iv.end > d0 && iv.start < d1).map(iv => {
        const left = ((Math.max(iv.start, d0) - d0) / 86400e3) * 100;
        const width = ((Math.min(iv.end, d1) - Math.max(iv.start, d0)) / 86400e3) * 100;
        return `<b style="left:${left.toFixed(2)}%;width:${Math.max(width, 0.4).toFixed(2)}%" title="on supplemental O₂"></b>`;
      }).join('');
      return segs ? `<tr class="ribbon-row"><td></td><td colspan="${COLS}"><div class="o2ribbon">${segs}</div></td></tr>` : '';
    }

    function actogramTable(days, ivs, colorOf, titleOf, labelOf) {
      const headers = ['<th></th>'];
      for (let h = 0; h < 24; h += 3) headers.push(`<th colspan="6">${fmtClock(h * 60)}</th>`);
      const rows = days.map(day => {
        const cells = day.cells.map((row, col) => {
          const focus = encodeURIComponent(new Date(day.date.getTime() + col * BUCKET_SEC * 1000).toISOString());
          const label = labelOf ? `&label=${encodeURIComponent(labelOf(day, col, row))}` : '';
          return `<td class="cell"><a href="/data?focus=${focus}&span=120${label}" style="display:block;height:100%"><i style="background:${colorOf(row)}" title="${titleOf(day, col, row)}"></i></a></td>`;
        }).join('');
        const label = day.date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
        return `<tr><td class="day">${label}</td>${cells}</tr>` + ribbonRow(day, ivs);
      }).join('');
      return `<table class="acto"><tr>${headers.join('')}</tr>${rows}</table>`;
    }

    const RIBBON_LEGEND = '<span><span class="rib"></span>On supplemental O₂</span>';

    function renderActogram(days, ivs) {
      return section('Two weeks, half-hour by half-hour',
        `<div class="acto-card card">${actogramTable(days, ivs, cellColor, cellTitle)}
        <div class="acto-legend">
          <span><span class="grad"><i style="background:var(--accent-soft)"></i><i style="background:var(--sleep-light)"></i><i style="background:var(--accent)"></i><i style="background:var(--sleep-deep)"></i></span>Sleep (light → deep)</span>
          <span><i style="background:var(--awake)"></i>Awake</span>
          <span><i style="background:var(--nodata)"></i>No signal</span>
          ${ivs.length ? RIBBON_LEGEND : ''}
        </div></div>`);
    }

    // ----- #1: O₂ dip map ------------------------------------------------------
    function dipColor(row) {
      if (!row || row.min_oxygen_saturation == null) return 'var(--nodata)';
      const v = row.min_oxygen_saturation;
      if (v < O2.critical) return 'var(--bad)';
      if (v < O2.warn) return 'var(--warn)';
      if (v < O2.warn + SOFT_BAND) return 'color-mix(in srgb, var(--warn) 28%, var(--surface))';
      return 'color-mix(in srgb, var(--good) 10%, var(--surface))';
    }
    function dipTitle(day, col, row) {
      const when = `${day.date.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${fmtClock(col * 30)}`;
      if (!row || row.min_oxygen_saturation == null) return `${when} — no signal`;
      return `${when} — low ${Math.round(row.min_oxygen_saturation)}%`;
    }
    function renderDipMap(days, ivs) {
      const any = days.some(day => day.cells.some(row => row && row.min_oxygen_saturation != null));
      if (!any) return '';
      return section('Where the dips live',
        `<div class="acto-card card">${actogramTable(days, ivs, dipColor, dipTitle,
          (day, col, row) => row && row.min_oxygen_saturation != null ? `Low ${Math.round(row.min_oxygen_saturation)}%` : 'This half-hour')}
        <div class="acto-legend">
          <span><i style="background:color-mix(in srgb, var(--good) 10%, var(--surface))"></i>Fine (≥${O2.warn + SOFT_BAND}%)</span>
          <span><i style="background:color-mix(in srgb, var(--warn) 28%, var(--surface))"></i>Soft (${O2.warn}–${O2.warn + SOFT_BAND}%)</span>
          <span><i style="background:var(--warn)"></i>Dip (&lt;${O2.warn}%)</span>
          <span><i style="background:var(--bad)"></i>Deep dip (&lt;${O2.critical}%)</span>
          ${ivs.length ? RIBBON_LEGEND : ''}
        </div>
        <p class="tile" style="padding:10px 0 0; font-size:13px; color:var(--dim)">Each cell is that half-hour's <b style="font-size:13px">lowest</b> reading. Recurring desats line up in columns — a 3 AM sag shows as a vertical stripe.</p>
        </div>`);
    }

    // ----- nights helper (user's night window, keyed by the evening's date) ----
    // Defaults 7 PM → 7 AM; overwritten from preferences in boot().
    // Oxygen severity tiers from settings; SOFT_BAND is the width of the
    // "nearly fine" wash that sits just above the warning tier on the heatmap.
    const SOFT_BAND = 2;
    let O2 = window.owletO2(null);
    let NIGHT = { start: 19 * 60, end: 7 * 60 };
    let BIRTH = null;   // ISO 'YYYY-MM-DD' once known, for age-adjusted framing
    let FEEDS = true;   // feed-tracking preference gates the feed sections

    function ageContext() {
      if (!BIRTH) return '';
      const birth = new Date(BIRTH + 'T00:00:00');
      if (isNaN(birth)) return '';
      const days = Math.floor((Date.now() - birth) / 86400000);
      if (days < 0) return '';
      const weeks = Math.floor(days / 7), months = Math.floor(days / 30.44);
      if (weeks < 6) return ` At ${weeks} week${weeks === 1 ? '' : 's'} old, a clear day-night rhythm usually hasn't emerged yet — it typically begins around 6 weeks.`;
      if (weeks <= 16) return ` At ${weeks} weeks she's right in the 6–16 week window when the body clock switches on and night sleep consolidates fastest.`;
      return ` At ${months} month${months === 1 ? '' : 's'}, a consolidated night is typical — steadier and higher is better.`;
    }
    function nightWindowFrom(prefs) {
      const toMin = (value, fallback) => {
        const m = /^([01]?\\d|2[0-3]):([0-5]\\d)$/.exec(value || '');
        return m ? Number(m[1]) * 60 + Number(m[2]) : fallback;
      };
      const win = { start: toMin(prefs.night_start, 19 * 60), end: toMin(prefs.night_end, 7 * 60) };
      return win.start > win.end ? win : { start: 19 * 60, end: 7 * 60 }; // night must cross midnight
    }
    function nightOf(t) {
      const d = new Date(t);
      const mins = d.getHours() * 60 + d.getMinutes();
      if (mins >= NIGHT.start) return new Date(d.getFullYear(), d.getMonth(), d.getDate());
      if (mins < NIGHT.end) return new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1);
      return null;
    }

    // ----- circadian consolidation: how much sleep has moved into the night ----
    // A newborn sleeps evenly around the clock (~50% at night). As the melatonin
    // rhythm switches on (~6–16 weeks), more sleep migrates into the night. This
    // charts that migration — the strongest science-to-signal fit we have.
    function renderCircadian(r5, name) {
      const byDay = new Map();
      for (const row of r5) {
        const sleep = row.sleep_seconds || 0;
        const signal = sleep + (row.awake_seconds || 0);
        if (signal <= 0) continue;
        const t = new Date(row.bucket_start);
        const key = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`;
        const mins = t.getHours() * 60 + t.getMinutes();
        const isNight = mins >= NIGHT.start || mins < NIGHT.end;
        const rec = byDay.get(key) || { date: new Date(t.getFullYear(), t.getMonth(), t.getDate()), night: 0, day: 0, buckets: 0 };
        if (isNight) rec.night += sleep; else rec.day += sleep;
        rec.buckets += 1;
        byDay.set(key, rec);
      }
      const days = [...byDay.values()]
        .filter(d => (d.night + d.day) >= 3 * 3600 && d.buckets >= 96) // ≥3h sleep, ≥8h signal
        .map(d => ({ date: d.date, share: d.night / (d.night + d.day) }))
        .sort((a, b) => a.date - b.date).slice(-56);
      if (days.length < 5) return '';
      const W = 360, H = 100, lo = 0.4, hi = 1.0;
      const x = i => (i / (days.length - 1)) * W;
      const y = v => H - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * H;
      const line = days.map((d, i) => `${x(i).toFixed(1)},${y(d.share).toFixed(1)}`).join(' ');
      const evenY = y(0.5).toFixed(1);
      const half = Math.max(1, Math.floor(days.length / 3));
      const early = avg(days.slice(0, half).map(d => d.share));
      const late = avg(days.slice(-half).map(d => d.share));
      const who = name ? name + '’s' : 'her';
      let note = `About ${Math.round(late * 100)}% of ${who} sleep now lands at night`;
      if (early != null && late != null && late - early > 0.04) note += `, up from ${Math.round(early * 100)}% at the start of this window — her body clock is organizing.`;
      else if (early != null && late != null && early - late > 0.04) note += `, down from ${Math.round(early * 100)}% here — single weeks bounce around, so watch the longer trend.`;
      else note += `, holding about steady across this window.`;
      return section('Day-night rhythm',
        `<div class="tile card"><h3>Share of sleep that happens at night — last ${days.length} days</h3>
        <div class="drift-wrap">
          <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
            <line x1="0" x2="${W}" y1="${evenY}" y2="${evenY}" class="drift-hair"/>
            <polyline points="${line}" class="drift-line"/>
          </svg>
          <span class="drift-ylab" style="top:0">100%</span>
          <span class="drift-ylab" style="bottom:0">40%</span>
        </div>
        <div class="drift-axis"><span>${days[0].date.toLocaleDateString([], { month: 'short', day: 'numeric' })}</span><span>${days[days.length - 1].date.toLocaleDateString([], { month: 'short', day: 'numeric' })}</span></div>
        <p>The dashed line is 50% — sleep spread evenly around the clock, like a newborn with no rhythm yet. As the body clock matures, more sleep climbs above it into the night. ${note}${ageContext()}</p></div>`);
    }

    // ----- day prep vs night sleep ---------------------------------------------
    // The question this answers: "has she been awake enough today to sleep
    // well tonight?" Pairs each day's awake time with that night's sleep.
    function renderDayPrep(r5) {
      const dateKey = d => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      const dayAgg = new Map(), nightAgg = new Map();
      for (const row of r5) {
        const t = new Date(row.bucket_start);
        const mins = t.getHours() * 60 + t.getMinutes();
        const signal = (row.awake_seconds || 0) + (row.sleep_seconds || 0) > 0;
        if (mins >= NIGHT.end && mins < NIGHT.start) {
          const key = dateKey(t);
          const rec = dayAgg.get(key) || { date: new Date(t.getFullYear(), t.getMonth(), t.getDate()), awake: 0, buckets: 0 };
          rec.awake += row.awake_seconds || 0;
          if (signal) rec.buckets += 1;
          dayAgg.set(key, rec);
        } else {
          const nightDate = nightOf(t.getTime());
          if (!nightDate) continue;
          const key = dateKey(nightDate);
          const rec = nightAgg.get(key) || { sleep: 0, buckets: 0 };
          rec.sleep += row.sleep_seconds || 0;
          if (signal) rec.buckets += 1;
          nightAgg.set(key, rec);
        }
      }
      const pairs = [...dayAgg.entries()]
        .map(([key, day]) => ({ ...day, night: nightAgg.get(key) }))
        .filter(p => p.buckets >= 60 && p.night && p.night.buckets >= 60) // ≥5h signal each side
        .sort((a, b) => a.date - b.date).slice(-10);
      if (pairs.length < 5) return '';
      const maxAwake = Math.max(...pairs.map(p => p.awake), 1);
      const maxSleep = Math.max(...pairs.map(p => p.night.sleep), 1);
      const rows = pairs.map(p => `<div class="prep-row">
        <span class="prep-day">${p.date.toLocaleDateString([], { weekday: 'short', day: 'numeric' })}</span>
        <span class="prep-cell"><span class="prep-track day"><i style="width:${((p.awake / maxAwake) * 100).toFixed(1)}%"></i></span><span class="prep-val">${fmtDur(p.awake)}</span></span>
        <span class="prep-cell"><span class="prep-track night"><i style="width:${((p.night.sleep / maxSleep) * 100).toFixed(1)}%"></i></span><span class="prep-val">${fmtDur(p.night.sleep)}</span></span>
      </div>`).join('');
      const sorted = [...pairs].sort((a, b) => a.awake - b.awake);
      const half = Math.floor(pairs.length / 2);
      const quiet = avg(sorted.slice(0, half).map(p => p.night.sleep));
      const busy = avg(sorted.slice(pairs.length - half).map(p => p.night.sleep));
      const diff = busy != null && quiet != null ? busy - quiet : null;
      const note = diff == null || Math.abs(diff) < 900
        ? 'No clear link yet between daytime awake hours and night sleep — more days will sharpen this.'
        : diff > 0
          ? `Busier days are earning their keep: the most-awake days bought about ${fmtDur(diff)} more night sleep than the quietest.`
          : `More awake time hasn't meant more night sleep — the busiest days actually slept about ${fmtDur(-diff)} less. Overtiredness may be in play.`;
      return section('Does the day set up the night?',
        `<div class="tile card"><h3>Awake by day, asleep by night</h3>
        <div class="prep-head"><span></span><span>Awake ${fmtClock(NIGHT.end)}–${fmtClock(NIGHT.start)}</span><span>Sleep that night</span></div>
        <div class="prep-rows">${rows}</div>
        <p>Each row is one day: how much awake time it held, and how the following night went. ${note}</p></div>`);
    }

    // ----- #3: desat burden per night ------------------------------------------
    function renderDesatBurden(r5) {
      const nights = new Map();
      let lastKey = null, lastLow = false;
      for (const row of r5) {
        if (row.min_oxygen_saturation == null) { lastLow = false; continue; }
        const t = Date.parse(row.bucket_start);
        const nightDate = nightOf(t);
        if (!nightDate) { lastLow = false; continue; }
        const key = `${nightDate.getFullYear()}-${nightDate.getMonth()}-${nightDate.getDate()}`;
        const rec = nights.get(key) || { date: nightDate, dips: 0, floor: 100, buckets: 0 };
        rec.buckets += 1;
        rec.floor = Math.min(rec.floor, row.min_oxygen_saturation);
        const low = row.min_oxygen_saturation < O2.warn;
        if (low && !(lastLow && lastKey === key)) rec.dips += 1;
        lastLow = low; lastKey = key;
        nights.set(key, rec);
      }
      const list = [...nights.values()].filter(n => n.buckets >= 24)
        .sort((a, b) => a.date - b.date).slice(-14);
      if (list.length < 2) return '';
      const maxDips = Math.max(...list.map(n => n.dips), 1);
      const bars = list.map(n => {
        const tint = n.floor < O2.critical ? 'var(--bad)' : 'var(--warn)';
        const floorClass = n.floor < O2.critical ? 'floor-bad' : n.floor < O2.warn ? 'floor-warn' : '';
        return `<div class="wb">
        <b>${n.dips}</b>
        <i style="height:${Math.max(5, (n.dips / maxDips) * 64).toFixed(0)}px; background: color-mix(in srgb, ${tint} 26%, var(--surface)); border-color: color-mix(in srgb, ${tint} 55%, transparent)"></i>
        <span>${n.date.toLocaleDateString([], { weekday: 'short' })} ${n.date.getDate()}</span>
        <em class="dip-floor ${floorClass}">low ${Math.round(n.floor)}%</em></div>`;
      }).join('');
      const week = list.slice(-7), prior = list.slice(0, -7);
      const now = avg(week.map(n => n.dips)), before = avg(prior.map(n => n.dips));
      let note = `Each bar counts that night’s dip episodes below ${O2.warn}% — taller means a busier night. Under each night sits its lowest reading; a red bar means the floor went under ${O2.critical}%.`;
      if (now != null && before != null) {
        const diff = Math.round((now - before) * 10) / 10;
        note += diff <= -0.5 ? ` Averaging ${-diff} fewer episodes per night than the week before.`
          : diff >= 0.5 ? ` Averaging ${diff} more episodes per night than the week before.`
          : ' Holding about even with the week before.';
      }
      return section('Desat burden, night by night',
        `<div class="tile card"><h3>Dip episodes below ${O2.warn}% per night</h3>
        <div class="wear-bars">${bars}</div><p>${note}</p></div>`);
    }

    // ----- #7: baseline drift ---------------------------------------------------
    function renderBaselineDrift(r5) {
      const byDay = new Map();
      for (const row of r5) {
        if (row.avg_oxygen_saturation == null) continue;
        const t = new Date(row.bucket_start);
        const key = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`;
        if (!byDay.has(key)) byDay.set(key, { date: new Date(t.getFullYear(), t.getMonth(), t.getDate()), values: [] });
        byDay.get(key).values.push(row.avg_oxygen_saturation);
      }
      const daysArr = [...byDay.values()].filter(d => d.values.length >= 24)
        .sort((a, b) => a.date - b.date).slice(-30);
      if (daysArr.length < 3) return '';
      const q = (values, p) => { const s = [...values].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
      const pts = daysArr.map((d, i) => ({ i, p5: q(d.values, 0.05), p50: q(d.values, 0.5), p95: q(d.values, 0.95) }));
      const lo = Math.min(...pts.map(p => p.p5)) - 0.4, hi = Math.max(...pts.map(p => p.p95)) + 0.4;
      const W = 360, H = 100;
      const x = i => (i / (pts.length - 1)) * W;
      const y = v => H - ((v - lo) / (hi - lo)) * H;
      const band = pts.map(p => `${x(p.i).toFixed(1)},${y(p.p95).toFixed(1)}`).join(' ')
        + ' ' + [...pts].reverse().map(p => `${x(p.i).toFixed(1)},${y(p.p5).toFixed(1)}`).join(' ');
      const line = pts.map(p => `${x(p.i).toFixed(1)},${y(p.p50).toFixed(1)}`).join(' ');
      const drift = pts[pts.length - 1].p50 - pts[0].p50;
      const note = Math.abs(drift) < 0.3
        ? 'Flat for now — drift shows up over weeks, not days.'
        : drift > 0 ? `Up ${drift.toFixed(1)} points across the window — slow, steady progress.`
        : `Down ${Math.abs(drift).toFixed(1)} points across the window.`;
      return section('Baseline drift',
        `<div class="tile card"><h3>Daily median SpO₂ — last ${pts.length} days</h3>
        <div class="drift-wrap">
          <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
            <polygon points="${band}" class="drift-band"/>
            <polyline points="${line}" class="drift-line"/>
          </svg>
          <span class="drift-ylab" style="top:0">${hi.toFixed(0)}</span>
          <span class="drift-ylab" style="bottom:0">${lo.toFixed(0)}</span>
        </div>
        <div class="drift-axis"><span>${daysArr[0].date.toLocaleDateString([], { month: 'short', day: 'numeric' })}</span><span>${daysArr[daysArr.length - 1].date.toLocaleDateString([], { month: 'short', day: 'numeric' })}</span></div>
        <p>The band spans each day's 5th–95th percentile; the line is the median. ${note}</p></div>`);
    }

    // ----- #8: deep-sleep O₂ gap -------------------------------------------------
    function renderDeepGap(r5) {
      const B5 = 300;
      const nights = new Map();
      for (const row of r5) {
        if (row.avg_oxygen_saturation == null) continue;
        const t = Date.parse(row.bucket_start);
        const nightDate = nightOf(t);
        if (!nightDate) continue;
        const key = `${nightDate.getFullYear()}-${nightDate.getMonth()}-${nightDate.getDate()}`;
        const rec = nights.get(key) || { date: nightDate, deep: [], awake: [] };
        if ((row.deep_sleep_seconds || 0) > B5 * 0.6) rec.deep.push(row.avg_oxygen_saturation);
        else if ((row.awake_seconds || 0) > B5 * 0.6) rec.awake.push(row.avg_oxygen_saturation);
        nights.set(key, rec);
      }
      const list = [...nights.values()]
        .map(n => ({ date: n.date, deep: median(n.deep), awake: median(n.awake) }))
        .filter(n => n.deep != null && n.awake != null)
        .sort((a, b) => a.date - b.date).slice(-10);
      if (list.length < 2) return '';
      const values = list.flatMap(n => [n.deep, n.awake]);
      const lo = Math.min(...values) - 0.5, hi = Math.max(...values) + 0.5;
      const pct = v => (((v - lo) / (hi - lo)) * 100);
      const rows = list.map(n => {
        const a = pct(n.awake), d = pct(n.deep);
        return `<div class="gap-row">
          <span class="gap-day">${n.date.toLocaleDateString([], { weekday: 'short', day: 'numeric' })}</span>
          <span class="gap-track">
            <i class="gap-line" style="left:${Math.min(a, d).toFixed(1)}%;width:${Math.abs(a - d).toFixed(1)}%"></i>
            <i class="gap-dot awake" style="left:${a.toFixed(1)}%" title="awake ${n.awake.toFixed(1)}%"></i>
            <i class="gap-dot deep" style="left:${d.toFixed(1)}%" title="deep sleep ${n.deep.toFixed(1)}%"></i>
          </span>
          <b class="${n.deep < n.awake - 1.5 ? 'floor-warn' : ''}">${(n.deep - n.awake).toFixed(1)}</b>
        </div>`;
      }).join('');
      const meanGap = avg(list.map(n => n.deep - n.awake));
      const note = meanGap != null && meanGap < -1
        ? `Runs about ${Math.abs(meanGap).toFixed(1)} points lower in deep sleep — worth mentioning at the next appointment.`
        : 'No meaningful state-dependent drop in this window.';
      return section('Deep-sleep O₂ gap',
        `<div class="tile card"><h3>Awake vs deep sleep, per night</h3>
        <div class="gap-rows">${rows}</div>
        <p>Amber dot = median SpO₂ while awake, violet = in deep sleep; the number is the difference. ${note}</p></div>`);
    }

    // ----- #5: on-O₂ vs off-O₂ report -------------------------------------------
    function renderO2Report(r5, ivs) {
      if (!ivs.length) return '';
      const make = () => ({ o2: [], lowSeconds: 0, spanSeconds: 0, dips: 0, floor: null });
      const groups = { on: make(), off: make() };
      let lastGroup = null, lastLow = false;
      for (const row of r5) {
        if (row.avg_oxygen_saturation == null) { lastLow = false; continue; }
        const mid = Date.parse(row.bucket_start) + 150000;
        const g = onO2At(ivs, mid) ? 'on' : 'off';
        const rec = groups[g];
        rec.o2.push(row.avg_oxygen_saturation);
        rec.lowSeconds += row.low_oxygen_seconds || 0;
        rec.spanSeconds += 300;
        if (row.min_oxygen_saturation != null) {
          rec.floor = rec.floor == null ? row.min_oxygen_saturation : Math.min(rec.floor, row.min_oxygen_saturation);
          const low = row.min_oxygen_saturation < O2.warn;
          if (low && !(lastLow && lastGroup === g)) rec.dips += 1;
          lastLow = low; lastGroup = g;
        }
      }
      if (groups.on.spanSeconds < 2 * 3600 || groups.off.spanSeconds < 2 * 3600) return '';
      const column = (label, rec) => {
        const hours = rec.spanSeconds / 3600;
        return `<div class="tile card"><h3>${label} — ${fmtDur(rec.spanSeconds)}</h3>
          <div class="report-row"><span>Median SpO₂</span><b>${median(rec.o2).toFixed(1)}%</b></div>
          <div class="report-row"><span>Dips &lt;${O2.warn}% per hour</span><b>${(rec.dips / hours).toFixed(2)}</b></div>
          <div class="report-row"><span>Time under ${O2.warn}%</span><b>${((rec.lowSeconds / rec.spanSeconds) * 100).toFixed(1)}%</b></div>
          <div class="report-row"><span>Floor</span><b class="${rec.floor < O2.critical ? 'floor-bad' : rec.floor < O2.warn ? 'floor-warn' : ''}">${Math.round(rec.floor)}%</b></div>
        </div>`;
      };
      return section('On oxygen vs off',
        `<div class="report-grid">${column('On supplemental O₂', groups.on)}${column('Off O₂', groups.off)}</div>
        <p class="lede" style="font-size:13px; margin:10px 2px 0; color:var(--faint)">Computed from your logged O₂ on/off events over the last two weeks — the comparison to bring to the next appointment.</p>`);
    }

    // ----- feed rhythm: the Huckleberry view — when and how much, day by day ----
    function renderFeedRhythm(events) {
      if (!FEEDS) return '';
      const feeds = events.filter(e => e.kind === 'Feeding');
      if (feeds.length < 3) return '';
      const ML_PER_OZ = 29.5735;
      const byDay = new Map();
      feeds.forEach(f => {
        const d = new Date(f.t);
        const key = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
        if (!byDay.has(key)) byDay.set(key, []);
        byDay.get(key).push(f);
      });
      const days = [...byDay.entries()].sort((a, b) => a[0] - b[0]).slice(-14);
      const maxMl = Math.max(...feeds.map(f => f.amount_ml || 0), 4 * ML_PER_OZ);
      const W = 288;
      const rows = days.map(([dayStart, list]) => {
        const date = new Date(dayStart);
        const x = t => ((t - dayStart) / 86400000) * W;
        const marks = list.map(f => {
          const title = `<title>${new Date(f.t).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</title>`;
          if (f.method === 'nursing') {
            const r = (3 + 3 * Math.min(1, (f.duration_min || 10) / 30)).toFixed(1);
            return `<circle cx="${x(f.t).toFixed(1)}" cy="10" r="${r}" class="fm-nurse">${title}</circle>`;
          }
          if (f.method === 'solids') {
            return `<rect x="${(x(f.t) - 2.8).toFixed(1)}" y="7.2" width="5.6" height="5.6" rx="1.4" class="fm-solid">${title}</rect>`;
          }
          const r = (2.6 + 4 * Math.sqrt(Math.min(1, (f.amount_ml || 2 * ML_PER_OZ) / maxMl))).toFixed(1);
          return `<circle cx="${x(f.t).toFixed(1)}" cy="10" r="${r}" class="fm-bottle">${title}</circle>`;
        }).join('');
        const ml = list.reduce((a, f) => a + (f.amount_ml || 0), 0);
        const ozText = ml ? (Math.round((ml / ML_PER_OZ) * 2) / 2) + ' oz' : list.length + '×';
        return `<div class="feedmap-row">
          <span class="feedmap-day">${date.toLocaleDateString([], { weekday: 'short', day: 'numeric' })}</span>
          <svg viewBox="0 0 ${W} 20" preserveAspectRatio="none"><line x1="0" x2="${W}" y1="10" y2="10" class="fs-track"/>${marks}</svg>
          <b class="feedmap-total">${ozText}</b>
        </div>`;
      }).join('');
      const perDay = days.map(([, list]) => list.length);
      const avgCount = Math.round(avg(perDay) * 10) / 10;
      const dayOz = days.map(([, list]) => list.reduce((a, f) => a + (f.amount_ml || 0), 0)).filter(v => v > 0);
      const avgOz = dayOz.length >= 2 ? Math.round((avg(dayOz) / ML_PER_OZ) * 2) / 2 : null;
      const times = feeds.map(f => f.t).sort((a, b) => a - b);
      const gapsMs = [];
      for (let i = 1; i < times.length; i++) {
        const gap = times[i] - times[i - 1];
        if (gap > 20 * 60000 && gap < 8 * 3600000) gapsMs.push(gap);
      }
      const gapText = gapsMs.length >= 3 ? fmtDur(median(gapsMs) / 1000) : null;
      let note = `Averaging ${avgCount} feed${avgCount === 1 ? '' : 's'}${avgOz ? ` and ${avgOz} oz` : ''} a day`;
      note += gapText ? `, typically ~${gapText} apart.` : '.';
      return section('Feed rhythm',
        `<div class="tile card"><h3>When and how much, day by day</h3>
        <div class="feedmap-row feedmap-head"><span></span>
          <div class="drift-axis" style="margin:0"><span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>12 AM</span></div><b></b></div>
        <div class="feedmap">${rows}</div>
        <p>Dot size is the bottle's ounces; rings are nursing (sized by minutes); squares are solids.
        ${note} Over weeks, feeds drifting into a pattern here usually shows up as steadier nights above.</p></div>`);
    }

    // ----- #6: feed-aligned O₂ response -----------------------------------------
    function renderFeedResponse(r5, events) {
      if (!FEEDS) return '';
      const feeds = events.filter(e => e.kind === 'Feeding');
      if (feeds.length < 3) return '';
      const byBucket = new Map();
      for (const row of r5) {
        if (row.avg_oxygen_saturation != null) byBucket.set(Math.floor(Date.parse(row.bucket_start) / 300000), row.avg_oxygen_saturation);
      }
      const offsets = [];
      for (let m = -30; m <= 60; m += 5) offsets.push(m);
      const series = offsets.map(m => {
        const values = feeds.map(f => byBucket.get(Math.floor((f.t + m * 60000) / 300000))).filter(v => v != null);
        return values.length >= Math.max(2, Math.ceil(feeds.length / 2)) ? median(values) : null;
      });
      const valid = series.filter(v => v != null);
      if (valid.length < 12) return '';
      const lo = Math.min(...valid) - 0.4, hi = Math.max(...valid) + 0.4;
      const W = 360, H = 100;
      const x = i => (i / (offsets.length - 1)) * W;
      const y = v => H - ((v - lo) / (hi - lo)) * H;
      let segments = [], run = [];
      series.forEach((v, i) => {
        if (v == null) { if (run.length > 1) segments.push(run); run = []; return; }
        run.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`);
      });
      if (run.length > 1) segments.push(run);
      const lines = segments.map(seg => `<polyline points="${seg.join(' ')}" class="drift-line"/>`).join('');
      const zeroX = x(offsets.indexOf(0)).toFixed(1);
      const before = avg(offsets.map((m, i) => m < 0 ? series[i] : null).filter(v => v != null));
      const after = avg(offsets.map((m, i) => (m >= 5 && m <= 30) ? series[i] : null).filter(v => v != null));
      const note = before != null && after != null && before - after > 0.8
        ? `Feeds pull her down about ${(before - after).toFixed(1)} points in the half-hour after — a known pattern in O₂-dependent infants, worth watching during feeds.`
        : 'No consistent feed-associated drop in this window.';
      return section('Around feeds',
        `<div class="tile card"><h3>Median SpO₂ around ${feeds.length} logged feeds</h3>
        <div class="feed-wrap">
          <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
            <line x1="${zeroX}" x2="${zeroX}" y1="0" y2="${H}" class="drift-hair"/>
            ${lines}
          </svg>
          <span class="drift-ylab" style="top:0">${hi.toFixed(0)}</span>
          <span class="drift-ylab" style="bottom:0">${lo.toFixed(0)}</span>
        </div>
        <div class="drift-axis"><span>30m before</span><span>feed</span><span>60m after</span></div>
        <p>${note}</p></div>`);
    }

    // ----- #4: O₂ challenge ledger ------------------------------------------------
    function renderChallengeLedger(items) {
      if (!items.length) return '';
      const list = [...items].sort((a, b) => Date.parse(a.start_time) - Date.parse(b.start_time)).slice(-8);
      const maxDur = Math.max(...list.map(c => (c.summary && c.summary.duration_seconds) || 0), 1);
      const rows = list.map(c => {
        const s = c.summary || {}, cmp = c.comparison || {};
        const dur = s.duration_seconds || 0;
        const date = new Date(c.start_time).toLocaleDateString([], { month: 'short', day: 'numeric' });
        const delta = cmp.avg_oxygen_delta;
        const badge = delta == null || Math.abs(delta) < 0.05 ? ''
          : ` <em class="${delta >= 0 ? 'up' : 'down'}">${delta > 0 ? '↑' : '↓'}${Math.abs(delta).toFixed(1)}</em>`;
        const meta = [fmtDur(dur)];
        if (s.avg_oxygen_saturation != null) meta.push(`avg ${s.avg_oxygen_saturation.toFixed(1)}%`);
        if (s.min_oxygen_saturation != null) meta.push(`low ${Math.round(s.min_oxygen_saturation)}%`);
        return `<div class="ledger-row">
          <span class="ledger-date">${date}${c.active ? ' · live' : ''}</span>
          <span class="ledger-track"><i style="width:${Math.max(4, (dur / maxDur) * 100).toFixed(1)}%"></i></span>
          <span class="ledger-meta">${meta.join(' · ')}${badge}</span>
        </div>`;
      }).join('');
      return section('O₂ challenge ledger',
        `<div class="tile card"><h3>Each trial, oldest to newest</h3>
        <div class="ledger">${rows}</div>
        <p>Bar length is how long the trial ran. The arrow compares its average SpO₂ against the equivalent stretch just before it — trials getting longer and holding higher is the weaning story.</p></div>`);
    }

    // ----- pattern analysis (tiles) ---------------------------------------------
    function nightlyAnalysis(days) {
      // For each configured night (start on day N -> end on day N+1):
      // total sleep, bedtime, longest stretch.
      const byTime = new Map();
      days.forEach(day => day.cells.forEach((row, col) => {
        if (row) byTime.set(day.date.getTime() + col * BUCKET_SEC * 1000, row);
      }));
      const nights = [];
      days.forEach(day => {
        const startMin = Math.floor(NIGHT.start / BUCKET_MIN) * BUCKET_MIN;
        const endMin = 24 * 60 + Math.ceil(NIGHT.end / BUCKET_MIN) * BUCKET_MIN;
        const start = day.date.getTime() + startMin * 60000;
        const end = day.date.getTime() + endMin * 60000;
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
      const provisional = nights.length < 5;
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
        if (delta === null) return '';
        if (Math.abs(delta) < 0.05) return '<span class="delta flat">→ steady</span>';
        const good = invert ? delta < 0 : delta > 0;
        const arrow = delta > 0 ? '↑' : '↓';
        return `<span class="delta ${good ? 'up' : 'down'}">${arrow} ${unit}</span>`;
      };

      const tiles = [];
      tiles.push(`<div class="tile card"><h3>Sleep per night</h3>
        <b>${sleepNow != null ? fmtDur(sleepNow) : '—'}</b>${deltaBadge(sleepDelta, sleepDelta != null ? fmtDur(Math.abs(sleepDelta)) + ' vs last week' : '')}
        <p>${provisional ? 'So far — average of' : 'Average over the last'} ${week.length} night${week.length === 1 ? '' : 's'}${prior.length ? ', compared with the week before' : ''}.</p></div>`);
      tiles.push(`<div class="tile card"><h3>Typical bedtime</h3>
        <b>${bedAvg != null ? fmtClock(bedAvg % (24 * 60)) : '—'}</b>
        <p>${provisional
          ? `Based on ${bedtimes.length || week.length} night${(bedtimes.length || week.length) === 1 ? '' : 's'} — too early to call it a rhythm.`
          : bedSpread != null ? (bedSpread <= 30
            ? `Remarkably consistent — within ±${Math.round(bedSpread)} minutes. A rhythm is forming.`
            : `Still drifting by about ±${Math.round(bedSpread)} minutes night to night.`)
          : `First sustained sleep after ${fmtClock(NIGHT.start)}.`}</p></div>`);
      tiles.push(`<div class="tile card"><h3>Longest stretch</h3>
        <b>${longest ? fmtDur(longest) : '—'}</b>
        <p>${longestNight && longest ? `Best unbroken sleep this week, on ${longestNight.date.toLocaleDateString([], { weekday: 'long' })} night.` : 'Longest unbroken sleep this week.'}</p></div>`);
      tiles.push(`<div class="tile card"><h3>Oxygen baseline</h3>
        <b>${o2Week != null ? o2Week.toFixed(1) + '<small>%</small>' : '—'}</b>${o2Prior != null && o2Week != null ? deltaBadge(o2Week - o2Prior, Math.abs(o2Week - o2Prior).toFixed(1) + ' pts vs last week') : ''}
        <p>Average SpO₂ across the whole week, day and night.</p></div>`);
      const heading = provisional ? 'What the pattern says — so far' : 'What the pattern says';
      const caveat = provisional
        ? `<p class="lede" style="font-size:13px; margin:0 0 14px; color:var(--faint)">Only ${nights.length} night${nights.length === 1 ? '' : 's'} of data — these numbers firm up after a full week.</p>`
        : '';
      return section(heading, caveat + `<div class="tiles">${tiles.join('')}</div>`);
    }

    async function boot() {
      let rollups = [], rollups5 = [], careEvents = [], challenges = [], deviceName = null;
      try {
        const [r30, r5, ev, ch, accounts] = await Promise.all([
          fetch('/api/rollups?bucket=30m&hours=336&limit=100000').then(r => r.json()),
          fetch('/api/rollups?bucket=5m&hours=336&limit=100000').then(r => r.json()).catch(() => ({})),
          fetch('/api/events?hours=336&limit=2000').then(r => r.json()).catch(() => ({})),
          fetch('/api/oxygen-challenges?hours=336&limit=100').then(r => r.json()).catch(() => ({})),
          fetch('/api/accounts').then(r => r.json())
        ]);
        rollups = r30.rollups || [];
        rollups5 = r5.rollups || [];
        careEvents = (ev.events || []).map(e => ({ ...e, t: Date.parse(e.at) }));
        challenges = ch.items || [];
        const account = (accounts.accounts || [])[0];
        const prefs = (account && account.dashboard_preferences) || {};
        O2 = window.owletO2(prefs);
        deviceName = prefs.baby_name || null;
        NIGHT = nightWindowFrom(prefs);
        BIRTH = prefs.birth_date || null;
        FEEDS = prefs.feed_tracking !== false;
      } catch (error) {
        el('content').innerHTML = '<div class="empty">Could not load readings — is the collector running?</div>';
        return;
      }
      el('title').innerHTML = deviceName ? `The shape of <em>${deviceName}’s</em> days` : 'The shape of the days';
      const days = dayGrid(rollups);
      if (!days.length) {
        el('content').innerHTML = `<div class="empty">Nothing to chart yet.<br/>
          Give it a night or two — each day of readings adds a row here.</div>`;
        return;
      }
      const t1 = Date.now(), t0 = t1 - 336 * 3600e3;
      const o2iv = o2Intervals(careEvents, t0, t1);
      el('content').innerHTML = [
        renderActogram(days, o2iv),
        renderCircadian(rollups5, deviceName),
        renderDipMap(days, o2iv),
        renderTiles(days, rollups),
        renderDayPrep(rollups5),
        renderDesatBurden(rollups5),
        renderBaselineDrift(rollups5),
        renderDeepGap(rollups5),
        renderO2Report(rollups5, o2iv),
        renderFeedRhythm(careEvents),
        renderFeedResponse(rollups5, careEvents),
        renderChallengeLedger(challenges),
      ].join('');
    }
    boot();
  </script>"""


def render_rhythms_page() -> str:
    return render_shell(
        view="rhythms",
        title="Rhythms",
        head=RHYTHMS_HEAD,
        body=RHYTHMS_BODY,
        scripts=RHYTHMS_SCRIPTS,
    )
