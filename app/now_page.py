"""'Today' — the app's home. The ten-second check: live vitals with personal
context, today so far, and doors into the deeper views. The hero charts are
touchable: tap or hold to read a value, pull right to scroll back in time."""

from __future__ import annotations

from app.shell import render_shell

NOW_HEAD = """<link rel="manifest" href="/manifest.webmanifest" />
  <style>
    .status-line { font-size: 17px; color: var(--dim); line-height: 1.5; margin: 0 0 26px;
      max-width: 60ch; }
    .status-line b { color: var(--ink); font-weight: 600; }
    .hero { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 8px; }
    @media (max-width: 640px) { .hero { grid-template-columns: 1fr; } }
    .vital { padding: 22px 22px 76px; position: relative; overflow: hidden;
      touch-action: pan-y; user-select: none; -webkit-user-select: none; cursor: crosshair; }
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
    .vital.inspecting .band { color: var(--accent); font-weight: 600; }
    .chartzone { position: absolute; left: 0; right: 0; bottom: 0; height: 60px; }
    .chartzone svg { position: absolute; inset: 0; width: 100%; height: 100%; opacity: .6; }
    .chartzone polyline { fill: none; stroke: var(--accent); stroke-width: 1.6;
      stroke-linejoin: round; stroke-linecap: round; vector-effect: non-scaling-stroke; }
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
    @media (prefers-reduced-motion: reduce) { .chartzone svg g { transition: none !important; } }
  </style>"""

NOW_BODY = """<p class="status-line" id="statusLine">Checking in…</p>
    <div class="hero" id="hero">
      <div class="vital card" id="cardO2" data-metric="o2">
        <span class="label">Oxygen</span>
        <div class="value"><span id="o2Value">—</span><small> %</small></div>
        <div class="band" id="o2Band"></div>
        <div class="chartzone">
          <svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true"><g id="o2G"></g></svg>
          <div class="xline" id="o2X" hidden></div>
        </div>
      </div>
      <div class="vital card" id="cardHr" data-metric="hr">
        <span class="label">Heart rate</span>
        <div class="value"><span id="hrValue">—</span><small> bpm</small></div>
        <div class="band" id="hrBand"></div>
        <div class="chartzone">
          <svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true"><g id="hrG"></g></svg>
          <div class="xline" id="hrX" hidden></div>
        </div>
      </div>
    </div>
    <div class="timescale">
      <span id="tsStart"></span>
      <button class="live-chip" id="tsLive" type="button">● live</button>
      <span id="tsEnd"></span>
    </div>
    <div id="belowHero"></div>"""

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

    const o2Zone = value => value < 86 ? 'var(--bad)' : (value < 90 ? 'var(--awake)' : 'var(--accent)');

    // ---- data buffers ------------------------------------------------------
    // liveReadings is the always-fresh last hour; histReadings grows on demand
    // as the user pulls back in time. Points arrays hold only valid vitals, so
    // collector-off stretches show up as time gaps in the line.
    const WINDOW_MS = 60 * 60 * 1000;
    const GAP_MS = 90 * 1000;
    const HISTORY_STEPS = [3, 6, 12, 24];
    let liveReadings = [], histReadings = [], loadedHours = 1, loadingHistory = false;
    let points = { o2: [], hr: [] };
    let bands = { o2: null, hr: null };
    let latest = { o2: null, hr: null, offline: true };
    let baselineState = 'awake';

    function allReadings() {
      if (!histReadings.length) return liveReadings;
      const cut = liveReadings.length ? Date.parse(liveReadings[0].recorded_at) : Infinity;
      return histReadings.filter(r => Date.parse(r.recorded_at) < cut).concat(liveReadings);
    }
    function rebuildPoints() {
      const rows = allReadings();
      points.hr = rows.filter(r => !isOffline(r) && r.heart_rate > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.heart_rate }));
      points.o2 = rows.filter(r => !isOffline(r) && r.oxygen_saturation > 0)
        .map(r => ({ x: Date.parse(r.recorded_at), y: r.oxygen_saturation }));
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

    function renderChart(key, zoneOf) {
      const g = el(key + 'G'); if (!g) return;
      const end = chartEnd();
      const renderStart = end - 2 * WINDOW_MS, renderEnd = end + WINDOW_MS / 4;
      const pts = downsample(points[key].filter(p => p.x >= renderStart && p.x <= renderEnd));
      if (pts.length < 2) { g.innerHTML = ''; g.removeAttribute('transform'); return; }
      let min = Infinity, max = -Infinity;
      for (const p of pts) { if (p.y < min) min = p.y; if (p.y > max) max = p.y; }
      const padY = Math.max(0.5, (max - min) * 0.1); min -= padY; max += padY;
      const xOf = t => ((t - (end - WINDOW_MS)) / WINDOW_MS) * 100;
      const yOf = v => 40 - ((v - min) / (max - min)) * 36;
      const zone = zoneOf || (() => 'var(--accent)');
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
      g.innerHTML = segs.filter(s => s.coords.length > 1)
        .map(s => `<polyline points="${s.coords.join(' ')}" style="stroke:${s.color}"/>`)
        .join('');
      g.removeAttribute('transform');
    }
    function renderCharts() {
      anchorEnd = chartEnd();
      renderChart('o2', o2Zone);
      renderChart('hr', null);
      updateTimescale();
    }
    function applyPan() {
      const shift = ((anchorEnd - chartEnd()) / WINDOW_MS) * 100;
      if (Math.abs(shift) > 85) { renderCharts(); return; }
      const t = `translate(${shift.toFixed(3)} 0)`;
      el('o2G').setAttribute('transform', t);
      el('hrG').setAttribute('transform', t);
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
      const o2 = nearestPoint(points.o2, t), hr = nearestPoint(points.hr, t);
      el('o2Value').textContent = o2 ? Math.round(o2.y) : '—';
      el('hrValue').textContent = hr ? Math.round(hr.y) : '—';
      const when = `at ${fmtClock(new Date(t))}`;
      el('o2Band').textContent = o2 ? when : `no reading ${when}`;
      el('hrBand').textContent = hr ? when : `no reading ${when}`;
      [el('cardO2'), el('cardHr')].forEach(c => c.classList.add('inspecting'));
      [el('o2X'), el('hrX')].forEach(x => { x.hidden = false; x.style.left = (frac * 100) + '%'; });
    }
    function clearInspect() {
      [el('o2X'), el('hrX')].forEach(x => { x.hidden = true; });
      [el('cardO2'), el('cardHr')].forEach(c => c.classList.remove('inspecting'));
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
    [el('cardO2'), el('cardHr')].forEach(card => {
      card.addEventListener('pointerdown', e => onDown(e, card));
      card.addEventListener('pointermove', onMove);
      card.addEventListener('pointerup', onUp);
      card.addEventListener('pointercancel', onUp);
    });

    // ---- live vitals + narrative --------------------------------------------
    const bandText = (band, unit) => band
      ? `typical ${baselineState} range ${Math.round(band.low)}–${Math.round(band.high)}${unit}`
      : 'building her baseline — needs a couple of days';

    function updateHeroLive() {
      if (el('cardO2').classList.contains('inspecting')) return;
      el('o2Value').textContent = latest.o2 != null ? Math.round(latest.o2) : '—';
      el('hrValue').textContent = latest.hr != null ? Math.round(latest.hr) : '—';
      el('o2Band').textContent = bandText(bands.o2, '%');
      el('hrBand').textContent = bandText(bands.hr, '');
      const o2Out = bands.o2 && latest.o2 != null && (latest.o2 < bands.o2.low || latest.o2 > bands.o2.high);
      const hrOut = bands.hr && latest.hr != null && (latest.hr < bands.hr.low || latest.hr > bands.hr.high);
      el('cardO2').className = 'vital card' +
        (latest.o2 != null && latest.o2 < 86 ? ' critical' : latest.o2 != null && latest.o2 < 90 ? ' low' : o2Out ? ' out' : '');
      el('cardHr').className = 'vital card' + (hrOut ? ' out' : '');
    }

    function todayWindow() {
      const start = new Date(); start.setHours(0, 0, 0, 0);
      return { start, end: new Date() };
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
      latest.offline = offline;
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
      const tempNow = latestRow && latestRow.skin_temperature > 0 ? latestRow.skin_temperature : null;

      el('belowHero').innerHTML = `
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
        title="Today",
        head=NOW_HEAD,
        body=NOW_BODY,
        scripts=NOW_SCRIPTS,
    )
