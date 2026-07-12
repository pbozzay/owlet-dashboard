/* Shared insight definitions for the simplified views (Now / Tonight / Rhythms).
   One place defines what a "wake-up", "bedtime", "baseline" mean, so pages agree. */
(function () {
  const BUCKET_SEC = 300; // 5m rollups

  function isAsleep(row) {
    return (row.sleep_seconds || 0) > BUCKET_SEC * 0.5;
  }
  function isAwake(row) {
    return (row.awake_seconds || 0) > (row.sleep_seconds || 0) && (row.awake_seconds || 0) > 60;
  }

  /* Personal baseline: 5th-95th percentile of a metric over same-state 5m buckets. */
  function baselineBand(rollups, metric, state) {
    const pick = state === 'asleep' ? isAsleep : isAwake;
    const values = rollups
      .filter(row => pick(row))
      .map(row => metric === 'hr' ? row.avg_heart_rate : row.avg_oxygen_saturation)
      .filter(v => v != null)
      .sort((a, b) => a - b);
    if (values.length < 24) return null; // need ~2h of same-state history
    const at = q => values[Math.min(values.length - 1, Math.floor(q * values.length))];
    return { low: at(0.05), high: at(0.95), n: values.length };
  }

  /* Consecutive-state sessions from 5m rollups within [start, end). */
  function sessions(rollups, start, end) {
    const inWindow = rollups.filter(row => {
      const t = new Date(row.bucket_start);
      return t >= start && t < end;
    }).sort((a, b) => new Date(a.bucket_start) - new Date(b.bucket_start));
    const out = [];
    let current = null;
    inWindow.forEach(row => {
      const t = new Date(row.bucket_start).getTime();
      const state = isAsleep(row) ? 'asleep' : (isAwake(row) ? 'awake' : 'nodata');
      if (current && current.state === state && t - current.end <= BUCKET_SEC * 1000) {
        current.end = t + BUCKET_SEC * 1000;
        current.buckets += 1;
      } else {
        if (current) out.push(current);
        current = { state, start: t, end: t + BUCKET_SEC * 1000, buckets: 1 };
      }
    });
    if (current) out.push(current);
    return out;
  }

  /* Wake-ups inside a night window: awake stretches of >=2 buckets between sleep. */
  function wakeUps(rollups, nightStart, nightEnd) {
    const runs = sessions(rollups, nightStart, nightEnd);
    const first = runs.findIndex(run => run.state === 'asleep' && run.buckets >= 2);
    if (first < 0) return [];
    return runs.slice(first + 1)
      .filter(run => run.state === 'awake' && run.buckets >= 2)
      .map(run => ({ at: new Date(run.start), seconds: (run.end - run.start) / 1000 }));
  }

  /* Bedtime: start of first sleep run (>=2 buckets) after 6 PM in the night window. */
  function bedtime(rollups, nightStart, nightEnd) {
    const runs = sessions(rollups, nightStart, nightEnd);
    const run = runs.find(r => r.state === 'asleep' && r.buckets >= 2);
    return run ? new Date(run.start) : null;
  }

  /* Typical bedtime (average minutes-from-midnight, evening-normalized) over N prior nights. */
  function typicalBedtimeMinutes(rollups, nights) {
    const values = [];
    for (let offset = 1; offset <= nights; offset++) {
      const now = new Date();
      const anchor = new Date(now);
      if (now.getHours() < 12) anchor.setDate(anchor.getDate() - 1);
      anchor.setDate(anchor.getDate() - offset);
      const start = new Date(anchor); start.setHours(18, 0, 0, 0);
      const end = new Date(start); end.setDate(end.getDate() + 1); end.setHours(12, 0, 0, 0);
      const bed = bedtime(rollups, start, end);
      if (bed) {
        let minutes = bed.getHours() * 60 + bed.getMinutes();
        if (minutes < 12 * 60) minutes += 24 * 60;
        values.push(minutes);
      }
    }
    if (!values.length) return null;
    return { mean: values.reduce((a, b) => a + b, 0) / values.length, n: values.length };
  }

  /* Battery projection from recent raw readings ({x: ms, y: percent}). */
  function batteryProjection(samples) {
    const clean = samples.filter(s => s.y != null && s.y > 0);
    if (clean.length < 10) return null;
    const first = clean[0], last = clean[clean.length - 1];
    const hours = (last.x - first.x) / 3600000;
    if (hours < 0.25) return null;
    const drainPerHour = (first.y - last.y) / hours;
    if (drainPerHour <= 0.2) return { level: last.y, charging: drainPerHour < -0.5, hoursLeft: Infinity };
    return { level: last.y, charging: false, hoursLeft: last.y / drainPerHour };
  }

  window.OwletInsights = {
    BUCKET_SEC, isAsleep, isAwake, baselineBand, sessions, wakeUps,
    bedtime, typicalBedtimeMinutes, batteryProjection
  };
})();
