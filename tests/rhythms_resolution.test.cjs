// Run with: node --test tests/rhythms_resolution.test.cjs
// Execute the actual page functions with controlled fetch completion order.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, '../app/rhythms_page.py'), 'utf8');
const functions = source.slice(source.indexOf('    let bucketSelection ='), source.indexOf('    async function boot()'));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
function setup() {
  const pending = [], loading = new Set(), renders = [];
  const context = vm.createContext({
    RESOLUTIONS: {'5m': 5, '10m': 10, '15m': 15, '30m': 30},
    BUCKET: '30m', rollups: ['initial'], bucketCache: new Map([['30m', ['initial']]]),
    rollups5Fetch: null,
    el: () => ({classList: {add: x => loading.add(x), remove: x => loading.delete(x)}}),
    fetch: url => { const request = deferred(); pending.push({url, ...request}); return request.promise; },
    applyBucket: bucket => { context.BUCKET = bucket; },
    updateLede() {}, paintRangeSeg() {},
    renderDayGrids: () => renders.push({bucket: context.BUCKET, rows: context.rollups}),
  });
  context.window = {owletFetch: context.fetch};
  vm.runInContext(functions, context);
  const reply = (index, rows = [index], status = 200) => pending[index].resolve({
    ok: status === 200, status, json: async () => rows === null ? {detail: 'error'} : {rollups: rows},
  });
  return {context, pending, loading, renders, reply, select: bucket => context.selectBucket(bucket)};
}
test('latest selection wins when responses arrive out of order', async () => {
  const h = setup(), first = h.select('10m'), last = h.select('15m');
  h.reply(1); await last; h.reply(0); await first;
  assert.equal(h.context.BUCKET, '15m');
  assert.deepEqual(h.renders.map(r => r.bucket), ['15m']);
});
test('clicking displayed resolution cancels a pending change', async () => {
  const h = setup(), request = h.select('10m');
  await h.select('30m'); assert.equal(h.loading.size, 0);
  h.reply(0); await request;
  assert.equal(h.context.BUCKET, '30m'); assert.equal(h.renders.length, 0);
});
test('superseded failure does not clear newer loading state', async () => {
  const h = setup(), first = h.select('10m'), last = h.select('15m');
  h.pending[0].reject(new Error('offline')); await first;
  assert.equal(h.loading.has('is-loading'), true);
  h.reply(1); await last; assert.equal(h.loading.size, 0);
});
for (const failure of ['401', 'malformed', 'network', 'invalid JSON']) {
  test(`${failure} preserves charts and allows retry`, async () => {
    const h = setup(), request = h.select('10m');
    if (failure === 'network') h.pending[0].reject(new Error('offline'));
    else if (failure === 'invalid JSON') h.pending[0].resolve({ok: true, json: async () => {throw new Error('JSON');}});
    else h.reply(0, null, failure === '401' ? 401 : 200);
    await request;
    assert.equal(h.context.BUCKET, '30m'); assert.equal(h.renders.length, 0);
    assert.equal(h.context.bucketCache.has('10m'), false); assert.equal(h.loading.size, 0);
    const retry = h.select('10m'); h.reply(1, ['retry']); await retry;
    assert.equal(h.context.BUCKET, '10m'); assert.deepEqual(h.context.rollups, ['retry']);
  });
}
test('repeated clicks cannot apply an earlier response', async () => {
  const h = setup(), first = h.select('10m'), last = h.select('10m');
  h.reply(1, ['new']); await last; h.reply(0, ['old']); await first;
  assert.deepEqual(h.context.rollups, ['new']); assert.equal(h.renders.length, 1);
});
test('boot 5m response is reused and cannot override a later selection', async () => {
  const h = setup(), boot = deferred(); h.context.rollups5Fetch = boot.promise;
  const first = h.select('5m'); await h.select('30m');
  boot.resolve({rollups: ['boot']}); await first;
  assert.equal(h.context.BUCKET, '30m'); assert.equal(h.pending.length, 0);
  await h.select('5m'); assert.equal(h.context.BUCKET, '5m');
  assert.deepEqual(h.context.rollups, ['boot']); assert.equal(h.pending.length, 0);
});
test('failed boot 5m request is retried', async () => {
  const h = setup(); h.context.rollups5Fetch = Promise.resolve({});
  const request = h.select('5m'); await new Promise(setImmediate);
  h.reply(0, ['retry']); await request; assert.equal(h.context.BUCKET, '5m');
});
test('all resolutions switch normally and cached selections avoid requests', async () => {
  const h = setup();
  for (const [i, bucket] of ['5m', '10m', '15m'].entries()) {
    const request = h.select(bucket); h.reply(i); await request;
    assert.equal(h.context.BUCKET, bucket);
  }
  await h.select('30m'); await h.select('5m');
  assert.equal(h.pending.length, 3); assert.equal(h.context.BUCKET, '5m');
});
