"""'Now' — the app's home. The ten-second check: live vitals with personal
context, today so far, and doors into the deeper views."""

from __future__ import annotations

from app.shell import render_shell

NOW_HEAD = """<link rel="manifest" href="/manifest.webmanifest" />
  <style>
    .status-line { font-size: 17px; color: var(--dim); line-height: 1.5; margin: 0 0 26px;
      max-width: 60ch; }
    .status-line b { color: var(--ink); font-weight: 600; }
    .hero { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
    @media (max-width: 640px) { .hero { grid-template-columns: 1fr; } }
    .vital { padding: 22px 22px 58px; position: relative; overflow: hidden; }
    .vital .label { font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
      color: var(--faint); font-weight: 700; }
    .vital .value { font-size: clamp(56px, 9vw, 84px); line-height: 1.02;
      letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
    .vital .value small { font-size: 22px; color: var(--dim); font-weight: 500;
      letter-spacing: 0; }
    .vital.out .value { color: var(--warn); }
    .vital.low .value { color: var(--awake); }
    .vital.critical .value { color: var(--bad); }
    .vital .band { font-size: 12.5px; color: var(--dim); margin-top: 2px; }
    .vital svg { position: absolute; right: 0; bottom: 0; left: 0; width: 100%;
      height: 42px; opacity: .55; }
    .vital svg polyline { fill: none; stroke: var(--accent); stroke-width: 1.6;
      stroke-linejoin: round; stroke-linecap: round; vector-effect: non-scaling-stroke; }
    .session { font-size: 15px; color: var(--dim); margin: 0 0 26px; }
    .session b { color: var(--ink); }
    .strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px; margin-bottom: 26px; }
    .chip { padding: 15px 16px 13px; }
    .chip b { display: block; font-size: 21px; letter-spacing: -0.01em;
      font-variant-numeric: tabular-nums; }
    .chip span { font-size: 11.5px; color: var(--dim); }
    .chip .sub { display: block; font-size: 11px; color: var(--faint); margin-top: 3px; }
    .chip.warn b { color: var(--warn); }
    .chip.good b { color: var(--good); }
    .doors { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 640px) { .doors { grid-template-columns: 1fr; } }
    .door { display: block; padding: 18px 20px; text-decoration: none; color: var(--ink); }
    .door b { display: block; font-size: 15px; margin-bottom: 3px; }
    .door span { font-size: 13px; color: var(--dim); line-height: 1.45; }
    .door:hover { border-color: var(--accent); }
    .empty { text-align: center; color: var(--dim); padding: 80px 20px; font-size: 15px; }
  </style>"""

NOW_BODY = """<p class="status-line" id="statusLine">Checking in…</p>
    <div id="content"></div>"""

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
    let pollSeconds = 5;
    let deviceName = 'your little one';
    let rollups = [];

    const stateLabel = value => ({ '0': 'resting', '1': 'awake', '8': 'in light sleep', '15': 'in deep sleep' }[String(value)] || null);
    const isOffline = row => !!(row?.sock_disconnected || row?.sock_off
      || (row?.heart_rate != null && row.heart_rate <= 0)
      || (row?.oxygen_saturation != null && row.oxygen_saturation <= 0));

    function sparkline(points, min, max, zoneOf) {
      if (points.length < 2) return '';
      const t0 = points[0].x, t1 = points[points.length - 1].x;
      const coord = p => {
        const x = ((p.x - t0) / Math.max(1, t1 - t0)) * 100;
        const y = 40 - ((p.y - min) / Math.max(0.001, max - min)) * 36;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      };
      // Split into contiguous zone runs so dips render amber/red inline.
      const zone = zoneOf || (() => 'var(--accent)');
      const segments = [];
      let run = { color: zone(points[0].y), coords: [coord(points[0])] };
      for (let i = 1; i < points.length; i++) {
        const color = zone(points[i].y);
        run.coords.push(coord(points[i]));
        if (color !== run.color) {
          segments.push(run);
          run = { color, coords: [coord(points[i])] };
        }
      }
      segments.push(run);
      const lines = segments
        .filter(seg => seg.coords.length > 1)
        .map(seg => `<polyline points="${seg.coords.join(' ')}" style="stroke:${seg.color}"/>`)
        .join('');
      return `<svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true">${lines}</svg>`;
    }

    const o2Zone = value => value < 86 ? 'var(--bad)' : (value < 90 ? 'var(--awake)' : 'var(--accent)');

    function heroCard(label, value, unit, band, points, stateClass, zoneOf) {
      const min = points.length ? Math.min(...points.map(p => p.y)) : 0;
      const max = points.length ? Math.max(...points.map(p => p.y)) : 1;
      return `<div class="vital card ${stateClass || ''}">
        <span class="label">${label}</span>
        <div class="value">${value}<small> ${unit}</small></div>
        <div class="band">${band}</div>
        ${sparkline(points, min - (max - min) * 0.1, max + (max - min) * 0.1, zoneOf)}
      </div>`;
    }

    function todayWindow() {
      const start = new Date(); start.setHours(0, 0, 0, 0);
      return { start, end: new Date() };
    }

    function render(readings, widget) {
      const latest = readings[readings.length - 1] || null;
      const offline = latest ? isOffline(latest) : true;
      const stateText = latest && !offline ? stateLabel(latest.sleep_state) : null;

      // --- current sleep/wake session ------------------------------------
      const today = todayWindow();
      const runs = I.sessions(rollups, new Date(Date.now() - 18 * 3600 * 1000), new Date());
      const currentRun = runs.length ? runs[runs.length - 1] : null;
      const sleepRunsToday = I.sessions(rollups, today.start, today.end)
        .filter(run => run.state === 'asleep' && run.buckets >= 2).length;

      // --- baselines -------------------------------------------------------
      const state = currentRun && currentRun.state === 'asleep' ? 'asleep' : 'awake';
      const hrBand = I.baselineBand(rollups, 'hr', state);
      const o2Band = I.baselineBand(rollups, 'o2', state);
      const hrNow = latest && !offline ? latest.heart_rate : null;
      const o2Now = latest && !offline ? latest.oxygen_saturation : null;
      const hrOut = hrBand && hrNow != null && (hrNow < hrBand.low || hrNow > hrBand.high);
      const o2Out = o2Band && o2Now != null && (o2Now < o2Band.low || o2Now > o2Band.high);
      const bandText = (band, unit) => band
        ? `typical ${state} range ${Math.round(band.low)}–${Math.round(band.high)}${unit}`
        : `building her baseline — needs a couple of days`;

      const hrPoints = readings.filter(r => !isOffline(r) && r.heart_rate > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.heart_rate }));
      const o2Points = readings.filter(r => !isOffline(r) && r.oxygen_saturation > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.oxygen_saturation }));

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

      // --- movement / temp -----------------------------------------------------
      const recent = readings.slice(-24);
      const moveAvg = recent.length ? recent.reduce((a, r) => a + (r.movement || 0), 0) / recent.length : 0;
      const moveText = offline ? '—' : (moveAvg < 4 ? 'calm' : moveAvg < 20 ? 'stirring' : 'active');
      const temps = rollups.map(r => r.avg_skin_temperature).filter(v => v != null);
      const tempNow = latest && latest.skin_temperature > 0 ? latest.skin_temperature : null;

      el('content').innerHTML = `
        <div class="hero">
          ${heroCard('Oxygen', o2Now != null ? Math.round(o2Now) : '—', '%', bandText(o2Band, '%'), o2Points,
            o2Now != null && o2Now < 86 ? 'critical' : (o2Now != null && o2Now < 90 ? 'low' : (o2Out ? 'out' : '')), o2Zone)}
          ${heroCard('Heart rate', hrNow != null ? Math.round(hrNow) : '—', 'bpm', bandText(hrBand, ''), hrPoints,
            hrOut ? 'out' : '', null)}
        </div>
        <div class="strip">
          <div class="chip card"><b>${fmtDur(sleepToday)}</b><span>sleep today</span></div>
          <div class="chip card ${dipsToday ? 'warn' : 'good'}"><b>${dipsToday}</b><span>O₂ dips today</span></div>
          <div class="chip card ${batteryClass}"><b>${batteryText}</b><span>battery</span><span class="sub">${batterySub}</span></div>
          <div class="chip card"><b>${moveText}</b><span>movement</span></div>
          <div class="chip card"><b>${tempNow != null ? tempNow.toFixed(1) + '°' : '—'}</b><span>skin temp</span>
            <span class="sub">${temps.length ? Math.min(...temps).toFixed(1) + '–' + Math.max(...temps).toFixed(1) + '° last days' : ''}</span></div>
        </div>
        <div class="doors">
          <a class="door card" href="/night"><b>Last night's report →</b>
            <span>Sleep story, wake-ups, and every oxygen event, in plain language.</span></a>
          <a class="door card" href="/data"><b>The raw data →</b>
            <span>Full charts, tables, exports — every reading behind these numbers.</span></a>
        </div>`;
    }

    async function refresh() {
      try {
        const [readings, widget] = await Promise.all([
          fetch('/api/readings?hours=1&limit=2000').then(r => r.json()),
          fetch('/api/widget?hours=24').then(r => r.json())
        ]);
        render(readings, widget);
      } catch (error) { /* keep last render */ }
    }

    async function boot() {
      // Rollups (baselines/sessions) can take seconds to compute server-side;
      // render live vitals immediately and fold history in when it arrives.
      const rollupsReady = fetch('/api/rollups?bucket=5m&hours=192&limit=100000')
        .then(r => r.json())
        .then(data => { rollups = data.rollups || []; })
        .catch(() => {});
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
    }
    boot();
  </script>"""


def render_now_page() -> str:
    return render_shell(
        view="now",
        title="Now",
        head=NOW_HEAD,
        body=NOW_BODY,
        scripts=NOW_SCRIPTS,
    )
