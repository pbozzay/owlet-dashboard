"""'Today' — the app's home. The ten-second check: live vitals with personal
context, today so far, and doors into the deeper views. The hero charts are
touchable: tap or hold to read a value, pull right to scroll back in time.
Chips open detail sheets, and care events (O₂ on/off, sock off…) can be
logged and show up as markers on the charts."""

from __future__ import annotations

from app.shell import render_shell

NOW_HEAD = """<link rel="manifest" href="/manifest.webmanifest" />
  <style>
    .status-line { font-size: 17px; color: var(--dim); line-height: 1.5; margin: 0 0 26px;
      max-width: 60ch; }
    .status-line b { color: var(--ink); font-weight: 600; }
    .hero { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
    @media (max-width: 640px) { .hero { grid-template-columns: 1fr; } }
    .hero-minor { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 8px; }
    .vital { padding: 22px 22px 76px; position: relative; overflow: hidden;
      touch-action: pan-y; user-select: none; -webkit-user-select: none; cursor: crosshair; }
    .vital .label { font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
      color: var(--faint); font-weight: 700; }
    .vital .value { font-size: clamp(56px, 9vw, 84px); line-height: 1.02;
      letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
    .vital .value small { font-size: 22px; color: var(--dim); font-weight: 500;
      letter-spacing: 0; }
    .vital.minor { padding: 16px 18px 58px; }
    .vital.minor .value { font-size: clamp(28px, 5vw, 40px); }
    .vital.minor .value small { font-size: 15px; }
    .vital.minor .chartzone { height: 44px; }
    .vital.out .value { color: var(--warn); }
    .vital.low .value { color: var(--awake); }
    .vital.critical .value { color: var(--bad); }
    .vital .band { font-size: 12.5px; color: var(--dim); margin-top: 2px; }
    .vital.inspecting .band { color: var(--accent); font-weight: 600; }
    .chartzone { position: absolute; left: 0; right: 0; bottom: 0; height: 60px; }
    .chartzone svg { position: absolute; inset: 0; width: 100%; height: 100%; opacity: .6; }
    .chartzone polyline, .ms-chartwrap polyline { fill: none; stroke: var(--accent);
      stroke-width: 1.6; stroke-linejoin: round; stroke-linecap: round;
      vector-effect: non-scaling-stroke; }
    .chartzone line.evline, .ms-chartwrap line.evline { stroke: var(--warn);
      stroke-width: 1; stroke-dasharray: 2 3; vector-effect: non-scaling-stroke; opacity: .85; }
    .chartzone .evflag, .ms-chartwrap .evflag { fill: var(--warn); }
    /* offline ghost: holds the last reading's level through a gap, dashed grey
       so it can't be mistaken for live data */
    .chartzone .ghostline, .ms-chartwrap .ghostline { stroke: var(--faint);
      stroke-width: 1.4; stroke-dasharray: 4 4; vector-effect: non-scaling-stroke;
      opacity: .75; }
    /* hypnogram: rounded state bars in three lanes, tracker-style */
    .chartzone .sleepbar, .ms-chartwrap .sleepbar { fill: none; stroke-linecap: round;
      vector-effect: non-scaling-stroke; }
    .sleepbar.sleep-awake { stroke: var(--awake); }
    .sleepbar.sleep-light { stroke: var(--sleep-light); }
    .sleepbar.sleep-deep { stroke: var(--sleep-deep); }
    #card-sleep .value { text-transform: lowercase; }
    /* no-data bands: quiet grey = collector wasn't running, warm = sock off/charging */
    .gapband.collector { fill: color-mix(in srgb, var(--ink) 7%, transparent); }
    .gapband.sock { fill: color-mix(in srgb, var(--awake) 10%, transparent); }
    .vital-expand { all: unset; position: absolute; top: 10px; right: 10px; z-index: 2;
      cursor: pointer; color: var(--faint); padding: 7px 9px; border-radius: 9px;
      font-size: 14px; line-height: 1; }
    .vital-expand:hover { color: var(--accent); background: var(--accent-soft); }

    /* ---- metric detail sheet ---------------------------------------------- */
    .ms-top { display: flex; justify-content: space-between; align-items: baseline;
      gap: 10px; margin-bottom: 10px; min-height: 34px; }
    .ms-value { font-size: 28px; font-weight: 700; letter-spacing: -.02em;
      font-variant-numeric: tabular-nums; }
    .ms-value small { font-size: 14px; color: var(--dim); font-weight: 500; }
    .ms-when { color: var(--dim); font-size: 12px; text-align: right; }
    .ms-seg { display: flex; background: var(--accent-soft); border-radius: 999px;
      padding: 3px; margin-bottom: 12px; }
    .ms-seg button { all: unset; flex: 1; text-align: center; cursor: pointer;
      font-size: 12px; font-weight: 600; color: var(--dim); padding: 5px 0;
      border-radius: 999px; }
    .ms-seg button.active { background: var(--surface); color: var(--accent);
      box-shadow: 0 2px 8px rgba(0, 0, 0, .12); }
    .ms-chartwrap { position: relative; touch-action: pan-y; user-select: none;
      -webkit-user-select: none; cursor: crosshair; }
    .ms-chartwrap svg { display: block; width: 100%; height: 150px; }
    .ms-chartwrap .threshold { stroke: var(--bad); opacity: .3; stroke-width: 1;
      stroke-dasharray: 3 4; vector-effect: non-scaling-stroke; }
    .ms-xline { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--dim);
      opacity: .8; pointer-events: none; }
    .ms-axis { display: flex; justify-content: space-between; color: var(--faint);
      font-size: 10.5px; margin-top: 5px; font-variant-numeric: tabular-nums; }
    .ms-ylab { position: absolute; right: 3px; font-size: 10px; color: var(--faint);
      font-variant-numeric: tabular-nums; pointer-events: none; }
    .ms-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
      margin: 14px 0 4px; }
    .ms-stats div { text-align: center; }
    .ms-stats b { display: block; font-size: 15px; font-variant-numeric: tabular-nums; }
    .ms-stats span { font-size: 10.5px; color: var(--faint); text-transform: uppercase;
      letter-spacing: .08em; }
    .ms-dips { margin-top: 12px; display: grid; gap: 6px; }
    .ms-dips button { all: unset; box-sizing: border-box; cursor: pointer; display: flex;
      justify-content: space-between; gap: 10px; padding: 8px 11px;
      border: 1px solid var(--surface-line); border-radius: var(--radius-control);
      font-size: 12.5px; font-variant-numeric: tabular-nums; }
    .ms-dips button:hover { border-color: var(--accent); }
    .ms-dips b { color: var(--awake); }
    .ms-dips b.deep { color: var(--bad); }
    .ms-link { display: block; margin-top: 14px; text-align: center; color: var(--accent);
      text-decoration: none; font-size: 13px; font-weight: 600; }
    .xline { position: absolute; top: 12px; bottom: 0; width: 1px;
      background: var(--dim); opacity: .8; pointer-events: none; }
    .xline::after { content: ''; position: absolute; top: -5px; left: -2.5px;
      width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
    .timescale { display: flex; justify-content: space-between; align-items: center;
      gap: 10px; font-size: 11px; color: var(--faint); margin: 0 4px 24px;
      font-variant-numeric: tabular-nums; }
    .timescale .live-chip { all: unset; font-size: 11px; color: var(--faint);
      letter-spacing: .04em; }
    .timescale .live-chip.paused { cursor: pointer; color: var(--accent);
      background: var(--accent-soft); padding: 3px 11px; border-radius: 999px;
      font-weight: 700; }
    .strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px; margin-bottom: 26px; }
    .chip { padding: 15px 16px 13px; }
    .chip b { display: block; font-size: 21px; letter-spacing: -0.01em;
      font-variant-numeric: tabular-nums; }
    .chip span { font-size: 11.5px; color: var(--dim); }
    .chip .sub { display: block; font-size: 11px; color: var(--faint); margin-top: 3px; }
    .chip.warn b { color: var(--warn); }
    .chip.good b { color: var(--good); }
    /* Reset only the button chrome — `all: unset` would also wipe the .card
       background/border/radius that these chips rely on. */
    button.chip { display: block; width: 100%; margin: 0; font: inherit;
      color: inherit; text-align: left; cursor: pointer; appearance: none; }
    button.chip:hover { border-color: var(--accent); }
    .doors { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 640px) { .doors { grid-template-columns: 1fr; } }
    .door { display: block; padding: 18px 20px; text-decoration: none; color: var(--ink); }
    .door b { display: block; font-size: 15px; margin-bottom: 3px; }
    .door span { font-size: 13px; color: var(--dim); line-height: 1.45; }
    .door:hover { border-color: var(--accent); }
    .empty { text-align: center; color: var(--dim); padding: 80px 20px; font-size: 15px; }

    /* ---- detail sheet ---------------------------------------------------- */
    .sheet-backdrop { position: fixed; inset: 0; z-index: 80;
      background: rgba(10, 12, 30, .45); display: flex; align-items: center;
      justify-content: center; padding: 20px; }
    .sheet-backdrop[hidden] { display: none; }
    .sheet { width: min(460px, 100%); max-height: min(72vh, 620px); overflow-y: auto;
      padding: 20px 22px 22px; }
    @media (max-width: 640px) {
      .sheet-backdrop { align-items: flex-end; padding: 0; }
      .sheet { width: 100%; max-height: 80vh; border-radius: 18px 18px 0 0;
        padding-bottom: calc(22px + env(safe-area-inset-bottom)); }
    }
    .sheet header { display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 14px; }
    .sheet header b { font-size: 16px; }
    .sheet header button { all: unset; cursor: pointer; color: var(--dim);
      font-size: 15px; padding: 4px 8px; }
    .sheet header button:hover { color: var(--ink); }
    .sheet .row { display: flex; justify-content: space-between; gap: 12px;
      padding: 9px 0; border-bottom: 1px solid var(--surface-line); font-size: 13.5px; }
    .sheet .row:last-child { border-bottom: 0; }
    .sheet .row b { font-variant-numeric: tabular-nums; }
    .sheet .row .mut { color: var(--dim); }
    .sheet .row a { color: var(--accent); text-decoration: none; font-weight: 600; }
    .sheet .note { font-size: 12.5px; color: var(--dim); line-height: 1.5; margin: 10px 0 0; }
    .sheet .ev-del { all: unset; cursor: pointer; color: var(--faint); padding: 0 4px; }
    .sheet .ev-del:hover { color: var(--bad); }
    .ev-presets { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px; }
    .ev-presets button { all: unset; box-sizing: border-box; text-align: center; cursor: pointer;
      padding: 10px 4px; border: 1px solid var(--surface-line); border-radius: var(--radius-control);
      font-size: 13px; font-weight: 600; color: var(--ink); }
    .ev-presets button:hover, .ev-presets button.sel { border-color: var(--accent);
      color: var(--accent); background: var(--accent-soft); }
    .ev-form { display: grid; gap: 10px; }
    .ev-form input { padding: 9px 11px; border: 1px solid var(--surface-line);
      border-radius: var(--radius-control); background: var(--surface); color: var(--ink);
      font-size: 13.5px; font-family: inherit; }
    .ev-save { all: unset; box-sizing: border-box; text-align: center; cursor: pointer;
      padding: 10px 0; border-radius: var(--radius-control); background: var(--accent);
      color: #fff; font-size: 13.5px; font-weight: 700; }
    .ev-save[disabled] { opacity: .5; cursor: default; }
    .sheet .section-title { margin-top: 18px; }
    @media (prefers-reduced-motion: reduce) { .chartzone svg g { transition: none !important; } }
  </style>"""

_VITAL_CARD = """<div class="vital card{minor}" id="card-{key}" data-metric="{key}">
        <button class="vital-expand" data-expand="{key}" type="button"
          aria-label="Expand {label} chart" title="Bigger chart &amp; stats">⤢</button>
        <span class="label">{label}</span>
        <div class="value"><span id="{key}Value">—</span><small id="{key}Unit"> {unit}</small></div>
        <div class="band" id="{key}Band"></div>
        <div class="chartzone">
          <svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true"><g id="{key}G"></g></svg>
          <div class="xline" id="{key}X" hidden></div>
        </div>
      </div>"""

NOW_BODY = (
    """<p class="status-line" id="statusLine">Checking in…</p>
    <div class="hero">"""
    + _VITAL_CARD.format(minor="", key="o2", label="Oxygen", unit="%")
    + _VITAL_CARD.format(minor="", key="hr", label="Heart rate", unit="bpm")
    + """</div>
    <div class="hero-minor">"""
    + _VITAL_CARD.format(minor=" minor", key="sleep", label="Sleep", unit="")
    + _VITAL_CARD.format(minor=" minor", key="move", label="Movement", unit="")
    + """</div>
    <div class="timescale">
      <span id="tsStart"></span>
      <button class="live-chip" id="tsLive" type="button">● live</button>
      <span id="tsEnd"></span>
    </div>
    <div id="belowHero"></div>
    <div class="sheet-backdrop" id="sheetBackdrop" hidden>
      <div class="sheet card" role="dialog" aria-modal="true" aria-labelledby="sheetTitle">
        <header><b id="sheetTitle"></b><button id="sheetClose" type="button" aria-label="Close">✕</button></header>
        <div id="sheetBody"></div>
      </div>
    </div>"""
)

NOW_SCRIPTS = """<script src="/insights.js"></script>
  <script>
    const I = window.OwletInsights;
    const el = id => document.getElementById(id);
    const pad = n => String(n).padStart(2, '0');
    const fmtDur = seconds => {
      const totalMinutes = Math.round(seconds / 60);
      const h = Math.floor(totalMinutes / 60), m = totalMinutes % 60;
      return h ? `${h}h ${pad(m)}m` : `${m}m`;
    };
    const fmtClock = date => {
      let h = date.getHours(); const m = pad(date.getMinutes());
      const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
      return `${h}:${m} ${ap}`;
    };
    const esc = text => String(text).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    let pollSeconds = 5;
    let deviceName = 'your little one';
    let rollups = [];

    const stateLabel = value => ({ '0': 'resting', '1': 'awake', '8': 'in light sleep', '15': 'in deep sleep' }[String(value)] || null);
    const isOffline = row => !!(row?.sock_disconnected || row?.sock_off
      || (row?.heart_rate != null && row.heart_rate <= 0)
      || (row?.oxygen_saturation != null && row.oxygen_saturation <= 0));

    const o2Zone = value => value < 86 ? 'var(--bad)' : (value < 90 ? 'var(--awake)' : 'var(--accent)');
    const moveWord = avg => avg < 4 ? 'calm' : avg < 20 ? 'stirring' : 'active';

    const METRICS = [
      { key: 'o2',   label: 'Oxygen',     unit: '%',   fmt: v => Math.round(v), zone: o2Zone },
      { key: 'hr',   label: 'Heart rate', unit: 'bpm', fmt: v => Math.round(v), zone: null },
      { key: 'temp', label: 'Skin temp',  unit: '°C',  fmt: v => v.toFixed(1),  zone: null },
      { key: 'move', label: 'Movement',   unit: '',    fmt: v => Math.round(v), zone: null },
    ];
    // Cards on the page: temp lives in the chip strip now; sleep is a hypnogram.
    const HERO_KEYS = ['o2', 'hr', 'sleep', 'move'];
    const SLEEP_WORD = { awake: 'awake', light: 'light', deep: 'deep' };

    // ---- data buffers ------------------------------------------------------
    // liveReadings is the always-fresh last hour; histReadings grows on demand
    // as the user pulls back in time. Points arrays hold only valid vitals, so
    // collector-off stretches show up as time gaps in the line.
    const WINDOW_MS = 60 * 60 * 1000;
    const GAP_MS = 90 * 1000;
    const HISTORY_STEPS = [3, 6, 12, 24];
    let liveReadings = [], histReadings = [], loadedHours = 1, loadingHistory = false;
    let points = { o2: [], hr: [], temp: [], move: [] };
    let gaps = [];   // {start, end, kind: 'collector' | 'sock'} — why the line breaks
    let bands = { o2: null, hr: null };
    let latest = { o2: null, hr: null, temp: null, move: null, offline: true };
    let tempRangeText = '';
    let baselineState = 'awake';
    let careEvents = [];

    function allReadings() {
      if (!histReadings.length) return liveReadings;
      const cut = liveReadings.length ? Date.parse(liveReadings[0].recorded_at) : Infinity;
      return histReadings.filter(r => Date.parse(r.recorded_at) < cut).concat(liveReadings);
    }
    function rebuildPoints() {
      const rows = allReadings();
      const valid = rows.filter(r => !isOffline(r));
      points.hr = valid.filter(r => r.heart_rate > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.heart_rate }));
      points.o2 = valid.filter(r => r.oxygen_saturation > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.oxygen_saturation }));
      points.temp = valid.filter(r => r.skin_temperature > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.skin_temperature }));
      points.move = valid.map(r => ({ x: Date.parse(r.recorded_at), y: r.movement || 0 }));
      gaps = computeGaps(rows);
      sleepRuns = computeSleepRuns(rows);
    }
    let sleepRuns = [];   // {start, end, level: 'awake' | 'light' | 'deep'}
    function computeSleepRuns(rows) {
      const level = s => { const v = String(s); return v === '8' ? 'light' : v === '15' ? 'deep' : 'awake'; };
      const out = [];
      let run = null;
      for (const r of rows) {
        if (isOffline(r)) { run = null; continue; }
        const t = Date.parse(r.recorded_at);
        const lv = level(r.sleep_state);
        if (run && run.level === lv && t - run.end <= GAP_MS) run.end = t;
        else { run = { start: t, end: t, level: lv }; out.push(run); }
      }
      // drop sub-45s flickers — Owlet's state flaps sample to sample
      return out.filter(r => r.end - r.start >= 45 * 1000);
    }
    function sleepLevelAt(t) {
      const run = sleepRuns.find(r => t >= r.start - GAP_MS && t <= r.end + GAP_MS);
      return run ? run.level : null;
    }
    function computeGaps(rows) {
      const out = [];
      let sockRun = null;
      for (let i = 0; i < rows.length; i++) {
        const t = Date.parse(rows[i].recorded_at);
        if (i > 0) {
          const prev = Date.parse(rows[i - 1].recorded_at);
          if (t - prev > 2 * 60 * 1000) out.push({ start: prev, end: t, kind: 'collector' });
        }
        if (isOffline(rows[i])) {
          if (!sockRun) sockRun = { start: t, end: t, kind: 'sock' };
          else sockRun.end = t;
        } else if (sockRun) { out.push(sockRun); sockRun = null; }
      }
      if (sockRun) { sockRun.end = Date.now(); out.push(sockRun); }
      if (rows.length) {
        const lastT = Date.parse(rows[rows.length - 1].recorded_at);
        if (Date.now() - lastT > 2 * 60 * 1000) out.push({ start: lastT, end: Date.now(), kind: 'collector' });
        const firstT = Date.parse(rows[0].recorded_at);
        if (firstT - loadedStart() > 2 * 60 * 1000) out.unshift({ start: loadedStart(), end: firstT, kind: 'collector' });
      }
      return out;
    }
    function gapAt(t) { return gaps.find(g => t >= g.start && t <= g.end) || null; }
    function lastPointBefore(pts, t) {
      if (!pts.length || pts[0].x > t) return null;
      let lo = 0, hi = pts.length - 1;
      while (lo < hi) { const mid = (lo + hi + 1) >> 1; (pts[mid].x <= t ? lo = mid : hi = mid - 1); }
      return pts[lo];
    }
    function loadedStart() { return Date.now() - loadedHours * 3600 * 1000; }
    async function extendHistory() {
      const next = HISTORY_STEPS.find(h => h > loadedHours);
      if (!next || loadingHistory) return;
      loadingHistory = true;
      try {
        const rows = await fetch(`/api/readings?hours=${next}&limit=40000`).then(r => r.json());
        histReadings = rows; loadedHours = next;
        rebuildPoints();
        if (!gesture) renderCharts();
      } catch (error) { /* keep what we have */ }
      loadingHistory = false;
    }
    async function ensureHistoryHours(hours) {
      for (let i = 0; i < HISTORY_STEPS.length && loadedHours < hours; i++) {
        const before = loadedHours;
        await extendHistory();
        if (loadedHours === before) break;   // concurrent fetch or nothing left to load
      }
    }
    async function loadEvents() {
      try {
        const data = await fetch('/api/events?hours=48').then(r => r.json());
        careEvents = (data.events || []).map(e => ({ ...e, x: Date.parse(e.at) }));
        if (!gesture) renderCharts();
      } catch (error) { /* non-fatal */ }
    }

    // ---- hero charts: virtualized pan window -------------------------------
    // viewEnd === null means "live" (window pinned to now). While panned, the
    // window is anchored to an absolute time so it stays frozen as new data
    // streams into the buffer behind it.
    let viewEnd = null;
    let anchorEnd = 0;   // window end the SVGs were last drawn against
    const chartEnd = () => viewEnd ?? Date.now();

    function downsample(pts) {
      if (pts.length <= 1500) return pts;
      const buckets = 700, out = [];
      const t0 = pts[0].x, span = pts[pts.length - 1].x - t0 || 1;
      let b = -1, lo = null, hi = null;
      for (const p of pts) {
        const idx = Math.floor(((p.x - t0) / span) * (buckets - 1));
        if (idx !== b) {
          if (lo) out.push(...(lo.x <= hi.x ? [lo, hi] : [hi, lo]).filter((v, i, a) => a.indexOf(v) === i));
          b = idx; lo = hi = p;
        } else {
          if (p.y < lo.y) lo = p;
          if (p.y > hi.y) hi = p;
        }
      }
      if (lo) out.push(...(lo.x <= hi.x ? [lo, hi] : [hi, lo]).filter((v, i, a) => a.indexOf(v) === i));
      return out;
    }

    // Shared SVG builder for hero strips and the detail sheet. Maps the time
    // domain [t0, t1] to x [0, w]; points outside may overflow (the hero pans
    // over its margins, the svg clips). Draws no-data bands, event markers
    // with a flag dot, then zone-colored line segments.
    function buildSeriesMarkup(key, t0, t1, dataStart, dataEnd, w, h, opts = {}) {
      const metric = METRICS.find(m => m.key === key);
      const xOf = t => ((t - t0) / (t1 - t0)) * w;
      const clampX = x => Math.max(0, Math.min(w, x));
      const bands = gaps
        .filter(g => g.end >= dataStart && g.start <= dataEnd && g.end - g.start > GAP_MS)
        .map(g => {
          const x0 = opts.clip ? clampX(xOf(g.start)) : xOf(g.start);
          const x1 = opts.clip ? clampX(xOf(g.end)) : xOf(g.end);
          return x1 - x0 < 0.2 ? '' : `<rect class="gapband ${g.kind}" x="${x0.toFixed(2)}" y="0" width="${(x1 - x0).toFixed(2)}" height="${h}"/>`;
        }).join('');
      const eventMarks = careEvents
        .filter(e => e.x >= dataStart && e.x <= dataEnd)
        .map(e => `<line class="evline" x1="${xOf(e.x).toFixed(2)}" x2="${xOf(e.x).toFixed(2)}" y1="0" y2="${h}"><title>${esc(e.kind)}</title></line>`
          + `<circle class="evflag" cx="${xOf(e.x).toFixed(2)}" cy="3" r="2"/>`)
        .join('');
      const pts = downsample(points[key].filter(p => p.x >= dataStart && p.x <= dataEnd));
      if (pts.length < 2) return { markup: bands + eventMarks, min: null, max: null };
      let min = Infinity, max = -Infinity;
      for (const p of pts) { if (p.y < min) min = p.y; if (p.y > max) max = p.y; }
      // Anchor the O₂ domain near the 90% line so a dip to 85 reads as a real
      // plunge instead of vanishing into an auto-fit scale.
      if (key === 'o2') { min = Math.min(min, 91); max = Math.max(max, 99); }
      const domainMin = min, domainMax = max;
      const padY = Math.max(0.5, (max - min) * 0.1); min -= padY; max += padY;
      const yOf = v => (h - 2) - ((v - min) / (max - min)) * (h - 6);
      let thresholds = '';
      if (key === 'o2' && opts.thresholds) {
        thresholds = [90, 86].filter(v => v > min && v < max)
          .map(v => `<line class="threshold" x1="0" x2="${w}" y1="${yOf(v).toFixed(2)}" y2="${yOf(v).toFixed(2)}"/>`)
          .join('');
      }
      // Hold the last reading's level through each offline stretch as a dashed
      // grey line, so the gap reads as "signal lost here" rather than nothing.
      const ghosts = gaps
        .filter(g => g.end >= dataStart && g.start <= dataEnd && g.end - g.start > GAP_MS)
        .map(g => {
          const prior = lastPointBefore(points[key], g.start + 1000);
          if (!prior) return '';
          const gy = Math.max(2, Math.min(h - 2, yOf(prior.y)));
          const x0 = opts.clip ? clampX(xOf(g.start)) : xOf(g.start);
          const x1 = opts.clip ? clampX(xOf(g.end)) : xOf(g.end);
          if (x1 - x0 < 0.5) return '';
          return `<line class="ghostline" x1="${x0.toFixed(2)}" x2="${x1.toFixed(2)}" y1="${gy.toFixed(2)}" y2="${gy.toFixed(2)}"/>`;
        }).join('');
      const zone = (metric && metric.zone) || (() => 'var(--accent)');
      const segs = [];
      let run = { color: zone(pts[0].y), coords: [`${xOf(pts[0].x).toFixed(2)},${yOf(pts[0].y).toFixed(2)}`] };
      for (let i = 1; i < pts.length; i++) {
        const gap = pts[i].x - pts[i - 1].x > GAP_MS;
        const color = zone(pts[i].y);
        const coord = `${xOf(pts[i].x).toFixed(2)},${yOf(pts[i].y).toFixed(2)}`;
        if (gap) { segs.push(run); run = { color, coords: [coord] }; continue; }
        run.coords.push(coord);
        if (color !== run.color) { segs.push(run); run = { color, coords: [coord] }; }
      }
      segs.push(run);
      const lines = segs.filter(s => s.coords.length > 1)
        .map(s => `<polyline points="${s.coords.join(' ')}" style="stroke:${s.color}"/>`)
        .join('');
      return { markup: bands + thresholds + ghosts + eventMarks + lines, min: domainMin, max: domainMax };
    }

    // Tracker-style hypnogram: rounded bars in three lanes (awake / light / deep).
    function buildSleepMarkup(t0, t1, dataStart, dataEnd, w, h, opts = {}) {
      const xOf = t => ((t - t0) / (t1 - t0)) * w;
      const clampX = x => Math.max(0, Math.min(w, x));
      const bands = gaps
        .filter(g => g.end >= dataStart && g.start <= dataEnd && g.end - g.start > GAP_MS)
        .map(g => {
          const x0 = opts.clip ? clampX(xOf(g.start)) : xOf(g.start);
          const x1 = opts.clip ? clampX(xOf(g.end)) : xOf(g.end);
          return x1 - x0 < 0.2 ? '' : `<rect class="gapband ${g.kind}" x="${x0.toFixed(2)}" y="0" width="${(x1 - x0).toFixed(2)}" height="${h}"/>`;
        }).join('');
      const eventMarks = careEvents
        .filter(e => e.x >= dataStart && e.x <= dataEnd)
        .map(e => `<line class="evline" x1="${xOf(e.x).toFixed(2)}" x2="${xOf(e.x).toFixed(2)}" y1="0" y2="${h}"><title>${esc(e.kind)}</title></line>`
          + `<circle class="evflag" cx="${xOf(e.x).toFixed(2)}" cy="3" r="2"/>`)
        .join('');
      const lanes = { awake: h * 0.2, light: h * 0.5, deep: h * 0.8 };
      const bars = sleepRuns
        .filter(r => r.end >= dataStart && r.start <= dataEnd)
        .map(r => {
          const x0 = opts.clip ? clampX(xOf(r.start)) : xOf(r.start);
          const x1 = opts.clip ? clampX(xOf(r.end)) : xOf(r.end);
          if (x1 - x0 < 0.4) return '';
          const y = lanes[r.level].toFixed(2);
          return `<line class="sleepbar sleep-${r.level}" x1="${x0.toFixed(2)}" x2="${x1.toFixed(2)}" y1="${y}" y2="${y}" style="stroke-width:${opts.bar || 5}px"/>`;
        }).join('');
      return { markup: bands + eventMarks + bars };
    }

    function renderChart(key) {
      const g = el(key + 'G'); if (!g) return;
      const end = chartEnd();
      const built = key === 'sleep'
        ? buildSleepMarkup(end - WINDOW_MS, end, end - 2 * WINDOW_MS, end + WINDOW_MS / 4, 100, 42)
        : buildSeriesMarkup(key, end - WINDOW_MS, end, end - 2 * WINDOW_MS, end + WINDOW_MS / 4, 100, 42);
      g.innerHTML = built.markup;
      g.removeAttribute('transform');
    }
    function renderCharts() {
      anchorEnd = chartEnd();
      HERO_KEYS.forEach(renderChart);
      updateTimescale();
    }
    function applyPan() {
      const shift = ((anchorEnd - chartEnd()) / WINDOW_MS) * 100;
      if (Math.abs(shift) > 85) { renderCharts(); return; }
      const t = `translate(${shift.toFixed(3)} 0)`;
      HERO_KEYS.forEach(key => el(key + 'G').setAttribute('transform', t));
      updateTimescale();
    }
    function updateTimescale() {
      const end = chartEnd();
      el('tsStart').textContent = fmtClock(new Date(end - WINDOW_MS));
      el('tsEnd').textContent = viewEnd == null ? 'now' : fmtClock(new Date(end));
      const chip = el('tsLive');
      chip.textContent = viewEnd == null ? '● live' : '⟳ back to now';
      chip.classList.toggle('paused', viewEnd != null);
    }
    el('tsLive').addEventListener('click', () => {
      if (viewEnd == null) return;
      viewEnd = null; clearInspect(); renderCharts();
    });

    // ---- inspect (tap / hold) ----------------------------------------------
    function nearestPoint(pts, t) {
      if (!pts.length) return null;
      let lo = 0, hi = pts.length - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; (pts[mid].x < t ? lo = mid : hi = mid); }
      const best = Math.abs(pts[lo].x - t) <= Math.abs(pts[hi].x - t) ? pts[lo] : pts[hi];
      return Math.abs(best.x - t) <= GAP_MS ? best : null;
    }
    function inspectAt(clientX, card) {
      const rect = card.getBoundingClientRect();
      const frac = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      const t = chartEnd() - WINDOW_MS + frac * WINDOW_MS;
      const nearEvent = careEvents.find(e => Math.abs(e.x - t) <= 3 * 60 * 1000);
      const when = `at ${fmtClock(new Date(t))}` + (nearEvent ? ` · ⚑ ${esc(nearEvent.kind)}` : '');
      const gap = gapAt(t);
      const gapLabel = gap ? (gap.kind === 'collector' ? 'collector was off' : 'sock was off') : 'no reading';
      HERO_KEYS.forEach(key => {
        if (key === 'sleep') {
          const level = sleepLevelAt(t);
          el('sleepValue').textContent = level ? SLEEP_WORD[level] : '—';
          el('sleepBand').innerHTML = level ? when : `${gapLabel} ${when}`;
        } else {
          const metric = METRICS.find(m => m.key === key);
          const p = nearestPoint(points[key], t);
          el(key + 'Value').textContent = p ? metric.fmt(p.y) : '—';
          el(key + 'Band').innerHTML = p ? when : `${gapLabel} ${when}`;
        }
        el('card-' + key).classList.add('inspecting');
        const x = el(key + 'X');
        x.hidden = false; x.style.left = (frac * 100) + '%';
      });
    }
    function clearInspect() {
      HERO_KEYS.forEach(key => {
        el(key + 'X').hidden = true;
        el('card-' + key).classList.remove('inspecting');
      });
      updateHeroLive();
    }

    // ---- gestures: hold to inspect, pull to pan ------------------------------
    let gesture = null, holdTimer = 0, momentumRaf = 0, inspectFade = 0;
    function stopMomentum() { if (momentumRaf) cancelAnimationFrame(momentumRaf); momentumRaf = 0; }

    function onDown(event, card) {
      if (event.button != null && event.button !== 0) return;
      stopMomentum(); clearTimeout(inspectFade);
      try { card.setPointerCapture(event.pointerId); } catch (error) { /* keep the gesture even if capture fails */ }
      gesture = {
        mode: 'pending', card,
        x0: event.clientX, y0: event.clientY,
        end0: chartEnd(),
        msPerPx: WINDOW_MS / card.getBoundingClientRect().width,
        hist: [{ x: event.clientX, t: performance.now() }],
      };
      inspectAt(event.clientX, card);   // respond on pointer-down, not release
      holdTimer = setTimeout(() => { if (gesture && gesture.mode === 'pending') gesture.mode = 'scrub'; }, 220);
    }
    function onMove(event) {
      if (!gesture) return;
      const dx = event.clientX - gesture.x0, dy = event.clientY - gesture.y0;
      const now = performance.now();
      gesture.hist.push({ x: event.clientX, t: now });
      while (gesture.hist.length > 2 && now - gesture.hist[0].t > 120) gesture.hist.shift();
      if (gesture.mode === 'pending') {
        if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) {
          gesture.mode = 'pan'; clearTimeout(holdTimer); clearInspect();
        } else if (Math.abs(dy) > 16) {   // vertical intent: hand back to the page
          clearTimeout(holdTimer); clearInspect(); gesture = null; return;
        }
      }
      if (gesture.mode === 'scrub') { inspectAt(event.clientX, gesture.card); return; }
      if (gesture.mode === 'pan') {
        let end = gesture.end0 - dx * gesture.msPerPx;   // pull right → back in time
        const nowMs = Date.now();
        const minEnd = loadedStart() + WINDOW_MS;
        if (end > nowMs) end = nowMs + (end - nowMs) / 3;             // rubber-band at "now"
        if (end < minEnd) { end = minEnd + (end - minEnd) / 3; extendHistory(); }
        else if (end - WINDOW_MS < loadedStart() + WINDOW_MS / 4) extendHistory();
        viewEnd = end;
        applyPan();
      }
    }
    function onUp(event) {
      clearTimeout(holdTimer);
      if (!gesture) return;
      const mode = gesture.mode, hist = gesture.hist, msPerPx = gesture.msPerPx;
      gesture = null;
      if (mode === 'pending') {           // plain tap: linger, then return to live
        inspectFade = setTimeout(clearInspect, 2500);
        return;
      }
      if (mode === 'scrub') { clearInspect(); return; }
      // pan: hand the finger's velocity to a decaying glide
      let vPx = 0;
      if (hist.length > 1) {
        const a = hist[0], b = hist[hist.length - 1];
        if (b.t > a.t) vPx = ((b.x - a.x) / (b.t - a.t)) * 1000;
      }
      startGlide(-vPx * msPerPx);
    }
    function startGlide(vMs) {   // velocity in window-ms per second
      const settle = () => {
        const nowMs = Date.now();
        let target = viewEnd;
        if (target != null && nowMs - target < 5000) target = null;
        if (target != null && target < loadedStart() + WINDOW_MS) target = loadedStart() + WINDOW_MS;
        viewEnd = target === null ? null : target;
        renderCharts();
      };
      if (Math.abs(vMs) < WINDOW_MS * 0.02) { settle(); return; }
      let last = performance.now();
      const step = t => {
        const dt = Math.min(64, t - last); last = t;
        vMs *= Math.pow(0.998, dt);
        let end = chartEnd() + vMs * (dt / 1000);
        const nowMs = Date.now(), minEnd = loadedStart() + WINDOW_MS;
        if (end >= nowMs) { viewEnd = null; settle(); return; }
        if (end <= minEnd) { viewEnd = minEnd; extendHistory(); settle(); return; }
        viewEnd = end;
        applyPan();
        if (Math.abs(vMs) > WINDOW_MS * 0.01) momentumRaf = requestAnimationFrame(step);
        else settle();
      };
      momentumRaf = requestAnimationFrame(step);
    }
    HERO_KEYS.forEach(key => {
      const card = el('card-' + key);
      card.addEventListener('pointerdown', e => onDown(e, card));
      card.addEventListener('pointermove', onMove);
      card.addEventListener('pointerup', onUp);
      card.addEventListener('pointercancel', onUp);
    });

    // ---- detail sheet --------------------------------------------------------
    function openSheet(title, bodyHtml) {
      el('sheetTitle').textContent = title;
      el('sheetBody').innerHTML = bodyHtml;
      el('sheetBackdrop').hidden = false;
    }
    function closeSheet() { el('sheetBackdrop').hidden = true; }
    el('sheetClose').addEventListener('click', closeSheet);
    el('sheetBackdrop').addEventListener('click', event => {
      if (event.target === el('sheetBackdrop')) closeSheet();
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') closeSheet(); });
    el('sheetBody').addEventListener('click', async event => {   // event-row delete (any sheet open)
      const id = event.target.dataset && event.target.dataset.del;
      if (!id) return;
      const response = await fetch('/api/events/' + id, { method: 'DELETE' });
      if (response.ok) { await loadEvents(); eventsSheet(); }
    });

    function todayWindow() {
      const start = new Date(); start.setHours(0, 0, 0, 0);
      return { start, end: new Date() };
    }

    function dipsSheet() {
      const today = todayWindow();
      const dips = [];
      let current = null;
      rollups.forEach(row => {
        const t = new Date(row.bucket_start);
        if (t < today.start) return;
        const low = row.min_oxygen_saturation != null && row.min_oxygen_saturation < 90;
        if (low) {
          if (!current) current = { start: t, end: t, min: row.min_oxygen_saturation };
          else { current.end = t; current.min = Math.min(current.min, row.min_oxygen_saturation); }
        } else if (current) { dips.push(current); current = null; }
      });
      if (current) dips.push(current);
      if (!dips.length) return openSheet('O₂ dips today', '<p class="note">No dips below 90% today. 🎉</p>');
      const rows = dips.map(d =>
        `<div class="row">
          <span>${fmtClock(d.start)}</span>
          <b style="color:${d.min < 86 ? 'var(--bad)' : 'var(--awake)'}">low ${Math.round(d.min)}%</b>
          <a href="/data?focus=${encodeURIComponent(d.start.toISOString())}&span=45">inspect →</a>
        </div>`).join('');
      openSheet('O₂ dips today', rows +
        '<p class="note">Each row is a stretch of 5-minute buckets whose lowest reading fell under 90%. "Inspect" opens the raw data zoomed to that moment.</p>');
    }

    let batterySheetData = null;
    function batterySheet() {
      const b = batterySheetData;
      if (!b) return openSheet('Battery', '<p class="note">No battery data yet.</p>');
      const rows = [
        `<div class="row"><span>Charge now</span><b>${b.text}</b></div>`,
        b.charging ? '<div class="row"><span>State</span><b>charging</b></div>' : '',
        b.hoursLeft != null && b.hoursLeft !== Infinity && !b.charging
          ? `<div class="row"><span>Projected runtime</span><b>~${Math.round(b.hoursLeft)}h</b></div>` : '',
        b.sub ? `<div class="row"><span>Tonight</span><b>${b.sub}</b></div>` : '',
      ].join('');
      openSheet('Battery', rows +
        '<p class="note">Runtime is projected from the drain rate over the last hour of readings, and compared against the hours until 7 AM.</p>');
    }

    // ---- care events ---------------------------------------------------------
    const EVENT_PRESETS = ['O₂ on', 'O₂ off', 'Sock off', 'Sock on', 'Feeding', 'Medicine'];
    function localInputValue(date) {
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }
    function eventsSheet() {
      const presets = EVENT_PRESETS.map(k => `<button type="button" data-kind="${esc(k)}">${esc(k)}</button>`).join('');
      const recent = careEvents.slice(0, 12).map(e =>
        `<div class="row">
          <span>${fmtClock(new Date(e.x))}</span>
          <b>${esc(e.kind)}</b>
          <span class="mut">${esc(e.note || '')}</span>
          <button class="ev-del" data-del="${e.id}" title="Delete">✕</button>
        </div>`).join('');
      openSheet('Log an event',
        `<div class="ev-presets" id="evPresets">${presets}</div>
        <div class="ev-form">
          <input id="evKind" placeholder="Event (pick above or type)" maxlength="60" />
          <input id="evWhen" type="datetime-local" value="${localInputValue(new Date())}" />
          <input id="evNote" placeholder="Note (optional)" maxlength="200" />
          <button class="ev-save" id="evSave" type="button">Save event</button>
        </div>
        ${recent ? '<h3 class="section-title">Recent</h3>' + recent : ''}
        <p class="note">Events show up as amber dashes on the charts, and next to the time when you scrub over them.</p>`);
      el('evPresets').addEventListener('click', event => {
        const kind = event.target.dataset && event.target.dataset.kind;
        if (!kind) return;
        el('evKind').value = kind;
        [...el('evPresets').children].forEach(b => b.classList.toggle('sel', b === event.target));
      });
      el('evSave').addEventListener('click', async () => {
        const kind = el('evKind').value.trim();
        if (!kind) { el('evKind').focus(); return; }
        el('evSave').disabled = true;
        const at = el('evWhen').value ? new Date(el('evWhen').value).toISOString() : undefined;
        try {
          const response = await fetch('/api/events', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kind, at, note: el('evNote').value.trim() }),
          });
          if (!response.ok) throw new Error(String(response.status));
          await loadEvents();
          closeSheet();
        } catch (error) {
          el('evSave').disabled = false;
          alert('Could not save the event — try again.');
        }
      });
    }

    // ---- metric detail sheet: bigger chart, stats, dip zoom -------------------
    const SPANS = [
      { label: '30m', ms: 30 * 60 * 1000 },
      { label: '1h',  ms: 3600 * 1000 },
      { label: '3h',  ms: 3 * 3600 * 1000 },
      { label: '12h', ms: 12 * 3600 * 1000 },
      { label: '24h', ms: 24 * 3600 * 1000 },
    ];
    let msState = null;   // { key, spanMs, center } — center=null means "ends now"
    function msWindow() {
      if (msState.center != null) {
        const t1 = Math.min(Date.now(), msState.center + msState.spanMs / 2);
        return { t0: t1 - msState.spanMs, t1 };
      }
      return { t0: Date.now() - msState.spanMs, t1: Date.now() };
    }
    function openMetricSheet(key) {
      msState = { key, spanMs: 3 * 3600 * 1000, center: null };
      renderMetricSheet();
    }
    async function renderMetricSheet() {
      if (!msState) return;
      const metric = METRICS.find(m => m.key === msState.key);
      await ensureHistoryHours(Math.ceil((Date.now() - msWindow().t0) / 3600000));
      const { t0, t1 } = msWindow();
      const built = buildSeriesMarkup(msState.key, t0, t1, t0, t1, 360, 150, { clip: true, thresholds: true });
      const inWin = points[msState.key].filter(p => p.x >= t0 && p.x <= t1);

      let stats = '';
      if (inWin.length) {
        const values = inWin.map(p => p.y);
        const minV = Math.min(...values), maxV = Math.max(...values);
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const fourth = msState.key === 'o2'
          ? `<div><b>${Math.round((values.filter(v => v < 90).length / values.length) * 100)}%</b><span>time &lt;90</span></div>`
          : `<div><b>${values.length}</b><span>samples</span></div>`;
        stats = `<div class="ms-stats">
          <div><b>${metric.fmt(minV)}</b><span>min</span></div>
          <div><b>${metric.fmt(avg)}</b><span>avg</span></div>
          <div><b>${metric.fmt(maxV)}</b><span>max</span></div>
          ${fourth}</div>`;
      }

      // O₂ only: tap a dip to recenter a 30-minute window on it
      let dips = '';
      if (msState.key === 'o2') {
        const dipRuns = [];
        let run = null;
        for (const p of inWin) {
          if (p.y < 90) {
            if (!run) run = { start: p.x, end: p.x, min: p.y, count: 1 };
            else { run.end = p.x; run.min = Math.min(run.min, p.y); run.count += 1; }
          } else if (run) { if (run.count >= 2) dipRuns.push(run); run = null; }
        }
        if (run && run.count >= 2) dipRuns.push(run);
        if (dipRuns.length) {
          dips = '<div class="ms-dips">' + dipRuns.slice(-6).reverse().map(d =>
            `<button type="button" data-dip="${d.start}">
              <span>${fmtClock(new Date(d.start))} · ${fmtDur(Math.max(60, (d.end - d.start) / 1000))}</span>
              <b class="${d.min < 86 ? 'deep' : ''}">low ${Math.round(d.min)}%</b>
            </button>`).join('') + '</div>';
        }
      }

      const segButtons = SPANS.map(s =>
        `<button type="button" data-span="${s.ms}" class="${s.ms === msState.spanMs ? 'active' : ''}">${s.label}</button>`).join('');
      const focusIso = new Date(msState.center ?? (t1 - msState.spanMs / 2)).toISOString();
      openSheet(metric.label,
        `<div class="ms-top">
          <div class="ms-value" id="msValue">—<small> ${metric.unit}</small></div>
          <div class="ms-when" id="msWhen">touch the chart to read a moment</div>
        </div>
        <div class="ms-seg" id="msSeg">${segButtons}</div>
        <div class="ms-chartwrap" id="msChart">
          <svg viewBox="0 0 360 150" preserveAspectRatio="none" aria-hidden="true">${built.markup}</svg>
          ${built.max != null ? `<span class="ms-ylab" style="top:2px">${metric.fmt(built.max)}</span><span class="ms-ylab" style="bottom:2px">${metric.fmt(built.min)}</span>` : ''}
          <div class="ms-xline" id="msX" hidden></div>
        </div>
        <div class="ms-axis"><span>${fmtClock(new Date(t0))}</span><span>${msState.center == null ? 'now' : fmtClock(new Date(t1))}</span></div>
        ${stats}${dips}
        <a class="ms-link" href="/data?focus=${encodeURIComponent(focusIso)}&span=${Math.round(msState.spanMs / 60000)}">Open in the Data workbench →</a>`);

      el('msSeg').addEventListener('click', event => {
        const span = event.target.dataset && event.target.dataset.span;
        if (!span) return;
        msState.spanMs = Number(span);
        msState.center = null;   // picking a span returns to "ends now"
        renderMetricSheet();
      });
      const dipRack = el('sheetBody').querySelector('.ms-dips');
      if (dipRack) dipRack.addEventListener('click', event => {
        const target = event.target.closest('[data-dip]');
        if (!target) return;
        msState.center = Number(target.dataset.dip);
        msState.spanMs = 30 * 60 * 1000;
        renderMetricSheet();
      });
      const chart = el('msChart');
      const scrub = event => {
        const rect = chart.getBoundingClientRect();
        const frac = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
        const t = t0 + frac * (t1 - t0);
        const p = nearestPoint(points[msState.key], t);
        const gap = gapAt(t);
        el('msValue').innerHTML = (p ? metric.fmt(p.y) : '—') + `<small> ${metric.unit}</small>`;
        el('msWhen').textContent = p
          ? `at ${fmtClock(new Date(t))}`
          : `${gap ? (gap.kind === 'collector' ? 'collector was off' : 'sock was off') : 'no reading'} at ${fmtClock(new Date(t))}`;
        const x = el('msX'); x.hidden = false; x.style.left = (frac * 100) + '%';
      };
      chart.addEventListener('pointerdown', event => {
        try { chart.setPointerCapture(event.pointerId); } catch (error) { /* fine */ }
        scrub(event);
      });
      chart.addEventListener('pointermove', scrub);
    }
    document.querySelectorAll('.vital-expand').forEach(button => {
      button.addEventListener('pointerdown', event => event.stopPropagation());
      button.addEventListener('click', event => {
        event.stopPropagation();
        if (button.dataset.expand === 'sleep') openSleepSheet();
        else openMetricSheet(button.dataset.expand);
      });
    });

    // ---- sleep detail sheet: bigger hypnogram, split, sessions ----------------
    let sleepSheetState = null;
    function openSleepSheet() {
      sleepSheetState = { spanMs: 12 * 3600 * 1000 };
      renderSleepSheet();
    }
    async function renderSleepSheet() {
      if (!sleepSheetState) return;
      await ensureHistoryHours(Math.ceil(sleepSheetState.spanMs / 3600000));
      const t1 = Date.now(), t0 = t1 - sleepSheetState.spanMs;
      const built = buildSleepMarkup(t0, t1, t0, t1, 360, 150, { clip: true, bar: 12 });
      const inWin = sleepRuns.filter(r => r.end > t0 && r.start < t1)
        .map(r => ({ level: r.level, start: Math.max(r.start, t0), end: Math.min(r.end, t1) }));
      const sum = level => inWin.filter(r => r.level === level).reduce((a, r) => a + (r.end - r.start), 0);
      const lightMs = sum('light'), deepMs = sum('deep');
      let wakeUps = 0;
      for (let i = 1; i < inWin.length - 1; i++) {
        if (inWin[i].level === 'awake' && inWin[i - 1].level !== 'awake' && inWin[i + 1].level !== 'awake') wakeUps += 1;
      }
      const stats = `<div class="ms-stats">
        <div><b>${fmtDur((lightMs + deepMs) / 1000)}</b><span>asleep</span></div>
        <div><b>${fmtDur(lightMs / 1000)}</b><span>light</span></div>
        <div><b>${fmtDur(deepMs / 1000)}</b><span>deep</span></div>
        <div><b>${wakeUps}</b><span>wake-ups</span></div></div>`;
      const naps = I.sessions(rollups, new Date(t0), new Date(t1))
        .filter(run => run.state === 'asleep' && run.buckets >= 2);
      const sessionRows = naps.slice(-8).reverse().map(run => {
        const ongoing = (Date.now() - run.end) < 10 * 60 * 1000;
        return `<div class="row">
          <span>${fmtClock(new Date(run.start))} – ${ongoing ? 'now' : fmtClock(new Date(run.end))}</span>
          <b>${fmtDur((run.end - run.start) / 1000)}</b>
        </div>`;
      }).join('');
      const spans = [3, 12, 24].map(h =>
        `<button type="button" data-hours="${h}" class="${h * 3600 * 1000 === sleepSheetState.spanMs ? 'active' : ''}">${h}h</button>`).join('');
      openSheet('Sleep',
        `<div class="ms-top">
          <div class="ms-value" id="msValue">—</div>
          <div class="ms-when" id="msWhen">touch the chart to read a moment</div>
        </div>
        <div class="ms-seg" id="msSeg">${spans}</div>
        <div class="ms-chartwrap" id="msChart">
          <svg viewBox="0 0 360 150" preserveAspectRatio="none" aria-hidden="true">${built.markup}</svg>
          <span class="ms-ylab" style="top:calc(20% - 6px)">awake</span>
          <span class="ms-ylab" style="top:calc(50% - 6px)">light</span>
          <span class="ms-ylab" style="top:calc(80% - 6px)">deep</span>
          <div class="ms-xline" id="msX" hidden></div>
        </div>
        <div class="ms-axis"><span>${fmtClock(new Date(t0))}</span><span>now</span></div>
        ${stats}
        ${sessionRows ? '<h3 class="section-title" style="margin-top:16px">Sleep sessions</h3>' + sessionRows : ''}
        <a class="ms-link" href="/night">Tonight's full report →</a>`);
      el('msSeg').addEventListener('click', event => {
        const hours = event.target.dataset && event.target.dataset.hours;
        if (!hours) return;
        sleepSheetState.spanMs = Number(hours) * 3600 * 1000;
        renderSleepSheet();
      });
      const chart = el('msChart');
      const scrub = event => {
        const rect = chart.getBoundingClientRect();
        const frac = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
        const t = t0 + frac * (t1 - t0);
        const level = sleepLevelAt(t);
        const gap = gapAt(t);
        el('msValue').textContent = level ? SLEEP_WORD[level] : '—';
        el('msWhen').textContent = level
          ? `at ${fmtClock(new Date(t))}`
          : `${gap ? (gap.kind === 'collector' ? 'collector was off' : 'sock was off') : 'no reading'} at ${fmtClock(new Date(t))}`;
        const x = el('msX'); x.hidden = false; x.style.left = (frac * 100) + '%';
      };
      chart.addEventListener('pointerdown', event => {
        try { chart.setPointerCapture(event.pointerId); } catch (error) { /* fine */ }
        scrub(event);
      });
      chart.addEventListener('pointermove', scrub);
    }

    // ---- live vitals + narrative --------------------------------------------
    const bandText = (band, unit) => band
      ? `typical ${baselineState} range ${Math.round(band.low)}–${Math.round(band.high)}${unit}`
      : 'building her baseline — needs a couple of days';

    let sleepSessionText = 'watching for the first session';
    function updateHeroLive() {
      if (el('card-o2').classList.contains('inspecting')) return;
      el('o2Value').textContent = latest.o2 != null ? Math.round(latest.o2) : '—';
      el('hrValue').textContent = latest.hr != null ? Math.round(latest.hr) : '—';
      el('sleepValue').textContent = latest.sleepLevel ? SLEEP_WORD[latest.sleepLevel] : '—';
      el('moveValue').textContent = latest.move != null ? moveWord(latest.move) : '—';
      el('o2Band').textContent = bandText(bands.o2, '%');
      el('hrBand').textContent = bandText(bands.hr, '');
      el('sleepBand').textContent = sleepSessionText;
      el('moveBand').textContent = 'wiggle level — spikes while awake are normal';
      const o2Out = bands.o2 && latest.o2 != null && (latest.o2 < bands.o2.low || latest.o2 > bands.o2.high);
      const hrOut = bands.hr && latest.hr != null && (latest.hr < bands.hr.low || latest.hr > bands.hr.high);
      el('card-o2').className = 'vital card' +
        (latest.o2 != null && latest.o2 < 86 ? ' critical' : latest.o2 != null && latest.o2 < 90 ? ' low' : o2Out ? ' out' : '');
      el('card-hr').className = 'vital card' + (hrOut ? ' out' : '');
    }

    function render(widget) {
      const readings = liveReadings;
      const latestRow = readings[readings.length - 1] || null;
      const offline = latestRow ? isOffline(latestRow) : true;
      const stateText = latestRow && !offline ? stateLabel(latestRow.sleep_state) : null;

      // --- current sleep/wake session ------------------------------------
      const today = todayWindow();
      const runs = I.sessions(rollups, new Date(Date.now() - 18 * 3600 * 1000), new Date());
      const currentRun = runs.length ? runs[runs.length - 1] : null;
      const sleepRunsToday = I.sessions(rollups, today.start, today.end)
        .filter(run => run.state === 'asleep' && run.buckets >= 2).length;

      // --- baselines -------------------------------------------------------
      baselineState = currentRun && currentRun.state === 'asleep' ? 'asleep' : 'awake';
      bands.hr = I.baselineBand(rollups, 'hr', baselineState);
      bands.o2 = I.baselineBand(rollups, 'o2', baselineState);
      latest.hr = latestRow && !offline ? latestRow.heart_rate : null;
      latest.o2 = latestRow && !offline ? latestRow.oxygen_saturation : null;
      latest.temp = latestRow && !offline && latestRow.skin_temperature > 0 ? latestRow.skin_temperature : null;
      latest.sleepLevel = latestRow && !offline
        ? ({ '8': 'light', '15': 'deep' }[String(latestRow.sleep_state)] || 'awake')
        : null;
      sleepSessionText = currentRun && currentRun.state !== 'nodata'
        ? `${currentRun.state === 'asleep' ? 'asleep' : 'awake'} for ${fmtDur((Date.now() - currentRun.start) / 1000)}`
        : 'settling in';
      const recent = readings.slice(-24).filter(r => !isOffline(r));
      latest.move = !offline && recent.length
        ? recent.reduce((a, r) => a + (r.movement || 0), 0) / recent.length
        : null;
      latest.offline = offline;
      const temps = rollups.map(r => r.avg_skin_temperature).filter(v => v != null);
      tempRangeText = temps.length
        ? `${Math.min(...temps).toFixed(1)}–${Math.max(...temps).toFixed(1)}° over recent days`
        : '';
      updateHeroLive();

      // --- today so far ----------------------------------------------------
      let sleepToday = 0, dipsToday = 0, inDip = false;
      rollups.forEach(row => {
        const t = new Date(row.bucket_start);
        if (t < today.start) return;
        sleepToday += row.sleep_seconds || 0;
        const low = row.min_oxygen_saturation != null && row.min_oxygen_saturation < 90;
        if (low && !inDip) dipsToday += 1;
        inDip = low;
      });

      // --- battery night-readiness ----------------------------------------
      const batterySamples = readings.filter(r => r.battery != null)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.battery }));
      const battery = I.batteryProjection(batterySamples);
      const morning = new Date(); morning.setDate(morning.getDate() + (morning.getHours() >= 7 ? 1 : 0)); morning.setHours(7, 0, 0, 0);
      const hoursToMorning = (morning - Date.now()) / 3600000;
      let batteryText = '—', batterySub = '', batteryClass = '';
      if (battery) {
        batteryText = `${Math.round(battery.level)}%`;
        if (battery.charging) { batterySub = 'charging'; batteryClass = 'good'; }
        else if (battery.hoursLeft === Infinity) { batterySub = 'barely draining'; batteryClass = 'good'; }
        else if (battery.hoursLeft > hoursToMorning + 2) { batterySub = `~${Math.round(battery.hoursLeft)}h left — fine for tonight`; batteryClass = 'good'; }
        else { batterySub = `~${Math.round(battery.hoursLeft)}h left — charge before bed`; batteryClass = 'warn'; }
      } else if (widget.battery != null) {
        batteryText = `${Math.round(widget.battery)}%`;
      }
      batterySheetData = battery || widget.battery != null
        ? { text: batteryText, sub: batterySub, charging: !!(battery && battery.charging),
            hoursLeft: battery ? battery.hoursLeft : null }
        : null;

      // --- bedtime context (evenings) ---------------------------------------
      let bedtimeLine = '';
      const nowDate = new Date();
      if (nowDate.getHours() >= 18 || nowDate.getHours() < 6) {
        const nightStart = new Date(nowDate); if (nowDate.getHours() < 12) nightStart.setDate(nightStart.getDate() - 1);
        nightStart.setHours(18, 0, 0, 0);
        const bed = I.bedtime(rollups, nightStart, new Date());
        const typical = I.typicalBedtimeMinutes(rollups, 7);
        if (bed && typical) {
          let minutes = bed.getHours() * 60 + bed.getMinutes(); if (minutes < 720) minutes += 1440;
          const delta = Math.round(minutes - typical.mean);
          if (Math.abs(delta) >= 10) bedtimeLine = ` Fell asleep ${fmtClock(bed)} — about ${Math.abs(delta)} min ${delta < 0 ? 'earlier' : 'later'} than usual.`;
          else bedtimeLine = ` Fell asleep ${fmtClock(bed)}, right on schedule.`;
        } else if (bed) bedtimeLine = ` Fell asleep ${fmtClock(bed)}.`;
      }

      // --- status sentence ---------------------------------------------------
      let status;
      if (offline) {
        status = `<b>${deviceName}</b>'s sock isn't reporting right now — it may be off or charging.`;
      } else {
        const sessionText = currentRun && currentRun.state !== 'nodata'
          ? `${currentRun.state === 'asleep' ? 'asleep' : 'awake'} for <b>${fmtDur((Date.now() - currentRun.start) / 1000)}</b>`
          : 'settling in';
        const nth = sleepRunsToday ? ` — sleep #${sleepRunsToday} today` : '';
        status = `<b>${deviceName}</b> is ${stateText || 'doing fine'}, ${sessionText}${nth}.${bedtimeLine}`;
      }
      el('statusLine').innerHTML = status;

      const lastEvent = careEvents[0];
      el('belowHero').innerHTML = `
        <div class="strip">
          <button class="chip card" id="chipSleep"><b>${fmtDur(sleepToday)}</b><span>sleep today</span><span class="sub">tap for sessions</span></button>
          <button class="chip card ${dipsToday ? 'warn' : 'good'}" id="chipDips"><b>${dipsToday}</b><span>O₂ dips today</span><span class="sub">tap for detail</span></button>
          <button class="chip card ${batteryClass}" id="chipBattery"><b>${batteryText}</b><span>battery</span><span class="sub">${batterySub}</span></button>
          <button class="chip card" id="chipTemp"><b>${latest.temp != null ? latest.temp.toFixed(1) + '°' : '—'}</b><span>skin temp</span><span class="sub">${tempRangeText || 'tap for history'}</span></button>
          <button class="chip card" id="chipEvents"><b>⚑ Log</b><span>event</span>
            <span class="sub">${lastEvent ? 'last: ' + esc(lastEvent.kind) + ' ' + fmtClock(new Date(lastEvent.x)) : 'O₂ on/off, sock off…'}</span></button>
        </div>
        <div class="doors">
          <a class="door card" href="/night"><b>Last night's report →</b>
            <span>Sleep story, wake-ups, and every oxygen event, in plain language.</span></a>
          <a class="door card" href="/data"><b>The raw data →</b>
            <span>Full charts, tables, exports — every reading behind these numbers.</span></a>
        </div>`;
      el('chipSleep').addEventListener('click', openSleepSheet);
      el('chipTemp').addEventListener('click', () => openMetricSheet('temp'));
      el('chipDips').addEventListener('click', dipsSheet);
      el('chipBattery').addEventListener('click', batterySheet);
      el('chipEvents').addEventListener('click', eventsSheet);
    }

    async function refresh() {
      try {
        const [readings, widget] = await Promise.all([
          fetch('/api/readings?hours=1&limit=2000').then(r => r.json()),
          fetch('/api/widget?hours=24').then(r => r.json())
        ]);
        liveReadings = readings;
        rebuildPoints();
        render(widget);
        // a panned window stays frozen; live windows track the newest data
        if (!gesture && !momentumRaf && viewEnd == null) renderCharts();
      } catch (error) { /* keep last render */ }
    }

    async function boot() {
      // Rollups (baselines/sessions) can take seconds to compute server-side;
      // render live vitals immediately and fold history in when it arrives.
      const rollupsReady = fetch('/api/rollups?bucket=5m&hours=192&limit=100000')
        .then(r => r.json())
        .then(data => { rollups = data.rollups || []; })
        .catch(() => {});
      loadEvents();
      try {
        const [devices, accounts] = await Promise.all([
          fetch('/api/devices').then(r => r.json()),
          fetch('/api/accounts').then(r => r.json())
        ]);
        const device = (devices.devices || [])[0];
        if (device) deviceName = device.baby_name || device.name || deviceName;
        const account = (accounts.accounts || [])[0];
        if (account && account.poll_interval_seconds) pollSeconds = account.poll_interval_seconds;
      } catch (error) {
        el('statusLine').textContent = 'Could not load readings — is the collector running?';
        return;
      }
      await refresh();
      rollupsReady.then(refresh);
      setInterval(refresh, Math.max(5, pollSeconds) * 1000);
      setInterval(async () => {  // refresh baselines occasionally
        const data = await fetch('/api/rollups?bucket=5m&hours=192&limit=100000').then(r => r.json()).catch(() => null);
        if (data) rollups = data.rollups || rollups;
      }, 5 * 60 * 1000);
      setInterval(loadEvents, 5 * 60 * 1000);
    }
    boot();
  </script>"""


def render_now_page() -> str:
    return render_shell(
        view="now",
        title="Today",
        head=NOW_HEAD,
        body=NOW_BODY,
        scripts=NOW_SCRIPTS,
    )
