"""'Today' — the app's home. The ten-second check: live vitals with personal
context, today so far, and doors into the deeper views. The hero charts are
touchable: tap or hold to read a value, pull right to scroll back in time.
Chips open detail sheets, and care events (O₂ on/off, sock off…) can be
logged and show up as markers on the charts."""

from __future__ import annotations

from app.shell import render_shell

NOW_HEAD = """<link rel="manifest" href="/manifest.webmanifest" />
  <style>
    .today-head { display: flex; justify-content: space-between; align-items: flex-start;
      flex-wrap: wrap; gap: 8px 16px; margin-bottom: 22px; }
    .status-line { font-size: 17px; color: var(--dim); line-height: 1.5; margin: 0;
      max-width: 70ch; flex: 1 1 320px; }
    .status-line .st-short { display: none; }
    /* Phones: one line — short status text beside a compact picker. */
    @media (max-width: 640px) {
      .today-head { flex-wrap: nowrap; align-items: center; }
      .status-line { flex: 1 1 auto; min-width: 0; font-size: 15px; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; }
      .status-line .st-full { display: none; }
      .status-line .st-short { display: inline; }
      .range-seg button, .range-seg .rs-custom { font-size: 11px; padding: 4px 7px; }
    }
    .status-line b { color: var(--ink); font-weight: 600; }
    .range-seg { display: flex; background: var(--accent-soft); border-radius: 999px;
      padding: 3px; margin-left: auto; flex: 0 0 auto; }
    .range-seg button { all: unset; cursor: pointer; font-size: 12px; font-weight: 600;
      color: var(--dim); padding: 5px 11px; border-radius: 999px;
      font-variant-numeric: tabular-nums; }
    .range-seg button.active { background: var(--surface); color: var(--accent);
      box-shadow: 0 2px 8px rgba(0, 0, 0, .12); }
    .range-seg .rs-custom { font-size: 12px; font-weight: 600; color: var(--accent);
      background: var(--surface); padding: 5px 11px; border-radius: 999px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, .12); }
    .range-seg .rs-custom[hidden] { display: none; }
    .hero { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
    @media (max-width: 640px) { .hero { grid-template-columns: 1fr; } }
    .hero-minor { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 8px; }
    .vital { padding: 22px 22px 76px; position: relative; overflow: hidden;
      touch-action: pan-y; user-select: none; -webkit-user-select: none; cursor: grab; }
    .vital.dragging { cursor: grabbing; }
    .vital.placing { cursor: crosshair; }
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
    /* amber = the sock isn't on her properly (same language as the title dot);
       grey stays for charging and collector-off */
    .chartzone .ghostline.warn, .ms-chartwrap .ghostline.warn { stroke: var(--awake); }
    .gaplabels span.warn { color: var(--awake); }
    /* hypnogram: rounded state bars in three lanes, tracker-style, with thin
       gradient connectors between stages the way Apple draws transitions */
    /* Butt caps: rounded ones extend half the bar width past each end and
       read as stages overlapping in time. */
    .chartzone .sleepbar, .ms-chartwrap .sleepbar { fill: none; stroke-linecap: butt;
      vector-effect: non-scaling-stroke; }
    .sleepbar.sleep-awake { stroke: var(--awake); }
    .sleepbar.sleep-light { stroke: var(--sleep-light); }
    .sleepbar.sleep-deep { stroke: var(--sleep-deep); }
    .chartzone .sleepconn, .ms-chartwrap .sleepconn { fill: none; stroke-width: 2px;
      opacity: .45; stroke-linecap: round; vector-effect: non-scaling-stroke; }
    #card-sleep .value { text-transform: lowercase; }
    /* gap captions: tiny inline label naming why the line is dotted there */
    .gaplabels { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
    .gaplabels span { position: absolute; transform: translateX(-50%);
      font-size: 9px; letter-spacing: .09em; text-transform: uppercase;
      color: var(--faint); white-space: nowrap; }
    .vital-expand { all: unset; position: absolute; top: 10px; right: 10px; z-index: 2;
      cursor: pointer; color: var(--faint); padding: 7px 9px; border-radius: 9px;
      font-size: 14px; line-height: 1; }
    .vital-expand:hover { color: var(--accent); background: var(--accent-soft); }
    .vital-o2toggle { all: unset; position: absolute; top: 10px; right: 44px; z-index: 2;
      cursor: pointer; font-size: 11px; font-weight: 700; padding: 6px 10px;
      border-radius: 999px; color: var(--faint); border: 1px solid var(--surface-line);
      line-height: 1; transition: color .35s ease, background-color .35s ease,
      border-color .35s ease; }
    .vital-o2toggle:hover { color: var(--accent); border-color: var(--accent); }
    .vital-o2toggle.on { color: var(--o2-on); background: color-mix(in srgb, var(--o2-on) 12%, transparent);
      border-color: color-mix(in srgb, var(--o2-on) 40%, transparent); }
    .vital-o2toggle.arming { color: #fff; background: var(--accent);
      border-color: var(--accent); }
    .vital.placing { outline: 2px solid var(--accent); outline-offset: -1px; }
    .place-hint { position: absolute; left: 50%; top: 44px; transform: translateX(-50%);
      z-index: 3; background: var(--accent); color: #fff; font-size: 11px;
      font-weight: 600; padding: 5px 12px; border-radius: 999px; white-space: nowrap;
      pointer-events: none; }
    .place-hint[hidden] { display: none; }

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
    .chip.o2-on { border-color: color-mix(in srgb, var(--o2-on) 45%, transparent); }
    .chip.o2-on b { color: var(--o2-on); }
    /* on-O2 atmosphere: a wispy tint rising from the chart floor — oxygen
       blue while on, grey while (logged) off, cross-fading at transitions */
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
    .prep { padding: 16px 18px 14px; margin-bottom: 12px; }
    .prep-top { display: flex; justify-content: space-between; align-items: baseline;
      gap: 12px; margin-bottom: 10px; }
    .prep-top b { font-size: 15px; }
    .prep-top span { font-size: 12px; color: var(--faint); white-space: nowrap;
      font-variant-numeric: tabular-nums; }
    .prep-facts { display: grid; gap: 6px; font-size: 13px; color: var(--dim); }
    .prep-facts b { color: var(--ink); font-variant-numeric: tabular-nums; }
    .prep-note { font-size: 13px; color: var(--dim); line-height: 1.5; margin: 10px 0 0; }
    .prep-feed-btn { font: inherit; font-size: 12px; font-weight: 600; color: var(--accent);
      background: var(--accent-soft); border: 0; border-radius: 999px; padding: 2px 10px;
      margin-left: 6px; cursor: pointer; }
    .prep-feed-btn:hover { filter: brightness(.96); }
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
    .sheet .row-del { all: unset; cursor: pointer; color: var(--faint); padding: 0 6px;
      font-size: 12px; flex: none; }
    .sheet .row-del:hover { color: var(--bad); }
    .sheet .row b:empty { display: none; }
    .feed-logrow { display: flex; align-items: center; gap: 12px; margin-top: 14px; }
    .feed-logrow label { display: flex; align-items: center; gap: 7px; font-size: 13px;
      color: var(--dim); flex: none; }
    .feed-logrow input[type="time"] { padding: 9px 10px; border: 1px solid var(--surface-line);
      border-radius: var(--radius-control); background: var(--surface); color: var(--ink);
      font-size: 13.5px; }
    .feed-logrow .o2-action { flex: 1; }
    .feed-note { width: 100%; box-sizing: border-box; padding: 10px 12px;
      border: 1px solid var(--surface-line); border-radius: var(--radius-control);
      background: var(--surface); color: var(--ink); font-size: 13.5px; margin-bottom: 2px; }
    .o2-state { text-align: center; margin-bottom: 14px; }
    .o2-state b { display: block; font-size: 24px; letter-spacing: -.01em; }
    .o2-state.on b { color: var(--accent); }
    .o2-state span { font-size: 12.5px; color: var(--dim); }
    .flow-presets { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
      margin-bottom: 12px; }
    .flow-presets button { all: unset; box-sizing: border-box; text-align: center; cursor: pointer;
      padding: 10px 4px; border: 1px solid var(--surface-line); border-radius: var(--radius-control);
      font-size: 13px; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
    .flow-presets button:hover, .flow-presets button.sel { border-color: var(--accent);
      color: var(--accent); background: var(--accent-soft); }
    .o2-action { all: unset; box-sizing: border-box; display: block; width: 100%;
      text-align: center; cursor: pointer; padding: 12px 0;
      border-radius: var(--radius-control); background: var(--accent); color: #fff;
      font-size: 14px; font-weight: 700; }
    .o2-action.stop { background: transparent; color: var(--bad);
      border: 1px solid color-mix(in srgb, var(--bad) 40%, transparent); }
    .o2-action[disabled] { opacity: .5; cursor: default; }
    .sheet .section-title { margin-top: 18px; }
    @media (prefers-reduced-motion: reduce) { .chartzone svg g { transition: none !important; } }
  </style>"""

_VITAL_CARD = """<div class="vital card{minor}" id="card-{key}" data-metric="{key}">
        {extra}<button class="vital-expand" data-expand="{key}" type="button"
          aria-label="Expand {label} chart" title="Bigger chart &amp; stats">⤢</button>
        <span class="label">{label}</span>
        <div class="value"><span id="{key}Value">—</span><small id="{key}Unit"> {unit}</small></div>
        <div class="band" id="{key}Band"></div>
        <div class="chartzone">
          <svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true"><g id="{key}G"></g></svg>
          <div class="gaplabels" id="{key}Gaps"></div>
          <div class="xline" id="{key}X" hidden></div>
        </div>
      </div>"""

NOW_BODY = (
    """<div class="today-head">
      <p class="status-line" id="statusLine">Checking in…</p>
      <div class="range-seg" id="rangeSeg" role="group" aria-label="Chart window">
        <button type="button" data-mins="60">1h</button>
        <button type="button" data-mins="180">3h</button>
        <button type="button" data-mins="360">6h</button>
        <button type="button" data-mins="720">12h</button>
        <button type="button" data-mins="1440">24h</button>
        <span class="rs-custom" id="rangeCustom" hidden>Custom</span>
      </div>
    </div>
    <div class="hero">"""
    + _VITAL_CARD.format(minor="", key="o2", label="Oxygen", unit="%", extra=(
        '<button class="vital-o2toggle" id="o2ToggleBtn" type="button" '
        'title="Log supplemental O\u2082 on/off at a point on the chart">O\u2082</button>'
        '<div class="place-hint" id="placeHint" hidden></div>'))
    + _VITAL_CARD.format(minor="", key="hr", label="Heart rate", unit="bpm", extra="")
    + """</div>
    <div class="hero-minor">"""
    + _VITAL_CARD.format(minor=" minor", key="sleep", label="Sleep", unit="", extra="")
    + _VITAL_CARD.format(minor=" minor", key="move", label="Movement", unit="", extra="")
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
    const capitalized = s => s.charAt(0).toUpperCase() + s.slice(1);
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
    const WINDOW_CHOICES = [60, 180, 360, 720, 1440];
    let windowMs = (() => {
      const saved = Number(localStorage.getItem('owletTodayWindow'));
      return WINDOW_CHOICES.includes(saved) ? saved * 60 * 1000 : 60 * 60 * 1000;
    })();
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
    // Display prefs (settings modal): the chart can ride Owlet's smoothed O₂
    // line or its normalized 0–100 activity level instead of the raw feeds.
    let DISPLAY = { o2: 'raw', move: 'raw' };
    function rebuildPoints() {
      const rows = allReadings();
      const valid = rows.filter(r => !isOffline(r));
      const o2Of = r => DISPLAY.o2 === 'smoothed' && r.oxygen_10_av > 0
        ? r.oxygen_10_av : r.oxygen_saturation;
      const moveOf = r => DISPLAY.move === 'bucket' && r.movement_bucket != null
        ? r.movement_bucket : (r.movement || 0);
      points.hr = valid.filter(r => r.heart_rate > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.heart_rate }));
      points.o2 = valid.filter(r => o2Of(r) > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: o2Of(r) }));
      points.temp = valid.filter(r => r.skin_temperature > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.skin_temperature }));
      points.move = valid.map(r => ({ x: Date.parse(r.recorded_at), y: moveOf(r) }));
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
    // How long the current asleep/awake stretch has run, straight from the
    // readings (rollup sessions lag and often read 'settling in'). Adjacent
    // runs of the same family merge across brief gaps; if the stretch reaches
    // the edge of the loaded buffer, the rollup session extends it further
    // back when it agrees on the state.
    function currentStateSince(rollupRun) {
      if (!sleepRuns.length) return null;
      const last = sleepRuns[sleepRuns.length - 1];
      if (Date.now() - last.end > GAP_MS * 2) return null;   // no live state
      const asleep = last.level !== 'awake';
      let start = last.start;
      for (let i = sleepRuns.length - 2; i >= 0; i--) {
        const run = sleepRuns[i];
        if ((run.level !== 'awake') !== asleep) break;
        if (start - run.end > GAP_MS * 4) break;
        start = run.start;
      }
      if (rollupRun && rollupRun.state !== 'nodata'
        && (rollupRun.state === 'asleep') === asleep
        && rollupRun.start < start && start - loadedStart() < 10 * 60 * 1000) {
        start = rollupRun.start;
      }
      return { asleep, start };
    }
    function sleepLevelAt(t) {
      const run = sleepRuns.find(r => t >= r.start - GAP_MS && t <= r.end + GAP_MS);
      return run ? run.level : null;
    }
    function computeGaps(rows) {
      const out = [];
      let sockRun = null;
      // Rows keep flowing while the sock itself is silent, so we can usually
      // say WHY: the sock's own charging flag (exact), battery climbing as a
      // fallback for old rows without it, explicit disconnect flag, or plain
      // sock-off. No rows at all = the collector wasn't running.
      const finishSockRun = run => {
        run.label = run.charging
          ? 'charging'
          : run.battery0 != null && run.battery1 != null && run.battery1 - run.battery0 > 1
            ? 'charging'
            : (run.disconnected ? 'disconnected' : 'sock off');
        return run;
      };
      for (let i = 0; i < rows.length; i++) {
        const t = Date.parse(rows[i].recorded_at);
        if (i > 0) {
          const prev = Date.parse(rows[i - 1].recorded_at);
          if (t - prev > 2 * 60 * 1000) out.push({ start: prev, end: t, kind: 'collector', label: 'collector off' });
        }
        if (isOffline(rows[i])) {
          const battery = rows[i].battery;
          if (!sockRun) sockRun = { start: t, end: t, kind: 'sock', battery0: battery, battery1: battery, disconnected: false, charging: false };
          else {
            sockRun.end = t;
            if (battery != null) { sockRun.battery1 = battery; if (sockRun.battery0 == null) sockRun.battery0 = battery; }
          }
          if (rows[i].sock_disconnected) sockRun.disconnected = true;
          if (rows[i].charging) sockRun.charging = true;
        } else if (sockRun) { out.push(finishSockRun(sockRun)); sockRun = null; }
      }
      if (sockRun) { sockRun.end = Date.now(); out.push(finishSockRun(sockRun)); }
      if (rows.length) {
        const lastT = Date.parse(rows[rows.length - 1].recorded_at);
        if (Date.now() - lastT > 2 * 60 * 1000) out.push({ start: lastT, end: Date.now(), kind: 'collector', label: 'collector off' });
        const firstT = Date.parse(rows[0].recorded_at);
        if (firstT - loadedStart() > 2 * 60 * 1000) out.unshift({ start: loadedStart(), end: firstT, kind: 'collector', label: 'collector off' });
      }
      return out;
    }
    // Small inline captions naming each gap wide enough to carry one.
    function gapLabelSpans(t0, t1, minFrac, ghostYs) {
      return gaps
        .filter(g => g.end > t0 && g.start < t1
          && (Math.min(g.end, t1) - Math.max(g.start, t0)) / (t1 - t0) >= minFrac)
        .map(g => {
          const mid = (Math.max(g.start, t0) + Math.min(g.end, t1)) / 2;
          const yFrac = ghostYs && ghostYs[g.start] != null ? ghostYs[g.start] : null;
          const top = yFrac == null ? 'top:5px' : `top:max(2px, calc(${(yFrac * 100).toFixed(1)}% - 16px))`;
          return `<span class="${gapWarn(g) ? 'warn' : ''}" style="left:${(((mid - t0) / (t1 - t0)) * 100).toFixed(2)}%;${top}">${esc(g.label)}</span>`;
        }).join('');
    }
    function gapAt(t) { return gaps.find(g => t >= g.start && t <= g.end) || null; }
    const gapWarn = g => g.label === 'disconnected' || g.label === 'sock off';
    function lastPointBefore(pts, t) {
      if (!pts.length || pts[0].x > t) return null;
      let lo = 0, hi = pts.length - 1;
      while (lo < hi) { const mid = (lo + hi + 1) >> 1; (pts[mid].x <= t ? lo = mid : hi = mid - 1); }
      return pts[lo];
    }
    function firstPointAfter(pts, t) {
      if (!pts.length || pts[pts.length - 1].x < t) return null;
      let lo = 0, hi = pts.length - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; (pts[mid].x >= t ? hi = mid : lo = mid + 1); }
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
        // Re-render immediately, even mid-drag — pan position derives from
        // viewEnd, so re-anchoring under the finger is seamless, and the
        // freshly loaded points appear while the graph is still moving.
        renderCharts();
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
        const data = await fetch('/api/events?hours=336&limit=2000').then(r => r.json());
        careEvents = (data.events || []).map(e => ({ ...e, x: Date.parse(e.at) }));
        computeO2();
        if (!gesture) renderCharts();
      } catch (error) { /* non-fatal */ }
    }

    // ---- supplemental O2: state + intervals from on/off events -------------
    let o2State = { on: false, since: null, flow: '' };
    let o2Spans = [];
    let o2HasLog = false;
    function computeO2() {
      const marks = careEvents
        .filter(e => e.kind === 'O₂ on' || e.kind === 'O₂ off')
        .sort((a, b) => a.x - b.x);
      o2HasLog = marks.length > 0;
      const spans = [];
      let open = null, flow = '';
      for (const mark of marks) {
        if (mark.kind === 'O₂ on') {
          if (open && (mark.note || '') !== flow) {     // flow change while on
            spans.push({ start: open.x, end: mark.x, flow, startId: open.id, endId: null });
            open = mark;
          } else if (!open) open = mark;
          flow = mark.note || flow;
        } else if (open) {
          spans.push({ start: open.x, end: mark.x, flow, startId: open.id, endId: mark.id });
          open = null; flow = '';
        }
      }
      if (open) spans.push({ start: open.x, end: Infinity, flow, startId: open.id, endId: null });
      o2Spans = spans;
      o2State = open
        ? { on: true, since: open.x, flow }
        : { on: false, since: marks.length ? marks[marks.length - 1].x : null, flow: '' };
      paintO2Toggle();
    }
    const onO2At = t => o2Spans.some(s => t >= s.start && t <= s.end);
    // A single rect carries the whole on/off timeline: a horizontal gradient
    // encodes the states (oxygen blue / grey) with soft stops at each
    // transition, and a vertical mask fades it out rising from the floor.
    function o2OverlayMarkup(t0, t1, dataStart, dataEnd, w, h, clip, pid, clipPoly) {
      if (!o2HasLog) return '';
      const xOf = t => ((t - t0) / (t1 - t0)) * w;
      const span = dataEnd - dataStart;
      const fade = Math.max(90 * 1000, span * 0.02);
      const colorFor = state => state === 'on' ? 'var(--o2-on)' : 'var(--faint)';
      const offsetOf = time => Math.max(0, Math.min(1, (time - dataStart) / span)).toFixed(4);
      const marks = [];
      o2Spans.forEach(s => {
        marks.push({ t: s.start, to: 'on' });
        if (s.end !== Infinity) marks.push({ t: s.end, to: 'off' });
      });
      marks.sort((a, b) => a.t - b.t);
      let state = onO2At(dataStart) ? 'on' : 'off';
      let stops = `<stop offset="0" style="stop-color:${colorFor(state)}"/>`;
      marks.filter(m => m.t > dataStart && m.t < dataEnd).forEach(m => {
        stops += `<stop offset="${offsetOf(m.t - fade)}" style="stop-color:${colorFor(state)}"/>`;
        state = m.to;
        stops += `<stop offset="${offsetOf(m.t + fade)}" style="stop-color:${colorFor(state)}"/>`;
      });
      stops += `<stop offset="1" style="stop-color:${colorFor(onO2At(dataEnd) ? 'on' : 'off')}"/>`;
      const x0 = xOf(dataStart), x1 = xOf(Math.min(dataEnd, Date.now()));
      if (x1 - x0 < 0.5) return '';
      const rect = `x="${x0.toFixed(1)}" y="0" width="${(x1 - x0).toFixed(1)}" height="${h}"`;
      // Clipped to the area under the data line when there is one (the wisp
      // "bumps up to each point"); otherwise a short floor-hugging fade.
      const vStops = clipPoly
        ? '<stop offset="0" stop-color="#fff" stop-opacity=".34"/>'
          + '<stop offset=".55" stop-color="#fff" stop-opacity=".14"/>'
          + '<stop offset="1" stop-color="#fff" stop-opacity=".05"/>'
        : '<stop offset="0" stop-color="#fff" stop-opacity=".26"/>'
          + '<stop offset=".28" stop-color="#fff" stop-opacity=".10"/>'
          + '<stop offset=".5" stop-color="#fff" stop-opacity="0"/>';
      const clipDef = clipPoly ? `<clipPath id="${pid}-o2c"><polygon points="${clipPoly}"/></clipPath>` : '';
      const clipAttr = clipPoly ? ` clip-path="url(#${pid}-o2c)"` : '';
      return `<defs>
        <linearGradient id="${pid}-o2h" x1="0" y1="0" x2="1" y2="0">${stops}</linearGradient>
        <linearGradient id="${pid}-o2v" x1="0" y1="1" x2="0" y2="0">${vStops}</linearGradient>
        <mask id="${pid}-o2m"><rect ${rect} fill="url(#${pid}-o2v)"/></mask>
        ${clipDef}
      </defs>
      <rect ${rect} fill="url(#${pid}-o2h)" mask="url(#${pid}-o2m)"${clipAttr}/>`;
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
      const eventMarks = careEvents
        .filter(e => e.x >= dataStart && e.x <= dataEnd && e.kind !== 'O₂ on' && e.kind !== 'O₂ off')
        .map(e => `<line class="evline" x1="${xOf(e.x).toFixed(2)}" x2="${xOf(e.x).toFixed(2)}" y1="0" y2="${h}"><title>${esc(e.kind)}</title></line>`
          + `<circle class="evflag" cx="${xOf(e.x).toFixed(2)}" cy="3" r="2"/>`)
        .join('');
      const pts = downsample(points[key].filter(p => p.x >= dataStart && p.x <= dataEnd));
      const overlayId = (opts.idPrefix || 'h') + '-' + key;
      const wantsO2 = key === 'o2' || key === 'hr';   // the vitals oxygen influences
      if (pts.length < 2) {
        const bare = wantsO2 ? o2OverlayMarkup(t0, t1, dataStart, dataEnd, w, h, !!opts.clip, overlayId, null) : '';
        return { markup: bare + eventMarks, min: null, max: null, ghostYs: {} };
      }
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
      const ghostYs = {};
      const ghosts = gaps
        .filter(g => g.end >= dataStart && g.start <= dataEnd && g.end - g.start > GAP_MS)
        .map(g => {
          // Anchor on the reading before the gap, or the one after it when the
          // earlier history simply isn't loaded yet — the line always draws.
          const anchor = lastPointBefore(points[key], g.start + 1000)
            || firstPointAfter(points[key], g.end - 1000);
          if (!anchor) return '';
          const gy = Math.max(2, Math.min(h - 2, yOf(anchor.y)));
          ghostYs[g.start] = gy / h;
          const x0 = opts.clip ? clampX(xOf(g.start)) : xOf(g.start);
          const x1 = opts.clip ? clampX(xOf(g.end)) : xOf(g.end);
          if (x1 - x0 < 0.5) return '';
          return `<line class="ghostline${gapWarn(g) ? ' warn' : ''}" x1="${x0.toFixed(2)}" x2="${x1.toFixed(2)}" y1="${gy.toFixed(2)}" y2="${gy.toFixed(2)}"/>`;
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
      const clipPoly = `${xOf(pts[0].x).toFixed(1)},${h} `
        + pts.map(p => `${xOf(p.x).toFixed(1)},${yOf(p.y).toFixed(1)}`).join(' ')
        + ` ${xOf(pts[pts.length - 1].x).toFixed(1)},${h}`;
      const o2Overlay = wantsO2
        ? o2OverlayMarkup(t0, t1, dataStart, dataEnd, w, h, !!opts.clip, overlayId, clipPoly)
        : '';
      return { markup: o2Overlay + thresholds + ghosts + eventMarks + lines, min: domainMin, max: domainMax, ghostYs };
    }

    // Tracker-style hypnogram: rounded bars in three lanes (awake / light / deep).
    function buildSleepMarkup(t0, t1, dataStart, dataEnd, w, h, opts = {}) {
      const xOf = t => ((t - t0) / (t1 - t0)) * w;
      const clampX = x => Math.max(0, Math.min(w, x));
      const eventMarks = careEvents
        .filter(e => e.x >= dataStart && e.x <= dataEnd && e.kind !== 'O₂ on' && e.kind !== 'O₂ off')
        .map(e => `<line class="evline" x1="${xOf(e.x).toFixed(2)}" x2="${xOf(e.x).toFixed(2)}" y1="0" y2="${h}"><title>${esc(e.kind)}</title></line>`
          + `<circle class="evflag" cx="${xOf(e.x).toFixed(2)}" cy="3" r="2"/>`)
        .join('');
      const o2Overlay = '';
      const lanes = { awake: h * 0.2, light: h * 0.5, deep: h * 0.8 };
      // Gradients keyed to lane positions (userSpaceOnUse), so a connector
      // blends from one stage's color into the next no matter its direction —
      // the Apple Health transition look.
      const pid = opts.idPrefix || 'hyp';
      const laneColor = { awake: 'var(--awake)', light: 'var(--sleep-light)', deep: 'var(--sleep-deep)' };
      const pairs = [['awake', 'light'], ['light', 'deep'], ['awake', 'deep']];
      const defs = '<defs>' + pairs.map(([a, b]) =>
        `<linearGradient id="${pid}-${a}-${b}" gradientUnits="userSpaceOnUse" x1="0" x2="0" y1="${lanes[a].toFixed(2)}" y2="${lanes[b].toFixed(2)}">
          <stop offset="0" style="stop-color:${laneColor[a]}"/>
          <stop offset="1" style="stop-color:${laneColor[b]}"/>
        </linearGradient>`).join('') + '</defs>';
      const gradientFor = (a, b) => {
        const pair = pairs.find(p => (p[0] === a && p[1] === b) || (p[0] === b && p[1] === a));
        return `${pid}-${pair[0]}-${pair[1]}`;
      };
      const connectors = [];
      for (let i = 1; i < sleepRuns.length; i++) {
        const a = sleepRuns[i - 1], b = sleepRuns[i];
        if (a.level === b.level || b.start - a.end > GAP_MS * 3) continue;
        const xm = (a.end + b.start) / 2;
        if (xm < dataStart || xm > dataEnd) continue;
        const x = (opts.clip ? clampX(xOf(xm)) : xOf(xm)).toFixed(2);
        connectors.push(`<line class="sleepconn" x1="${x}" x2="${x}" y1="${lanes[a.level].toFixed(2)}" y2="${lanes[b.level].toFixed(2)}" stroke="url(#${gradientFor(a.level, b.level)})"/>`);
      }
      const bars = sleepRuns
        .filter(r => r.end >= dataStart && r.start <= dataEnd)
        .map(r => {
          const x0 = opts.clip ? clampX(xOf(r.start)) : xOf(r.start);
          const x1 = opts.clip ? clampX(xOf(r.end)) : xOf(r.end);
          if (x1 - x0 < 0.4) return '';
          const y = lanes[r.level].toFixed(2);
          return `<line class="sleepbar sleep-${r.level}" x1="${x0.toFixed(2)}" x2="${x1.toFixed(2)}" y1="${y}" y2="${y}" style="stroke-width:${opts.bar || 5}px"/>`;
        }).join('');
      const ghostYs = {};
      const ghosts = gaps
        .filter(g => g.end >= dataStart && g.start <= dataEnd && g.end - g.start > GAP_MS)
        .map(g => {
          const anchor = sleepRuns.filter(r => r.end <= g.start + 1000).pop()
            || sleepRuns.find(r => r.start >= g.end - 1000);
          if (!anchor) return '';
          ghostYs[g.start] = lanes[anchor.level] / h;
          const x0 = opts.clip ? clampX(xOf(g.start)) : xOf(g.start);
          const x1 = opts.clip ? clampX(xOf(g.end)) : xOf(g.end);
          if (x1 - x0 < 0.5) return '';
          const y = lanes[anchor.level].toFixed(2);
          return `<line class="ghostline${gapWarn(g) ? ' warn' : ''}" x1="${x0.toFixed(2)}" x2="${x1.toFixed(2)}" y1="${y}" y2="${y}"/>`;
        }).join('');
      return { markup: defs + o2Overlay + ghosts + eventMarks + connectors.join('') + bars, ghostYs };
    }

    function renderChart(key) {
      const g = el(key + 'G'); if (!g) return;
      const end = chartEnd();
      const built = key === 'sleep'
        ? buildSleepMarkup(end - windowMs, end, end - 2 * windowMs, end + windowMs / 4, 100, 42)
        : buildSeriesMarkup(key, end - windowMs, end, end - 2 * windowMs, end + windowMs / 4, 100, 42);
      g.innerHTML = built.markup;
      g.removeAttribute('transform');
      const labels = el(key + 'Gaps');
      if (labels) { labels.innerHTML = gapLabelSpans(end - windowMs, end, 0.16, built.ghostYs); labels.style.transform = ''; }
    }
    function renderCharts() {
      anchorEnd = chartEnd();
      HERO_KEYS.forEach(renderChart);
      updateTimescale();
    }
    function applyPan() {
      const shift = ((anchorEnd - chartEnd()) / windowMs) * 100;
      if (Math.abs(shift) > 85) { renderCharts(); return; }
      const t = `translate(${shift.toFixed(3)} 0)`;
      HERO_KEYS.forEach(key => {
        el(key + 'G').setAttribute('transform', t);
        el(key + 'Gaps').style.transform = `translateX(${shift.toFixed(3)}%)`;
      });
      updateTimescale();
    }
    // While the graph is moving, a center reticle reads out whatever passes
    // beneath it — the big numbers become "the value at the middle".
    function panFocus() {
      inspectAtTime(chartEnd() - windowMs / 2, 0.5);
    }
    const fmtTick = date => {
      const label = fmtClock(date);
      return date.toDateString() === new Date().toDateString()
        ? label
        : `${date.getMonth() + 1}/${date.getDate()} ${label}`;
    };
    function updateTimescale() {
      const end = chartEnd();
      el('tsStart').textContent = fmtTick(new Date(end - windowMs));
      el('tsEnd').textContent = viewEnd == null ? 'now' : fmtTick(new Date(end));
      const chip = el('tsLive');
      chip.textContent = viewEnd == null ? '● live' : '⟳ back to now';
      chip.classList.toggle('paused', viewEnd != null);
    }
    el('tsLive').addEventListener('click', () => {
      stopMomentum();
      if (viewEnd == null) { clearInspect(); return; }
      viewEnd = null; clearInspect(); renderCharts();
    });

    // ---- window picker (top right): sets the span all four charts show ----
    function paintRangeSeg() {
      let preset = false;
      el('rangeSeg').querySelectorAll('button').forEach(button => {
        const hit = Number(button.dataset.mins) * 60 * 1000 === windowMs;
        button.classList.toggle('active', hit);
        preset = preset || hit;
      });
      el('rangeCustom').hidden = preset;
    }
    paintRangeSeg();
    el('rangeSeg').addEventListener('click', async event => {
      const mins = event.target.dataset && event.target.dataset.mins;
      if (!mins) return;
      stopMomentum();
      windowMs = Number(mins) * 60 * 1000;
      localStorage.setItem('owletTodayWindow', mins);
      viewEnd = null;             // a new span always starts back at "now"
      paintRangeSeg();
      clearInspect();
      renderCharts();
      await ensureHistoryHours(Math.ceil(windowMs / 3600000));
      renderCharts();
    });

    // ---- zoom: wheel and pinch; the picker shows "Custom" off-preset ----
    const MIN_WINDOW_MS = 10 * 60 * 1000, MAX_WINDOW_MS = 24 * 3600 * 1000;
    function zoomAround(anchorT, factor) {
      const next = Math.min(MAX_WINDOW_MS, Math.max(MIN_WINDOW_MS, windowMs * factor));
      if (next === windowMs) return;
      const end = chartEnd();
      const frac = (end - anchorT) / windowMs;   // anchor's distance from the right edge
      windowMs = next;
      let newEnd = anchorT + frac * windowMs;
      const nowMs = Date.now();
      viewEnd = newEnd >= nowMs - 5000 ? null : Math.min(newEnd, nowMs);
      paintRangeSeg();
      renderCharts();
      ensureHistoryHours(Math.ceil((Date.now() - (chartEnd() - windowMs)) / 3600000));
    }
    let pendingZoom = null;
    function scheduleZoom(anchorT, factor) {
      if (pendingZoom) { pendingZoom.factor *= factor; pendingZoom.anchorT = anchorT; return; }
      pendingZoom = { anchorT, factor };
      requestAnimationFrame(() => { const z = pendingZoom; pendingZoom = null; zoomAround(z.anchorT, z.factor); });
    }

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
      const t = chartEnd() - windowMs + frac * windowMs;
      inspectAtTime(t, frac);
    }
    function inspectAtTime(t, frac) {
      const nearEvent = careEvents.find(e => Math.abs(e.x - t) <= 3 * 60 * 1000
        && e.kind !== 'O₂ on' && e.kind !== 'O₂ off');
      const when = `at ${fmtClock(new Date(t))}`
        + (onO2At(t) ? ' · on O₂' : '')
        + (nearEvent ? ` · ⚑ ${esc(nearEvent.kind)}` : '');
      const gap = gapAt(t);
      const gapLabel = gap ? gap.label : 'no reading';
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
      if (o2Placing && card.id === 'card-o2') {
        try { card.setPointerCapture(event.pointerId); } catch (error) { /* fine */ }
        gesture = { mode: 'place', card, pointerId: event.pointerId, hist: [] };
        inspectAt(event.clientX, card);
        return;
      }
      stopMomentum(); clearTimeout(inspectFade);
      try { card.setPointerCapture(event.pointerId); } catch (error) { /* keep the gesture even if capture fails */ }
      if (gesture && gesture.card === card && gesture.pointerId !== event.pointerId && gesture.mode !== 'pinch') {
        // Second finger: the gesture becomes a pinch on the shared window.
        clearTimeout(holdTimer); clearInspect();
        card.classList.remove('dragging');
        const rect = card.getBoundingClientRect();
        const firstX = gesture.hist.length ? gesture.hist[gesture.hist.length - 1].x : gesture.x0;
        const midFrac = Math.min(1, Math.max(0, (((firstX + event.clientX) / 2) - rect.left) / rect.width));
        gesture = {
          mode: 'pinch', card, rect,
          pts: new Map([[gesture.pointerId, firstX], [event.pointerId, event.clientX]]),
          startDist: Math.max(24, Math.abs(firstX - event.clientX)),
          startWindow: windowMs,
          anchorT: chartEnd() - windowMs + midFrac * windowMs,
          startEnd: chartEnd(),
        };
        return;
      }
      gesture = {
        mode: 'pending', card, pointerId: event.pointerId,
        x0: event.clientX, y0: event.clientY,
        end0: chartEnd(),
        msPerPx: windowMs / card.getBoundingClientRect().width,
        hist: [{ x: event.clientX, t: performance.now() }],
      };
      inspectAt(event.clientX, card);   // respond on pointer-down, not release
      holdTimer = setTimeout(() => { if (gesture && gesture.mode === 'pending') gesture.mode = 'scrub'; }, 220);
    }
    function onMove(event) {
      if (!gesture) return;
      if (gesture.mode === 'pinch') {
        if (!gesture.pts.has(event.pointerId)) return;
        gesture.pts.set(event.pointerId, event.clientX);
        const xs = [...gesture.pts.values()];
        if (xs.length < 2) return;
        const dist = Math.max(24, Math.abs(xs[0] - xs[1]));
        const next = Math.min(MAX_WINDOW_MS, Math.max(MIN_WINDOW_MS, gesture.startWindow * (gesture.startDist / dist)));
        const frac = (gesture.startEnd - gesture.anchorT) / gesture.startWindow;
        windowMs = next;
        const newEnd = gesture.anchorT + frac * windowMs;
        const nowMs = Date.now();
        viewEnd = newEnd >= nowMs - 5000 ? null : Math.min(newEnd, nowMs);
        paintRangeSeg();
        if (!gesture.renderQueued) {
          gesture.renderQueued = true;
          requestAnimationFrame(() => { if (gesture) gesture.renderQueued = false; renderCharts(); });
        }
        return;
      }
      const dx = event.clientX - gesture.x0, dy = event.clientY - gesture.y0;
      const now = performance.now();
      gesture.hist.push({ x: event.clientX, t: now });
      while (gesture.hist.length > 2 && now - gesture.hist[0].t > 120) gesture.hist.shift();
      if (gesture.mode === 'pending') {
        if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) {
          gesture.mode = 'pan'; clearTimeout(holdTimer); clearInspect();
          gesture.card.classList.add('dragging');
          extendHistory();   // start pulling history the moment a drag begins
        } else if (Math.abs(dy) > 16) {   // vertical intent: hand back to the page
          clearTimeout(holdTimer); clearInspect(); gesture = null; return;
        }
      }
      if (gesture.mode === 'place') { inspectAt(event.clientX, gesture.card); return; }
      if (gesture.mode === 'scrub') { inspectAt(event.clientX, gesture.card); return; }
      if (gesture.mode === 'pan') {
        let end = gesture.end0 - dx * gesture.msPerPx;   // pull right → back in time
        const nowMs = Date.now();
        const minEnd = loadedStart() + windowMs;
        if (end > nowMs) end = nowMs + (end - nowMs) / 3;             // rubber-band at "now"
        if (end < minEnd) { end = minEnd + (end - minEnd) / 3; extendHistory(); }
        else if (end - windowMs < loadedStart() + windowMs / 4) extendHistory();
        viewEnd = end;
        applyPan();
        panFocus();
      }
    }
    function onUp(event) {
      clearTimeout(holdTimer);
      if (!gesture) return;
      if (gesture.mode === 'pinch') {
        gesture.pts.delete(event.pointerId);
        if (gesture.pts.size < 2) {
          gesture = null;
          ensureHistoryHours(Math.ceil((Date.now() - (chartEnd() - windowMs)) / 3600000));
          renderCharts();
        }
        return;
      }
      if (gesture.mode === 'place') {
        gesture = null;
        commitO2At(event.clientX);
        return;
      }
      gesture.card.classList.remove('dragging');
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
        if (target != null && target < loadedStart() + windowMs) target = loadedStart() + windowMs;
        viewEnd = target === null ? null : target;
        clearInspect();
        renderCharts();
      };
      if (Math.abs(vMs) < windowMs * 0.02) { settle(); return; }
      let last = performance.now();
      const step = t => {
        const dt = Math.min(64, t - last); last = t;
        vMs *= Math.pow(0.998, dt);
        let end = chartEnd() + vMs * (dt / 1000);
        const nowMs = Date.now(), minEnd = loadedStart() + windowMs;
        if (end >= nowMs) { viewEnd = null; settle(); return; }
        if (end <= minEnd) { viewEnd = minEnd; extendHistory(); settle(); return; }
        viewEnd = end;
        applyPan();
        panFocus();
        if (Math.abs(vMs) > windowMs * 0.01) momentumRaf = requestAnimationFrame(step);
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
      card.addEventListener('wheel', event => {
        event.preventDefault();
        const rect = card.getBoundingClientRect();
        const frac = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
        const anchorT = chartEnd() - windowMs + frac * windowMs;
        scheduleZoom(anchorT, Math.exp(event.deltaY * 0.0016));
      }, { passive: false });
    });

    // ---- detail sheet --------------------------------------------------------
    let sheetRerender = null;   // the open sheet's own re-render, for after deletes
    function openSheet(title, bodyHtml) {
      el('sheetTitle').textContent = title;
      el('sheetBody').innerHTML = bodyHtml;
      el('sheetBackdrop').hidden = false;
    }
    function closeSheet() { el('sheetBackdrop').hidden = true; sheetRerender = null; }
    el('sheetClose').addEventListener('click', closeSheet);
    el('sheetBackdrop').addEventListener('click', event => {
      if (event.target === el('sheetBackdrop')) closeSheet();
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') closeSheet(); });
    el('sheetBody').addEventListener('click', async event => {   // event-row delete (any sheet open)
      const ids = event.target.dataset && event.target.dataset.del;
      if (!ids) return;
      event.target.disabled = true;
      for (const id of String(ids).split(',')) {
        if (id) await fetch('/api/events/' + id, { method: 'DELETE' }).catch(() => {});
      }
      await loadEvents();
      await refresh();
      if (sheetRerender) sheetRerender();
    });

    function todayWindow() {
      const start = new Date(); start.setHours(0, 0, 0, 0);
      return { start, end: new Date() };
    }

    // ---- the user's night window (default 7 PM -> 7 AM) --------------------
    let NIGHT = { start: 19 * 60, end: 7 * 60 };
    function nightWindowFrom(prefs) {
      const toMin = (value, fallback) => {
        const m = /^([01]?\\d|2[0-3]):([0-5]\\d)$/.exec(value || '');
        return m ? Number(m[1]) * 60 + Number(m[2]) : fallback;
      };
      const win = { start: toMin(prefs.night_start, 19 * 60), end: toMin(prefs.night_end, 7 * 60) };
      return win.start > win.end ? win : { start: 19 * 60, end: 7 * 60 }; // night must cross midnight
    }
    const clockOfMins = mins => {
      let h = Math.floor(mins / 60) % 24; const m = String(mins % 60).padStart(2, '0');
      const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
      return `${h}:${m} ${ap}`;
    };

    // ---- "Ready for tonight?" — has the day built up enough sleep pressure? --
    function prepCardMarkup() {
      const now = new Date();
      const nowMins = now.getHours() * 60 + now.getMinutes();
      if (nowMins < NIGHT.end || nowMins >= NIGHT.start) return ''; // it IS night
      const dayStart = new Date(now);
      dayStart.setHours(Math.floor(NIGHT.end / 60), NIGHT.end % 60, 0, 0);
      const dayStartMs = dayStart.getTime();

      let awakeDay = 0;
      rollups.forEach(row => {
        if (Date.parse(row.bucket_start) >= dayStartMs) awakeDay += row.awake_seconds || 0;
      });

      // typical awake time by this clock hour, from the prior week
      const typicals = [];
      for (let back = 1; back <= 7; back++) {
        const from = dayStartMs - back * 86400000, to = Date.now() - back * 86400000;
        let awake = 0, signal = 0;
        rollups.forEach(row => {
          const t = Date.parse(row.bucket_start);
          if (t < from || t >= to) return;
          awake += row.awake_seconds || 0;
          signal += (row.awake_seconds || 0) + (row.sleep_seconds || 0);
        });
        if (signal >= 3 * 3600) typicals.push(awake);
      }
      const typical = typicals.length >= 3
        ? typicals.reduce((a, b) => a + b, 0) / typicals.length : null;

      const naps = I.sessions(rollups, dayStart, now)
        .filter(run => run.state === 'asleep' && run.buckets >= 3);
      const napTotal = naps.reduce((a, run) => a + (run.end - run.start) / 1000, 0);
      const lastNap = naps.length ? naps[naps.length - 1] : null;

      const feeds = careEvents.filter(e => e.kind === 'Feeding' && e.x >= dayStartMs)
        .sort((a, b) => a.x - b.x);

      let verdict = '';
      if (typical != null) {
        const delta = awakeDay - typical;
        verdict = Math.abs(delta) < 20 * 60
          ? 'Awake time is right in line with a typical day by this hour.'
          : delta > 0
            ? `That's ${fmtDur(delta)} more awake time than typical by this hour — good sleep pressure built up for tonight.`
            : `That's ${fmtDur(-delta)} less awake time than typical by this hour — bedtime may take a little longer to stick.`;
      }

      const untilNight = NIGHT.start - nowMins;
      const nightNote = untilNight <= 0 ? '' :
        untilNight < 60 ? `night starts in ${untilNight}m` : `night starts ${clockOfMins(NIGHT.start)}`;

      const napLine = naps.length
        ? `<span><b>${naps.length}</b> nap${naps.length === 1 ? '' : 's'} · <b>${fmtDur(napTotal)}</b>${lastNap ? `, last ended ${fmtClock(new Date(lastNap.end))}` : ''}</span>`
        : '<span>No naps registered yet today.</span>';
      const feedTotals = feedTotalsText(feeds);
      const feedLine = feeds.length
        ? `<span><b>${feeds.length}</b> feed${feeds.length === 1 ? '' : 's'}${feedTotals ? ' · <b>' + feedTotals + '</b>' : ''}, last at ${fmtClock(new Date(feeds[feeds.length - 1].x))}<button class="prep-feed-btn" id="logFeedBtn">+ feed</button></span>`
        : '<span>No feeds logged today.<button class="prep-feed-btn" id="logFeedBtn">+ feed</button></span>';

      return `<div class="prep card">
        <div class="prep-top"><b>Ready for tonight?</b><span>${nightNote}</span></div>
        <div class="prep-facts">
          <span><b>${fmtDur(awakeDay)}</b> awake since ${fmtClock(dayStart)}</span>
          ${napLine}
          ${feedLine}
        </div>
        ${verdict ? `<p class="prep-note">${verdict}</p>` : ''}
      </div>`;
    }

    // ---- feeds: first-class logging with amounts ----------------------------
    const ML_PER_OZ = 29.5735;
    const fmtOz = ml => {
      const oz = Math.round((ml / ML_PER_OZ) * 2) / 2;
      return (oz % 1 ? oz.toFixed(1) : String(oz)) + ' oz';
    };
    const feedsSince = ms => careEvents
      .filter(e => e.kind === 'Feeding' && e.x >= ms)
      .sort((a, b) => a.x - b.x);
    function feedTotalsText(feeds) {
      const ml = feeds.reduce((a, f) => a + (f.amount_ml || 0), 0);
      const mins = feeds.reduce((a, f) => a + (f.duration_min || 0), 0);
      const parts = [];
      if (ml) parts.push(fmtOz(ml));
      if (mins) parts.push(Math.round(mins) + 'm nursed');
      return parts.join(' · ');
    }
    let feedType = localStorage.getItem('owletFeedType') || 'bottle';
    let feedOz = Number(localStorage.getItem('owletFeedOz')) || 4;
    let feedMin = Number(localStorage.getItem('owletFeedMin')) || 15;

    function feedWhatText(f) {
      if (f.method === 'nursing') return 'nursed' + (f.duration_min ? ' · ' + Math.round(f.duration_min) + 'm' : '');
      if (f.method === 'solids') return 'solids' + (f.note ? ' · ' + esc(f.note) : '');
      if (f.amount_ml) return 'bottle · ' + fmtOz(f.amount_ml);
      return f.note ? esc(f.note) : 'feed';
    }
    function feedHistoryRows() {
      const feeds = careEvents
        .filter(e => e.kind === 'Feeding' && e.x >= Date.now() - 3 * 86400000)
        .sort((a, b) => b.x - a.x).slice(0, 14);
      return feeds.map(f => {
        const day = new Date(f.x).toDateString() === new Date().toDateString()
          ? '' : new Date(f.x).toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ';
        return `<div class="row">
          <span>${day}${fmtClock(new Date(f.x))}</span>
          <span class="mut">${feedWhatText(f)}</span>
          <b></b>
          <button type="button" class="row-del" data-del="${f.id}" title="Remove this feed">✕</button>
        </div>`;
      }).join('');
    }

    function feedSheet() {
      sheetRerender = feedSheet;
      const today = feedsSince(todayWindow().start.getTime());
      const totals = feedTotalsText(today);
      const last = today.length ? today[today.length - 1] : null;
      const summary = today.length
        ? `<div class="o2-state"><b>${today.length} feed${today.length === 1 ? '' : 's'} today${totals ? ' · ' + totals : ''}</b>
            <span>last at ${fmtClock(new Date(last.x))} · ${fmtDur((Date.now() - last.x) / 1000)} ago</span></div>`
        : `<div class="o2-state"><b>No feeds logged today</b><span>log the first one below</span></div>`;
      const typeSeg = [['bottle', 'Bottle'], ['nursing', 'Nursing'], ['solids', 'Solids']]
        .map(([value, label]) => `<button type="button" data-ftype="${value}" class="${feedType === value ? 'sel' : ''}">${label}</button>`)
        .join('');
      let amountBlock = '';
      if (feedType === 'bottle') {
        amountBlock = `<h3 class="section-title" style="margin:14px 0 8px">Amount</h3>
          <div class="flow-presets" id="feedAmts">${[2, 3, 4, 5, 6, 8]
            .map(oz => `<button type="button" data-amt="${oz}" class="${feedOz === oz ? 'sel' : ''}">${oz} oz</button>`).join('')}</div>`;
      } else if (feedType === 'nursing') {
        amountBlock = `<h3 class="section-title" style="margin:14px 0 8px">Time on</h3>
          <div class="flow-presets" id="feedAmts">${[5, 10, 15, 20, 30]
            .map(min => `<button type="button" data-amt="${min}" class="${feedMin === min ? 'sel' : ''}">${min} min</button>`).join('')}</div>`;
      } else {
        amountBlock = `<h3 class="section-title" style="margin:14px 0 8px">What</h3>
          <input type="text" id="feedNote" class="feed-note" placeholder="oatmeal, pears… (optional)" maxlength="60" />`;
      }
      const now = new Date();
      const timeValue = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
      const history = feedHistoryRows();
      openSheet('Feeds',
        `${summary}
        <h3 class="section-title" style="margin:14px 0 8px">Type</h3>
        <div class="flow-presets" id="feedTypes">${typeSeg}</div>
        ${amountBlock}
        <div class="feed-logrow">
          <label>at <input type="time" id="feedTime" value="${timeValue}" /></label>
          <button class="o2-action" id="feedLog" type="button">Log feed</button>
        </div>
        ${history ? '<h3 class="section-title" style="margin-top:18px">Last few days</h3>' + history : ''}
        <p class="note">Feeds feed the insights: the prep card counts the day, the evening report
          totals it, and Rhythms watches how O₂ behaves around feeds. ✕ removes a mistake.</p>`);
      el('feedTypes').addEventListener('click', event => {
        const type = event.target.dataset && event.target.dataset.ftype;
        if (!type) return;
        feedType = type;
        localStorage.setItem('owletFeedType', type);
        feedSheet();
      });
      if (el('feedAmts')) el('feedAmts').addEventListener('click', event => {
        const amt = Number(event.target.dataset && event.target.dataset.amt);
        if (!amt) return;
        if (feedType === 'bottle') { feedOz = amt; localStorage.setItem('owletFeedOz', String(amt)); }
        else { feedMin = amt; localStorage.setItem('owletFeedMin', String(amt)); }
        feedSheet();
      });
      el('feedLog').addEventListener('click', async () => {
        el('feedLog').disabled = true;
        const timeText = el('feedTime').value || timeValue;
        const [h, m] = timeText.split(':').map(Number);
        const at = new Date(); at.setHours(h, m, 0, 0);
        if (at.getTime() > Date.now() + 5 * 60 * 1000) at.setDate(at.getDate() - 1); // 11:50 PM logged at 12:10 AM
        const payload = { kind: 'Feeding', at: at.toISOString(), method: feedType };
        if (feedType === 'bottle') payload.amount_ml = Math.round(feedOz * ML_PER_OZ * 10) / 10;
        else if (feedType === 'nursing') payload.duration_min = feedMin;
        else payload.note = (el('feedNote') && el('feedNote').value.trim()) || '';
        try {
          const response = await fetch('/api/events', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          if (!response.ok) throw new Error(String(response.status));
          await loadEvents();
          await refresh();
          feedSheet();
        } catch (error) {
          el('feedLog').disabled = false;
          alert('Could not save the feed — try again.');
        }
      });
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
          if (!current) current = { start: t, end: t, min: row.min_oxygen_saturation, minAt: t };
          else {
            current.end = t;
            if (row.min_oxygen_saturation < current.min) { current.min = row.min_oxygen_saturation; current.minAt = t; }
          }
        } else if (current) { dips.push(current); current = null; }
      });
      if (current) dips.push(current);
      if (!dips.length) return openSheet('O₂ dips today', '<p class="note">No dips below 90% today. 🎉</p>');
      const rows = dips.map(d =>
        `<div class="row">
          <span>${fmtClock(d.start)}</span>
          <b style="color:${d.min < 86 ? 'var(--bad)' : 'var(--awake)'}">low ${Math.round(d.min)}%</b>
          <a href="/data?focus=${encodeURIComponent(new Date(d.minAt.getTime() + 150000).toISOString())}&span=45&label=${encodeURIComponent('Dip to ' + Math.round(d.min) + '%')}">inspect →</a>
        </div>`).join('');
      openSheet('O₂ dips today', rows +
        '<p class="note">Each row is a stretch of 5-minute buckets whose lowest reading fell under 90%. "Inspect" opens the raw data zoomed to that moment.</p>');
    }

    // ---- supplemental O2 sheet: on/off with a flow setting --------------------
    const FLOW_PRESETS = ['1/32 L', '1/16 L', '1/8 L', '1/4 L', '1/2 L', '1 L'];
    let pendingFlow = localStorage.getItem('owletO2Flow') || '1/16 L';
    async function logO2(kind, note, atMs) {
      const payload = { kind, note: note || '' };
      if (atMs) payload.at = new Date(atMs).toISOString();
      const response = await fetch('/api/events', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(String(response.status));
      await loadEvents();
    }

    // ---- on-chart toggle: arm, tap a moment on the O2 graph, log it ----------
    let o2Placing = false;
    function paintO2Toggle() {
      const button = el('o2ToggleBtn');
      if (!button) return;
      button.textContent = 'O₂ ' + (o2State.on ? 'on' : 'off');
      button.className = 'vital-o2toggle' + (o2Placing ? ' arming' : o2State.on ? ' on' : '');
      const hint = el('placeHint');
      if (hint) {
        hint.hidden = !o2Placing;
        hint.textContent = `tap the moment O₂ went ${o2State.on ? 'off' : 'on'}`;
      }
      el('card-o2').classList.toggle('placing', o2Placing);
    }
    function exitO2Placing() { o2Placing = false; paintO2Toggle(); }
    function commitO2At(clientX) {
      const card = el('card-o2');
      const rect = card.getBoundingClientRect();
      const frac = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      let t = chartEnd() - windowMs + frac * windowMs;
      t = Math.min(t, Date.now());
      exitO2Placing();
      clearInspect();
      if (o2State.on) {
        logO2('O₂ off', '', t).catch(() => alert('Could not save — try again.'));
      } else {
        openFlowConfirm(t);
      }
    }
    function openFlowConfirm(atMs) {
      const flows = FLOW_PRESETS.map(flow =>
        `<button type="button" data-flow="${esc(flow)}" class="${flow === pendingFlow ? 'sel' : ''}">${esc(flow)}</button>`).join('');
      openSheet('O₂ on at ' + fmtClock(new Date(atMs)),
        `<h3 class="section-title" style="margin-bottom:8px">Flow</h3>
        <div class="flow-presets" id="confirmFlows">${flows}</div>
        <button class="o2-action" id="confirmO2" type="button">Log O₂ on · ${esc(pendingFlow)}</button>
        <p class="note">Logged at the moment you tapped on the chart.</p>`);
      el('confirmFlows').addEventListener('click', event => {
        const flow = event.target.dataset && event.target.dataset.flow;
        if (!flow) return;
        pendingFlow = flow;
        localStorage.setItem('owletO2Flow', flow);
        el('confirmFlows').querySelectorAll('button').forEach(b => b.classList.toggle('sel', b.dataset.flow === flow));
        el('confirmO2').textContent = 'Log O₂ on · ' + flow;
      });
      el('confirmO2').addEventListener('click', async () => {
        el('confirmO2').disabled = true;
        try { await logO2('O₂ on', pendingFlow, atMs); closeSheet(); }
        catch (error) { el('confirmO2').disabled = false; alert('Could not save — try again.'); }
      });
    }
    function o2HistoryRows() {
      const now = Date.now();
      return o2Spans.slice(-6).reverse().map(span => {
        const endText = span.end === Infinity ? 'now' : fmtClock(new Date(span.end));
        const duration = (span.end === Infinity ? now : span.end) - span.start;
        const day = new Date(span.start).toDateString() === new Date().toDateString()
          ? '' : new Date(span.start).toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ';
        const ids = [span.startId, span.endId].filter(Boolean).join(',');
        return `<div class="row">
          <span>${day}${fmtClock(new Date(span.start))} – ${endText}</span>
          <span class="mut">${esc(span.flow || '')}</span>
          <b>${fmtDur(duration / 1000)}</b>
          ${ids ? `<button type="button" class="row-del" data-del="${ids}" title="Remove this session from the log">✕</button>` : ''}
        </div>`;
      }).join('');
    }
    function o2Sheet() {
      const stateBlock = o2State.on
        ? `<div class="o2-state on"><b>On oxygen${o2State.flow ? ' · ' + esc(o2State.flow) : ''}</b>
            <span>since ${fmtClock(new Date(o2State.since))} · ${fmtDur((Date.now() - o2State.since) / 1000)}</span></div>`
        : `<div class="o2-state"><b>Off oxygen</b>
            <span>${o2State.since ? 'since ' + fmtClock(new Date(o2State.since)) : 'nothing logged yet'}</span></div>`;
      const flows = FLOW_PRESETS.map(flow =>
        `<button type="button" data-flow="${esc(flow)}" class="${flow === pendingFlow ? 'sel' : ''}">${esc(flow)}</button>`).join('');
      const action = o2State.on
        ? `<button class="o2-action stop" id="o2Action" type="button">Stop oxygen</button>`
        : `<button class="o2-action" id="o2Action" type="button">Start oxygen · ${esc(pendingFlow)}</button>`;
      const flowLabel = o2State.on ? 'Change flow (logs the change)' : 'Flow';
      const history = o2HistoryRows();
      sheetRerender = o2Sheet;
      openSheet('Supplemental O₂',
        `${stateBlock}
        <h3 class="section-title" style="margin-bottom:8px">${flowLabel}</h3>
        <div class="flow-presets" id="flowPresets">${flows}</div>
        ${action}
        ${history ? '<h3 class="section-title" style="margin-top:18px">Recent sessions</h3>' + history : ''}
        <p class="note">Every on/off is a logged event — the charts shade on-O₂ time, and Rhythms
          compares how she does on oxygen vs off. ✕ removes a mislogged session.</p>`);
      el('flowPresets').addEventListener('click', async event => {
        const flow = event.target.dataset && event.target.dataset.flow;
        if (!flow) return;
        pendingFlow = flow;
        localStorage.setItem('owletO2Flow', flow);
        if (o2State.on && flow !== o2State.flow) {
          try { await logO2('O₂ on', flow); } catch (error) { alert('Could not log the flow change.'); }
        }
        o2Sheet();
      });
      el('o2Action').addEventListener('click', async () => {
        el('o2Action').disabled = true;
        try {
          if (o2State.on) await logO2('O₂ off');
          else await logO2('O₂ on', pendingFlow);
          o2Sheet();
        } catch (error) {
          el('o2Action').disabled = false;
          alert('Could not save — try again.');
        }
      });
    }

    // ---- metric detail sheet: bigger chart, stats, dip zoom -------------------    // ---- metric detail sheet: bigger chart, stats, dip zoom -------------------
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
          <div class="gaplabels">${gapLabelSpans(t0, t1, 0.08, built.ghostYs)}</div>
          <div class="ms-xline" id="msX" hidden></div>
        </div>
        <div class="ms-axis"><span>${fmtClock(new Date(t0))}</span><span>${msState.center == null ? 'now' : fmtClock(new Date(t1))}</span></div>
        ${stats}${dips}
        <a class="ms-link" data-workbench href="/data?focus=${encodeURIComponent(focusIso)}&span=${Math.round(msState.spanMs / 60000)}">Open in the Data workbench →</a>`);

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
          : `${gap ? gap.label : 'no reading'} at ${fmtClock(new Date(t))}`;
        const x = el('msX'); x.hidden = false; x.style.left = (frac * 100) + '%';
      };
      chart.addEventListener('pointerdown', event => {
        try { chart.setPointerCapture(event.pointerId); } catch (error) { /* fine */ }
        scrub(event);
      });
      chart.addEventListener('pointermove', scrub);
    }
    if (el('o2ToggleBtn')) {
      el('o2ToggleBtn').addEventListener('pointerdown', event => event.stopPropagation());
      el('o2ToggleBtn').addEventListener('click', event => {
        event.stopPropagation();
        o2Placing = !o2Placing;
        paintO2Toggle();
      });
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && o2Placing) exitO2Placing();
      });
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
      const built = buildSleepMarkup(t0, t1, t0, t1, 360, 150, { clip: true, bar: 12, idPrefix: 'hyps' });
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
          <div class="gaplabels">${gapLabelSpans(t0, t1, 0.08, built.ghostYs)}</div>
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
          : `${gap ? gap.label : 'no reading'} at ${fmtClock(new Date(t))}`;
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
      // The live reading decides asleep vs awake for the baseline bands —
      // rollup sessions lag up to a bucket and load on their own cycle, so
      // two open windows could disagree ("typical awake" on one device,
      // "typical asleep" on the other). Rollups are only the fallback while
      // the sock is off.
      const liveLevel = latestRow && !offline
        ? ({ '8': 'asleep', '15': 'asleep' }[String(latestRow.sleep_state)] || 'awake')
        : null;
      baselineState = liveLevel || (currentRun && currentRun.state === 'asleep' ? 'asleep' : 'awake');
      bands.hr = I.baselineBand(rollups, 'hr', baselineState);
      bands.o2 = I.baselineBand(rollups, 'o2', baselineState);
      latest.hr = latestRow && !offline ? latestRow.heart_rate : null;
      latest.o2 = latestRow && !offline ? latestRow.oxygen_saturation : null;
      latest.temp = latestRow && !offline && latestRow.skin_temperature > 0 ? latestRow.skin_temperature : null;
      latest.sleepLevel = latestRow && !offline
        ? ({ '8': 'light', '15': 'deep' }[String(latestRow.sleep_state)] || 'awake')
        : null;
      const liveRun = currentStateSince(currentRun);
      sleepSessionText = liveRun
        ? `${liveRun.asleep ? 'asleep' : 'awake'} for ${fmtDur((Date.now() - liveRun.start) / 1000)}`
        : currentRun && currentRun.state !== 'nodata'
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

      // --- bedtime context (evenings) ---------------------------------------
      let bedtimeLine = '';
      const nowDate = new Date();
      const nowDateMins = nowDate.getHours() * 60 + nowDate.getMinutes();
      if (nowDateMins >= NIGHT.start || nowDateMins < NIGHT.end) {
        // Hunt for bedtime from an hour before the configured night start, so
        // an early night still registers; typicals use the same search start.
        const searchMin = Math.max(0, NIGHT.start - 60);
        const nightStart = new Date(nowDate); if (nowDateMins < NIGHT.start) nightStart.setDate(nightStart.getDate() - 1);
        nightStart.setHours(Math.floor(searchMin / 60), searchMin % 60, 0, 0);
        const bed = I.bedtime(rollups, nightStart, new Date());
        const typical = I.typicalBedtimeMinutes(rollups, 7, searchMin);
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
        status = `<b>${capitalized(deviceName)}</b>'s sock isn't reporting right now — it may be off or charging.`;
      } else {
        const sessionText = liveRun
          ? `${liveRun.asleep ? 'asleep' : 'awake'} for <b>${fmtDur((Date.now() - liveRun.start) / 1000)}</b>`
          : currentRun && currentRun.state !== 'nodata'
            ? `${currentRun.state === 'asleep' ? 'asleep' : 'awake'} for <b>${fmtDur((Date.now() - currentRun.start) / 1000)}</b>`
            : 'settling in';
        const nth = sleepRunsToday ? ` — sleep #${sleepRunsToday} today` : '';
        const o2Note = o2State.on ? ` On <b>${o2State.flow ? esc(o2State.flow) + ' ' : ''}O₂</b>.` : '';
        status = `<b>${capitalized(deviceName)}</b> is ${stateText || 'doing fine'}, ${sessionText}${nth}.${o2Note}${bedtimeLine}`;
      }
      const shortState = offline ? "isn't reporting"
        : liveRun ? (liveRun.asleep ? 'is asleep' : 'is awake')
        : currentRun && currentRun.state === 'asleep' ? 'is asleep'
        : latest.sleepLevel === 'light' || latest.sleepLevel === 'deep' ? 'is asleep'
        : 'is awake';
      el('statusLine').innerHTML = `<span class="st-full">${status}</span>`
        + `<span class="st-short"><b>${capitalized(deviceName)}</b> ${shortState}${o2State.on ? ' · O₂' : ''}</span>`;

      el('belowHero').innerHTML = `
        <div class="strip">
          <button class="chip card" id="chipSleep"><b>${fmtDur(sleepToday)}</b><span>sleep today</span><span class="sub">tap for sessions</span></button>
          <button class="chip card ${dipsToday ? 'warn' : 'good'}" id="chipDips"><b>${dipsToday}</b><span>O₂ dips today</span><span class="sub">tap for detail</span></button>
          <button class="chip card" id="chipTemp"><b>${latest.temp != null ? latest.temp.toFixed(1) + '°' : '—'}</b><span>skin temp</span><span class="sub">${tempRangeText || 'tap for history'}</span></button>
          <button class="chip card ${o2State.on ? 'o2-on' : ''}" id="chipO2">
            <b>${o2State.on ? 'O₂ on' : 'O₂ off'}</b>
            <span>${o2State.on && o2State.flow ? esc(o2State.flow) : 'supplemental oxygen'}</span>
            <span class="sub">${o2State.since
              ? `since ${fmtClock(new Date(o2State.since))} · ${fmtDur((Date.now() - o2State.since) / 1000)}`
              : 'tap to log on/off'}</span></button>
          ${(() => {
            const feedsToday = feedsSince(today.start.getTime());
            const totals = feedTotalsText(feedsToday);
            const lastFeed = feedsToday.length ? feedsToday[feedsToday.length - 1] : null;
            return `<button class="chip card" id="chipFeeds">
              <b>${feedsToday.length}</b><span>feed${feedsToday.length === 1 ? '' : 's'} today</span>
              <span class="sub">${lastFeed
                ? `${totals ? totals + ' · ' : ''}last ${fmtDur((Date.now() - lastFeed.x) / 1000)} ago`
                : 'tap to log'}</span></button>`;
          })()}
        </div>
        ${prepCardMarkup()}
        <div class="doors">
          <a class="door card" href="/night"><b>Last night's report →</b>
            <span>Sleep story, wake-ups, and every oxygen event, in plain language.</span></a>
          <a class="door card" href="/data"><b>The raw data →</b>
            <span>Full charts, tables, exports — every reading behind these numbers.</span></a>
        </div>`;
      el('chipSleep').addEventListener('click', openSleepSheet);
      el('chipTemp').addEventListener('click', () => openMetricSheet('temp'));
      el('chipDips').addEventListener('click', dipsSheet);
      el('chipO2').addEventListener('click', o2Sheet);
      el('chipFeeds').addEventListener('click', feedSheet);
      if (el('logFeedBtn')) el('logFeedBtn').addEventListener('click', feedSheet);
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
        const account = (accounts.accounts || [])[0];
        const prefs = (account && account.dashboard_preferences) || {};
        if (prefs.baby_name) deviceName = prefs.baby_name;
        NIGHT = nightWindowFrom(prefs);
        DISPLAY = {
          o2: prefs.o2_display === 'smoothed' ? 'smoothed' : 'raw',
          move: prefs.movement_source === 'bucket' ? 'bucket' : 'raw'
        };
        if (account && account.poll_interval_seconds) pollSeconds = account.poll_interval_seconds;
      } catch (error) {
        el('statusLine').textContent = 'Could not load readings — is the collector running?';
        return;
      }
      await refresh();
      ensureHistoryHours(Math.max(3, Math.ceil(windowMs / 3600000)));
      rollupsReady.then(refresh);
      setInterval(refresh, Math.max(5, pollSeconds) * 1000);
      setInterval(async () => {  // refresh baselines occasionally
        const data = await fetch('/api/rollups?bucket=5m&hours=192&limit=100000').then(r => r.json()).catch(() => null);
        if (data) rollups = data.rollups || rollups;
      }, 5 * 60 * 1000);
      setInterval(loadEvents, 5 * 60 * 1000);
      document.addEventListener('owlet:prefs-changed', event => {
        const prefs = (event.detail && event.detail.dashboard_preferences) || null;
        if (!prefs) return;
        DISPLAY = {
          o2: prefs.o2_display === 'smoothed' ? 'smoothed' : 'raw',
          move: prefs.movement_source === 'bucket' ? 'bucket' : 'raw'
        };
        rebuildPoints();
        if (!gesture) renderCharts();
      });
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
