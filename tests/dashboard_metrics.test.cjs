const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, '../app/dashboard.py'), 'utf8');
const functions = source.slice(source.indexOf('    function metricValue('), source.indexOf('    function validMetricValues('));
const context = vm.createContext({isOffline: () => false});
vm.runInContext(functions, context);
test('missing chart values remain gaps while numeric zero is preserved', () => {
  for (const value of [null, undefined, '', NaN, Infinity]) assert.equal(context.metricValue({heart_rate: value}, 'heart_rate'), null);
  assert.equal(context.metricValue({}, 'heart_rate'), null);
  assert.equal(context.metricValue({heart_rate: 125}, 'heart_rate'), 125);
  assert.equal(context.metricValue({movement: 0}, 'movement'), 0);
});
