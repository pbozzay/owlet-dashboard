DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#122033" />
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-title" content="Owlet" />
  __PWA_HEAD__
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
    .battery-pill { display: inline-flex; align-items: center; gap: 7px; min-height: 38px; background: #f8fafc; color: var(--text); }
    .battery-shell { width: 28px; height: 15px; border: 2px solid currentColor; border-radius: 4px; padding: 2px; position: relative; display: inline-flex; align-items: stretch; }
    .battery-shell::after { content: ''; position: absolute; right: -5px; top: 4px; width: 3px; height: 5px; border-radius: 0 2px 2px 0; background: currentColor; }
    .battery-fill { display: block; min-width: 2px; border-radius: 2px; background: currentColor; }
    .battery-pill.good { color: var(--green); background: #ecfdf5; border-color: #bbf7d0; }
    .battery-pill.mid { color: var(--amber); background: #fffbeb; border-color: #fde68a; }
    .battery-pill.low { color: var(--red); background: #fff1f2; border-color: #fecdd3; }
    .battery-pill.unknown { color: var(--muted); background: #f8fafc; }
    .refresh-cluster #refresh { min-width: 112px; }
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
    .chart-frame.main { height: 370px; }
    .chart-frame.companion { height: 190px; }
    .chart-frame.secondary { height: 240px; }
    .chart-frame canvas { display: block; width: 100% !important; height: 100% !important; }
    .companion-chart { margin-top: 2px; padding-top: 0; background: transparent; }
    .info-popover-wrap { position: relative; display: inline-flex; align-items: center; }
    .companion-info { position: absolute; right: 6px; top: 6px; z-index: 2; }
    .info-button { width: 28px; height: 28px; border-radius: 999px; padding: 0; display: inline-grid; place-items: center; background: #eff6ff; color: #1d4ed8; font-weight: 950; }
    .info-popover { display: none; position: absolute; right: 0; top: calc(100% + 8px); width: min(360px, calc(100vw - 32px)); z-index: 25; background: #fff; border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 14px; padding: 12px; color: var(--text); font-size: .84rem; line-height: 1.35; text-transform: none; letter-spacing: normal; }
    .info-popover-wrap:hover .info-popover, .info-popover-wrap:focus-within .info-popover { display: block; }
    .time-pan-control { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: center; margin-top: 8px; color: var(--muted); font-size: .78rem; }
    .time-pan-control input[type="range"] { width: 100%; padding: 0; accent-color: var(--blue); }
    .time-pan-control input[disabled] { opacity: .4; cursor: not-allowed; }
    .chart-actions { display: flex; gap: 8px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
    .chart-hint { color: var(--muted); font-size: .8rem; }
    .update-chip { opacity: 0; transform: translateY(-2px); color: var(--green); font-size: .8rem; font-weight: 900; transition: opacity .45s ease, transform .45s ease; }
    .update-chip.show { opacity: 1; transform: translateY(0); }
    .pulse-new { animation: pulseNew .9s ease; }
    @keyframes pulseNew { 0% { background: #dcfce7; } 100% { background: transparent; } }
    .glance-strip { display: grid; grid-template-columns: 1.05fr 1.05fr 1.2fr .9fr; gap: 10px; margin: 10px 0 14px; }
    .glance-card { min-height: 92px; padding: 12px 13px; }
    .glance-card strong { display: block; font-size: clamp(1.45rem, 3vw, 2.25rem); line-height: 1; letter-spacing: -.045em; margin: 4px 0; }
    .glance-card small { display: block; color: var(--muted); line-height: 1.25; }
    .glance-card .inline-stat { color: var(--text); font-weight: 850; }
    .glance-card .inline-stat.up, .crypto-change.up { color: var(--green); }
    .glance-card .inline-stat.down, .crypto-change.down { color: var(--red); }
    .glance-card .inline-stat.flat, .crypto-change.flat { color: var(--blue); }
    .oxygen-value { font-weight: 950; }
    .oxygen-value.good { color: var(--green); }
    .oxygen-value.caution { color: var(--amber); }
    .oxygen-value.danger { color: var(--red); }
    .glance-progress { height: 7px; margin-top: 7px; }
    .crypto-lines { display: grid; gap: 2px; margin-top: 5px; }
    .crypto-line { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; color: var(--muted); font-size: .82rem; }
    .crypto-line b { color: var(--text); }
    .crypto-change { font-weight: 900; }
    .notification-button { position: relative; }
    .notification-count { display: inline-grid; place-items: center; min-width: 20px; height: 20px; padding: 0 6px; margin-left: 4px; border-radius: 999px; background: #fef2f2; color: #b91c1c; font-size: .72rem; font-weight: 900; }
    .notifications-popover { position: absolute; right: 0; top: calc(100% + 8px); width: min(420px, calc(100vw - 28px)); max-height: min(72vh, 520px); overflow: auto; background: #fff; border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: 12px; z-index: 30; }
    .notifications-popover.hidden { display: none; }
    .notification-list { display: grid; gap: 8px; max-height: 360px; overflow: auto; }
    .notification-item { border: 1px solid var(--line); border-left: 5px solid var(--amber); border-radius: 13px; padding: 9px 10px; background: #fffaf0; }
    .notification-item.critical { border-left-color: var(--red); background: #fff1f2; }
    .notification-item.info { border-left-color: var(--blue); background: #eff6ff; }
    .notification-title { font-weight: 900; }
    .notification-meta { color: var(--muted); font-size: .78rem; margin-top: 3px; line-height: 1.3; }
    .challenge-button { background: #eff6ff; color: #1d4ed8; }
    .challenge-count { display: inline-grid; place-items: center; min-width: 20px; height: 20px; padding: 0 6px; margin-left: 4px; border-radius: 999px; background: #dbeafe; color: #1d4ed8; font-size: .72rem; font-weight: 900; }
    .challenge-popover { position: absolute; right: 0; top: calc(100% + 8px); width: min(520px, calc(100vw - 28px)); max-height: min(74vh, 620px); overflow: auto; background: #fff; border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: 12px; z-index: 32; }
    .challenge-popover.hidden, .challenge-modal.hidden { display: none; }
    .challenge-list { display: grid; gap: 8px; max-height: 390px; overflow: auto; }
    .challenge-item { border: 1px solid #bfdbfe; border-left: 5px solid var(--blue); border-radius: 13px; padding: 9px 10px; background: #eff6ff; }
    .challenge-item.active { border-left-color: var(--green); background: #ecfdf5; }
    .challenge-title { display: flex; justify-content: space-between; gap: 8px; font-weight: 900; }
    .challenge-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin-top: 7px; font-size: .78rem; }
    .challenge-metrics span { background: rgba(255,255,255,.68); border: 1px solid rgba(191,219,254,.8); border-radius: 10px; padding: 5px 6px; }
    .challenge-empty-actions { display: grid; gap: 8px; margin-top: 14px; }
    .challenge-modal { position: fixed; inset: 0; z-index: 90; display: grid; place-items: center; padding: 16px; background: rgba(15, 23, 42, .35); }
    .challenge-modal-card { width: min(980px, 100%); max-height: min(780px, calc(100vh - 32px)); overflow: auto; background: #fff; border-radius: 22px; box-shadow: var(--shadow); padding: 16px; }
    .challenge-edit-form { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 12px 0; padding: 12px; background: #f8fafc; border: 1px solid var(--line); border-radius: 16px; }
    .challenge-edit-form label { display: grid; gap: 5px; }
    .challenge-edit-form input, .challenge-edit-form textarea { width: 100%; }
    .challenge-edit-form textarea { min-height: 66px; resize: vertical; }
    .challenge-edit-form .full { grid-column: 1 / -1; }
    .danger-button { background: #fff1f2; color: #991b1b; border-color: #fecdd3; }
    .challenge-summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 12px 0; }
    .challenge-summary-grid .mini { min-width: 0; }
    .state-strip-wrap { margin: -2px var(--chart-right-pad, 0px) 0 var(--chart-left-pad, 0px); }
    .state-strip { height: 18px; border-radius: 0 0 10px 10px; overflow: hidden; background: #e2e8f0; border: 1px solid var(--line); border-top: 0; cursor: crosshair; }
    .state-segment { min-width: 1px; }
    .state-segment:hover { filter: saturate(1.2) brightness(1.03); }
    .state-time-axis { position: relative; height: 18px; color: var(--muted); font-size: .72rem; }
    .state-time-axis span { position: absolute; top: 3px; transform: translateX(-50%); white-space: nowrap; }
    .state-segment.light { background: rgba(124, 58, 237, .72); }
    .state-segment.deep { background: rgba(37, 99, 235, .72); }
    .state-segment.awake { background: rgba(180, 83, 9, .72); }
    .state-segment.inactive { background: rgba(148, 163, 184, .72); }
    .state-segment.offline { background: rgba(239, 68, 68, .5); }
    .state-legend { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 5px; color: var(--muted); font-size: .74rem; }
    .state-legend span::before { content: ''; display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; vertical-align: -1px; background: var(--dot); }
    .sleep-overlay-controls { display: flex; flex-wrap: wrap; gap: 8px 12px; margin-top: 8px; color: var(--muted); font-size: .78rem; }
    .inline-toggle { display: inline-flex; align-items: center; gap: 6px; font-weight: 800; }
    .inline-toggle input { padding: 0; }
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
    .readings-grid { grid-template-columns: minmax(0, 1.45fr) minmax(320px, .55fr); margin-top: 14px; align-items: start; }
    .readings-panel .table-wrap { max-height: 560px; }
    .reading-detail-panel { position: sticky; top: 88px; }
    .reading-detail-panel .raw-box { max-height: 520px; }
    table { width: 100%; border-collapse: collapse; font-size: .9rem; }
    th, td { padding: 10px 9px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    th { color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; background: #f8fafc; position: sticky; top: 0; z-index: 1; }
    tr:hover td { background: #f8fafc; }
    tr.offline-row td { background: #fff1f2; color: #991b1b; }
    tr.offline-row:hover td { background: #ffe4e6; }
    tr.challenge-row td { background: #eff6ff; color: #1e3a8a; }
    tr.selected-row td { background: #ecfeff !important; box-shadow: inset 0 0 0 999px rgba(14, 165, 233, .08); }
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
      .metric-grid, .details-grid, .readings-grid { grid-template-columns: 1fr; }
      .reading-detail-panel { position: static; }
      .status { white-space: normal; }
      .toolbar { position: static; }
      .chart-frame.main { height: 360px; }
      .chart-frame.companion { height: 185px; }
      .chart-frame.secondary { height: 230px; }
    }
    @media (max-width: 640px) {
      .shell { width: min(100% - 14px, 1500px); padding: 10px 0 24px; }
      .hero { gap: 8px; margin-bottom: 8px; }
      h1 { font-size: clamp(1.75rem, 12vw, 2.7rem); }
      .subtitle { display: none; }
      .toolbar, .panel, .card { border-radius: 16px; box-shadow: 0 10px 26px rgba(15, 23, 42, .08); }
      .toolbar { padding: 7px; gap: 7px; margin: 8px 0; backdrop-filter: none; }
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
      .glance-card strong { font-size: 1.35rem; margin: 2px 0; }
      .glance-card small { font-size: .75rem; }
      .chart-panel, .panel, .card { padding: 9px; }
      .panel-title { gap: 8px; margin-bottom: 5px; align-items: flex-start; }
      .panel-title { flex-wrap: wrap; }
      .details-grid .panel-title .small { flex-basis: 100%; }
      .chart-hint { display: none; }
      .chart-frame.main { height: 430px; }
      .chart-frame.companion { height: 215px; }
      .chart-frame.secondary { height: 295px; }
      .notifications-popover, .challenge-popover { position: fixed; inset: 8px; width: auto; max-height: none; border-radius: 18px; z-index: 80; display: flex; flex-direction: column; box-shadow: 0 0 0 9999px rgba(15, 23, 42, .35), var(--shadow); }
      .notifications-popover.hidden, .challenge-popover.hidden { display: none; }
      .notification-list, .challenge-list { max-height: none; flex: 1; }
      .challenge-actions { display: grid !important; grid-template-columns: 1fr 1fr; align-items: stretch; }
      .challenge-actions .wide { grid-column: 1 / -1; }
      .challenge-modal { align-items: center; padding: 8px; }
      .challenge-modal-card { width: 100%; max-height: 88vh; border-radius: 18px 18px 12px 12px; padding: 12px; }
      .challenge-summary-grid, .challenge-edit-form { grid-template-columns: 1fr; }
      .challenge-edit-form .full { grid-column: auto; }
      .time-pan-control { grid-template-columns: 1fr; gap: 4px; }
      .state-time-axis { font-size: .66rem; }
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
        <button id="challengesToggle" class="challenge-button" type="button" aria-expanded="false">O₂ challenges / add <span id="challengeCount" class="challenge-count">0</span></button>
        <button id="notificationsToggle" class="notification-button" type="button" aria-expanded="false">Notifications <span id="notificationCount" class="notification-count">0</span></button>
        <button id="batteryStatus" class="battery-pill unknown" type="button" title="Battery details">
          <span class="battery-shell" aria-hidden="true"><span id="batteryFill" class="battery-fill" style="width: 0%;"></span></span>
          <span id="batteryLabel">—</span>
        </button>
        <button id="installApp" class="install-button" type="button" title="Install Owlet as an app">Install app</button>
        <button id="refresh" class="primary">Refresh (15s)</button>
        <div id="challengesPanel" class="challenge-popover hidden" role="dialog" aria-modal="true" aria-label="Oxygen challenges">
          <div class="panel-title">
            <h2>Oxygen challenges</h2>
            <div class="control-group"><span class="small" id="challengePage">—</span><button id="closeChallengesPanel" type="button">Close</button></div>
          </div>
          <div class="control-group challenge-actions" id="challengeActions" style="justify-content: space-between; margin-bottom: 10px;">
            <button id="addChallenge" class="primary wide" type="button">Add new O₂ challenge</button>
            <button id="startChallenge" type="button">Start now</button>
            <button id="endChallenge" type="button">End active</button>
            <button id="markVisibleChallenge" class="wide" type="button">Use visible chart window</button>
          </div>
          <div id="challengeList" class="challenge-list"></div>
        </div>
        <div id="notificationsPanel" class="notifications-popover hidden" role="dialog" aria-modal="true" aria-label="Notifications">
          <div class="panel-title">
            <h2>Notifications</h2>
            <div class="control-group"><span class="small" id="notificationPage">—</span><button id="closeNotificationsPanel" type="button">Close</button></div>
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
        <span class="eyebrow">O₂ now + today</span>
        <strong id="latestOxygen">—</strong>
        <small><span class="inline-stat" id="todayOxygen">—</span> 24h avg · <span class="inline-stat" id="o2Compare">—</span></small>
        <small>Prior <span class="inline-stat" id="priorOxygen">—</span></small>
      </article>
      <article class="card glance-card">
        <span class="eyebrow">Heart rate</span>
        <strong id="latestHr">—</strong>
        <small><span class="inline-stat" id="avgHr">—</span> 24h avg · <span class="inline-stat" id="hrCompare">—</span></small>
        <small>State <span class="inline-stat" id="latestState">—</span> · Move <span class="inline-stat" id="latestMove">—</span></small>
      </article>
      <article class="card glance-card crypto-card">
        <span class="eyebrow">Crypto</span>
        <strong id="cryptoHeadline">BTC —</strong>
        <div class="crypto-lines" id="cryptoLines">
          <small>Loading BTC / ETH / XMR…</small>
        </div>
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
        <div id="stateStripWrap" class="state-strip-wrap" title="Sleep/wake/offline state across the visible vitals window">
          <div id="stateStrip" class="state-strip"></div>
          <div id="stateTimeAxis" class="state-time-axis"></div>
        </div>
        <div class="companion-chart" aria-label="Oxygen trend companion chart">
          <div class="chart-frame companion"><canvas id="oxygenTrendChart"></canvas>
            <span class="info-popover-wrap companion-info">
              <button class="info-button" type="button" aria-label="How to read the O₂ trend companion">i</button>
              <span class="info-popover" role="tooltip">
                O₂ trend companion: a MACD-style oxygen view. It compares recent 30-minute O₂ against the 4-hour baseline. Green means recent O₂ is above baseline; red means below. Offline gaps and oxygen challenges are not bridged.
              </span>
            </span>
          </div>
        </div>
        <div class="state-legend">
          <span style="--dot: rgba(124,58,237,.72)">light sleep</span>
          <span style="--dot: rgba(37,99,235,.72)">deep sleep</span>
          <span style="--dot: rgba(180,83,9,.72)">awake</span>
          <span style="--dot: rgba(239,68,68,.5)">offline</span>
        </div>
        <div class="sleep-overlay-controls" aria-label="Sleep and wake highlighting controls">
          <label class="inline-toggle"><input id="sleepHighlightToggle" type="checkbox" /> Highlight sleep/wake on main graph</label>
          <label class="inline-toggle"><input id="sleepBallparkToggle" type="checkbox" disabled /> Ballpark by average window</label>
        </div>
        <div class="time-pan-control">
          <span id="panStartLabel">—</span>
          <input id="timePan" type="range" min="0" max="1000" value="0" disabled aria-label="Scroll visible time window" />
          <span id="panEndLabel">—</span>
        </div>
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

    <section class="panel" style="margin-top: 14px;">
        <div class="panel-title">
          <h2>Drill-down table</h2>
          <span class="small">averages + sleep/awake estimates</span>
        </div>
        <div class="table-wrap"><table id="rollupTable"></table></div>
    </section>

    <section class="grid readings-grid" aria-label="Readings and selected detail">
      <div class="panel readings-panel">
        <div class="panel-title">
          <h2>Readings table</h2>
          <span class="small" id="tableCount">—</span>
        </div>
        <div class="table-wrap"><table id="readingsTable"></table></div>
      </div>
      <div class="panel reading-detail-panel">
        <div class="panel-title">
          <h2>Selected reading</h2>
          <span class="small">click any row on the left</span>
        </div>
        <pre id="raw" class="raw-box">No reading selected yet.</pre>
      </div>
    </section>
  </main>

  <div id="challengeModal" class="challenge-modal hidden" role="dialog" aria-label="Oxygen challenge detail">
    <div class="challenge-modal-card">
      <div class="panel-title">
        <div>
          <h2 id="challengeModalTitle">Oxygen challenge</h2>
          <span class="small" id="challengeModalMeta">—</span>
        </div>
        <button id="closeChallengeModal" type="button">Close</button>
      </div>
      <div id="challengeSummary" class="challenge-summary-grid"></div>
      <form id="challengeEditForm" class="challenge-edit-form">
        <label>Label
          <input id="challengeEditLabel" name="label" type="text" />
        </label>
        <label>Start time
          <input id="challengeEditStart" name="start_time" type="datetime-local" />
        </label>
        <label>End time
          <input id="challengeEditEnd" name="end_time" type="datetime-local" />
        </label>
        <label class="full">Notes
          <textarea id="challengeEditNotes" name="notes"></textarea>
        </label>
        <div class="control-group full" style="justify-content: space-between;">
          <button id="saveChallengeEdits" type="submit">Save edits</button>
          <button id="deleteChallenge" class="danger-button" type="button">Delete challenge</button>
        </div>
      </form>
      <div id="challengeDetailChartFrame" class="chart-frame secondary"><canvas id="challengeDetailChart"></canvas></div>
      <p class="small" id="challengeNotes"></p>
    </div>
  </div>

  <script>
    const API_BASE = "__API_BASE__";
    const SHARE_MODE = __SHARE_MODE__;
    const REFRESH_SECONDS = 15;
    let readings = [];
    let filtered = [];
    let summary = null;
    let insights = null;
    let rollups = [];
    let comparisonRows = [];
    let notifications = { items: [], total: 0, limit: 500, offset: 0 };
    let challenges = { items: [], total: 0, limit: 100, offset: 0 };
    let crypto = { available: false, prices: {}, series: { bitcoin: [] } };
    let notificationPageOffset = 0;
    const NOTIFICATION_PAGE_SIZE = 10;
    const TREND_MAX_SAMPLE_GAP_MS = 5 * 60 * 1000;
    let vitalsChart = null;
    let oxygenTrendChart = null;
    let stateChart = null;
    let rollupChart = null;
    let challengeDetailChart = null;
    let secondsUntilRefresh = REFRESH_SECONDS;
    let syncInProgress = false;
    let zoomWindow = null;
    let lastLatestTimestamp = null;
    let deferredInstallPrompt = null;
    let currentChallengeDetail = null;
    let hoveredStateInterval = null;
    let sleepHighlightEnabled = false;
    let sleepBallparkEnabled = false;
    let stateStripSegments = [];
    let trendRenderToken = 0;
    let refreshToken = 0;

    const sleepPhaseColors = {
      light: 'rgba(124, 58, 237, .13)',
      deep: 'rgba(37, 99, 235, .13)',
      awake: 'rgba(180, 83, 9, .13)',
      inactive: 'rgba(148, 163, 184, .12)',
      offline: 'rgba(239, 68, 68, .14)'
    };

    const stateStripColors = {
      light: 'rgba(124, 58, 237, .72)',
      deep: 'rgba(37, 99, 235, .72)',
      awake: 'rgba(180, 83, 9, .72)',
      inactive: 'rgba(148, 163, 184, .72)',
      offline: 'rgba(239, 68, 68, .5)'
    };

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
    const challengeBandsPlugin = {
      id: 'challengeBands',
      beforeDatasetsDraw(chart, _args, options) {
        const intervals = options?.intervals || [];
        if (!intervals.length || !chart.scales?.x) return;
        const { ctx, chartArea, scales } = chart;
        ctx.save();
        ctx.fillStyle = 'rgba(37, 99, 235, 0.10)';
        ctx.strokeStyle = 'rgba(37, 99, 235, 0.26)';
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
    const notificationHoverPlugin = {
      id: 'notificationHoverPriority',
      afterEvent(chart, args) {
        if (chart.canvas.id !== 'vitalsChart') return;
        const event = args.event;
        const datasetIndex = chart.data.datasets.findIndex(dataset => dataset.id === 'notifications');
        if (datasetIndex < 0) return;
        const meta = chart.getDatasetMeta(datasetIndex);
        const isExit = event.type === 'mouseout' || event.type === 'touchend';
        if (isExit) {
          if (chart.$notificationHoverActive) {
            chart.tooltip.setActiveElements([], { x: 0, y: 0 });
            chart.$notificationHoverActive = false;
            chart.canvas.style.cursor = '';
            args.changed = true;
          }
          return;
        }
        if (!['mousemove', 'click', 'touchmove'].includes(event.type)) return;

        const mobile = window.matchMedia('(max-width: 640px)').matches;
        const xRadius = mobile ? 28 : 22;
        const yRadius = mobile ? 44 : 34;
        let best = null;
        meta.data.forEach((point, index) => {
          if (!point || point.skip) return;
          const dx = Math.abs(point.x - event.x);
          const dy = Math.abs(point.y - event.y);
          if (dx > xRadius || dy > yRadius) return;
          const score = dx + dy * 0.35;
          if (!best || score < best.score) best = { index, point, score };
        });

        if (best) {
          chart.tooltip.setActiveElements([{ datasetIndex, index: best.index }], { x: best.point.x, y: best.point.y });
          chart.setActiveElements([{ datasetIndex, index: best.index }]);
          chart.$notificationHoverActive = true;
          chart.canvas.style.cursor = 'help';
          args.changed = true;
        } else if (chart.$notificationHoverActive) {
          chart.tooltip.setActiveElements([], { x: event.x, y: event.y });
          chart.setActiveElements([]);
          chart.$notificationHoverActive = false;
          chart.canvas.style.cursor = '';
          args.changed = true;
        }
      }
    };
    const oxygen85ThresholdPlugin = {
      id: 'oxygen85Threshold',
      afterDraw(chart) {
        if (chart.canvas.id !== 'vitalsChart') return;
        const scale = chart.scales?.spo2;
        const { chartArea, ctx } = chart;
        if (!scale || !chartArea) return;
        const y = scale.getPixelForValue(85);
        if (!Number.isFinite(y) || y < chartArea.top || y > chartArea.bottom) return;
        ctx.save();
        ctx.setLineDash([6, 5]);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(220, 38, 38, .85)';
        ctx.beginPath();
        ctx.moveTo(chartArea.left, y);
        ctx.lineTo(chartArea.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(220, 38, 38, .92)';
        ctx.font = '700 11px ui-sans-serif, system-ui, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'bottom';
        ctx.fillText('85% O₂', chartArea.right - 4, y - 4);
        ctx.restore();
      }
    };
    const sleepBandsPlugin = {
      id: 'sleepBands',
      beforeDatasetsDraw(chart) {
        if (chart.canvas.id !== 'vitalsChart' || !sleepHighlightEnabled || !chart.scales?.x) return;
        const intervals = sleepOverlayIntervals();
        if (!intervals.length) return;
        const { ctx, chartArea, scales } = chart;
        ctx.save();
        intervals.forEach(interval => {
          const left = Math.max(chartArea.left, scales.x.getPixelForValue(interval.start));
          const right = Math.min(chartArea.right, scales.x.getPixelForValue(interval.end));
          if (!Number.isFinite(left) || !Number.isFinite(right) || right <= chartArea.left || left >= chartArea.right) return;
          ctx.fillStyle = sleepPhaseColors[interval.cls] || sleepPhaseColors.inactive;
          ctx.fillRect(left, chartArea.top, Math.max(1, right - left), chartArea.bottom - chartArea.top);
        });
        ctx.restore();
      }
    };
    const stateChartHoverPlugin = {
      id: 'stateChartHover',
      afterEvent(chart, args) {
        if (chart.canvas.id !== 'stateChart' || !chart.scales?.x) return;
        const event = args.event;
        if (event.type === 'mouseout') {
          hoveredStateInterval = null;
          vitalsChart?.update('none');
          return;
        }
        if (!['mousemove', 'click', 'touchmove'].includes(event.type)) return;
        const timestamp = chart.scales.x.getValueForPixel(event.x);
        const interval = rollupIntervalAt(timestamp) || stateIntervalAt(timestamp);
        hoveredStateInterval = interval;
        vitalsChart?.update('none');
      }
    };
    const sleepPhaseHoverPlugin = {
      id: 'sleepPhaseHover',
      beforeDatasetsDraw(chart) {
        if (chart.canvas.id !== 'vitalsChart' || !hoveredStateInterval || !chart.scales?.x) return;
        const { ctx, chartArea, scales } = chart;
        const left = Math.max(chartArea.left, scales.x.getPixelForValue(hoveredStateInterval.start));
        const right = Math.min(chartArea.right, scales.x.getPixelForValue(hoveredStateInterval.end));
        if (!Number.isFinite(left) || !Number.isFinite(right) || right <= left) return;
        ctx.save();
        ctx.fillStyle = sleepPhaseColors[hoveredStateInterval.cls] || sleepPhaseColors.inactive;
        ctx.strokeStyle = ctx.fillStyle.replace('.13', '.34').replace('.14', '.34').replace('.12', '.30');
        ctx.fillRect(left, chartArea.top, right - left, chartArea.bottom - chartArea.top);
        ctx.strokeRect(left, chartArea.top, right - left, chartArea.bottom - chartArea.top);
        ctx.restore();
      }
    };
    Chart.register(sleepBandsPlugin, challengeBandsPlugin, offlineBandsPlugin, sleepPhaseHoverPlugin, stateChartHoverPlugin, notificationGlyphsPlugin, notificationHoverPlugin, oxygen85ThresholdPlugin);

    const el = (id) => document.getElementById(id);
    const fmt = (value, suffix = '') => value === null || value === undefined ? '—' : `${value}${suffix}`;
    const num = (value, digits = 1) => value === null || value === undefined ? '—' : Number(value).toFixed(digits).replace(/\.0$/, '');
    const money = (value) => value === null || value === undefined ? '—' : Number(value).toLocaleString([], { style: 'currency', currency: 'USD', maximumFractionDigits: Number(value) >= 100 ? 0 : 2 });
    const pct = (value) => value === null || value === undefined ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(1)}%`;
    const changeClass = (value, threshold = 0) => value === null || value === undefined || Math.abs(Number(value)) <= threshold ? 'flat' : (Number(value) > 0 ? 'up' : 'down');
    const hours = (seconds) => seconds ? `${(seconds / 3600).toFixed(1).replace(/\.0$/, '')}h` : '0h';
    const trendClass = (trend) => `trend-${trend || 'unknown'}`;
    const stateLabel = (value) => ({ '0': 'inactive', '1': 'awake', '8': 'light sleep', '15': 'deep sleep' }[String(value)] || `state ${value ?? 'unknown'}`);
    const zeroOrNegative = (value) => value !== null && value !== undefined && Number(value) <= 0;
    const isOffline = (row) => zeroOrNegative(row?.heart_rate) || zeroOrNegative(row?.oxygen_saturation);
    const durationText = (seconds) => seconds ? `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`.replace(/^0h /, '') : '0m';
    const signed = (value, suffix = '') => value === null || value === undefined ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(1).replace(/\.0$/, '')}${suffix}`;
    const chartList = () => [vitalsChart, oxygenTrendChart, rollupChart, stateChart].filter(Boolean);

    function batteryClass(level) {
      const value = Number(level);
      if (!Number.isFinite(value)) return 'unknown';
      if (value <= 20) return 'low';
      if (value <= 45) return 'mid';
      return 'good';
    }

    function oxygenValueClass(level) {
      const value = Number(level);
      if (!Number.isFinite(value)) return 'unknown';
      if (value >= 92) return 'good';
      if (value >= 86) return 'caution';
      return 'danger';
    }

    function batteryTime(minutes) {
      const value = Number(minutes);
      if (!Number.isFinite(value) || value <= 0) return 'estimate unavailable';
      const hrs = Math.floor(value / 60);
      const mins = Math.round(value % 60);
      if (hrs <= 0) return `${mins}m remaining`;
      return `${hrs}h ${mins}m remaining`;
    }

    function renderBatteryStatus(latest) {
      const level = latest?.battery;
      const minutes = latest?.battery_minutes;
      const numeric = Number(level);
      const cls = batteryClass(level);
      const pill = el('batteryStatus');
      pill.className = `battery-pill ${cls}`;
      el('batteryLabel').textContent = Number.isFinite(numeric) ? `${Math.round(numeric)}%` : '—';
      el('batteryFill').style.width = Number.isFinite(numeric) ? `${Math.max(4, Math.min(100, numeric))}%` : '0%';
      pill.title = Number.isFinite(numeric)
        ? `Battery ${Math.round(numeric)}% · ${batteryTime(minutes)}`
        : 'Battery unavailable';
      pill.dataset.detail = pill.title;
      pill.setAttribute('aria-label', pill.title);
    }

    function updateRefreshButton(text = null) {
      el('refresh').textContent = text || `Refresh (${secondsUntilRefresh}s)`;
    }

    function challengeIntervals() {
      return (challenges.items || []).map(challenge => ({
        start: Date.parse(challenge.start_time),
        end: Date.parse(challenge.effective_end_time || challenge.end_time || new Date().toISOString())
      })).filter(interval => Number.isFinite(interval.start) && Number.isFinite(interval.end) && interval.end >= interval.start);
    }

    function timeInIntervals(time, intervals) {
      return intervals.some(interval => time >= interval.start && time <= interval.end);
    }

    function isInChallenge(rowOrTime) {
      const time = typeof rowOrTime === 'number' ? rowOrTime : Date.parse(rowOrTime?.recorded_at);
      return timeInIntervals(time, challengeIntervals());
    }

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

    function toDateTimeLocal(iso) {
      if (!iso) return '';
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return '';
      const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      return local.toISOString().slice(0, 16);
    }

    function fromDateTimeLocal(value) {
      return value ? new Date(value).toISOString() : null;
    }

    function average(values) {
      const clean = values.filter(value => value !== null && value !== undefined && Number.isFinite(Number(value))).map(Number);
      if (!clean.length) return null;
      return clean.reduce((sum, value) => sum + value, 0) / clean.length;
    }

    function windowAverage(rows, key, start, end) {
      return average(rows.filter(row => !isOffline(row) && !isInChallenge(row) && Date.parse(row.recorded_at) > start && Date.parse(row.recorded_at) <= end).map(row => row[key]));
    }

    function comparisonFor(key, threshold) {
      const rows = comparisonRows.length ? comparisonRows : readings;
      if (!rows.length) return { current: null, prior: null, delta: null, word: 'unknown', css: 'flat' };
      const latest = Date.parse(rows[rows.length - 1].recorded_at);
      const currentStart = latest - 24 * 3600 * 1000;
      const priorStart = latest - 48 * 3600 * 1000;
      const current = windowAverage(rows, key, currentStart, latest);
      const prior = windowAverage(rows, key, priorStart, currentStart);
      const delta = current === null || prior === null ? null : current - prior;
      const css = changeClass(delta, threshold);
      const oxygen = key === 'oxygen_saturation';
      const word = delta === null ? 'unknown' : (css === 'flat' ? 'stable' : (oxygen ? (delta > 0 ? 'improving' : 'worsening') : (delta > 0 ? 'increasing' : 'decreasing')));
      return { current, prior, delta, word, css };
    }

    function comparisonText(result, digits = 1, unit = '') {
      if (result.delta === null || result.prior === null) return 'need 48h';
      const sign = result.delta >= 0 ? '+' : '';
      return `${result.word} ${sign}${result.delta.toFixed(digits).replace(/\.0$/, '')}${unit}`;
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
      updateRefreshButton('Refreshing…');
      const token = ++refreshToken;
      const previousLatest = lastLatestTimestamp;
      const qs = queryParams();
      const rollupQs = queryParams({ bucket: el('bucket').value });
      const notificationQs = queryParams({ limit: '500', offset: '0' });
      const challengeQs = queryParams({ limit: '100', offset: '0' });
      const cryptoHours = selectedHours() || 720;
      const [health, rows, notificationData, challengeData] = await Promise.all([
        fetchJson(`${API_BASE}/api/health`),
        fetchJson(`${API_BASE}/api/readings?${qs}`),
        fetchJson(`${API_BASE}/api/notifications?${notificationQs}`),
        fetchJson(`${API_BASE}/api/oxygen-challenges?${challengeQs}`)
      ]);
      if (token !== refreshToken) return;
      readings = rows;
      notifications = notificationData;
      challenges = challengeData;
      lastLatestTimestamp = readings.length ? readings[readings.length - 1].recorded_at : null;
      if (resetZoom) zoomWindow = null;
      renderStatus(health);
      applyFilter();
      renderCharts({ deferTrend: true });
      renderNotifications();
      renderChallenges();
      updateRefreshButton();
      if (previousLatest && lastLatestTimestamp && lastLatestTimestamp !== previousLatest) showNewDataPulse();
      hydrateSecondaryData({ qs, rollupQs, cryptoHours, token }).catch(error => {
        console.error(error);
        el('refresh').title = 'Some details failed; core readings are still shown.';
      });
    }

    async function hydrateSecondaryData({ qs, rollupQs, cryptoHours, token }) {
      const [compareRows, stats, insightData, rollupData, cryptoData] = await Promise.all([
        fetchJson(`${API_BASE}/api/readings?hours=48&limit=100000`),
        fetchJson(`${API_BASE}/api/summary?${qs}`),
        fetchJson(`${API_BASE}/api/insights?${qs}`),
        fetchJson(`${API_BASE}/api/rollups?${rollupQs}`),
        fetchJson(`${API_BASE}/api/crypto?hours=${cryptoHours}`)
      ]);
      if (token !== refreshToken) return;
      comparisonRows = compareRows;
      summary = stats;
      insights = insightData;
      rollups = rollupData.rollups || [];
      crypto = cryptoData;
      renderInsights();
      renderCrypto();
      renderMetricCards();
      renderRollups();
      vitalsChart?.update('none');
    }

    function renderStatus(health) {
      const mode = SHARE_MODE ? 'Shared read-only view' : health.database_path;
      const latest = readings[readings.length - 1];
      const offlineNow = latest && isOffline(latest);
      const label = offlineNow ? 'Device offline / sock off' : (health.collecting ? 'Collecting live' : 'Stored data only');
      const dotClass = offlineNow ? 'offline' : (health.collecting ? 'good' : '');
      el('status').innerHTML = `<span class="status-dot ${dotClass}"></span>${label} · ${mode}`;
      renderBatteryStatus(latest);
    }

    function renderInsights() {
      const rawLatest = readings[readings.length - 1];
      const latest = rawLatest ? { ...rawLatest, sleep_state_label: isOffline(rawLatest) ? 'offline / sock off' : stateLabel(rawLatest.sleep_state) } : insights.latest;
      const oxygenCompare = comparisonFor('oxygen_saturation', 0.25);
      const hrCompare = comparisonFor('heart_rate', 1);
      el('latestOxygen').textContent = latest ? fmt(latest.oxygen_saturation, '% O₂') : '—';
      el('latestOxygen').className = `oxygen-value ${oxygenValueClass(latest?.oxygen_saturation)}`;
      el('todayOxygen').textContent = oxygenCompare.current === null ? '—' : `${oxygenCompare.current.toFixed(1).replace(/\.0$/, '')}%`;
      el('todayOxygen').className = `inline-stat oxygen-value ${oxygenValueClass(oxygenCompare.current)}`;
      el('latestHr').textContent = latest ? fmt(latest.heart_rate, ' bpm') : '—';
      el('avgHr').textContent = hrCompare.current === null ? '—' : fmt(hrCompare.current.toFixed(0), ' bpm');
      el('latestState').textContent = latest ? latest.sleep_state_label : '—';
      el('latestMove').textContent = latest ? num(latest.movement) : '—';
      renderBatteryStatus(latest);

      const breathing = insights.breathing;
      el('o2Compare').textContent = comparisonText(oxygenCompare, 1, ' pts');
      el('o2Compare').className = `inline-stat ${oxygenCompare.css}`;
      el('priorOxygen').textContent = oxygenCompare.prior === null ? fmt(breathing.previous_avg_oxygen, '%') : fmt(oxygenCompare.prior.toFixed(1), '%');
      el('hrCompare').textContent = comparisonText(hrCompare, 0, ' bpm');
      el('hrCompare').className = `inline-stat ${hrCompare.css}`;

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

    function renderCrypto() {
      if (!crypto.available) {
        el('cryptoHeadline').textContent = 'Crypto —';
        el('cryptoLines').innerHTML = `<small>${crypto.error ? 'Price feed unavailable' : 'Loading BTC / ETH / XMR…'}</small>`;
        return;
      }
      const entries = ['bitcoin', 'ethereum', 'monero'].map(id => crypto.prices?.[id]).filter(Boolean);
      const btc = crypto.prices?.bitcoin;
      el('cryptoHeadline').textContent = btc ? `BTC ${money(btc.usd)}` : 'BTC —';
      el('cryptoLines').innerHTML = entries.map(coin => `
        <div class="crypto-line">
          <span><b>${coin.symbol}</b> ${money(coin.usd)}</span>
          <span class="crypto-change ${changeClass(coin.usd_24h_change, .05)}">${pct(coin.usd_24h_change)}</span>
        </div>`).join('') || '<small>Price feed unavailable</small>';
    }

    function renderMetricCards() {
      const cards = [
        ['Avg oxygen', fmt(summary.oxygen_saturation.avg, '%'), `min ${fmt(summary.oxygen_saturation.min, '%')} · ${summary.oxygen_saturation.trend}`, summary.oxygen_saturation.trend],
        ['Avg heart rate', fmt(summary.heart_rate.avg, ' bpm'), `latest ${fmt(summary.heart_rate.latest, ' bpm')}`, summary.heart_rate.trend],
        ['Avg movement', num(summary.movement.avg), `latest ${num(summary.movement.latest)} · ${summary.movement.trend}`, summary.movement.trend],
        ['Coverage', `${summary.valid_count ?? summary.count}/${summary.total_count ?? summary.count}`, `${summary.offline_count || 0} offline/zero · ${summary.challenge_count || 0} challenge readings excluded`, summary.offline_count ? 'down' : 'unknown'],
      ];
      el('metricCards').innerHTML = cards.map(([label, value, foot, trend]) => `
        <article class="card">
          <div class="eyebrow">${label}</div>
          <div class="metric-value ${trendClass(trend)}">${value}</div>
          <div class="sub">${foot}</div>
        </article>`).join('');
      el('coverage').textContent = `${summary.window} · ${summary.count} stats readings · ${summary.challenge_count || 0} in challenges`;
    }

    function downsample(rows, maxPoints = 1200) {
      if (rows.length <= maxPoints) return rows;
      const step = Math.ceil(rows.length / maxPoints);
      return rows.filter((_, index) => index % step === 0 || index === rows.length - 1 || isOffline(rows[index]));
    }

    function downsamplePoints(points, maxPoints = 1200) {
      if (points.length <= maxPoints) return points;
      const step = Math.ceil(points.length / maxPoints);
      return points.filter((point, index) => point.y === null || index % step === 0 || index === points.length - 1);
    }

    function rollingOxygenAverage(minutes, challengeWindows = challengeIntervals()) {
      const windowMs = minutes * 60 * 1000;
      const queue = [];
      let sum = 0;
      const points = [];
      let previousValidTime = null;
      let inExcludedGap = false;
      const resetWindow = () => {
        queue.length = 0;
        sum = 0;
      };
      const addGapMarker = (time, reason) => {
        const last = points[points.length - 1];
        if (last && last.y === null && last.reason === reason && Math.abs(last.x - time) < TREND_MAX_SAMPLE_GAP_MS) return;
        points.push({ x: time, y: null, reason });
      };
      readings.forEach(row => {
        const time = Date.parse(row.recorded_at);
        const value = Number(row.oxygen_saturation);
        const inChallenge = timeInIntervals(time, challengeWindows);
        const excluded = isOffline(row) || inChallenge || !Number.isFinite(value);
        if (!Number.isFinite(time)) return;
        if (excluded) {
          if (!inExcludedGap) addGapMarker(time, inChallenge ? 'challenge' : 'offline');
          inExcludedGap = true;
          resetWindow();
          previousValidTime = null;
          return;
        }
        if (inExcludedGap) {
          inExcludedGap = false;
          resetWindow();
        }
        if (previousValidTime !== null && time - previousValidTime > TREND_MAX_SAMPLE_GAP_MS) {
          addGapMarker(previousValidTime + 60 * 1000, 'missing-data');
          resetWindow();
        }
        queue.push({ time, value });
        sum += value;
        while (queue.length && queue[0].time < time - windowMs) sum -= queue.shift().value;
        points.push({ x: time, y: sum / queue.length });
        previousValidTime = time;
      });
      return downsamplePoints(points);
    }

    function oxygenTrendSignal(short, long) {
      const byTime = new Map(long.map(point => [point.x, point.y]));
      return short.map(point => {
        const baseline = byTime.get(point.x);
        if (baseline === undefined) return null;
        if (point.y === null || baseline === null) return { x: point.x, y: null, reason: point.reason || 'gap' };
        return { x: point.x, y: point.y - baseline };
      }).filter(Boolean);
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

    function cryptoBitcoinPoints() {
      return (crypto.series?.bitcoin || []).map(point => ({ x: point.x, y: point.y }));
    }

    function notificationPoints() {
      return (notifications.items || []).filter(item => item.details?.source !== 'derived_oxygen_threshold').slice().reverse().map(item => {
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
      if (context.dataset.id === 'btcPrice') return `BTC price: ${money(context.parsed.y)}`;
      if (context.dataset.id === 'o2TrendSignal') {
        const value = context.parsed?.y;
        if (value === null || value === undefined || !Number.isFinite(Number(value))) {
          return 'Trend gap — offline, missing data, or O₂ challenge.';
        }
        if (value > 0.25) return 'Recent O₂ is running above baseline.';
        if (value < -0.25) return 'Recent O₂ is running below baseline.';
        return 'Recent O₂ is near baseline.';
      }
      if (context.dataset.id === 'o2Trailing30') {
        return null;
      }
      if (context.dataset.id === 'o2Baseline4h') {
        return null;
      }
      const value = context.parsed?.y;
      return `${context.dataset.label}: ${value === null || value === undefined ? '—' : value}`;
    }

    function legendOptions(overrides = {}) {
      if (overrides.display === false) return { display: false };
      const mobile = window.matchMedia('(max-width: 640px)').matches;
      return {
        position: overrides.position || (mobile ? 'chartArea' : 'bottom'),
        align: overrides.align || 'start',
        labels: { boxWidth: mobile ? 8 : 12, boxHeight: mobile ? 8 : 12, padding: mobile ? 6 : 12, usePointStyle: true, font: { size: mobile ? 10 : 12 } }
      };
    }

    function xScaleOptions({ hideTicks = false } = {}) {
      return {
        type: 'linear',
        min: zoomWindow?.min,
        max: zoomWindow?.max,
        ticks: { display: !hideTicks, maxRotation: 0, autoSkip: true, maxTicksLimit: window.matchMedia('(max-width: 640px)').matches ? 6 : 14, callback: timeTick }
      };
    }

    function zoomOptions() {
      return {
        limits: { x: { min: 'original', max: 'original' } },
        pan: { enabled: true, mode: 'x', onPanComplete: ({ chart }) => syncZoomFrom(chart) },
        zoom: {
          drag: { enabled: true, backgroundColor: 'rgba(37, 99, 235, .12)', borderColor: 'rgba(37, 99, 235, .55)', borderWidth: 1 },
          wheel: { enabled: true, speed: 0.08 },
          pinch: { enabled: true },
          mode: 'x',
          onZoomComplete: ({ chart }) => syncZoomFrom(chart)
        }
      };
    }

    function chartOptions(extraScales, options = {}) {
      const mobile = window.matchMedia('(max-width: 640px)').matches;
      const scales = { x: xScaleOptions({ hideTicks: options.hideXTicks }), ...extraScales };
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
        plugins: { legend: legendOptions(options.legend || {}), tooltip: { callbacks: { label: tooltipLabel } }, zoom: zoomOptions(), challengeBands: { intervals: challengeIntervals() }, offlineBands: { intervals: offlineIntervals() } },
        scales
      };
    }

    function notificationHit(chart, event) {
      const datasetIndex = chart.data.datasets.findIndex(dataset => dataset.id === 'notifications');
      if (datasetIndex < 0) return null;
      const meta = chart.getDatasetMeta(datasetIndex);
      const rect = chart.canvas.getBoundingClientRect();
      const source = event.touches?.[0] || event.changedTouches?.[0] || event;
      const x = source.clientX - rect.left;
      const y = source.clientY - rect.top;
      const mobile = window.matchMedia('(max-width: 640px)').matches;
      const xRadius = mobile ? 34 : 26;
      const yRadius = mobile ? 52 : 40;
      let best = null;
      meta.data.forEach((point, index) => {
        if (!point || point.skip) return;
        const dx = Math.abs(point.x - x);
        const dy = Math.abs(point.y - y);
        if (dx > xRadius || dy > yRadius) return;
        const score = dx + dy * 0.35;
        if (!best || score < best.score) best = { datasetIndex, index, point, score };
      });
      return best;
    }

    function setNotificationTooltip(chart, hit) {
      if (hit) {
        chart.tooltip.setActiveElements([{ datasetIndex: hit.datasetIndex, index: hit.index }], { x: hit.point.x, y: hit.point.y });
        chart.setActiveElements([{ datasetIndex: hit.datasetIndex, index: hit.index }]);
        chart.$notificationHoverActive = true;
        chart.canvas.style.cursor = 'help';
        chart.update();
      } else if (chart.$notificationHoverActive) {
        chart.tooltip.setActiveElements([], { x: 0, y: 0 });
        chart.setActiveElements([]);
        chart.$notificationHoverActive = false;
        chart.canvas.style.cursor = '';
        chart.update('none');
      }
    }

    function attachNotificationHover(chart) {
      if (chart.$notificationHoverAttached) return;
      const update = event => setNotificationTooltip(chart, notificationHit(chart, event));
      chart.canvas.addEventListener('mousemove', update);
      chart.canvas.addEventListener('click', update);
      chart.canvas.addEventListener('touchmove', update, { passive: true });
      chart.canvas.addEventListener('mouseleave', () => setNotificationTooltip(chart, null));
      chart.$notificationHoverAttached = true;
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
      renderStateStrip();
      updatePanControl();
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
      renderStateStrip();
      updatePanControl();
    }

    function upsertChart(existing, canvasId, config) {
      if (!existing) return new Chart(el(canvasId), config);
      const visibility = new Map();
      existing.data.datasets.forEach((dataset, index) => {
        const key = dataset.id || dataset.label;
        if (!key) return;
        const metaHidden = existing.getDatasetMeta(index)?.hidden;
        visibility.set(key, typeof metaHidden === 'boolean' ? metaHidden : !!dataset.hidden);
      });
      config.data.datasets.forEach(dataset => {
        const key = dataset.id || dataset.label;
        if (!key || !visibility.has(key)) return;
        dataset.hidden = visibility.get(key);
      });
      existing.data = config.data;
      existing.options.plugins = config.options.plugins;
      existing.options.scales = config.options.scales;
      existing.update();
      return existing;
    }

    function renderCharts({ deferTrend = false } = {}) {
      const sampled = downsample(readings);
      const dataPoint = (row, key) => ({ x: Date.parse(row.recorded_at), y: row[key] });
      const btcHidden = vitalsChart?.data.datasets.find(dataset => dataset.id === 'btcPrice')?.hidden ?? true;
      vitalsChart = upsertChart(vitalsChart, 'vitalsChart', {
        type: 'line',
        data: {
          datasets: [
            { label: 'Heart rate', data: sampled.map(r => dataPoint(r, 'heart_rate')), borderColor: '#dc2626', backgroundColor: '#dc262620', yAxisID: 'hr', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'SpO₂', data: sampled.map(r => dataPoint(r, 'oxygen_saturation')), borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'spo2', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'Movement', data: sampled.map(r => dataPoint(r, 'movement')), borderColor: '#059669', backgroundColor: '#05966920', yAxisID: 'move', spanGaps: true, pointRadius: 0, tension: .2 },
            { id: 'btcPrice', label: 'BTC price', data: cryptoBitcoinPoints(), borderColor: '#f97316', backgroundColor: '#f9731620', yAxisID: 'btc', hidden: btcHidden, spanGaps: true, pointRadius: 0, tension: .25 },
            { id: 'notifications', type: 'scatter', label: 'Notifications', data: notificationPoints(), yAxisID: 'spo2', pointStyle: 'triangle', pointRadius: 9, pointHoverRadius: 13, hitRadius: 24, showLine: false, borderWidth: 2, borderColor: '#92400e', backgroundColor: '#f59e0b' }
          ]
        },
        options: chartOptions({
          hr: { type: 'linear', position: 'left', title: { display: true, text: 'BPM' } },
          spo2: { type: 'linear', position: 'right', suggestedMin: 84, suggestedMax: 100, grid: { drawOnChartArea: false }, title: { display: true, text: 'SpO₂' } },
          btc: { type: 'linear', position: 'right', display: false, grid: { drawOnChartArea: false } },
          move: { display: false }
        }, { hideXTicks: true, legend: { position: 'top', align: 'end' } })
      });
      attachNotificationHover(vitalsChart);
      if (deferTrend) {
        renderOxygenTrendPlaceholder();
        scheduleOxygenTrendChart();
      } else {
        renderOxygenTrendChart();
      }
      renderStateStrip();
      updatePanControl();
    }

    function renderOxygenTrendPlaceholder() {
      if (oxygenTrendChart) return;
      oxygenTrendChart = upsertChart(oxygenTrendChart, 'oxygenTrendChart', {
        type: 'line',
        data: { datasets: [] },
        options: chartOptions({
          oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100 },
          signal: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } }
        }, { legend: { display: false } })
      });
    }

    function scheduleOxygenTrendChart() {
      const token = ++trendRenderToken;
      const render = () => {
        if (token !== trendRenderToken) return;
        renderOxygenTrendChart();
      };
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(render, { timeout: 1400 });
      } else {
        setTimeout(render, 60);
      }
    }

    function visibleRange() {
      if (zoomWindow) return zoomWindow;
      const times = readings.map(row => Date.parse(row.recorded_at)).filter(Number.isFinite);
      return times.length ? { min: Math.min(...times), max: Math.max(...times) } : null;
    }

    function fullDataRange() {
      const times = readings.map(row => Date.parse(row.recorded_at)).filter(Number.isFinite);
      return times.length ? { min: Math.min(...times), max: Math.max(...times) } : null;
    }

    function updatePrimaryChartAlignment() {
      if (!vitalsChart?.chartArea) return;
      const { left, right } = vitalsChart.chartArea;
      const width = vitalsChart.width || 0;
      el('stateStripWrap').style.setProperty('--chart-left-pad', `${Math.max(0, left)}px`);
      el('stateStripWrap').style.setProperty('--chart-right-pad', `${Math.max(0, width - right)}px`);
    }

    function updatePanControl() {
      const slider = el('timePan');
      const full = fullDataRange();
      const visible = visibleRange();
      if (!full || !visible || full.max <= full.min) {
        slider.disabled = true;
        el('panStartLabel').textContent = '—';
        el('panEndLabel').textContent = '—';
        return;
      }
      const width = visible.max - visible.min;
      const span = full.max - full.min;
      slider.disabled = width >= span - 1000;
      slider.value = slider.disabled ? 0 : Math.round(((visible.min - full.min) / Math.max(1, span - width)) * 1000);
      el('panStartLabel').textContent = timeTick(visible.min);
      el('panEndLabel').textContent = timeTick(visible.max);
    }

    function panToSliderValue(value) {
      const full = fullDataRange();
      const visible = visibleRange();
      if (!full || !visible) return;
      const width = visible.max - visible.min;
      const maxStart = full.max - width;
      if (maxStart <= full.min) return;
      const start = full.min + (Number(value) / 1000) * (maxStart - full.min);
      zoomWindow = { min: start, max: start + width };
      chartList().forEach(chart => {
        chart.options.scales.x.min = zoomWindow.min;
        chart.options.scales.x.max = zoomWindow.max;
        chart.update('none');
      });
      renderStateStrip();
      updatePanControl();
    }

    function stateClass(row) {
      if (isOffline(row)) return 'offline';
      const state = String(row.sleep_state ?? '');
      if (state === '8') return 'light';
      if (state === '15') return 'deep';
      if (state === '1') return 'awake';
      return 'inactive';
    }

    function bucketDurationMs(bucket = el('bucket').value) {
      return ({ '5m': 5, '15m': 15, '30m': 30, hour: 60, '6h': 360, '12h': 720, day: 1440 }[bucket] || 60) * 60 * 1000;
    }

    function pushMergedInterval(intervals, interval) {
      if (!interval || interval.cls === 'inactive' || interval.cls === 'offline') return;
      const last = intervals[intervals.length - 1];
      if (last && last.cls === interval.cls && Math.abs(last.end - interval.start) < 1000) {
        last.end = Math.max(last.end, interval.end);
        return;
      }
      intervals.push(interval);
    }

    function rawStateIntervals(range = visibleRange(), { includeInactive = true } = {}) {
      if (!range || range.max <= range.min || !readings.length) return [];
      const segments = [];
      readings.forEach((row, index) => {
        const start = Date.parse(row.recorded_at);
        const next = readings[index + 1] ? Date.parse(readings[index + 1].recorded_at) : start + 60 * 1000;
        const left = Math.max(start, range.min);
        const right = Math.min(next, range.max);
        if (!Number.isFinite(left) || !Number.isFinite(right) || right <= left) return;
        const cls = stateClass(row);
        if (!includeInactive && (cls === 'inactive' || cls === 'offline')) return;
        const label = `${isOffline(row) ? 'offline / sock off' : stateLabel(row.sleep_state)} · ${localTime(row.recorded_at)}`;
        const previous = segments[segments.length - 1];
        if (previous && previous.cls === cls && Math.abs(previous.end - left) < 1000) {
          previous.end = right;
          return;
        }
        segments.push({ cls, start: left, end: right, label });
      });
      return segments;
    }

    function stateIntervalAt(timestamp) {
      if (!Number.isFinite(timestamp)) return null;
      const candidates = stateStripSegments.length ? stateStripSegments : rawStateIntervals(visibleRange());
      const segment = candidates.find(item => timestamp >= item.start && timestamp <= item.end);
      return segment ? { start: segment.start, end: segment.end, cls: segment.cls } : null;
    }

    function ballparkClass(row) {
      const sleepSeconds = (row.light_sleep_seconds || 0) + (row.deep_sleep_seconds || 0);
      const awakeSeconds = row.awake_seconds || 0;
      const total = sleepSeconds + awakeSeconds;
      if (total <= 0) return null;
      if (sleepSeconds >= total * 0.55) return (row.deep_sleep_seconds || 0) > (row.light_sleep_seconds || 0) ? 'deep' : 'light';
      if (awakeSeconds >= total * 0.55) return 'awake';
      return sleepSeconds >= awakeSeconds ? 'light' : 'awake';
    }

    function rollupIntervals(range = visibleRange()) {
      if (!range || !rollups.length) return [];
      const bucketMs = bucketDurationMs();
      return rollups.map((row, index) => {
        const start = Date.parse(row.bucket_start);
        const nextStart = rollups[index + 1] ? Date.parse(rollups[index + 1].bucket_start) : start + bucketMs;
        const end = Number.isFinite(nextStart) && nextStart > start ? nextStart : start + bucketMs;
        const cls = ballparkClass(row);
        if (!Number.isFinite(start) || !Number.isFinite(end) || !cls) return null;
        return { start: Math.max(start, range.min), end: Math.min(end, range.max), cls };
      }).filter(item => item && item.end > item.start);
    }

    function rollupIntervalAt(timestamp) {
      if (!Number.isFinite(timestamp)) return null;
      const interval = rollupIntervals(visibleRange()).find(item => timestamp >= item.start && timestamp <= item.end);
      return interval ? { start: interval.start, end: interval.end, cls: interval.cls } : null;
    }

    function sleepOverlayIntervals() {
      const intervals = [];
      if (sleepBallparkEnabled) return rollupIntervals(visibleRange());
      rawStateIntervals(visibleRange(), { includeInactive: false }).forEach(interval => pushMergedInterval(intervals, interval));
      return intervals;
    }

    function setStateStripHoverFromEvent(event) {
      const range = visibleRange();
      if (!range || range.max <= range.min) return;
      const source = event.touches?.[0] || event.changedTouches?.[0] || event;
      const rect = el('stateStrip').getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (source.clientX - rect.left) / Math.max(1, rect.width)));
      const timestamp = range.min + ratio * (range.max - range.min);
      hoveredStateInterval = stateIntervalAt(timestamp);
      vitalsChart?.update('none');
    }

    function attachStateStripHover() {
      const strip = el('stateStrip');
      if (strip.dataset.hoverAttached === 'true') return;
      strip.addEventListener('mousemove', setStateStripHoverFromEvent);
      strip.addEventListener('click', setStateStripHoverFromEvent);
      strip.addEventListener('touchstart', setStateStripHoverFromEvent, { passive: true });
      strip.addEventListener('touchmove', setStateStripHoverFromEvent, { passive: true });
      strip.addEventListener('mouseleave', () => { hoveredStateInterval = null; vitalsChart?.update('none'); });
      strip.dataset.hoverAttached = 'true';
    }

    function setStateChartHoverFromEvent(event) {
      if (!stateChart?.scales?.x) return;
      const source = event.touches?.[0] || event.changedTouches?.[0] || event;
      const rect = stateChart.canvas.getBoundingClientRect();
      const timestamp = stateChart.scales.x.getValueForPixel(source.clientX - rect.left);
      hoveredStateInterval = rollupIntervalAt(timestamp) || stateIntervalAt(timestamp);
      vitalsChart?.update('none');
    }

    function attachStateChartHover(chart) {
      if (!chart || chart.$stateHoverAttached) return;
      chart.canvas.addEventListener('mousemove', setStateChartHoverFromEvent);
      chart.canvas.addEventListener('click', setStateChartHoverFromEvent);
      chart.canvas.addEventListener('touchstart', setStateChartHoverFromEvent, { passive: true });
      chart.canvas.addEventListener('touchmove', setStateChartHoverFromEvent, { passive: true });
      chart.canvas.addEventListener('mouseleave', () => { hoveredStateInterval = null; vitalsChart?.update('none'); });
      chart.$stateHoverAttached = true;
    }

    function renderStateStrip() {
      const range = visibleRange();
      updatePrimaryChartAlignment();
      attachStateStripHover();
      if (!range || range.max <= range.min || !readings.length) {
        stateStripSegments = [];
        el('stateStrip').style.background = '#e2e8f0';
        el('stateStrip').innerHTML = '';
        el('stateTimeAxis').innerHTML = '';
        return;
      }
      stateStripSegments = rawStateIntervals(range);
      el('stateStrip').innerHTML = '';
      const stops = stateStripSegments.flatMap(segment => {
        const left = ((segment.start - range.min) / (range.max - range.min)) * 100;
        const right = ((segment.end - range.min) / (range.max - range.min)) * 100;
        const color = stateStripColors[segment.cls] || stateStripColors.inactive;
        return [`${color} ${Math.max(0, left).toFixed(3)}%`, `${color} ${Math.min(100, right).toFixed(3)}%`];
      });
      el('stateStrip').style.background = stops.length ? `linear-gradient(to right, ${stops.join(', ')})` : '#e2e8f0';
      const ticks = [0, .25, .5, .75, 1].map(position => `<span style="left:${position * 100}%">${timeTick(range.min + (range.max - range.min) * position)}</span>`).join('');
      el('stateTimeAxis').innerHTML = ticks;
    }

    function renderOxygenTrendChart() {
      const challengeWindows = challengeIntervals();
      const shortAvg = rollingOxygenAverage(30, challengeWindows);
      const longAvg = rollingOxygenAverage(240, challengeWindows);
      const signal = oxygenTrendSignal(shortAvg, longAvg);
      oxygenTrendChart = upsertChart(oxygenTrendChart, 'oxygenTrendChart', {
        type: 'line',
        data: {
          datasets: [
            { id: 'o2Trailing30', label: 'Recent 30m O₂ avg', data: shortAvg, borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'oxygen', tension: .25, pointRadius: 0, spanGaps: false },
            { id: 'o2Baseline4h', label: 'Baseline 4h O₂ avg', data: longAvg, borderColor: '#7c3aed', backgroundColor: '#7c3aed20', yAxisID: 'oxygen', tension: .25, pointRadius: 0, borderDash: [6, 4], spanGaps: false },
            { id: 'o2TrendSignal', type: 'bar', label: '30m − 4h signal', data: signal, yAxisID: 'signal', backgroundColor: ctx => (ctx.raw?.y ?? 0) >= 0 ? 'rgba(5, 150, 105, .42)' : 'rgba(220, 38, 38, .42)', borderColor: ctx => (ctx.raw?.y ?? 0) >= 0 ? '#059669' : '#dc2626', borderWidth: 1 }
          ]
        },
        options: chartOptions({
          oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100 },
          signal: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: value => `${value > 0 ? '+' : ''}${value}` } }
        }, { legend: { display: false } })
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
      attachStateChartHover(stateChart);

      const rows = rollups.slice().reverse().map((row, index) => `<tr class="${index === 0 ? 'newest-rollup' : ''}"><td>${rollupLabel(row)}</td><td>${row.samples}/${row.total_samples ?? row.samples}</td><td>${fmt(row.avg_oxygen_saturation, '%')}</td><td>${fmt(row.min_oxygen_saturation, '%')}</td><td>${fmt(row.avg_heart_rate, ' bpm')}</td><td>${hours(row.sleep_seconds)}</td><td>${hours(row.awake_seconds)}</td><td>${row.offline_samples || 0}</td></tr>`).join('');
      el('rollupTable').innerHTML = `<thead><tr><th>Window</th><th>Valid/total</th><th>Avg O₂</th><th>Min O₂</th><th>Avg HR</th><th>Sleep</th><th>Awake</th><th>Offline</th></tr></thead><tbody>${rows || '<tr><td colspan="8" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function applyFilter() {
      filtered = readings;
      renderReadingsTable();
    }

    function renderReadingsTable() {
      const rows = filtered.slice().reverse().map((row, index) => `
        <tr data-index="${readings.indexOf(row)}" class="${index === 0 ? 'latest-row' : ''} ${isOffline(row) ? 'offline-row' : ''} ${isInChallenge(row) ? 'challenge-row' : ''}">
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
          el('readingsTable').querySelectorAll('tr.selected-row').forEach(row => row.classList.remove('selected-row'));
          tr.classList.add('selected-row');
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

    function renderChallenges() {
      const items = challenges.items || [];
      const total = challenges.total ?? items.length;
      const active = items.find(item => item.active);
      el('challengeCount').textContent = total;
      el('challengePage').textContent = total ? `${total} total${active ? ' · active now' : ''}` : 'none yet';
      el('challengeActions').style.display = SHARE_MODE ? 'none' : '';
      el('endChallenge').disabled = !active;
      const emptyChallengeMarkup = SHARE_MODE
        ? '<div class="empty">No oxygen challenges in this range.</div>'
        : `<div class="empty"><b>No oxygen challenges in this range yet.</b><br />Add one from this popup, or zoom the chart first and use the visible window.
            <div class="challenge-empty-actions">
              <button class="primary" type="button" data-add-challenge-empty>Add new O₂ challenge</button>
              <button type="button" data-visible-challenge-empty>Use visible chart window</button>
            </div>
          </div>`;
      el('challengeList').innerHTML = items.map(item => {
        const summary = item.summary || {};
        const comparison = item.comparison || {};
        return `<article class="challenge-item ${item.active ? 'active' : ''}">
          <div class="challenge-title"><span>${item.active ? '🟢 ' : ''}${item.label || 'Oxygen challenge'}</span><button type="button" data-challenge-id="${item.id}">Open</button></div>
          <div class="notification-meta">${localTime(item.start_time)} → ${item.active ? 'active' : localTime(item.effective_end_time)} · ${durationText(summary.duration_seconds)}</div>
          <div class="challenge-metrics">
            <span>Avg O₂ <b>${fmt(summary.avg_oxygen_saturation, '%')}</b></span>
            <span>Min O₂ <b>${fmt(summary.min_oxygen_saturation, '%')}</b></span>
            <span>Avg HR <b>${fmt(summary.avg_heart_rate, ' bpm')}</b></span>
            <span>Low O₂ <b>${summary.low_oxygen_samples || 0}</b> (${signed(comparison.low_oxygen_delta)})</span>
          </div>
        </article>`;
      }).join('') || emptyChallengeMarkup;
      [...el('challengeList').querySelectorAll('button[data-challenge-id]')].forEach(button => {
        button.addEventListener('click', () => openChallengeDetail(Number(button.dataset.challengeId)));
      });
      el('challengeList').querySelector('[data-add-challenge-empty]')?.addEventListener('click', () => openNewChallengeModal());
      el('challengeList').querySelector('[data-visible-challenge-empty]')?.addEventListener('click', markVisibleChallenge);
    }

    async function saveChallenge(payload) {
      const response = await fetch(`${API_BASE}/api/oxygen-challenges`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error(`Could not save challenge: ${response.status}`);
      await refresh();
    }

    async function startChallenge() {
      await saveChallenge({ start_time: new Date().toISOString(), label: 'Oxygen challenge', notes: 'Started from dashboard' });
    }

    async function endActiveChallenge() {
      const active = (challenges.items || []).find(item => item.active);
      if (!active) return;
      const response = await fetch(`${API_BASE}/api/oxygen-challenges/${active.id}`, {
        method: 'PATCH', credentials: 'include', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ end_time: new Date().toISOString() })
      });
      if (!response.ok) throw new Error(`Could not end challenge: ${response.status}`);
      await refresh();
    }

    async function markVisibleChallenge() {
      const range = visibleRange();
      if (!range || range.max <= range.min) return;
      openNewChallengeModal({ start: new Date(range.min).toISOString(), end: new Date(range.max).toISOString(), notes: 'Marked from visible chart window' });
    }

    function openNewChallengeModal(prefill = {}) {
      currentChallengeDetail = null;
      el('challengesPanel').classList.add('hidden');
      el('challengesToggle').setAttribute('aria-expanded', 'false');
      el('challengeModalTitle').textContent = 'Add O₂ challenge';
      el('challengeModalMeta').textContent = 'Create an off-oxygen window by choosing start and end times.';
      el('challengeSummary').innerHTML = '';
      el('challengeSummary').style.display = 'none';
      el('challengeDetailChartFrame').style.display = 'none';
      el('challengeNotes').textContent = 'Tip: use “Use visible chart window” after zooming to prefill the exact chart interval.';
      el('challengeEditForm').style.display = 'grid';
      el('challengeEditLabel').value = prefill.label || 'Oxygen challenge';
      el('challengeEditStart').value = toDateTimeLocal(prefill.start || new Date().toISOString());
      el('challengeEditEnd').value = prefill.end ? toDateTimeLocal(prefill.end) : '';
      el('challengeEditNotes').value = prefill.notes || '';
      el('deleteChallenge').style.display = 'none';
      el('saveChallengeEdits').textContent = 'Add challenge';
      if (challengeDetailChart) {
        challengeDetailChart.destroy();
        challengeDetailChart = null;
      }
      el('challengeModal').classList.remove('hidden');
    }

    async function openChallengeDetail(id) {
      el('challengesPanel').classList.add('hidden');
      el('challengesToggle').setAttribute('aria-expanded', 'false');
      el('notificationsPanel').classList.add('hidden');
      el('notificationsToggle').setAttribute('aria-expanded', 'false');
      const detail = await fetchJson(`${API_BASE}/api/oxygen-challenges/${id}`);
      currentChallengeDetail = detail;
      const summary = detail.summary || {};
      const prior = detail.prior_summary || {};
      const comparison = detail.comparison || {};
      el('challengeModalTitle').textContent = detail.label || 'Oxygen challenge';
      el('challengeModalMeta').textContent = `${localTime(detail.start_time)} → ${detail.active ? 'active' : localTime(detail.effective_end_time)} · ${durationText(summary.duration_seconds)} off oxygen`;
      el('challengeNotes').textContent = detail.notes || 'Challenge data is excluded from normal dashboard averages and compared against the same-length window immediately before oxygen came off.';
      el('challengeSummary').style.display = 'grid';
      el('challengeDetailChartFrame').style.display = 'block';
      el('challengeEditForm').style.display = SHARE_MODE ? 'none' : 'grid';
      el('challengeEditLabel').value = detail.label || 'Oxygen challenge';
      el('challengeEditStart').value = toDateTimeLocal(detail.start_time);
      el('challengeEditEnd').value = detail.end_time ? toDateTimeLocal(detail.end_time) : '';
      el('challengeEditNotes').value = detail.notes || '';
      el('deleteChallenge').style.display = SHARE_MODE ? 'none' : '';
      el('saveChallengeEdits').textContent = 'Save edits';
      el('challengeSummary').innerHTML = [
        ['Avg O₂', fmt(summary.avg_oxygen_saturation, '%'), `vs prior ${fmt(prior.avg_oxygen_saturation, '%')} (${signed(comparison.avg_oxygen_delta, ' pts')})`],
        ['Min O₂', fmt(summary.min_oxygen_saturation, '%'), `vs prior ${fmt(prior.min_oxygen_saturation, '%')} (${signed(comparison.min_oxygen_delta, ' pts')})`],
        ['Avg HR', fmt(summary.avg_heart_rate, ' bpm'), `vs prior ${fmt(prior.avg_heart_rate, ' bpm')} (${signed(comparison.avg_heart_rate_delta, ' bpm')})`],
        ['Events', `${summary.low_oxygen_samples || 0} low · ${summary.critical_oxygen_samples || 0} critical`, `sleep ${durationText(summary.sleep_seconds)} · awake ${durationText(summary.awake_seconds)}`]
      ].map(([label, value, foot]) => `<div class="mini"><span class="eyebrow">${label}</span><b>${value}</b><small>${foot}</small></div>`).join('');
      el('challengeModal').classList.remove('hidden');
      renderChallengeDetailChart(detail);
    }

    async function saveChallengeEdits(event) {
      event.preventDefault();
      const payload = {
        label: el('challengeEditLabel').value || 'Oxygen challenge',
        start_time: fromDateTimeLocal(el('challengeEditStart').value),
        notes: el('challengeEditNotes').value || ''
      };
      if (!payload.start_time) {
        alert('Start time is required.');
        return;
      }
      const endTime = fromDateTimeLocal(el('challengeEditEnd').value);
      payload.end_time = endTime;
      const url = currentChallengeDetail
        ? `${API_BASE}/api/oxygen-challenges/${currentChallengeDetail.id}`
        : `${API_BASE}/api/oxygen-challenges`;
      const response = await fetch(url, {
        method: currentChallengeDetail ? 'PATCH' : 'POST',
        credentials: 'include',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error(`Could not save challenge: ${response.status}`);
      const saved = await response.json();
      await refresh();
      await openChallengeDetail(saved.id);
    }

    async function deleteCurrentChallenge() {
      if (!currentChallengeDetail) return;
      if (!window.confirm('Delete this oxygen challenge? Its readings will return to normal stats.')) return;
      const response = await fetch(`${API_BASE}/api/oxygen-challenges/${currentChallengeDetail.id}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (!response.ok) throw new Error(`Could not delete challenge: ${response.status}`);
      currentChallengeDetail = null;
      el('challengeModal').classList.add('hidden');
      await refresh();
    }

    function renderChallengeDetailChart(detail) {
      const toPoint = (row, key) => ({ x: Date.parse(row.recorded_at), y: row[key] });
      if (challengeDetailChart) challengeDetailChart.destroy();
      challengeDetailChart = new Chart(el('challengeDetailChart'), {
        type: 'line',
        data: { datasets: [
          { label: 'Challenge O₂', data: (detail.readings || []).map(row => toPoint(row, 'oxygen_saturation')), yAxisID: 'oxygen', borderColor: '#2563eb', pointRadius: 1, tension: .2 },
          { label: 'Prior O₂', data: (detail.prior_readings || []).map(row => toPoint(row, 'oxygen_saturation')), yAxisID: 'oxygen', borderColor: '#94a3b8', borderDash: [5, 4], pointRadius: 0, tension: .2 },
          { label: 'Challenge HR', data: (detail.readings || []).map(row => toPoint(row, 'heart_rate')), yAxisID: 'hr', borderColor: '#dc2626', pointRadius: 1, tension: .2 }
        ] },
        options: chartOptions({
          oxygen: { type: 'linear', position: 'left', suggestedMin: 86, suggestedMax: 100, title: { display: true, text: 'O₂' } },
          hr: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'BPM' } }
        })
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

    async function safeRefresh(options = {}) {
      try {
        await refresh(options);
      } catch (error) {
        console.error(error);
        updateRefreshButton('Refresh failed');
        el('status').innerHTML = '<span class="status-dot offline"></span>Refresh failed · keeping last loaded data';
        setTimeout(() => updateRefreshButton(), 1500);
      }
    }

    function tickCountdown() {
      secondsUntilRefresh = Math.max(0, secondsUntilRefresh - 1);
      updateRefreshButton();
      if (secondsUntilRefresh === 0) safeRefresh();
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
    el('batteryStatus').addEventListener('click', () => alert(el('batteryStatus').dataset.detail || 'Battery unavailable'));

    el('window').addEventListener('change', () => { notificationPageOffset = 0; safeRefresh({ resetZoom: true }); });
    el('bucket').addEventListener('change', () => safeRefresh({ resetZoom: true }));
    el('refresh').addEventListener('click', () => safeRefresh());
    el('download').addEventListener('click', downloadCsv);
    el('resetZoom').addEventListener('click', resetZoom);
    el('challengesToggle').addEventListener('click', () => {
      el('notificationsPanel').classList.add('hidden');
      el('notificationsToggle').setAttribute('aria-expanded', 'false');
      const panel = el('challengesPanel');
      const hidden = panel.classList.toggle('hidden');
      el('challengesToggle').setAttribute('aria-expanded', String(!hidden));
    });
    el('startChallenge').addEventListener('click', startChallenge);
    el('endChallenge').addEventListener('click', endActiveChallenge);
    el('addChallenge').addEventListener('click', () => openNewChallengeModal());
    el('markVisibleChallenge').addEventListener('click', markVisibleChallenge);
    el('closeChallengesPanel').addEventListener('click', () => { el('challengesPanel').classList.add('hidden'); el('challengesToggle').setAttribute('aria-expanded', 'false'); });
    el('closeNotificationsPanel').addEventListener('click', () => { el('notificationsPanel').classList.add('hidden'); el('notificationsToggle').setAttribute('aria-expanded', 'false'); });
    el('closeChallengeModal').addEventListener('click', () => { currentChallengeDetail = null; el('challengeModal').classList.add('hidden'); });
    el('challengeEditForm').addEventListener('submit', saveChallengeEdits);
    el('deleteChallenge').addEventListener('click', deleteCurrentChallenge);
    el('timePan').addEventListener('input', event => panToSliderValue(event.target.value));
    el('sleepHighlightToggle').addEventListener('change', event => {
      sleepHighlightEnabled = event.target.checked;
      el('sleepBallparkToggle').disabled = !sleepHighlightEnabled;
      vitalsChart?.update('none');
    });
    el('sleepBallparkToggle').addEventListener('change', event => {
      sleepBallparkEnabled = event.target.checked;
      vitalsChart?.update('none');
    });
    el('notificationsToggle').addEventListener('click', () => {
      el('challengesPanel').classList.add('hidden');
      el('challengesToggle').setAttribute('aria-expanded', 'false');
      const panel = el('notificationsPanel');
      const hidden = panel.classList.toggle('hidden');
      el('notificationsToggle').setAttribute('aria-expanded', String(!hidden));
    });
    el('notificationsPrev').addEventListener('click', () => { notificationPageOffset = Math.max(0, notificationPageOffset - NOTIFICATION_PAGE_SIZE); renderNotifications(); });
    el('notificationsNext').addEventListener('click', () => { notificationPageOffset += NOTIFICATION_PAGE_SIZE; renderNotifications(); });
    ['vitalsChart', 'oxygenTrendChart', 'rollupChart', 'stateChart'].forEach(id => {
      el(id).addEventListener('dblclick', resetZoom);
    });
    window.addEventListener('resize', () => { renderCharts({ deferTrend: true }); renderRollups(); updatePanControl(); });
    if ('serviceWorker' in navigator && !SHARE_MODE) {
      window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').then(updateInstallButton).catch(updateInstallButton));
    }
    updateInstallButton();
    safeRefresh({ resetZoom: true });
    setInterval(tickCountdown, 1000);
  </script>
</body>
</html>
"""


def render_dashboard(api_base: str = "", *, share_mode: bool = False) -> str:
    pwa_head = (
        ""
        if share_mode
        else '<link rel="manifest" href="/manifest.webmanifest" />\n  <link rel="apple-touch-icon" href="/icon-192.png" />'
    )
    return (
        DASHBOARD_HTML.replace("__API_BASE__", api_base)
        .replace("__SHARE_MODE__", "true" if share_mode else "false")
        .replace("__PWA_HEAD__", pwa_head)
    )
