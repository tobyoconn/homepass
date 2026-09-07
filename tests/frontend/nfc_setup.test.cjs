const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const element = tag => ({
  tag, children: [], attributes: {}, listeners: {},
  append(...children) { this.children.push(...children); },
  setAttribute(key, value) { this.attributes[key] = value; },
  addEventListener(key, fn) { this.listeners[key] = fn; },
});
let now = 0;
const context = {
  HTMLElement: class {}, customElements: { get: () => true }, URL, console,
  document: { createElement: element }, requestAnimationFrame: fn => fn(),
  Date: class extends Date { static now() { return now; } },
  window: { setTimeout(fn) { now += 16000; fn(); } },
};
const source = fs.readFileSync(path.join(__dirname, '../../custom_components/homepass/frontend/homepass-panel.js'), 'utf8');
vm.runInNewContext(source.replace(/^import .*\n/, '').replaceAll('import.meta.url', JSON.stringify('http://localhost/homepass-panel.js')) +
  '\nglobalThis.Panel = HomePassPanel;', context);

const all = node => [node, ...node.children.flatMap(all)];
function fixture() {
  const calls = [];
  const p = Object.assign(Object.create(context.Panel.prototype), {
    _hass: { user: { is_admin: true }, services: {}, callWS: async call => {
      calls.push(call);
      return { response: { public_origin: null, reason: 'cloud_unavailable' } };
    } },
    _selectedDoorId: 'door', _selectedDoor: { display_name: 'Example Door' },
    _doorControlDialogOpen: true, _doorNfcOriginDraft: '',
    _selectedPerson: { person_id: 'person' }, _detailsPersonId: 'person',
    _nfcEnrollmentOriginDraft: '', _nfcAccessSelection: new Set(),
    shadowRoot: { querySelector: () => undefined },
    _render() {}, _loadNfcEnrollment: async () => {},
  });
  return { p, calls };
}
function ready(p) {
  p._hass.services.homepass = {
    list_nfc_tags: {}, create_nfc_enrollment: {}, get_nfc_enrollment_status: {},
  };
}

for (const flow of ['door', 'person']) {
  const start = p => flow === 'door' ? p._openDoorNfcSetup() : p._createNfcEnrollment();
  const configuring = p => flow === 'door' ? p._doorNfcConfiguring : p._nfcEnrollmentConfiguring;
  const error = p => flow === 'door' ? p._doorNfcConfigurationError : p._nfcEnrollmentConfigurationError;

  test(`${flow} setup discovers without typed data and hides the manual field while waiting`, async () => {
    const { p, calls } = fixture();
    let finish;
    p._hass.callWS = call => { calls.push(call); return new Promise(resolve => { finish = resolve; }); };
    const pending = start(p);
    assert.equal(configuring(p), true);
    assert.equal(calls[0].service, 'configure_nfc');
    assert.equal(Object.keys(calls[0].service_data).length, 0);
    if (flow === 'door') {
      const markup = p._doorControlDialogTemplate();
      assert.match(markup, /Finding your secure address/);
      assert.doesNotMatch(markup, /id="door-nfc-public-origin"/);
    } else {
      const nodes = all(p._nfcEnrollmentCard());
      assert.ok(nodes.some(n => /Finding your secure address/.test(n.textContent)));
      assert.ok(!nodes.some(n => n.tag === 'input'));
    }
    finish({ response: { public_origin: null, reason: 'cloud_unavailable' } });
    await pending;
    assert.equal(configuring(p), false);
    assert.match(error(p), /enable Remote access/);
    if (flow === 'door') {
      assert.match(p._doorControlDialogTemplate(), /id="door-nfc-public-origin"/);
      assert.match(p._doorControlDialogTemplate(), /Try automatic setup again/);
    } else {
      const nodes = all(p._nfcEnrollmentCard());
      assert.ok(nodes.some(n => n.id === 'user-nfc-public-origin'));
      assert.ok(nodes.some(n => n.textContent === 'Try automatic setup again'));
    }
  });

  test(`${flow} setup uses the discovered address and continues when NFC becomes available`, async () => {
    const { p, calls } = fixture();
    p._hass.callWS = async call => {
      calls.push(call);
      ready(p);
      return { response: call.service === 'configure_nfc'
        ? { public_origin: 'https://example.ui.nabu.casa', reload_pending: true }
        : { enrollment_url: 'https://example.ui.nabu.casa/enroll' } };
    };
    await start(p);
    assert.equal(configuring(p), false);
    assert.equal(error(p), undefined);
    if (flow === 'door') {
      assert.match(p._doorControlDialogTemplate(), /access-point-id="door"/);
      assert.doesNotMatch(p._doorControlDialogTemplate(), /id="door-nfc-public-origin"/);
      assert.equal(calls.length, 1);
    } else {
      assert.equal(p._nfcEnrollmentSetupOpen, false);
      assert.equal(calls[1].service, 'create_nfc_enrollment');
      assert.equal(calls[1].service_data.person_id, 'person');
      assert.equal(p._nfcEnrollmentUrl, 'https://example.ui.nabu.casa/enroll');
    }
  });

  test(`${flow} setup retains a usable manual fallback after a request failure`, async () => {
    const { p, calls } = fixture();
    p._hass.callWS = async () => { throw new Error('Disconnected'); };
    await start(p);
    assert.match(error(p), /Try again or enter/);
    assert.equal(configuring(p), false);
    p._hass.callWS = async call => {
      calls.push(call); ready(p);
      return { response: { public_origin: 'https://access.example.com', enrollment_url: 'https://access.example.com/enroll' } };
    };
    if (flow === 'door') {
      p._doorNfcOriginDraft = 'https://access.example.com';
      await p._configureDoorNfc();
    } else {
      p._nfcEnrollmentOriginDraft = 'https://access.example.com';
      await p._configureNfcEnrollment();
    }
    assert.equal(calls[0].service_data.nfc_public_origin, 'https://access.example.com');
    assert.equal(error(p), undefined);
  });

  test(`${flow} setup rejects insecure manual input without sending it`, async () => {
    const { p, calls } = fixture();
    if (flow === 'door') {
      p._doorNfcOriginDraft = 'http://example.com';
      await p._configureDoorNfc();
    } else {
      p._nfcEnrollmentOriginDraft = 'http://example.com';
      await p._configureNfcEnrollment();
    }
    assert.equal(calls.length, 0);
    assert.match(error(p), /HTTPS address/);
  });

  test(`${flow} setup reports a slow reload and retains the saved address for retry`, async () => {
    const { p, calls } = fixture();
    p._hass.callWS = async call => {
      calls.push(call);
      return { response: { public_origin: 'https://example.ui.nabu.casa' } };
    };
    await start(p);
    assert.equal(configuring(p), false);
    assert.equal(calls.length, 1);
    assert.equal(flow === 'door' ? p._doorNfcOriginDraft : p._nfcEnrollmentOriginDraft,
      'https://example.ui.nabu.casa');
    assert.match(flow === 'door' ? p._doorNfcConfigurationNotice : p._nfcEnrollmentConfigurationNotice,
      /address is saved/);
  });
}

test('already configured door setup never calls discovery or rewrites an address', async () => {
  const { p, calls } = fixture();
  ready(p);
  await p._openDoorNfcSetup();
  assert.equal(calls.length, 0);
});

test('closing and reopening a door ignores the earlier discovery result', async () => {
  const { p, calls } = fixture();
  const resolves = [];
  p._hass.callWS = call => { calls.push(call); return new Promise(resolve => resolves.push(resolve)); };
  const first = p._openDoorNfcSetup();
  p._closeDoorNfcSetup();
  const second = p._openDoorNfcSetup();
  resolves[0]({ response: { public_origin: 'https://stale.example.com' } });
  await first;
  assert.equal(p._doorNfcConfiguring, true);
  assert.equal(p._doorNfcOriginDraft, '');
  resolves[1]({ response: { public_origin: null } });
  await second;
  assert.equal(p._doorNfcConfiguring, false);
});

test('leaving a person during setup never creates enrollment for another person', async () => {
  const { p, calls } = fixture();
  let finish;
  p._hass.callWS = call => { calls.push(call); return new Promise(resolve => { finish = resolve; }); };
  const pending = p._createNfcEnrollment();
  p._detailsPersonId = 'another-person';
  p._nfcEnrollmentConfigurationRequest = undefined;
  ready(p);
  finish({ response: { public_origin: 'https://example.ui.nabu.casa' } });
  await pending;
  assert.equal(calls.length, 1);
});
