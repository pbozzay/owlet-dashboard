"""'Tonight' — a narrative night report. Calm, built for the 7am question:
"how was last night?" Rendered through the shared app shell; the night-sky
styling appears in dark theme, a morning-paper rendering in light."""

from __future__ import annotations

from app.shell import render_shell

NIGHT_HEAD = """<style>
    .stars { position: fixed; inset: 0; pointer-events: none; opacity: 0; transition: opacity .4s; }
    :root[data-theme="dark"] .stars { opacity: .5; }
    .stars {
      background-image:
        radial-gradient(1px 1px at 12% 22%, #fff 50%, transparent 50%),
        radial-gradient(1px 1px at 78% 12%, #fff 50%, transparent 50%),
        radial-gradient(1.5px 1.5px at 55% 8%, #cdd6ff 50%, transparent 50%),
        radial-gradient(1px 1px at 32% 6%, #fff 50%, transparent 50%),
        radial-gradient(1px 1px at 90% 38%, #cdd6ff 50%, transparent 50%),
        radial-gradient(1.5px 1.5px at 8% 52%, #fff 50%, transparent 50%);
    }
    .night-nav { display: flex; align-items: baseline; gap: 14px; margin-bottom: 6px; }
    .night-nav button { all: unset; cursor: pointer; color: var(--dim); font-size: 22px;
      padding: 0 6px; border-radius: 8px; }
    .night-nav button:hover:not(:disabled) { color: var(--ink); }
    .night-nav button:disabled { opacity: .25; cursor: default; }
    h1 { font-size: clamp(34px, 6vw, 52px); letter-spacing: -0.025em; line-height: 1.04; margin: 0; }
    h1 small { display: block; font-size: 15px; letter-spacing: 0; color: var(--dim);
      font-weight: 400; margin-top: 10px; }
    .lede { font-size: 17px; line-height: 1.55; color: var(--dim);
      margin: 18px 0 34px; }
    .lede b { color: var(--ink); font-weight: 600; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px; margin-bottom: 34px; }
    .stat { padding: 18px 18px 15px; }
    .stat b { display: block; font-size: clamp(24px, 3.4vw, 32px); letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums; }
    .stat span { font-size: 12px; color: var(--dim); }
    .stat .sub { font-size: 11.5px; color: var(--faint); margin-top: 4px; display: block; }
    .stat.alert b { color: var(--bad); }
    .stat.calm b { color: var(--good); }
    .timeline-card { padding: 20px; margin-bottom: 34px; }
    .timeline { display: flex; height: 44px; border-radius: 10px; overflow: hidden;
      background: var(--nodata); }
    .timeline span { height: 100%; }
    .tl-axis { display: flex; justify-content: space-between; font-size: 11px;
      color: var(--faint); margin-top: 8px; font-variant-numeric: tabular-nums; }
    .legend { display: flex; flex-wrap: wrap; gap: 18px; font-size: 12px; color: var(--dim);
      margin-top: 14px; }
    .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px;
      margin-right: 6px; vertical-align: -1px; }
    .events { display: grid; gap: 10px; margin-bottom: 34px; }
    .event { display: flex; align-items: baseline; gap: 14px; padding: 14px 18px;
      font-size: 14px; }
    .event time { color: var(--dim); font-variant-numeric: tabular-nums; flex: 0 0 76px; }
    .event .depth { margin-left: auto; color: var(--bad); font-weight: 600;
      font-variant-numeric: tabular-nums; }
    .event.fine { color: var(--dim); }
    .event.fine .tick { color: var(--good); margin-right: 4px; }
    .week { padding: 20px; }
    .week-bars { display: flex; align-items: flex-end; gap: 10px; height: 92px; margin-top: 6px; }
    .wb { flex: 1; display: flex; flex-direction: column; justify-content: flex-end;
      align-items: center; gap: 6px; height: 100%; }
    .wb i { display: flex; flex-direction: column; width: 100%; max-width: 46px;
      border-radius: 6px 6px 2px 2px; overflow: hidden; min-height: 3px; }
    .wb i u { display: block; }
    .wb i .lt { background: var(--sleep-light); flex-grow: 1; }
    .wb i .dp { background: var(--sleep-deep); }
    .wb.tonight i { box-shadow: 0 0 18px var(--accent-soft); }
    .wb span { font-size: 10.5px; color: var(--faint); }
    .wb b { font-size: 11px; color: var(--dim); font-weight: 500;
      font-variant-numeric: tabular-nums; }
    .week .legend { margin-top: 14px; }
    .week-note { font-size: 13px; color: var(--dim); line-height: 1.55; margin: 12px 0 0; }
    .week-note b { color: var(--ink); font-weight: 600; }
    .empty { text-align: center; color: var(--dim); padding: 70px 20px; font-size: 15px; }
  </style>"""

NIGHT_BODY = """<div class="stars" aria-hidden="true"></div>
    <div class="night-nav">
      <button id="prevNight" aria-label="Previous night">‹</button>
      <h1 id="nightTitle">Tonight<small id="nightSub">loading…</small></h1>
      <button id="nextNight" aria-label="Next night">›</button>
    </div>
    <p class="lede" id="lede"></p>
    <div id="content"></div>"""

NIGHT_SCRIPTS = """<script>
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
      const totalMinutes = Math.round(seconds / 60);
      const h = Math.floor(totalMinutes / 60), m = totalMinutes % 60;
      return h ? `${h}h ${pad(m)}m` : `${m}m`;
    };

    // The user's night window (default 7 PM -> 7 AM); loaded from preferences in boot().
    let NIGHT = { start: 19 * 60, end: 7 * 60 };
    function nightWindowFrom(prefs) {
      const toMin = (value, fallback) => {
        const m = /^([01]?\\d|2[0-3]):([0-5]\\d)$/.exec(value || '');
        return m ? Number(m[1]) * 60 + Number(m[2]) : fallback;
      };
      const win = { start: toMin(prefs.night_start, 19 * 60), end: toMin(prefs.night_end, 7 * 60) };
      return win.start > win.end ? win : { start: 19 * 60, end: 7 * 60 }; // night must cross midnight
    }

    function nightWindow(offset) {
      // A "night" spans the configured window, local time. The most recent
      // night stays current until the next one begins.
      const now = new Date();
      const anchor = new Date(now);
      if (now.getHours() * 60 + now.getMinutes() < NIGHT.start) anchor.setDate(anchor.getDate() - 1);
      anchor.setDate(anchor.getDate() - offset);
      const start = new Date(anchor);
      start.setHours(Math.floor(NIGHT.start / 60), NIGHT.start % 60, 0, 0);
      const end = new Date(start);
      end.setDate(end.getDate() + 1);
      end.setHours(Math.floor(NIGHT.end / 60), NIGHT.end % 60, 0, 0);
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
      // A "dip" groups adjacent 5m buckets whose floor fell under 90 — but the
      // bucket span wildly overstates a blip, so we carry the actual seconds
      // spent under 90 (low_oxygen_seconds) and report THAT.
      const dips = [];
      let current = null;
      buckets.forEach(row => {
        const low = row.min_oxygen_saturation != null && row.min_oxygen_saturation < 90;
        if (low) {
          const lowSec = row.low_oxygen_seconds != null ? row.low_oxygen_seconds : BUCKET_SEC;
          if (!current) {
            current = { start: new Date(row.bucket_start), min: row.min_oxygen_saturation,
                        minAt: new Date(row.bucket_start), lowSec: 0 };
          } else if (row.min_oxygen_saturation < current.min) {
            current.min = row.min_oxygen_saturation;
            current.minAt = new Date(row.bucket_start);
          }
          current.lowSec += lowSec;
          current.end = new Date(new Date(row.bucket_start).getTime() + BUCKET_SEC * 1000);
        } else if (current) { dips.push(current); current = null; }
      });
      if (current) dips.push(current);
      return dips;
    }
    function dipDepthText(dip) {
      if (dip.lowSec < 50) {
        const secs = Math.max(5, Math.round(dip.lowSec / 5) * 5);
        return `Momentary dip — about ${secs}s under 90%`;
      }
      return `About ${fmtDur(dip.lowSec)} under 90%`;
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
      const capName = name.charAt(0) === '<' ? name.replace(/<b>(.)/, (m, c) => '<b>' + c.toUpperCase()) : name;
      const opener = inProgress ? `So far tonight, ${name} has logged` : `${capName} logged`;
      return `${opener} ${sleepText}, with ${mood}.`;
    }

    function renderTimeline(window, buckets) {
      const byTime = new Map(buckets.map(row => [new Date(row.bucket_start).getTime(), row]));
      const colors = { deep: 'var(--sleep-deep)', light: 'var(--sleep-light)', awake: 'var(--awake)', nodata: 'transparent' };
      let spans = '';
      for (let t = window.start.getTime(); t < window.end.getTime(); t += BUCKET_SEC * 1000) {
        const row = byTime.get(t);
        const cls = row ? classify(row) : 'nodata';
        spans += `<span style="flex:1;background:${colors[cls]}"></span>`;
      }
      const axis = [];
      for (let k = 0; k <= 4; k++) {
        const d = new Date(window.start.getTime() + (window.end - window.start) * k / 4);
        axis.push(`<span>${fmtClock(d)}</span>`);
      }
      const nightFocus = encodeURIComponent(window.start.toISOString());
      const nightSpan = Math.round((window.end - window.start) / 60000);
      return `<div class="timeline-card card"><h2 class="section-title">The night, minute by minute
        <a href="/data?focus=${nightFocus}&span=${nightSpan}" data-workbench style="float:right;color:var(--accent);text-decoration:none;text-transform:none;letter-spacing:0">raw trace →</a></h2>
        <div class="timeline">${spans}</div>
        <div class="tl-axis">${axis.join('')}</div>
        <div class="legend">
          <span><i style="background:var(--sleep-deep)"></i>Deep sleep</span>
          <span><i style="background:var(--sleep-light)"></i>Light sleep</span>
          <span><i style="background:var(--awake)"></i>Awake</span>
          <span><i style="background:var(--nodata);border:1px solid var(--surface-line)"></i>No signal</span>
        </div></div>`;
    }

    function renderStats(stats, dips) {
      const minO2Text = stats.minO2 != null
        ? `<b>${Math.round(stats.minO2)}%</b><span>lowest O₂</span><span class="sub">${stats.minO2At ? 'at ' + fmtClock(stats.minO2At) : ''}</span>` : `<b>—</b><span>lowest O₂</span>`;
      return `<div class="stats">
        <div class="stat card"><b>${fmtDur(stats.sleep)}</b><span>total sleep</span>
          <span class="sub">${fmtDur(stats.deep)} deep · ${fmtDur(stats.awake)} awake</span></div>
        <div class="stat card"><b>${stats.avgO2 != null ? stats.avgO2.toFixed(1) + '%' : '—'}</b><span>average O₂</span></div>
        <div class="stat card ${stats.minO2 != null && stats.minO2 < 88 ? 'alert' : ''}">${minO2Text}</div>
        <div class="stat card"><b>${stats.avgHr != null ? Math.round(stats.avgHr) : '—'}</b><span>avg heart rate (bpm)</span></div>
        <div class="stat card ${dips.length ? 'alert' : 'calm'}"><b>${dips.length}</b><span>O₂ dips below 90%</span></div>
      </div>`;
    }

    function renderEvents(dips) {
      if (!dips.length) {
        return `<section><h2 class="section-title">Oxygen events</h2><div class="events">
          <div class="event card fine"><span class="tick">✓</span>No dips below 90% — nothing to review.</div>
        </div></section>`;
      }
      const items = dips.map(dip => {
        // center on the run's lowest bucket — the focus modal marks this moment
        const focus = new Date(dip.minAt.getTime() + BUCKET_SEC * 500).toISOString();
        const label = encodeURIComponent(`Dip to ${Math.round(dip.min)}%`);
        return `<a class="event card" href="/data?focus=${encodeURIComponent(focus)}&span=45&label=${label}"
          title="Open the raw trace around this dip" style="text-decoration:none;color:inherit">
        <time>${fmtClock(dip.start)}</time>
        <span>${dipDepthText(dip)}</span>
        <span class="depth">↓ ${Math.round(dip.min)}% →</span></a>`;
      }).join('');
      return `<section><h2 class="section-title">Oxygen events</h2><div class="events">${items}</div></section>`;
    }

    function renderWeek() {
      const bars = [];
      let maxSleep = 1;
      const nights = [];
      for (let offset = 13; offset >= 0; offset--) {
        const win = nightWindow(offset);
        const stats = nightStats(bucketsIn(win));
        nights.push({ offset, win, stats });
        if (offset <= 6) maxSleep = Math.max(maxSleep, stats.sleep);
      }
      nights.filter(n => n.offset <= 6).forEach(({ offset, win, stats }) => {
        const height = Math.round((stats.sleep / maxSleep) * 100);
        const deepFrac = stats.sleep ? stats.deep / stats.sleep : 0;
        const label = offset === 0 ? 'tonight'
          : win.start.toLocaleDateString([], { weekday: 'short' });
        const detail = stats.sleep
          ? `${fmtDur(stats.deep)} deep · ${fmtDur(Math.max(0, stats.sleep - stats.deep))} light · ${fmtDur(stats.awake)} awake`
          : 'no readings';
        bars.push(`<div class="wb ${offset === 0 ? 'tonight' : ''}" title="${detail}">
          <b>${stats.sleep ? fmtDur(stats.sleep) : ''}</b>
          <i style="height:${Math.max(3, height)}%">
            <u class="lt"></u><u class="dp" style="height:${Math.round(deepFrac * 100)}%"></u>
          </i><span>${label}</span></div>`);
      });

      // week-over-week trend lines; only speak when both weeks have real nights
      const covered = n => n.stats.coveredSec >= 1800;
      const thisWeek = nights.filter(n => n.offset <= 6 && covered(n));
      const lastWeek = nights.filter(n => n.offset > 6 && covered(n));
      const mean = (list, pick) => list.length ? list.reduce((a, n) => a + pick(n.stats), 0) / list.length : null;
      const fragment = (label, pick) => {
        const now = mean(thisWeek, pick);
        if (now == null) return '';
        const before = lastWeek.length >= 3 ? mean(lastWeek, pick) : null;
        let delta = '';
        if (before != null && Math.abs(now - before) >= 300) {
          delta = ` (${now > before ? 'up' : 'down'} ${fmtDur(Math.abs(now - before))} on last week)`;
        }
        return `<b>${fmtDur(now)}</b> ${label}${delta}`;
      };
      const provisional = thisWeek.length < 4
        ? `Only ${thisWeek.length} night${thisWeek.length === 1 ? '' : 's'} recorded so far, so these will move around. `
        : '';
      const parts = [
        fragment('of sleep', s => s.sleep),
        fragment('of it deep', s => s.deep),
        fragment('awake overnight', s => s.awake),
      ].filter(Boolean);
      const note = parts.length ? `Averaging ${parts.join(', ')} per night.` : '';
      return `<section><div class="week card"><h2 class="section-title">The last seven nights</h2>
        <div class="week-bars">${bars.join('')}</div>
        <div class="legend">
          <span><i style="background:var(--sleep-deep)"></i>Deep</span>
          <span><i style="background:var(--sleep-light)"></i>Light</span>
        </div>
        ${note ? `<p class="week-note">${provisional}${note}</p>` : ''}
        </div></section>`;
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
        const [rollupData, accounts] = await Promise.all([
          fetch('/api/rollups?bucket=5m&hours=336&limit=100000').then(r => r.json()),
          fetch('/api/accounts').then(r => r.json())
        ]);
        rollups = rollupData.rollups || [];
        const account = (accounts.accounts || [])[0];
        const prefs = (account && account.dashboard_preferences) || {};
        if (prefs.baby_name) deviceName = prefs.baby_name;
        NIGHT = nightWindowFrom(prefs);
      } catch (error) {
        el('lede').textContent = 'Could not load readings — is the collector running?';
        return;
      }
      render();
      el('prevNight').addEventListener('click', () => { nightOffset = Math.min(6, nightOffset + 1); render(); });
      el('nextNight').addEventListener('click', () => { nightOffset = Math.max(0, nightOffset - 1); render(); });
      setInterval(async () => {   // keep "still collecting" nights fresh
        if (nightOffset !== 0 || document.hidden) return;
        const data = await fetch('/api/rollups?bucket=5m&hours=336&limit=100000').then(r => r.json()).catch(() => null);
        if (data) { rollups = data.rollups || rollups; render(); }
      }, 300000);
    }
    boot();
  </script>"""


def render_night_page() -> str:
    return render_shell(
        view="night",
        title="Tonight",
        head=NIGHT_HEAD,
        body=NIGHT_BODY,
        scripts=NIGHT_SCRIPTS,
    )
