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
    .hero-right { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
    .baby-name { color: var(--text); font-weight: 950; font-size: clamp(1rem, 2.5vw, 1.35rem); background: rgba(255,255,255,.76); border: 1px solid rgba(226,232,240,.9); border-radius: 999px; padding: .38rem .75rem; box-shadow: 0 8px 24px rgba(15,23,42,.08); }
    h1 { margin: 0; letter-spacing: -.045em; font-size: clamp(2.1rem, 5vw, 4.2rem); line-height: .92; }
    .title-status-dot { display: none; }
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
    .mobile-label { display: none; }
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
    .chart-frame canvas { display: block; width: 100% !important; height: 100% !important; touch-action: pan-y; }
    .companion-chart { margin-top: 2px; padding-top: 0; background: transparent; }
    .info-popover-wrap { position: relative; display: inline-flex; align-items: center; }
    .companion-info { position: absolute; right: 6px; top: 6px; z-index: 2; }
    .info-button { width: 28px; height: 28px; border-radius: 999px; padding: 0; display: inline-grid; place-items: center; background: #eff6ff; color: #1d4ed8; font-weight: 950; }
    .info-popover { display: none; position: absolute; right: 0; top: calc(100% + 8px); width: min(360px, calc(100vw - 32px)); z-index: 25; background: #fff; border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 14px; padding: 12px; color: var(--text); font-size: .84rem; line-height: 1.35; text-transform: none; letter-spacing: normal; }
    .info-popover-wrap:hover .info-popover, .info-popover-wrap:focus-within .info-popover { display: block; }
    .chart-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 10px; padding: 8px; border: 1px solid rgba(226,232,240,.9); background: rgba(248,250,252,.78); border-radius: 14px; }
    .control-section { display: contents; }
    .control-section-title { color: var(--muted); font-size: .72rem; font-weight: 950; text-transform: uppercase; letter-spacing: .08em; margin-right: 2px; }
    .control-field { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: .78rem; font-weight: 850; }
    .control-field select { min-width: 124px; }
    .chart-toolbar .inline-toggle { border: 1px solid rgba(203,213,225,.9); border-radius: 999px; padding: 6px 9px; background: #fff; color: var(--text); }
    .coverage-chip { margin-left: auto; white-space: nowrap; }
    .o2-menu-wrap { position: relative; }
    .o2-add-button { background: #1d4ed8; color: #fff; border-color: #1d4ed8; min-width: 54px; box-shadow: 0 8px 24px rgba(37,99,235,.22); }
    .o2-add-menu { position: absolute; right: 0; top: calc(100% + 8px); display: grid; gap: 8px; width: min(240px, calc(100vw - 32px)); padding: 10px; border: 1px solid #bfdbfe; border-radius: 14px; background: #fff; box-shadow: var(--shadow); z-index: 28; }
    .o2-add-menu.hidden { display: none; }
    .o2-add-menu button { justify-content: flex-start; text-align: left; }
    .share-only-hidden { display: none !important; }
    .time-pan-control { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: center; margin-top: 8px; color: var(--muted); font-size: .78rem; }
    .time-pan-control input[type="range"] { width: 100%; padding: 0; accent-color: var(--blue); }
    .time-pan-control input[disabled] { opacity: .4; cursor: not-allowed; }
    .chart-actions { display: flex; gap: 8px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
    .chart-hint { color: var(--muted); font-size: .8rem; }
    .update-chip { opacity: 0; transform: translateY(-2px); color: var(--green); font-size: .8rem; font-weight: 900; transition: opacity .45s ease, transform .45s ease; }
    .update-chip.show { opacity: 1; transform: translateY(0); }
    .pulse-new { animation: pulseNew .9s ease; }
    @keyframes pulseNew { 0% { background: #dcfce7; } 100% { background: transparent; } }
    .initial-loading { position: fixed; inset: 0; z-index: 200; display: grid; place-items: center; padding: 20px; background: rgba(248, 250, 252, .86); backdrop-filter: blur(9px); transition: opacity .22s ease, visibility .22s ease; }
    .initial-loading.hidden { opacity: 0; visibility: hidden; pointer-events: none; }
    .loading-card { width: min(360px, 100%); border: 1px solid rgba(191, 219, 254, .9); border-radius: 22px; background: rgba(255,255,255,.94); box-shadow: var(--shadow); padding: 18px; display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: center; }
    .loading-spinner { width: 32px; height: 32px; border-radius: 999px; border: 4px solid #dbeafe; border-top-color: var(--blue); animation: loadingSpin .8s linear infinite; }
    .loading-title { font-weight: 950; letter-spacing: -.02em; }
    .loading-message { color: var(--muted); font-size: .9rem; margin-top: 2px; }
    .initial-loading.error .loading-spinner { animation: none; border-color: #fecdd3; border-top-color: var(--red); }
    @keyframes loadingSpin { to { transform: rotate(360deg); } }
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
    .account-cluster.hidden { display: none; }
    .account-add-button { padding-inline: .65rem; }
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
    .daily-insights-button { background: #f0f9ff; color: #0369a1; border-color: #bae6fd; }
    .daily-insights-summary { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 12px; }
    .daily-insights-summary span { background: #f8fafc; border: 1px solid var(--line); border-radius: 999px; padding: 7px 10px; font-size: .83rem; color: var(--muted); }
    .daily-insights-chart { height: 260px; margin: 8px 0 12px; padding: 10px; border: 1px solid var(--line); border-radius: 16px; background: #f8fafc; }
    .daily-insights-table th, .daily-insights-table td { text-align: right; }
    .daily-insights-table th:first-child, .daily-insights-table td:first-child { text-align: left; position: sticky; left: 0; background: inherit; }
    .daily-insights-table tbody tr:hover td { background: #f8fafc; }
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
    .state-strip-wrap { position: relative; margin: -2px var(--chart-right-pad, 0px) 0 var(--chart-left-pad, 0px); }
    .state-strip { height: 18px; border-radius: 0 0 10px 10px; overflow: hidden; background: #e2e8f0; border: 1px solid var(--line); border-top: 0; cursor: crosshair; }
    .state-segment { min-width: 1px; }
    .state-segment:hover { filter: saturate(1.2) brightness(1.03); }
    .state-time-axis { position: relative; height: 18px; color: var(--muted); font-size: .72rem; }
    .state-time-axis span { position: absolute; top: 3px; transform: translateX(-50%); white-space: nowrap; }
    .state-segment.light { background: rgba(124, 58, 237, .72); }
    .state-segment.deep { background: rgba(37, 99, 235, .72); }
    .state-segment.awake { background: rgba(180, 83, 9, .72); }
    .state-segment.inactive { background: rgba(148, 163, 184, .72); }
    .state-segment.offline { background: rgba(100, 116, 139, .48); }
    .state-tooltip { position: fixed; z-index: 120; max-width: min(300px, calc(100vw - 24px)); background: #0f172a; color: #f8fafc; border: 1px solid rgba(255,255,255,.12); box-shadow: var(--shadow); border-radius: 12px; padding: 8px 10px; font-size: .78rem; line-height: 1.3; pointer-events: none; }
    .state-tooltip.hidden { display: none; }
    .state-tooltip b { display: block; color: #fff; margin-bottom: 2px; }
    .sleep-overlay-controls { display: flex; flex-wrap: wrap; justify-content: flex-start; gap: 8px 12px; color: var(--muted); font-size: .78rem; }
    .inline-toggle { display: inline-flex; align-items: center; gap: 6px; font-weight: 800; }
    .inline-toggle input { padding: 0; }
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
    tr.offline-row td { background: #f1f5f9; color: #475569; }
    tr.offline-row:hover td { background: #e2e8f0; }
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
      .details-grid, .readings-grid { grid-template-columns: 1fr; }
      .reading-detail-panel { position: static; }
      .status { white-space: normal; }
      .toolbar { position: static; }
      .chart-frame.main { height: 360px; }
      .chart-frame.companion { height: 185px; }
      .chart-frame.secondary { height: 230px; }
    }
    @media (max-width: 640px) {
      .shell { width: min(100% - 14px, 1500px); padding: 10px 0 24px; }
      .hero { gap: 8px; margin-bottom: 6px; align-items: center; flex-direction: row; }
      .hero > div:first-child { min-width: 0; }
      h1 { display: flex; align-items: center; gap: 8px; font-size: clamp(1.55rem, 10vw, 2.3rem); }
      .title-status-dot { display: inline-block; flex: 0 0 auto; width: 11px; height: 11px; box-shadow: 0 0 0 5px rgba(34,197,94,.13); }
      .title-status-dot.good { animation: livePulse 1.8s ease-in-out infinite; }
      @keyframes livePulse { 0%, 100% { box-shadow: 0 0 0 4px rgba(34,197,94,.14); } 50% { box-shadow: 0 0 0 8px rgba(34,197,94,.05); } }
      .subtitle { display: none; }
      .toolbar, .panel, .card { border-radius: 16px; box-shadow: 0 10px 26px rgba(15, 23, 42, .08); }
      .toolbar { flex-wrap: nowrap; justify-content: flex-start; align-items: center; padding: 6px; gap: 4px; margin: 6px 0 8px; backdrop-filter: none; overflow: visible; }
      .control-group { gap: 4px; width: auto; flex-wrap: nowrap; }
      .filter-cluster { flex: 1 1 auto; min-width: 74px; }
      .device-label { display: none; }
      .filter-cluster select { width: 100%; min-width: 0; max-width: 104px; }
      .hero-right, .baby-name, .status { display: none; }
      .refresh-cluster { flex: 0 0 auto; justify-content: flex-end; margin-left: auto; }
      .desktop-label { display: none; }
      .mobile-label { display: inline; }
      .install-button.show { display: none; }
      label { font-size: .76rem; }
      select, button { padding: .38rem .42rem; border-radius: 10px; font-size: .78rem; min-height: 32px; }
      button.icon-button { width: 34px; height: 34px; }
      .challenge-button { white-space: nowrap; }
      .notification-button { width: 36px; height: 32px; padding: 0; display: inline-grid; place-items: center; font-size: .94rem; }
      .notification-count { position: absolute; right: -5px; top: -6px; min-width: 17px; height: 17px; padding: 0 4px; margin: 0; font-size: .64rem; }
      .challenge-count { min-width: 17px; height: 17px; padding: 0 4px; margin-left: 2px; font-size: .64rem; }
      .battery-pill { gap: 4px; min-height: 32px; padding-inline: .42rem; }
      .battery-shell { width: 22px; height: 13px; border-width: 1.5px; padding: 2px; }
      .battery-shell::after { right: -4px; top: 4px; width: 2px; height: 4px; }
      #batteryLabel { font-size: .72rem; }
      .refresh-cluster #refresh { min-width: 34px; width: 40px; padding-inline: 0; }
      .chart-stack, .grid { gap: 8px; }
      .glance-strip { gap: 7px; margin: 8px 0; }
      .glance-card { min-height: 66px; padding: 8px 9px; }
      .glance-card strong { font-size: 1.35rem; margin: 2px 0; }
      .glance-card small { font-size: .75rem; }
      .chart-panel, .panel, .card { padding: 9px; }
      .panel-title { gap: 8px; margin-bottom: 5px; align-items: flex-start; }
      .panel-title { flex-wrap: wrap; }
      .primary-chart > .panel-title { flex-wrap: nowrap; align-items: center; }
      .primary-chart .chart-actions { flex: 0 0 auto; margin-left: auto; }
      .primary-chart .o2-add-button { min-width: 58px; font-size: .9rem; padding: .48rem .62rem; }
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
  <div id="initialLoading" class="initial-loading" role="status" aria-live="polite">
    <div class="loading-card">
      <span class="loading-spinner" aria-hidden="true"></span>
      <span>
        <span class="loading-title">Loading Owlet data…</span>
        <span id="initialLoadingMessage" class="loading-message">Connecting to local dashboard.</span>
      </span>
    </div>
  </div>
  <main class="shell">
    <section class="hero">
      <div>
        <h1><span>Owlet Dashboard</span><span id="titleStatusDot" class="status-dot title-status-dot" aria-hidden="true"></span></h1>
        <p class="subtitle">
          Live-updated pulse plus historical drill-downs for breathing, sleep, wake time,
          and raw readings. Retrospective trend viewing only — not a medical monitor or alert replacement.
        </p>
      </div>
      <div class="hero-right">
        <div class="baby-name" id="babyName">Owlet sock</div>
        <div class="status" id="status"><span class="status-dot"></span>Checking collector…</div>
      </div>
    </section>

    <section class="toolbar" aria-label="Date and data controls">
      <div id="accountCluster" class="control-group filter-cluster account-cluster hidden">
        <label class="device-label" for="accountSelect">Account</label>
        <select id="accountSelect"><option value="">Default</option></select>
        <button id="addAccount" class="account-add-button" type="button" title="Link another Owlet account">Link Owlet</button>
      </div>
      <div class="control-group filter-cluster">
        <label class="device-label" for="deviceSelect">Device</label>
        <select id="deviceSelect"><option value="">Loading devices…</option></select>
      </div>
      <div class="control-group refresh-cluster toolbar-right">
        <button id="dailyInsightsToggle" class="daily-insights-button" type="button" aria-label="Daily insights"><span class="desktop-label">Daily insights</span><span class="mobile-label" aria-hidden="true">📊</span></button>
        <button id="challengesToggle" class="challenge-button" type="button" aria-expanded="false" aria-label="O₂ challenges"><span class="desktop-label">O₂ challenges</span><span class="mobile-label" aria-hidden="true">O₂ Ch.</span> <span id="challengeCount" class="challenge-count">0</span></button>
        <button id="notificationsToggle" class="notification-button" type="button" aria-expanded="false" aria-label="Notifications"><span class="desktop-label">Notifications</span><span class="mobile-label" aria-hidden="true">🔔</span> <span id="notificationCount" class="notification-count">0</span></button>
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
      <article class="card glance-card">
        <span class="eyebrow">Sleep</span>
        <strong id="sleepTotal">—</strong>
        <small id="sleepSummary">Estimated from intervals.</small>
        <div class="progress glance-progress" title="Light sleep / deep sleep / awake">
          <span id="lightBar"></span><span id="deepBar"></span><span id="awakeBar"></span>
        </div>
        <small>Light <span class="inline-stat" id="lightSleep">—</span> · Deep <span class="inline-stat" id="deepSleep">—</span> · Awake <span class="inline-stat" id="awakeTime">—</span></small>
      </article>
      <article class="card glance-card crypto-card">
        <span class="eyebrow">Crypto</span>
        <strong id="cryptoHeadline">BTC —</strong>
        <div class="crypto-lines" id="cryptoLines">
          <small>Loading BTC / ETH / XMR…</small>
        </div>
      </article>
    </section>

    <section class="chart-stack" aria-label="Primary charts">
      <div class="panel chart-panel primary-chart">
        <div class="panel-title">
          <div>
            <h2>Main vitals trace</h2>
            <span class="chart-hint">Drag charts to pan. Desktop drag-select zooms; double-click resets.</span>
          </div>
          <div class="chart-actions">
            <span class="update-chip" id="updateChip">New data</span>
            <span class="o2-menu-wrap" id="o2AddWrap">
              <button id="o2AddMenuToggle" class="o2-add-button" type="button" aria-expanded="false" title="Add O₂ challenge event">O₂+</button>
              <span id="o2AddMenu" class="o2-add-menu hidden" role="menu" aria-label="Add O₂ challenge">
                <button id="menuVisibleChallenge" type="button" role="menuitem">Use current graph window</button>
                <button id="menuNewChallenge" type="button" role="menuitem">Enter new times…</button>
              </span>
            </span>
          </div>
        </div>
        <div class="chart-toolbar" aria-label="Graph controls">
          <div class="control-section view-section">
            <label class="control-field" for="window">Range
              <select id="window">
                <option value="6">6 hours</option>
                <option value="12">12 hours</option>
                <option selected value="24">24 hours</option>
                <option value="72">3 days</option>
                <option value="168">7 days</option>
                <option value="720">30 days</option>
                <option value="all">All stored data</option>
              </select>
            </label>
            <label class="control-field" for="smoothing">Smoothing
              <select id="smoothing">
                <option selected value="raw">Raw points</option>
                <option value="5">5 min avg</option>
                <option value="15">15 min avg</option>
                <option value="30">30 min avg</option>
                <option value="60">1 hour avg</option>
                <option value="240">4 hour avg</option>
              </select>
            </label>
            <button id="resetZoom" type="button">Reset zoom</button>
            <button id="download" class="icon-button" title="Download CSV" aria-label="Download CSV">CSV</button>
            <span class="control-section-title">Overlays</span>
            <label class="inline-toggle"><input id="challengeBandsToggle" type="checkbox" checked /> O₂ windows</label>
            <label class="inline-toggle"><input id="sleepHighlightToggle" type="checkbox" /> Sleep colors</label>
            <label class="inline-toggle"><input id="sleepBallparkToggle" type="checkbox" disabled /> Guess sleep windows</label>
            <span class="small coverage-chip" id="coverage">—</span>
          </div>
        </div>
        <div class="chart-frame main"><canvas id="vitalsChart"></canvas></div>
        <div id="stateStripWrap" class="state-strip-wrap" title="Sleep/wake/offline state across the visible vitals window">
          <div id="stateStrip" class="state-strip"></div>
          <div id="stateTimeAxis" class="state-time-axis"></div>
          <div id="stateTooltip" class="state-tooltip hidden" role="tooltip"></div>
        </div>
        <div class="companion-chart" aria-label="Oxygen trend companion chart">
          <div class="chart-frame companion"><canvas id="oxygenTrendChart"></canvas>
            <span class="info-popover-wrap companion-info">
              <button class="info-button" type="button" aria-label="How to read the O₂ trend companion">i</button>
              <span class="info-popover" role="tooltip">
                O₂ trend companion: a MACD-style oxygen view. It compares recent 30-minute O₂ against the 4-hour baseline. Green means recent O₂ is above baseline; red means below. Offline gaps are not bridged; oxygen challenges stay visible as real readings behind the blue challenge band.
              </span>
            </span>
          </div>
        </div>
        <div class="time-pan-control">
          <span id="panStartLabel">—</span>
          <input id="timePan" type="range" min="0" max="1000" value="0" disabled aria-label="Scroll visible time window" />
          <span id="panEndLabel">—</span>
        </div>
      </div>
    </section>

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

  <div id="dailyInsightsModal" class="challenge-modal hidden" role="dialog" aria-label="Daily insights">
    <div class="challenge-modal-card">
      <div class="panel-title">
        <div>
          <h2>Daily insights</h2>
          <span class="small" id="dailyInsightsMeta">Last 7 rolling 24-hour periods. Offline/sock-off and O₂ challenge samples excluded.</span>
        </div>
        <button id="closeDailyInsights" type="button">Close</button>
      </div>
      <div id="dailyInsightsSummary" class="daily-insights-summary"></div>
      <div class="daily-insights-chart" aria-label="Daily O₂, heart-rate, and skin-temperature comparison chart"><canvas id="dailyInsightsChart"></canvas></div>
      <div class="table-wrap"><table id="dailyInsightsTable" class="daily-insights-table"></table></div>
      <p class="small">Sleeping = Owlet light/deep sleep states. Waking = Owlet awake state. Inactive/unknown samples count only in overall averages.</p>
    </div>
  </div>

  <script>
    const API_BASE = "__API_BASE__";
    const SHARE_MODE = __SHARE_MODE__;
    const REFRESH_SECONDS = 15;
    const TABLE_ROW_LIMIT = 500;
    const CHART_MAX_POINTS = 1000;
    let readings = [];
    let filtered = [];
    let summary = null;
    let insights = null;
    let devices = [];
    let accounts = [];
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
    let challengeDetailChart = null;
    let dailyInsightsChart = null;
    let secondsUntilRefresh = REFRESH_SECONDS;
    let syncInProgress = false;
    let zoomWindow = null;
    let loadedHours = null;
    let loadingOlderHistory = false;
    let lastLatestTimestamp = null;
    let deferredInstallPrompt = null;
    let currentChallengeDetail = null;
    let hoveredStateInterval = null;
    let sleepHighlightEnabled = false;
    let sleepBallparkEnabled = false;
    let challengeBandsEnabled = true;
    let stateStripSegments = [];
    let trendRenderToken = 0;
    let refreshToken = 0;
    let firstLoadComplete = false;
    let refreshInFlight = null;
    let readingsTableSignature = '';

    const sleepPhaseColors = {
      light: 'rgba(124, 58, 237, .21)',
      deep: 'rgba(37, 99, 235, .21)',
      awake: 'rgba(180, 83, 9, .20)',
      inactive: 'rgba(148, 163, 184, .16)',
      offline: 'rgba(100, 116, 139, .18)'
    };

    const stateStripColors = {
      light: 'rgba(124, 58, 237, .72)',
      deep: 'rgba(37, 99, 235, .72)',
      awake: 'rgba(180, 83, 9, .72)',
      inactive: 'rgba(148, 163, 184, .72)',
      offline: 'rgba(100, 116, 139, .48)'
    };

    const offlineBandsPlugin = {
      id: 'offlineBands',
      beforeDatasetsDraw(chart, _args, options) {
        const intervals = options?.intervals || [];
        if (!intervals.length || !chart.scales?.x) return;
        const { ctx, chartArea, scales } = chart;
        ctx.save();
        ctx.fillStyle = 'rgba(100, 116, 139, 0.14)';
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.32)';
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
      beforeDraw(chart, _args, options) {
        const intervals = options?.intervals || [];
        if (!intervals.length || !chart.scales?.x) return;
        const { ctx, chartArea, scales } = chart;
        const isTrendCompanion = chart.canvas.id === 'oxygenTrendChart';
        ctx.save();
        ctx.fillStyle = isTrendCompanion ? 'rgba(37, 99, 235, 0.045)' : 'rgba(37, 99, 235, 0.10)';
        ctx.strokeStyle = 'rgba(37, 99, 235, 0.22)';
        intervals.forEach(({ start, end }) => {
          const left = Math.max(chartArea.left, scales.x.getPixelForValue(start));
          const right = Math.min(chartArea.right, scales.x.getPixelForValue(end));
          if (!Number.isFinite(left) || !Number.isFinite(right) || right <= chartArea.left || left >= chartArea.right) return;
          const width = Math.max(2, right - left);
          ctx.fillRect(left, chartArea.top, width, chartArea.bottom - chartArea.top);
          if (!isTrendCompanion) ctx.strokeRect(left, chartArea.top, width, chartArea.bottom - chartArea.top);
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
    function sleepStageInfo(stage) {
      const key = String(stage || '').toLowerCase().replace(/_/g, ' ');
      if (key.includes('deep') || key === '15') return { name: 'Deep sleep', description: 'Quiet/deeper sleep estimate from Owlet state data.' };
      if (key.includes('light') || key === '8') return { name: 'Light sleep', description: 'Lighter sleep estimate from Owlet state data.' };
      if (key.includes('awake') || key === '1') return { name: 'Awake', description: 'Awake or active period estimate.' };
      if (key.includes('offline') || key.includes('sock')) return { name: 'Offline / sock off', description: 'No reliable physiological signal during this period.' };
      return { name: 'Inactive / unknown', description: 'Owlet did not report a clear sleep stage for this period.' };
    }
    const zeroOrNegative = (value) => value !== null && value !== undefined && Number(value) <= 0;
    const isOffline = (row) => !!(row?.sock_disconnected || row?.sock_off || zeroOrNegative(row?.heart_rate) || zeroOrNegative(row?.oxygen_saturation));
    const durationText = (seconds) => seconds ? `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`.replace(/^0h /, '') : '0m';
    const signed = (value, suffix = '') => value === null || value === undefined ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(1).replace(/\.0$/, '')}${suffix}`;
    const chartList = () => [vitalsChart, oxygenTrendChart].filter(Boolean);

    function smoothingMinutes() {
      const value = el('smoothing').value;
      return value === 'raw' ? 0 : Number(value || 0);
    }

    function smoothingLabel() {
      const option = el('smoothing')?.selectedOptions?.[0];
      return option ? option.textContent.replace(' avg', '') : 'Raw';
    }

    function rollupBucket() {
      return '30m';
    }

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
      const button = el('refresh');
      const mobile = isMobileViewport();
      if (text) {
        button.textContent = mobile ? (text.startsWith('Refreshing') ? '↻' : '!') : text;
        button.title = text;
        button.setAttribute('aria-label', text);
        return;
      }
      button.textContent = mobile ? `↻ ${secondsUntilRefresh}` : `Refresh (${secondsUntilRefresh}s)`;
      button.title = `Refresh (${secondsUntilRefresh}s)`;
      button.setAttribute('aria-label', button.title);
    }

    function setInitialLoading(message, kind = '') {
      if (firstLoadComplete) return;
      const loading = el('initialLoading');
      loading.classList.remove('hidden', 'error');
      if (kind) loading.classList.add(kind);
      el('initialLoadingMessage').textContent = message;
    }

    function hideInitialLoading() {
      firstLoadComplete = true;
      el('initialLoading').classList.add('hidden');
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

    function isMobileViewport() {
      return window.matchMedia('(max-width: 640px)').matches;
    }

    function applyResponsiveDefaultWindow() {
      const selector = el('window');
      if (isMobileViewport() && selector?.value === '24') selector.value = '6';
    }

    function historyHoursForSelection(hours = selectedHours()) {
      if (!hours) return null;
      return Math.min(24 * 365, Math.max(hours * 3, hours + 48));
    }

    function selectedWindowMs() {
      const hours = selectedHours();
      return hours ? hours * 60 * 60 * 1000 : null;
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

    function metricValue(row, key) {
      const value = Number(row?.[key]);
      if (!Number.isFinite(value)) return null;
      if (key === 'skin_temperature' && (isOffline(row) || value <= 0)) return null;
      return value;
    }

    function validMetricValues(rows, key) {
      return rows.map(row => metricValue(row, key)).filter(value => value !== null);
    }

    function summarizeMetric(rows, key) {
      const values = validMetricValues(rows, key);
      if (!values.length) return { avg: null, min: null, max: null };
      return {
        avg: values.reduce((sum, value) => sum + value, 0) / values.length,
        min: Math.min(...values),
        max: Math.max(...values)
      };
    }

    function sleepBucket(row) {
      const state = String(row?.sleep_state ?? '');
      if (state === '8' || state === '15') return 'sleeping';
      if (state === '1') return 'waking';
      return 'unknown';
    }

    function metricCell(summary, key, field) {
      const value = summary?.[key]?.[field];
      if (value === null || value === undefined) return '—';
      const digits = key === 'heart_rate' ? 0 : 1;
      const suffix = key === 'oxygen_saturation' ? '%' : (key === 'skin_temperature' ? '°C' : '');
      return `${Number(value).toFixed(digits).replace(/\.0$/, '')}${suffix}`;
    }

    function dailyInsightPeriods(sourceRows, sourceChallenges, days = 7) {
      if (!sourceRows.length) return [];
      const challengeWindows = (sourceChallenges || []).map(challenge => ({
        start: Date.parse(challenge.start_time),
        end: Date.parse(challenge.effective_end_time || challenge.end_time || new Date().toISOString())
      })).filter(interval => Number.isFinite(interval.start) && Number.isFinite(interval.end));
      const latest = Date.parse(sourceRows[sourceRows.length - 1].recorded_at);
      const dayMs = 24 * 60 * 60 * 1000;
      return Array.from({ length: days }, (_, index) => {
        const end = latest - index * dayMs;
        const start = end - dayMs;
        const rows = sourceRows.filter(row => {
          const time = Date.parse(row.recorded_at);
          return Number.isFinite(time) && time > start && time <= end && !isOffline(row) && !timeInIntervals(time, challengeWindows);
        });
        const sleeping = rows.filter(row => sleepBucket(row) === 'sleeping');
        const waking = rows.filter(row => sleepBucket(row) === 'waking');
        const summarizeRows = periodRows => ({
          oxygen_saturation: summarizeMetric(periodRows, 'oxygen_saturation'),
          heart_rate: summarizeMetric(periodRows, 'heart_rate'),
          skin_temperature: summarizeMetric(periodRows, 'skin_temperature')
        });
        return {
          index,
          start,
          end,
          rows,
          sleeping,
          waking,
          overall: summarizeRows(rows),
          sleepingStats: summarizeRows(sleeping),
          wakingStats: summarizeRows(waking)
        };
      });
    }

    function dailyInsightLabel(period) {
      if (period.index === 0) return 'Last 24h';
      return `${period.index * 24}–${(period.index + 1) * 24}h ago`;
    }

    function dailyInsightChartValue(period, group, key) {
      const value = period?.[group]?.[key]?.avg;
      return value === null || value === undefined ? null : Number(value.toFixed(1));
    }

    function renderDailyInsightsChart(periods) {
      const chartPeriods = periods.slice().reverse();
      const labels = chartPeriods.map(period => period.index === 0 ? 'Last 24h' : `${period.index}d ago`);
      const datasets = [
        { id: 'dailyOxygenAvg', label: 'O₂ avg', data: chartPeriods.map(period => dailyInsightChartValue(period, 'overall', 'oxygen_saturation')), yAxisID: 'oxygen', borderColor: '#2563eb', backgroundColor: '#2563eb20', pointBackgroundColor: '#2563eb', pointRadius: 4, tension: .28, spanGaps: false },
        { id: 'dailyOxygenSleep', label: 'Sleep O₂', data: chartPeriods.map(period => dailyInsightChartValue(period, 'sleepingStats', 'oxygen_saturation')), yAxisID: 'oxygen', borderColor: '#7c3aed', backgroundColor: '#7c3aed20', pointBackgroundColor: '#7c3aed', borderDash: [5, 4], pointRadius: 3, tension: .28, spanGaps: false },
        { id: 'dailyOxygenWake', label: 'Wake O₂', data: chartPeriods.map(period => dailyInsightChartValue(period, 'wakingStats', 'oxygen_saturation')), yAxisID: 'oxygen', borderColor: '#f59e0b', backgroundColor: '#f59e0b20', pointBackgroundColor: '#f59e0b', borderDash: [3, 3], pointRadius: 3, tension: .28, spanGaps: false },
        { id: 'dailyHeartRateAvg', label: 'HR avg', data: chartPeriods.map(period => dailyInsightChartValue(period, 'overall', 'heart_rate')), yAxisID: 'heart', borderColor: '#dc2626', backgroundColor: '#dc262620', pointBackgroundColor: '#dc2626', pointRadius: 4, tension: .25, spanGaps: false },
        { id: 'dailySkinTempAvg', label: 'Skin temp °C', data: chartPeriods.map(period => dailyInsightChartValue(period, 'overall', 'skin_temperature')), yAxisID: 'temp', borderColor: '#0f766e', backgroundColor: '#0f766e20', pointBackgroundColor: '#0f766e', pointRadius: 4, tension: .25, spanGaps: false }
      ];
      if (dailyInsightsChart) dailyInsightsChart.destroy();
      dailyInsightsChart = new Chart(el('dailyInsightsChart'), {
        type: 'line',
        data: { labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 250 },
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true } },
            tooltip: { callbacks: { label: context => {
              const suffix = context.dataset.yAxisID === 'oxygen' ? '%' : (context.dataset.yAxisID === 'temp' ? '°C' : ' bpm');
              const digits = context.dataset.yAxisID === 'heart' ? 0 : 1;
              const value = context.parsed?.y;
              return `${context.dataset.label}: ${value === null || value === undefined ? '—' : `${Number(value).toFixed(digits).replace(/\\.0$/, '')}${suffix}`}`;
            } } }
          },
          scales: {
            x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: false } },
            oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100, title: { display: true, text: 'O₂ %' } },
            heart: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'HR bpm' } },
            temp: { type: 'linear', position: 'right', display: false, suggestedMin: 28, suggestedMax: 38, grid: { drawOnChartArea: false } }
          }
        }
      });
    }

    function renderDailyInsights(periods) {
      const allRows = periods.flatMap(period => period.rows);
      const sleepingRows = periods.flatMap(period => period.sleeping);
      const wakingRows = periods.flatMap(period => period.waking);
      const overall = {
        oxygen_saturation: summarizeMetric(allRows, 'oxygen_saturation'),
        heart_rate: summarizeMetric(allRows, 'heart_rate'),
        skin_temperature: summarizeMetric(allRows, 'skin_temperature')
      };
      const sleepingStats = {
        oxygen_saturation: summarizeMetric(sleepingRows, 'oxygen_saturation'),
        heart_rate: summarizeMetric(sleepingRows, 'heart_rate'),
        skin_temperature: summarizeMetric(sleepingRows, 'skin_temperature')
      };
      const wakingStats = {
        oxygen_saturation: summarizeMetric(wakingRows, 'oxygen_saturation'),
        heart_rate: summarizeMetric(wakingRows, 'heart_rate'),
        skin_temperature: summarizeMetric(wakingRows, 'skin_temperature')
      };
      el('dailyInsightsSummary').innerHTML = `
        <span>Overall O₂ <b>${metricCell(overall, 'oxygen_saturation', 'avg')}</b></span>
        <span>Sleep O₂ <b>${metricCell(sleepingStats, 'oxygen_saturation', 'avg')}</b></span>
        <span>Wake O₂ <b>${metricCell(wakingStats, 'oxygen_saturation', 'avg')}</b></span>
        <span>Overall HR <b>${metricCell(overall, 'heart_rate', 'avg')}</b></span>
        <span>Sleep HR <b>${metricCell(sleepingStats, 'heart_rate', 'avg')}</b></span>
        <span>Wake HR <b>${metricCell(wakingStats, 'heart_rate', 'avg')}</b></span>
        <span>Skin temp <b>${metricCell(overall, 'skin_temperature', 'avg')}</b></span>`;
      renderDailyInsightsChart(periods);
      const rows = periods.map(period => `
        <tr>
          <td><b>${dailyInsightLabel(period)}</b><br><span class="small">${localTime(new Date(period.start).toISOString(), true)} → ${localTime(new Date(period.end).toISOString(), true)} · ${period.rows.length} valid</span></td>
          <td>${metricCell(period.overall, 'oxygen_saturation', 'avg')}</td>
          <td>${metricCell(period.sleepingStats, 'oxygen_saturation', 'avg')}</td>
          <td>${metricCell(period.wakingStats, 'oxygen_saturation', 'avg')}</td>
          <td>${metricCell(period.overall, 'oxygen_saturation', 'min')}</td>
          <td>${metricCell(period.overall, 'oxygen_saturation', 'max')}</td>
          <td>${metricCell(period.overall, 'heart_rate', 'avg')}</td>
          <td>${metricCell(period.sleepingStats, 'heart_rate', 'avg')}</td>
          <td>${metricCell(period.wakingStats, 'heart_rate', 'avg')}</td>
          <td>${metricCell(period.overall, 'heart_rate', 'min')}</td>
          <td>${metricCell(period.overall, 'heart_rate', 'max')}</td>
          <td>${metricCell(period.overall, 'skin_temperature', 'avg')}</td>
          <td>${metricCell(period.overall, 'skin_temperature', 'min')}</td>
          <td>${metricCell(period.overall, 'skin_temperature', 'max')}</td>
        </tr>`).join('');
      el('dailyInsightsTable').innerHTML = `<thead><tr><th>24h period</th><th>O₂ avg</th><th>O₂ sleep</th><th>O₂ wake</th><th>O₂ low</th><th>O₂ high</th><th>HR avg</th><th>HR sleep</th><th>HR wake</th><th>HR low</th><th>HR high</th><th>Temp avg</th><th>Temp low</th><th>Temp high</th></tr></thead><tbody>${rows || '<tr><td colspan="14" class="empty">No valid readings in the last 7 days.</td></tr>'}</tbody>`;
      const totalSamples = periods.reduce((sum, period) => sum + period.rows.length, 0);
      el('dailyInsightsMeta').textContent = `${periods.length} rolling 24-hour periods · ${totalSamples} valid samples · offline/sock-off and O₂ challenge samples excluded`;
    }

    async function openDailyInsightsModal() {
      el('challengesPanel').classList.add('hidden');
      el('notificationsPanel').classList.add('hidden');
      el('challengesToggle').setAttribute('aria-expanded', 'false');
      el('notificationsToggle').setAttribute('aria-expanded', 'false');
      el('dailyInsightsModal').classList.remove('hidden');
      if (dailyInsightsChart) {
        dailyInsightsChart.destroy();
        dailyInsightsChart = null;
      }
      el('dailyInsightsSummary').innerHTML = '<span>Loading daily insights…</span>';
      el('dailyInsightsTable').innerHTML = '<tbody><tr><td class="empty">Loading last 7 days…</td></tr></tbody>';
      try {
        const qs = queryParams({}, { hoursOverride: 168 });
        const challengeQs = queryParams({ limit: '500', offset: '0' }, { hoursOverride: 168 });
        const [readingData, challengeData] = await Promise.all([
          fetchJson(`${API_BASE}/api/readings?${qs}`),
          fetchJson(`${API_BASE}/api/oxygen-challenges?${challengeQs}`)
        ]);
        renderDailyInsights(dailyInsightPeriods(readingData || [], challengeData.items || []));
      } catch (error) {
        console.error(error);
        el('dailyInsightsSummary').innerHTML = '<span>Could not load daily insights.</span>';
        el('dailyInsightsTable').innerHTML = '<tbody><tr><td class="empty">Daily insights failed to load. Try refresh and open again.</td></tr></tbody>';
      }
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

    function queryParams(extra = {}, options = {}) {
      const window = el('window').value;
      const params = new URLSearchParams({ limit: '100000', ...extra });
      const hours = options.hoursOverride ?? (window === 'all' ? null : window);
      if (hours) params.set('hours', hours);
      const account = selectedAccount();
      if (account) params.set('account', account);
      const device = selectedDevice();
      if (device) params.set('device', device);
      return params.toString();
    }

    function selectedAccount() {
      return el('accountSelect')?.value || new URLSearchParams(window.location.search).get('account') || '';
    }

    function setUrlAccount(account) {
      const url = new URL(window.location.href);
      if (account) url.searchParams.set('account', account);
      else url.searchParams.delete('account');
      url.searchParams.delete('device');
      window.history.replaceState({}, '', url);
    }

    function selectedDevice() {
      return el('deviceSelect')?.value || new URLSearchParams(window.location.search).get('device') || '';
    }

    function setUrlDevice(device) {
      const url = new URL(window.location.href);
      if (device) url.searchParams.set('device', device);
      else url.searchParams.delete('device');
      window.history.replaceState({}, '', url);
    }

    async function loadAccounts() {
      if (SHARE_MODE) return;
      try {
        const data = await fetchJson(`${API_BASE}/api/accounts`);
        accounts = data.accounts || [];
      } catch (error) {
        console.error(error);
        accounts = [];
      }
      const requested = new URLSearchParams(window.location.search).get('account') || '';
      const selected = accounts.some(account => String(account.id) === requested) ? requested : (accounts[0]?.id ? String(accounts[0].id) : '');
      renderAccountOptions(selected);
      if (selected) setUrlAccount(selected);
    }

    function renderAccountOptions(selected = selectedAccount()) {
      const cluster = el('accountCluster');
      if (!cluster) return;
      cluster.classList.toggle('hidden', SHARE_MODE);
      el('accountSelect').innerHTML = accounts.length
        ? accounts.map(account => {
          const status = account.status && account.status !== 'active' ? ` (${account.status.replace('_', ' ')})` : '';
          const label = account.display_name || account.email || `Account ${account.id}`;
          return `<option value="${account.id}" ${String(account.id) === String(selected) ? 'selected' : ''}>${label}${status}</option>`;
        }).join('')
        : '<option value="">Default</option>';
    }

    async function addAccountFromPrompt() {
      const email = prompt('Owlet email');
      if (!email) return;
      const password = prompt('Owlet password (used once to fetch refresh token; not stored)');
      if (!password) return;
      const region = prompt('Owlet region', 'world') || 'world';
      const displayName = prompt('Display name', email) || email;
      try {
        updateRefreshButton('Adding account…');
        const response = await fetch(`${API_BASE}/api/accounts`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, region, display_name: displayName })
        });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        const data = await response.json();
        await loadAccounts();
        const accountId = data.account?.id ? String(data.account.id) : selectedAccount();
        if (accountId) setUrlAccount(accountId);
        await loadDevices();
        notificationPageOffset = 0;
        loadedHours = null;
        readingsTableSignature = '';
        safeRefresh({ resetZoom: true, force: true });
      } catch (error) {
        console.error(error);
        alert('Could not validate that Owlet account. Check the email/password/region and try again.');
      }
    }

    async function loadDevices() {
      try {
        const account = selectedAccount();
        const accountQs = account ? `?account=${encodeURIComponent(account)}` : '';
        const data = await fetchJson(`${API_BASE}/api/devices${accountQs}`);
        devices = data.devices || [];
      } catch (error) {
        console.error(error);
        devices = [];
      }
      const requested = new URLSearchParams(window.location.search).get('device') || '';
      const selected = devices.some(device => device.serial === requested) ? requested : (devices[0]?.serial || '');
      renderDeviceOptions(selected);
      if (selected) setUrlDevice(selected);
      renderBabyName();
    }

    function compactDeviceName(device) {
      const name = device?.name || device?.serial || 'Device';
      const digits = name.match(/(\d{3,})\s*$/)?.[1] || device?.serial?.slice(-4);
      if (device?.baby_name && device.baby_name !== name) return device.baby_name;
      return digits ? `Sock ${digits}` : name;
    }

    function renderDeviceOptions(selected = selectedDevice()) {
      el('deviceSelect').innerHTML = devices.length
        ? devices.map(device => {
          const label = isMobileViewport() ? compactDeviceName(device) : (device.name || device.serial);
          return `<option value="${device.serial}" ${device.serial === selected ? 'selected' : ''}>${label}</option>`;
        }).join('')
        : '<option value="">All devices</option>';
    }

    function currentDevice() {
      const serial = selectedDevice();
      return devices.find(device => device.serial === serial) || devices[0] || null;
    }

    function renderBabyName() {
      const device = currentDevice();
      el('babyName').textContent = device?.baby_name || device?.name || 'Owlet sock';
    }

    async function fetchJson(url) {
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText} while fetching ${url}`);
      return response.json();
    }

    async function refresh({ resetZoom = false } = {}) {
      secondsUntilRefresh = REFRESH_SECONDS;
      setInitialLoading('Loading readings and notifications…');
      updateRefreshButton('Refreshing…');
      const token = ++refreshToken;
      const previousLatest = lastLatestTimestamp;
      const previousVisible = visibleWindowSnapshot({ resetZoom });
      if (resetZoom || loadedHours === null || selectedHours() === null) loadedHours = historyHoursForSelection();
      const qs = queryParams();
      const dataQs = queryParams({}, { hoursOverride: loadedHours });
      const rollupQs = queryParams({ bucket: rollupBucket() }, { hoursOverride: loadedHours });
      const notificationQs = queryParams({ limit: '500', offset: '0' }, { hoursOverride: loadedHours });
      const challengeQs = queryParams({ limit: '100', offset: '0' }, { hoursOverride: loadedHours });
      const cryptoHours = selectedHours() || 720;
      const [health, rows, notificationData, challengeData] = await Promise.all([
        fetchJson(`${API_BASE}/api/health`),
        fetchJson(`${API_BASE}/api/readings?${dataQs}`),
        fetchJson(`${API_BASE}/api/notifications?${notificationQs}`),
        fetchJson(`${API_BASE}/api/oxygen-challenges?${challengeQs}`)
      ]);
      if (token !== refreshToken) return;
      readings = rows;
      notifications = notificationData;
      challenges = challengeData;
      lastLatestTimestamp = readings.length ? readings[readings.length - 1].recorded_at : null;
      zoomWindow = refreshedVisibleRange(previousVisible);
      setInitialLoading('Drawing charts and controls…');
      renderStatus(health);
      applyFilter();
      renderCharts({ deferTrend: true });
      renderNotifications();
      renderChallenges();
      updateRefreshButton();
      hideInitialLoading();
      if (previousLatest && lastLatestTimestamp && lastLatestTimestamp !== previousLatest) showNewDataPulse();
      hydrateSecondaryData({ qs, rollupQs, cryptoHours, token, compareRows: rows }).catch(error => {
        console.error(error);
        el('refresh').title = 'Some details failed; core readings are still shown.';
      });
    }

    async function hydrateSecondaryData({ qs, rollupQs, cryptoHours, token, compareRows }) {
      const [stats, insightData, rollupData, cryptoData] = await Promise.all([
        fetchJson(`${API_BASE}/api/summary?${qs}`),
        fetchJson(`${API_BASE}/api/insights?${qs}`),
        fetchJson(`${API_BASE}/api/rollups?${rollupQs}`),
        fetchJson(`${API_BASE}/api/crypto?hours=${cryptoHours}`)
      ]);
      if (token !== refreshToken) return;
      comparisonRows = compareRows || readings;
      summary = stats;
      insights = insightData;
      rollups = rollupData.rollups || [];
      crypto = cryptoData;
      renderInsights();
      renderCrypto();
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
      el('titleStatusDot').className = `status-dot title-status-dot ${dotClass}`;
      el('titleStatusDot').title = label;
      renderBatteryStatus(latest);
    }

    function renderInsights() {
      const rawLatest = readings[readings.length - 1];
      const latest = rawLatest ? { ...rawLatest, sleep_state_label: isOffline(rawLatest) ? 'offline / sock off' : stateLabel(rawLatest.sleep_state) } : insights.latest;
      const currentSleep = currentSleepStatus();
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
      el('sleepTotal').textContent = currentSleep.title;
      el('sleepSummary').textContent = `${hours(sleep.sleep_seconds)} sleep · ${hours(sleep.awake_seconds)} awake · ${currentSleep.detail}`;
      el('lightSleep').textContent = hours(sleep.light_sleep_seconds);
      el('deepSleep').textContent = hours(sleep.deep_sleep_seconds);
      el('awakeTime').textContent = hours(sleep.awake_seconds);
      const total = Math.max(1, sleep.light_sleep_seconds + sleep.deep_sleep_seconds + sleep.awake_seconds);
      el('lightBar').style.width = `${(sleep.light_sleep_seconds / total) * 100}%`;
      el('deepBar').style.width = `${(sleep.deep_sleep_seconds / total) * 100}%`;
      el('awakeBar').style.width = `${(sleep.awake_seconds / total) * 100}%`;
      el('coverage').textContent = `${summary.window} · ${summary.challenge_count || 0} in challenges`;
    }

    function currentSleepStatus() {
      if (!readings.length) return { title: '—', detail: 'No current state yet' };
      const range = dataRange();
      const latest = readings[readings.length - 1];
      const cls = stateClass(latest);
      const latestTime = Date.parse(latest.recorded_at);
      let start = latestTime;
      for (let index = readings.length - 2; index >= 0; index -= 1) {
        const row = readings[index];
        const rowTime = Date.parse(row.recorded_at);
        const nextTime = Date.parse(readings[index + 1].recorded_at);
        if (stateClass(row) !== cls || !Number.isFinite(rowTime) || !Number.isFinite(nextTime) || nextTime - rowTime > TREND_MAX_SAMPLE_GAP_MS) break;
        start = rowTime;
      }
      const end = range?.max && range.max >= latestTime ? range.max + 60 * 1000 : latestTime + 60 * 1000;
      const duration = durationText(Math.max(60, (end - start) / 1000));
      const names = { light: 'Sleeping', deep: 'Deep sleep', awake: 'Awake', offline: 'Offline', inactive: 'Inactive' };
      const name = names[cls] || 'Unknown';
      return {
        title: `${name} (${duration})`,
        detail: `current ${name.toLowerCase()}`,
      };
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

    function downsample(rows, maxPoints = CHART_MAX_POINTS) {
      if (rows.length <= maxPoints) return rows;
      const range = visibleRange();
      const step = Math.ceil(rows.length / maxPoints);
      return rows.filter((row, index) => {
        const time = Date.parse(row.recorded_at);
        const visibleEdge = range && (time === range.min || time === range.max);
        const offlineTransition = isOffline(row) && (!isOffline(rows[index - 1]) || !isOffline(rows[index + 1]));
        return visibleEdge || offlineTransition || index % step === 0 || index === rows.length - 1;
      });
    }

    function downsamplePoints(points, maxPoints = CHART_MAX_POINTS) {
      const range = visibleRange();
      if (points.length <= maxPoints) return extendPointsToVisibleEdges(points, range);
      const step = Math.ceil(points.length / maxPoints);
      const sampled = points.filter((point, index) => {
        const visibleEdge = range && (point.x === range.min || point.x === range.max);
        return visibleEdge || point.y === null || index % step === 0 || index === points.length - 1;
      });
      return extendPointsToVisibleEdges(sampled, range, points);
    }

    function extendPointsToVisibleEdges(points, range = visibleRange(), sourcePoints = points) {
      if (!range || !points.length || range.max <= range.min) return points;
      const visible = sourcePoints.filter(point => point && Number.isFinite(point.x) && point.x >= range.min && point.x <= range.max);
      if (!visible.length) return points;
      const extended = points.slice();
      const first = visible[0];
      const last = visible[visible.length - 1];
      if (first.x > range.min && !extended.some(point => point.x === range.min)) extended.push({ ...first, x: range.min });
      if (last.x < range.max && !extended.some(point => point.x === range.max)) extended.push({ ...last, x: range.max });
      return extended.sort((a, b) => a.x - b.x);
    }

    function readingSeries(key) {
      const minutes = smoothingMinutes();
      if (minutes > 0) return rollingAverageForKey(key, minutes);
      const sampled = downsample(readings).map(row => ({ x: Date.parse(row.recorded_at), y: metricValue(row, key) }));
      const source = readings.map(row => ({ x: Date.parse(row.recorded_at), y: metricValue(row, key) }));
      return extendPointsToVisibleEdges(sampled, visibleRange(), source);
    }

    function rollingAverageForKey(key, minutes) {
      const windowMs = minutes * 60 * 1000;
      const queue = [];
      let sum = 0;
      const points = [];
      let previousValidTime = null;
      const reset = () => { queue.length = 0; sum = 0; };
      readings.forEach(row => {
        const time = Date.parse(row.recorded_at);
        const value = metricValue(row, key);
        if (isOffline(row) || value === null) {
          reset();
          points.push({ x: time, y: key === 'skin_temperature' ? null : 0, reason: key === 'skin_temperature' ? 'missing' : 'offline-zero' });
          previousValidTime = null;
          return;
        }
        if (previousValidTime && time - previousValidTime > TREND_MAX_SAMPLE_GAP_MS) reset();
        previousValidTime = time;
        queue.push({ time, value });
        sum += value;
        while (queue.length && queue[0].time < time - windowMs) sum -= queue.shift().value;
        points.push({ x: time, y: sum / queue.length });
      });
      return downsamplePoints(points);
    }

    function rollingOxygenAverage(minutes) {
      const windowMs = minutes * 60 * 1000;
      const queue = [];
      let sum = 0;
      const points = [];
      let previousValidTime = null;
      let inOfflineGap = false;
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
        const offline = isOffline(row) || !Number.isFinite(value);
        if (!Number.isFinite(time)) return;
        if (offline) {
          if (!inOfflineGap) addGapMarker(time, 'offline');
          inOfflineGap = true;
          resetWindow();
          previousValidTime = null;
          return;
        }
        if (inOfflineGap) {
          inOfflineGap = false;
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
      return (notifications.items || []).slice().reverse().map(item => {
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

    function tooltipTitle(items) {
      const first = items?.[0];
      const rawX = first?.raw?.x;
      const parsedX = first?.parsed?.x;
      const timestamp = Number.isFinite(Number(parsedX)) ? Number(parsedX) : Number(rawX);
      return Number.isFinite(timestamp) ? localTime(new Date(timestamp).toISOString()) : '';
    }

    function tooltipLabel(context) {
      if (context.dataset.id === 'notifications') return context.raw.tooltipLines;
      if (context.dataset.id === 'btcPrice') return `BTC price: ${money(context.parsed.y)}`;
      if (context.chart?.canvas?.id === 'stateChart') {
        const stage = sleepStageInfo(context.dataset.label);
        const value = context.parsed?.y;
        const amount = Number.isFinite(Number(value)) ? `${Number(value).toFixed(1).replace(/\.0$/, '')}h` : '—';
        return [`${stage.name}: ${amount}`, stage.description];
      }
      if (context.dataset.id === 'o2TrendSignal') {
        const value = context.parsed?.y;
        if (value === null || value === undefined || !Number.isFinite(Number(value))) {
          return 'Trend gap — offline or missing data.';
        }
        const valueText = `${value > 0 ? '+' : ''}${Number(value).toFixed(1)} pts`;
        if (value > 0.25) return `Trend signal ${valueText}: recent O₂ is running above baseline.`;
        if (value < -0.25) return `Trend signal ${valueText}: recent O₂ is running below baseline.`;
        return `Trend signal ${valueText}: recent O₂ is near baseline.`;
      }
      if (context.dataset.id === 'o2Trailing30') {
        return `${context.dataset.label}: ${Number(context.parsed.y).toFixed(1)}%`;
      }
      if (context.dataset.id === 'o2Baseline4h') {
        return `${context.dataset.label}: ${Number(context.parsed.y).toFixed(1)}%`;
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
      const range = visibleRange();
      return {
        type: 'linear',
        offset: false,
        min: range?.min,
        max: range?.max,
        ticks: { display: !hideTicks, maxRotation: 0, autoSkip: true, maxTicksLimit: window.matchMedia('(max-width: 640px)').matches ? 6 : 14, callback: timeTick }
      };
    }

    function zoomOptions() {
      const mobile = isMobileViewport();
      return {
        limits: { x: { min: 'original', max: 'original' } },
        pan: { enabled: true, mode: 'x', threshold: mobile ? 4 : 8, onPanComplete: ({ chart }) => syncZoomFrom(chart) },
        zoom: {
          drag: { enabled: !mobile, backgroundColor: 'rgba(37, 99, 235, .12)', borderColor: 'rgba(37, 99, 235, .55)', borderWidth: 1 },
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
          if (key !== 'x' && scale.title && !options.keepAxisTitles) scale.title.display = false;
          scale.ticks = { ...(scale.ticks || {}), font: { size: 10 }, padding: 2, maxTicksLimit: 6 };
        });
      }
      return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 450 },
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: legendOptions(options.legend || {}), tooltip: { callbacks: { title: tooltipTitle, label: tooltipLabel } }, zoom: zoomOptions(), challengeBands: { intervals: challengeBandsEnabled ? challengeIntervals() : [] }, offlineBands: { intervals: offlineIntervals() } },
        scales
      };
    }

    function updateChallengeBandOptions() {
      const intervals = challengeBandsEnabled ? challengeIntervals() : [];
      chartList().forEach(chart => {
        chart.options.plugins.challengeBands = { ...(chart.options.plugins.challengeBands || {}), intervals };
        chart.update('none');
      });
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
      zoomWindow = defaultVisibleRange();
      chartList().forEach(chart => {
        if (typeof chart.resetZoom === 'function') chart.resetZoom('none');
        chart.options.scales.x.min = zoomWindow?.min;
        chart.options.scales.x.max = zoomWindow?.max;
        chart.update('none');
      });
      renderStateStrip();
      updatePanControl();
    }

    function applyVisibleWindow(range) {
      if (!range || !Number.isFinite(range.min) || !Number.isFinite(range.max) || range.max <= range.min) return;
      zoomWindow = range;
      chartList().forEach(chart => {
        chart.options.scales.x.min = zoomWindow.min;
        chart.options.scales.x.max = zoomWindow.max;
        chart.update('none');
      });
      renderStateStrip();
      updatePanControl();
    }

    function panVisibleWindowByPixels(chart, startRange, deltaX) {
      const full = fullDataRange();
      const area = chart?.chartArea;
      if (!full || !area || !startRange || startRange.max <= startRange.min) return false;
      const width = startRange.max - startRange.min;
      const panSpan = full.max - full.min;
      const pixelWidth = Math.max(1, area.right - area.left);
      if (width >= panSpan - 1000) return false;
      const shiftMs = -(deltaX / pixelWidth) * width;
      const min = Math.max(full.min, Math.min(startRange.min + shiftMs, full.max - width));
      applyVisibleWindow({ min, max: min + width });
      return true;
    }

    function attachMobileDragPan(chart) {
      if (!chart?.canvas || chart.$mobileDragPanAttached) return;
      const state = { tracking: false, active: false, startX: 0, startY: 0, range: null };
      const start = (x, y) => {
        if (!isMobileViewport()) return;
        const range = visibleRange();
        if (!range) return;
        state.tracking = true;
        state.active = false;
        state.startX = x;
        state.startY = y;
        state.range = { ...range };
      };
      const move = (x, y, event) => {
        if (!state.tracking || !isMobileViewport()) return;
        const dx = x - state.startX;
        const dy = y - state.startY;
        if (!state.active) {
          if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx) * 1.2) {
            state.tracking = false;
            return;
          }
          if (Math.abs(dx) < 8 || Math.abs(dx) < Math.abs(dy) * 1.1) return;
          state.active = true;
        }
        if (panVisibleWindowByPixels(chart, state.range, dx)) event?.preventDefault?.();
      };
      const stop = () => {
        state.tracking = false;
        state.active = false;
        state.range = null;
        loadOlderHistoryIfNeeded().catch(console.error);
      };
      chart.canvas.addEventListener('touchstart', event => {
        if (event.touches?.length === 1) start(event.touches[0].clientX, event.touches[0].clientY);
      }, { passive: true });
      chart.canvas.addEventListener('touchmove', event => {
        if (event.touches?.length === 1) move(event.touches[0].clientX, event.touches[0].clientY, event);
      }, { passive: false });
      chart.canvas.addEventListener('touchend', stop, { passive: true });
      chart.canvas.addEventListener('touchcancel', stop, { passive: true });
      chart.canvas.addEventListener('pointerdown', event => {
        if (event.pointerType === 'touch') start(event.clientX, event.clientY);
      });
      chart.canvas.addEventListener('pointermove', event => {
        if (event.pointerType === 'touch') move(event.clientX, event.clientY, event);
      });
      chart.canvas.addEventListener('pointerup', stop);
      chart.canvas.addEventListener('pointercancel', stop);
      chart.$mobileDragPanAttached = true;
    }

    function upsertChart(existing, canvasId, config) {
      if (!existing) {
        const chart = new Chart(el(canvasId), config);
        attachMobileDragPan(chart);
        return chart;
      }
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
      attachMobileDragPan(existing);
      return existing;
    }

    function renderCharts({ deferTrend = false } = {}) {
      const btcHidden = vitalsChart?.data.datasets.find(dataset => dataset.id === 'btcPrice')?.hidden ?? true;
      const skinTempHidden = vitalsChart?.data.datasets.find(dataset => dataset.id === 'skinTemperature')?.hidden ?? true;
      vitalsChart = upsertChart(vitalsChart, 'vitalsChart', {
        type: 'line',
        data: {
          datasets: [
            { label: 'Heart rate', data: readingSeries('heart_rate'), borderColor: '#dc2626', backgroundColor: '#dc262620', yAxisID: 'hr', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'SpO₂', data: readingSeries('oxygen_saturation'), borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'spo2', spanGaps: true, pointRadius: 0, tension: .25 },
            { label: 'Movement', data: readingSeries('movement'), borderColor: '#059669', backgroundColor: '#05966920', yAxisID: 'move', spanGaps: true, pointRadius: 0, tension: .2 },
            { id: 'skinTemperature', label: 'Skin temp °C', data: readingSeries('skin_temperature'), borderColor: '#0f766e', backgroundColor: '#0f766e20', yAxisID: 'temp', hidden: skinTempHidden, spanGaps: true, pointRadius: 0, tension: .25 },
            { id: 'btcPrice', label: 'BTC price', data: cryptoBitcoinPoints(), borderColor: '#f97316', backgroundColor: '#f9731620', yAxisID: 'btc', hidden: btcHidden, spanGaps: true, pointRadius: 0, tension: .25 },
            { id: 'notifications', type: 'scatter', label: 'Notifications', data: notificationPoints(), yAxisID: 'spo2', pointStyle: 'triangle', pointRadius: 9, pointHoverRadius: 13, hitRadius: 24, showLine: false, borderWidth: 2, borderColor: '#92400e', backgroundColor: '#f59e0b' }
          ]
        },
        options: chartOptions({
          hr: { type: 'linear', position: 'left', min: 0, title: { display: true, text: 'BPM' } },
          spo2: { type: 'linear', position: 'right', min: 0, suggestedMax: 100, grid: { drawOnChartArea: false }, title: { display: true, text: 'SpO₂' } },
          temp: { type: 'linear', position: 'right', display: false, suggestedMin: 28, suggestedMax: 38, grid: { drawOnChartArea: false } },
          btc: { type: 'linear', position: 'right', min: 0, display: false, grid: { drawOnChartArea: false } },
          move: { min: 0, display: false }
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
          oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100, title: { display: true, text: 'O₂ avg (%)' } },
          signal: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: '30m − 4h signal' } }
        }, { legend: { display: false }, keepAxisTitles: true })
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

    function dataRange(rows = readings) {
      const times = rows.map(row => Date.parse(row.recorded_at)).filter(Number.isFinite);
      return times.length ? { min: Math.min(...times), max: Math.max(...times) } : null;
    }

    function defaultVisibleRange() {
      const full = dataRange();
      if (!full) return null;
      const width = selectedWindowMs();
      if (!width) return full;
      const floor = full.max - width;
      const visible = dataRange(readings.filter(row => {
        const time = Date.parse(row.recorded_at);
        return Number.isFinite(time) && time >= floor && time <= full.max;
      }));
      if (visible && visible.max > visible.min) return visible;
      return { min: Math.max(full.min, floor), max: full.max };
    }

    function visibleRange() {
      if (zoomWindow?.max > zoomWindow?.min) return zoomWindow;
      return defaultVisibleRange();
    }

    function visibleWindowAtLoadedEnd() {
      const full = dataRange();
      if (!zoomWindow || !full) return true;
      return Math.abs(zoomWindow.max - full.max) < 5 * 60 * 1000;
    }

    function visibleWindowSnapshot({ resetZoom = false } = {}) {
      const full = fullDataRange();
      const visible = visibleRange();
      if (resetZoom || !full || !visible || visible.max <= visible.min) {
        return { resetZoom: true, atLatest: true, width: selectedWindowMs() };
      }
      const width = visible.max - visible.min;
      const slider = el('timePan');
      const sliderAtEnd = slider && !slider.disabled && Number(slider.value) >= 995;
      const distanceFromEnd = Math.max(0, full.max - visible.max);
      const atLatest = sliderAtEnd || distanceFromEnd <= Math.max(60 * 1000, width * 0.01);
      return { min: visible.min, max: visible.max, width, distanceFromEnd, atLatest, resetZoom: false };
    }

    function refreshedVisibleRange(snapshot) {
      const full = dataRange();
      if (!full) return null;
      if (snapshot?.resetZoom || !snapshot || !snapshot.width) return defaultVisibleRange();
      const width = Math.min(snapshot.width, full.max - full.min || snapshot.width);
      if (snapshot.atLatest) {
        return { min: Math.max(full.min, full.max - width), max: full.max };
      }
      const min = Math.max(full.min, Math.min(snapshot.min, full.max - width));
      return { min, max: Math.min(full.max, min + width) };
    }

    function fullDataRange() {
      return dataRange();
    }

    async function loadOlderHistoryIfNeeded() {
      if (SHARE_MODE || loadingOlderHistory || selectedHours() === null) return;
      const slider = el('timePan');
      if (slider.disabled || Number(slider.value) > 20) return;
      const nextHours = Math.min(24 * 365, Math.max((loadedHours || selectedHours()) * 2, (loadedHours || selectedHours()) + 24));
      if (!loadedHours || nextHours <= loadedHours) return;
      loadingOlderHistory = true;
      const previousTitle = slider.title;
      slider.title = `Loading ${nextHours}h of history…`;
      loadedHours = nextHours;
      await safeRefresh();
      slider.title = previousTitle || 'Scroll left for older loaded history; release near the left edge to load more.';
      loadingOlderHistory = false;
    }

    function visibleRows() {
      const range = visibleRange();
      if (!range) return readings;
      return readings.filter(row => {
        const time = Date.parse(row.recorded_at);
        return Number.isFinite(time) && time >= range.min && time <= range.max;
      });
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
      slider.title = selectedHours() === null ? 'Showing all loaded history.' : 'Scroll left for older loaded history; release near the left edge to load more.';
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
      applyVisibleWindow({ min: start, max: start + width });
    }

    function stateClass(row) {
      if (isOffline(row)) return 'offline';
      const state = String(row.sleep_state ?? '');
      if (state === '8') return 'light';
      if (state === '15') return 'deep';
      if (state === '1') return 'awake';
      return 'inactive';
    }

    function bucketDurationMs(bucket = rollupBucket()) {
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
      return segment ? { start: segment.start, end: segment.end, cls: segment.cls, label: segment.label } : null;
    }

    function stateTooltipText(interval, prefix = '') {
      if (!interval) return null;
      const stage = sleepStageInfo(interval.cls || interval.label);
      const duration = durationText(Math.max(0, (interval.end - interval.start) / 1000));
      return {
        title: `${prefix}${stage.name}`,
        body: `${stage.description} ${localTime(new Date(interval.start).toISOString(), true)} → ${localTime(new Date(interval.end).toISOString(), true)} · ${duration}.`
      };
    }

    function showStateTooltip(interval, event, prefix = '') {
      const tooltip = el('stateTooltip');
      const text = stateTooltipText(interval, prefix);
      if (!text || !event) {
        tooltip.classList.add('hidden');
        return;
      }
      const source = event.touches?.[0] || event.changedTouches?.[0] || event;
      tooltip.innerHTML = `<b>${text.title}</b><span>${text.body}</span>`;
      tooltip.classList.remove('hidden');
      const pad = 12;
      const rect = tooltip.getBoundingClientRect();
      const left = Math.min(window.innerWidth - rect.width - pad, Math.max(pad, source.clientX + 12));
      const top = Math.min(window.innerHeight - rect.height - pad, Math.max(pad, source.clientY + 12));
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    }

    function hideStateTooltip() {
      el('stateTooltip').classList.add('hidden');
    }

    function ballparkClass(row) {
      const sleepSeconds = (row.light_sleep_seconds || 0) + (row.deep_sleep_seconds || 0);
      const awakeSeconds = row.awake_seconds || 0;
      const movementSeconds = row.movement_seconds || 0;
      const total = row.duration_seconds || sleepSeconds + awakeSeconds;
      if (total <= 0) return null;
      const awakeLikeSeconds = Math.min(total, awakeSeconds + movementSeconds);
      const movementBurst = movementSeconds >= Math.max(90, total * 0.14);
      if (awakeLikeSeconds >= total * 0.28 || (movementBurst && (row.max_movement || 0) >= (row.movement_awake_threshold || 10))) return 'awake';
      if (awakeSeconds >= total * 0.45) return 'awake';
      if (sleepSeconds >= total * 0.66) return (row.deep_sleep_seconds || 0) > (row.light_sleep_seconds || 0) ? 'deep' : 'light';
      return 'awake';
    }

    function smoothBallparkIntervals(items, bucketMs = bucketDurationMs()) {
      const sorted = items.filter(Boolean).sort((a, b) => a.start - b.start).map(item => ({ ...item }));
      sorted.forEach((item, index) => {
        if (item.cls === 'awake') return;
        const duration = item.end - item.start;
        const prev = sorted[index - 1];
        const next = sorted[index + 1];
        const bridgedByWake = prev?.cls === 'awake' && next?.cls === 'awake' && item.start - prev.end <= bucketMs && next.start - item.end <= bucketMs;
        if (bridgedByWake && duration <= Math.max(bucketMs * 1.75, 45 * 60 * 1000)) item.cls = 'awake';
      });
      return sorted.reduce((merged, item) => {
        const last = merged[merged.length - 1];
        if (last && last.cls === item.cls && item.start - last.end <= Math.max(1000, bucketMs * 0.25)) {
          last.end = Math.max(last.end, item.end);
          return merged;
        }
        merged.push(item);
        return merged;
      }, []);
    }

    function subtractIntervals(interval, blockers) {
      let pieces = [interval];
      blockers.forEach(blocker => {
        pieces = pieces.flatMap(piece => {
          if (blocker.end <= piece.start || blocker.start >= piece.end) return [piece];
          const split = [];
          if (blocker.start > piece.start) split.push({ ...piece, end: Math.min(blocker.start, piece.end) });
          if (blocker.end < piece.end) split.push({ ...piece, start: Math.max(blocker.end, piece.start) });
          return split;
        });
      });
      return pieces.filter(piece => piece.end > piece.start);
    }

    function rollupIntervals(range = visibleRange()) {
      if (!range || !rollups.length) return [];
      const bucketMs = bucketDurationMs();
      const blockers = offlineIntervals();
      const classified = rollups.map((row, index) => {
        const start = Date.parse(row.bucket_start);
        const nextStart = rollups[index + 1] ? Date.parse(rollups[index + 1].bucket_start) : start + bucketMs;
        const end = Number.isFinite(nextStart) && nextStart > start ? nextStart : start + bucketMs;
        const cls = ballparkClass(row);
        if (!Number.isFinite(start) || !Number.isFinite(end) || !cls) return null;
        return { start: Math.max(start, range.min), end: Math.min(end, range.max), cls };
      }).filter(item => item && item.end > item.start);
      return smoothBallparkIntervals(classified, bucketMs)
        .flatMap(item => subtractIntervals(item, blockers))
        .filter(item => item && item.end > item.start);
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
      showStateTooltip(hoveredStateInterval, event);
      vitalsChart?.update('none');
    }

    function attachStateStripHover() {
      const strip = el('stateStrip');
      if (strip.dataset.hoverAttached === 'true') return;
      strip.addEventListener('mousemove', setStateStripHoverFromEvent);
      strip.addEventListener('click', setStateStripHoverFromEvent);
      strip.addEventListener('touchstart', setStateStripHoverFromEvent, { passive: true });
      strip.addEventListener('touchmove', setStateStripHoverFromEvent, { passive: true });
      strip.addEventListener('mouseleave', () => { hoveredStateInterval = null; hideStateTooltip(); vitalsChart?.update('none'); });
      strip.dataset.hoverAttached = 'true';
    }

    function setStateChartHoverFromEvent(event) {
      if (!stateChart?.scales?.x) return;
      const source = event.touches?.[0] || event.changedTouches?.[0] || event;
      const rect = stateChart.canvas.getBoundingClientRect();
      const timestamp = stateChart.scales.x.getValueForPixel(source.clientX - rect.left);
      hoveredStateInterval = rollupIntervalAt(timestamp) || stateIntervalAt(timestamp);
      showStateTooltip(hoveredStateInterval, event, rollupIntervalAt(timestamp) ? 'Ballpark ' : '');
      vitalsChart?.update('none');
    }

    function attachStateChartHover(chart) {
      if (!chart || chart.$stateHoverAttached) return;
      chart.canvas.addEventListener('mousemove', setStateChartHoverFromEvent);
      chart.canvas.addEventListener('click', setStateChartHoverFromEvent);
      chart.canvas.addEventListener('touchstart', setStateChartHoverFromEvent, { passive: true });
      chart.canvas.addEventListener('touchmove', setStateChartHoverFromEvent, { passive: true });
      chart.canvas.addEventListener('mouseleave', () => { hoveredStateInterval = null; hideStateTooltip(); vitalsChart?.update('none'); });
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
      const shortMinutes = smoothingMinutes() || 30;
      const longMinutes = Math.max(240, shortMinutes * 8);
      const shortLabel = `${shortMinutes}m O₂ avg`;
      const signalLabel = `${shortMinutes}m − ${Math.round(longMinutes / 60)}h signal`;
      const shortAvg = rollingOxygenAverage(shortMinutes);
      const longAvg = rollingOxygenAverage(longMinutes);
      const signal = oxygenTrendSignal(shortAvg, longAvg);
      oxygenTrendChart = upsertChart(oxygenTrendChart, 'oxygenTrendChart', {
        type: 'line',
        data: {
          datasets: [
            { id: 'o2Trailing30', label: shortLabel, data: shortAvg, borderColor: '#2563eb', backgroundColor: '#2563eb20', yAxisID: 'oxygen', tension: .25, pointRadius: 0, spanGaps: false },
            { id: 'o2Baseline4h', label: `Baseline ${Math.round(longMinutes / 60)}h O₂ avg`, data: longAvg, borderColor: '#7c3aed', backgroundColor: '#7c3aed20', yAxisID: 'oxygen', tension: .25, pointRadius: 0, borderDash: [6, 4], spanGaps: false },
            { id: 'o2TrendSignal', type: 'bar', label: signalLabel, data: signal, yAxisID: 'signal', backgroundColor: ctx => (ctx.raw?.y ?? 0) >= 0 ? 'rgba(4, 120, 87, .96)' : 'rgba(185, 28, 28, .96)', borderColor: ctx => (ctx.raw?.y ?? 0) >= 0 ? '#065f46' : '#991b1b', borderWidth: 1, barThickness: isMobileViewport() ? 3 : 4, maxBarThickness: 8, minBarLength: 2 }
          ]
        },
        options: chartOptions({
          oxygen: { type: 'linear', position: 'left', suggestedMin: 88, suggestedMax: 100, title: { display: true, text: 'O₂ avg (%)' } },
          signal: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: `${shortMinutes}m signal` }, ticks: { callback: value => `${value > 0 ? '+' : ''}${value}` } }
        }, { legend: { display: false }, keepAxisTitles: true })
      });
    }

    function renderRollups() {
      const rows = rollups.slice().reverse().map((row, index) => `<tr class="${index === 0 ? 'newest-rollup' : ''}"><td>${rollupLabel(row)}</td><td>${row.samples}/${row.total_samples ?? row.samples}</td><td>${fmt(row.avg_oxygen_saturation, '%')}</td><td>${fmt(row.min_oxygen_saturation, '%')}</td><td>${fmt(row.avg_heart_rate, ' bpm')}</td><td>${fmt(row.avg_skin_temperature, '°C')}</td><td>${hours(row.sleep_seconds)}</td><td>${hours(row.awake_seconds)}</td><td>${row.offline_samples || 0}</td></tr>`).join('');
      el('rollupTable').innerHTML = `<thead><tr><th>Window</th><th>Valid/total</th><th>Avg O₂</th><th>Min O₂</th><th>Avg HR</th><th>Avg skin temp</th><th>Sleep</th><th>Awake</th><th>Offline</th></tr></thead><tbody>${rows || '<tr><td colspan="9" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function applyFilter() {
      filtered = readings;
      renderReadingsTable();
    }

    function renderReadingsTable() {
      const first = filtered[0]?.recorded_at || '';
      const last = filtered[filtered.length - 1]?.recorded_at || '';
      const challengeSignature = (challenges.items || []).map(item => `${item.id}:${item.start_time}:${item.effective_end_time || item.end_time || ''}`).join('|');
      const tableStart = Math.max(0, filtered.length - TABLE_ROW_LIMIT);
      const tableRows = filtered.slice(tableStart);
      const nextSignature = `${filtered.length}:${first}:${last}:${tableStart}:${challengeSignature}`;
      el('tableCount').textContent = filtered.length > tableRows.length ? `newest ${tableRows.length} of ${filtered.length} loaded` : `${filtered.length} loaded`;
      if (nextSignature === readingsTableSignature) return;
      readingsTableSignature = nextSignature;
      const indexedRows = tableRows.map((row, index) => ({ row, index: filtered === readings ? tableStart + index : readings.indexOf(row) })).reverse();
      const rows = indexedRows.map(({ row, index }, displayIndex) => `
        <tr data-index="${index}" class="${displayIndex === 0 ? 'latest-row' : ''} ${isOffline(row) ? 'offline-row' : ''} ${isInChallenge(row) ? 'challenge-row' : ''}">
          <td>${localTime(row.recorded_at)}</td>
          <td>${fmt(row.device_serial)}</td>
          <td>${num(row.heart_rate)}</td>
          <td>${num(row.oxygen_saturation)}%</td>
          <td>${num(row.movement)}</td>
          <td>${isOffline(row) ? 'offline / sock off' : stateLabel(row.sleep_state)}</td>
          <td>${fmt(row.battery, '%')}</td>
          <td>${fmt(row.skin_temperature, '°C')}</td>
        </tr>`).join('');
      el('readingsTable').innerHTML = `<thead><tr><th>Time</th><th>Serial</th><th>HR</th><th>O₂</th><th>Move</th><th>State</th><th>Battery</th><th>Skin temp</th></tr></thead><tbody>${rows || '<tr><td colspan="8" class="empty">No readings yet.</td></tr>'}</tbody>`;
    }

    function attachReadingsTableSelection() {
      const table = el('readingsTable');
      if (table.dataset.selectionAttached === 'true') return;
      table.addEventListener('click', event => {
        const tr = event.target.closest('tbody tr[data-index]');
        if (!tr || !table.contains(tr)) return;
        table.querySelectorAll('tr.selected-row').forEach(row => row.classList.remove('selected-row'));
        tr.classList.add('selected-row');
        const row = readings[Number(tr.dataset.index)];
        el('raw').textContent = JSON.stringify(row, null, 2);
      });
      table.dataset.selectionAttached = 'true';
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
      const account = selectedAccount();
      const scopedPayload = account ? { ...payload, account_id: Number(account) } : payload;
      const response = await fetch(`${API_BASE}/api/oxygen-challenges`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(scopedPayload)
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
      const { force = false, ...refreshOptions } = options;
      if (refreshInFlight && !force) return refreshInFlight;
      const run = (async () => {
        try {
          await refresh(refreshOptions);
        } catch (error) {
          console.error(error);
          if (!firstLoadComplete) setInitialLoading('Could not load dashboard data. Retrying soon…', 'error');
          updateRefreshButton('Refresh failed');
          el('status').innerHTML = '<span class="status-dot offline"></span>Refresh failed · keeping last loaded data';
          setTimeout(() => updateRefreshButton(), 1500);
        }
      })();
      let tracked;
      tracked = run.finally(() => {
        if (refreshInFlight === tracked) refreshInFlight = null;
      });
      refreshInFlight = tracked;
      return tracked;
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

    function closeO2AddMenu() {
      el('o2AddMenu')?.classList.add('hidden');
      el('o2AddMenuToggle')?.setAttribute('aria-expanded', 'false');
    }

    function toggleO2AddMenu() {
      const menu = el('o2AddMenu');
      const hidden = menu.classList.toggle('hidden');
      el('o2AddMenuToggle').setAttribute('aria-expanded', String(!hidden));
    }

    if (SHARE_MODE) {
      el('o2AddMenu').innerHTML = '<span class="small">Open the full dashboard to add O₂ challenges.</span>';
      el('o2AddMenuToggle').title = 'Open the full dashboard to add O₂ challenges';
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

    el('accountSelect')?.addEventListener('change', async event => {
      setUrlAccount(event.target.value);
      devices = [];
      renderDeviceOptions('');
      await loadDevices();
      renderBabyName();
      notificationPageOffset = 0;
      loadedHours = null;
      readingsTableSignature = '';
      safeRefresh({ resetZoom: true, force: true });
    });
    el('addAccount')?.addEventListener('click', addAccountFromPrompt);

    el('deviceSelect').addEventListener('change', event => {
      setUrlDevice(event.target.value);
      renderBabyName();
      notificationPageOffset = 0;
      loadedHours = null;
      readingsTableSignature = '';
      safeRefresh({ resetZoom: true, force: true });
    });
    el('window').addEventListener('change', () => { notificationPageOffset = 0; readingsTableSignature = ''; safeRefresh({ resetZoom: true, force: true }); });
    el('smoothing').addEventListener('change', () => { renderCharts({ deferTrend: true }); safeRefresh({ resetZoom: false }); });
    el('refresh').addEventListener('click', () => safeRefresh());
    el('dailyInsightsToggle').addEventListener('click', openDailyInsightsModal);
    el('closeDailyInsights').addEventListener('click', () => el('dailyInsightsModal').classList.add('hidden'));
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
    el('o2AddMenuToggle').addEventListener('click', event => {
      event.stopPropagation();
      toggleO2AddMenu();
    });
    el('menuNewChallenge')?.addEventListener('click', () => { closeO2AddMenu(); openNewChallengeModal(); });
    el('menuVisibleChallenge')?.addEventListener('click', () => { closeO2AddMenu(); markVisibleChallenge(); });
    el('closeChallengesPanel').addEventListener('click', () => { el('challengesPanel').classList.add('hidden'); el('challengesToggle').setAttribute('aria-expanded', 'false'); });
    el('closeNotificationsPanel').addEventListener('click', () => { el('notificationsPanel').classList.add('hidden'); el('notificationsToggle').setAttribute('aria-expanded', 'false'); });
    el('closeChallengeModal').addEventListener('click', () => { currentChallengeDetail = null; el('challengeModal').classList.add('hidden'); });
    el('challengeEditForm').addEventListener('submit', saveChallengeEdits);
    el('deleteChallenge').addEventListener('click', deleteCurrentChallenge);
    el('timePan').addEventListener('input', event => panToSliderValue(event.target.value));
    el('timePan').addEventListener('change', () => loadOlderHistoryIfNeeded().catch(console.error));
    el('challengeBandsToggle').addEventListener('change', event => {
      challengeBandsEnabled = event.target.checked;
      updateChallengeBandOptions();
    });
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
    document.addEventListener('click', event => {
      if (!el('o2AddWrap').contains(event.target)) closeO2AddMenu();
    });
    ['vitalsChart', 'oxygenTrendChart'].forEach(id => {
      el(id)?.addEventListener('dblclick', resetZoom);
    });
    window.addEventListener('resize', () => { renderDeviceOptions(); updateRefreshButton(); renderCharts({ deferTrend: true }); renderRollups(); updatePanControl(); });
    if ('serviceWorker' in navigator && !SHARE_MODE) {
      window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').then(updateInstallButton).catch(updateInstallButton));
    }
    updateInstallButton();
    applyResponsiveDefaultWindow();
    attachReadingsTableSelection();
    loadAccounts().then(loadDevices).then(() => safeRefresh({ resetZoom: true }));
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
