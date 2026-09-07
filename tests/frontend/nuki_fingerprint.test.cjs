const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const context = {
  HTMLElement: class {},
  customElements: { get: () => true },
  URL,
  console,
  document: { createElement: tag => ({ tag }) },
};
const source = fs.readFileSync(
  path.join(__dirname, '../../custom_components/homepass/frontend/homepass-panel.js'),
  'utf8',
);
vm.runInNewContext(
  source
    .replace(/^import .*\n/, '')
    .replaceAll('import.meta.url', JSON.stringify('http://localhost/homepass-panel.js')) +
    '\nglobalThis.Panel = HomePassPanel;',
  context,
);

function fixture(callWS) {
  let renders = 0;
  const panel = Object.assign(Object.create(context.Panel.prototype), {
    _hass: { callWS },
    _selectedPerson: { person_id: 'person' },
    _detailsPersonId: 'person',
    _nukiFingerprintRequestGeneration: 0,
    _nukiFingerprintLoading: false,
    _nukiFingerprintCheckingLock: false,
    _nukiFingerprintError: undefined,
    _render() { renders += 1; },
  });
  return { panel, renders: () => renders };
}

test('passive fingerprint status load does not request a Nuki Bluetooth read', async () => {
  const calls = [];
  const { panel } = fixture(async call => {
    calls.push(call);
    return { response: { person_id: 'person', doors: [] } };
  });

  await panel._loadNukiFingerprintStatus('person');

  assert.equal(calls.length, 1);
  assert.equal(calls[0].service_data.refresh_from_lock, false);
});

test('Check Nuki now performs one lock read and blocks duplicate clicks', async () => {
  const calls = [];
  let finish;
  const { panel, renders } = fixture(call => {
    calls.push(call);
    return new Promise(resolve => { finish = resolve; });
  });

  const first = panel._loadNukiFingerprintStatus('person', true);
  await panel._loadNukiFingerprintStatus('person', true);

  assert.equal(calls.length, 1);
  assert.equal(calls[0].service_data.refresh_from_lock, true);
  assert.equal(panel._nukiFingerprintLoading, true);
  assert.equal(panel._nukiFingerprintCheckingLock, true);
  assert.equal(renders(), 1);

  finish({ response: { person_id: 'person', doors: [{ status: 'confirmed' }] } });
  await first;

  assert.equal(panel._nukiFingerprintStatus.doors[0].status, 'confirmed');
  assert.equal(panel._nukiFingerprintLoading, false);
  assert.equal(panel._nukiFingerprintCheckingLock, false);
  assert.equal(renders(), 2);
});
