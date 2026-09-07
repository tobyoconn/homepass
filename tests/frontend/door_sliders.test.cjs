const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function element(width = 320) {
  return {
    hidden: false, disabled: false, style: {}, attributes: {}, clientWidth: width,
    offsetWidth: width, addEventListener() {},
    setAttribute(name, value) { this.attributes[name] = value; },
    getBoundingClientRect() { return { width }; },
    setPointerCapture() {}, releasePointerCapture() {},
  };
}

const context = {
  HTMLElement: class {
    constructor() { this.listeners = new Map(); }
    attachShadow() {
      const elements = new Map(['track', 'thumb', 'label', 'detail', 'spinner', 'check', 'arrow']
        .map(id => [`#${id}`, element(id === 'thumb' ? 48 : 320)]));
      this.shadowRoot = { querySelector: id => elements.get(id) };
    }
    addEventListener(name, fn) { this.listeners.set(name, fn); }
    dispatchEvent(event) { event.currentTarget = this; this.listeners.get(event.type)?.(event); }
  },
  CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
  customElements: { get: () => true }, URL, console,
  window: { setTimeout: () => 1, clearTimeout() {} },
};
const source = fs.readFileSync(path.join(__dirname, '../../custom_components/homepass/frontend/homepass-panel.js'), 'utf8');
vm.runInNewContext(source.replace(/^import .*\n/, '').replaceAll('import.meta.url', JSON.stringify('http://localhost/homepass-panel.js')) +
  '\nglobalThis.Panel = HomePassPanel; globalThis.Slider = HomePassSlideAction;', context);

function fixture(overrides = {}) {
  const calls = [];
  const sliders = ['primary', 'open'].map(control => {
    const slider = new context.Slider();
    slider.dataset = { doorSlider: control };
    slider.connectedCallback();
    return slider;
  });
  const elements = new Map(['door-operation-region', 'door-operation-error', 'door-operation-error-title',
    'door-operation-error-message', 'open-remove-door-confirmation'].map(id => [`#${id}`, element()]));
  const p = Object.assign(Object.create(context.Panel.prototype), {
    _selectedDoor: { id: 'example', control_profile: 'lock', lock_state: 'locked', availability: 'available', supports_open: true, open_enabled: true, entry_action: 'open', ...overrides },
    _selectedDoorId: 'example', _doorControlDialogOpen: true,
    _doorOperationState: 'IDLE', _doorOperationGeneration: 0, _dashboardAccessPoints: [],
    _hass: { states: {}, callWS: call => { calls.push(call); return new Promise(() => {}); } },
    shadowRoot: { querySelector: id => elements.get(id), querySelectorAll: () => sliders },
  });
  p._bindDoorSliders();
  p._updateDoorOperationControls();
  return { p, primary: sliders[0], open: sliders[1], calls, elements };
}

const pointer = (clientX, pointerId = 1) => ({ clientX, pointerId, preventDefault() {} });
function drag(slider, end = 258) {
  slider._handlePointerDown(pointer(0));
  slider._handlePointerUp(pointer(end));
}

test('locked doors immediately offer two described sliders with no action selection', () => {
  const { primary, open } = fixture();
  assert.equal(primary.hidden, false);
  assert.equal(open.hidden, false);
  assert.equal(primary.label, 'Slide to Unlock');
  assert.equal(primary.description, 'Leave the latch engaged');
  assert.equal(open.label, 'Slide to Open Door');
  assert.equal(open.description, 'Briefly retract the latch');
  assert.match(open.shadowRoot.querySelector('#track').attributes['aria-label'], /Open Door — Briefly retract/);
});

for (const [control, service] of [['primary', 'unlock_access_point'], ['open', 'open_access_point']]) {
  test(`${control} slider sends exactly its own command only after a complete slide`, () => {
    const f = fixture();
    const slider = f[control];
    const other = f[control === 'primary' ? 'open' : 'primary'];
    slider._handleClick({ detail: 1 });
    drag(slider, 100);
    assert.equal(f.calls.length, 0);
    assert.equal(other.disabled, false);
    slider._handlePointerDown(pointer(0));
    assert.equal(other.disabled, true);
    assert.equal(f.calls.length, 0);
    slider._handlePointerUp(pointer(258));
    assert.equal(f.calls.length, 1);
    assert.equal(f.calls[0].service, service);
    assert.equal(f.calls[0].service_data.access_point_id, 'example');
    assert.equal(slider.busy, true);
    assert.equal(other.busy, false);
    assert.equal(other.disabled, true);
    other._handleKeyDown({ key: 'Enter', preventDefault() {} });
    other.callback();
    assert.equal(f.calls.length, 1);
  });
}

test('partial drag progress survives control refresh and cancellation re-enables the other slider', () => {
  const { p, primary, open, calls } = fixture();
  primary._handlePointerDown(pointer(0));
  primary._handlePointerMove(pointer(120));
  const progress = primary._progress;
  p._updateDoorOperationControls();
  assert.equal(primary._progress, progress);
  assert.equal(open.disabled, true);
  primary._cancelSlide();
  assert.equal(open.disabled, false);
  assert.equal(calls.length, 0);
});

test('a lock state change during an Unlock slide cannot turn it into a Lock command', () => {
  const { p, primary, calls } = fixture();
  primary._handlePointerDown(pointer(0));
  p._selectedDoor.lock_state = 'unlocked';
  primary._handlePointerUp(pointer(258));
  assert.equal(calls.length, 0);
  assert.equal(primary.label, 'Slide to Lock');
  drag(primary);
  assert.equal(calls[0].service, 'lock_access_point');
});

test('Open permission or capability loss cancels a pending gesture', () => {
  for (const field of ['open_enabled', 'supports_open']) {
    const { p, primary, open, calls } = fixture();
    open._handlePointerDown(pointer(0));
    p._selectedDoor[field] = false;
    p._updateDoorOperationControls();
    open._handlePointerUp(pointer(258));
    assert.equal(open.hidden, true);
    assert.equal(primary.disabled, false);
    assert.equal(calls.length, 0);
  }
});

test('offline and loading doors cannot dispatch either command', () => {
  for (const state of ['offline', 'loading']) {
    const { p, primary, open, calls } = fixture();
    if (state === 'offline') p._selectedDoor.availability = 'offline';
    else p._doorControlLoading = true;
    p._updateDoorOperationControls();
    assert.equal(primary.disabled, true);
    assert.equal(open.disabled, true);
    primary.callback(); open.callback();
    assert.equal(calls.length, 0);
  }
});

test('only the active slider shows success and both recover after a failed command', () => {
  const { p, primary, open, calls, elements } = fixture();
  drag(open);
  p._failDoorOperation(p._doorOperationGeneration);
  assert.equal(elements.get('#door-operation-error').hidden, false);
  assert.equal(primary.disabled, false);
  assert.equal(open.disabled, false);
  drag(open);
  assert.equal(calls.length, 2);
  p._completeDoorOperation(p._doorOperationGeneration);
  assert.equal(open.success, true);
  assert.equal(open.label, 'Latch released');
  assert.equal(primary.success, false);
  assert.equal(primary.disabled, true);
});

test('an unlocked door retains Lock and Open Door controls', () => {
  const { primary, open, calls } = fixture({ lock_state: 'unlocked' });
  assert.equal(primary.label, 'Slide to Lock');
  assert.equal(open.label, 'Slide to Open Door');
  drag(primary);
  assert.equal(calls[0].service, 'lock_access_point');
});

test('a released latch retains the Lock slider and does not offer a repeated Open command', () => {
  const { p, primary, open, calls } = fixture({ lock_state: 'open' });
  assert.equal(primary.label, 'Slide to Lock');
  assert.equal(primary.disabled, false);
  assert.equal(open.hidden, false);
  assert.equal(open.disabled, true);
  p._hass.states['lock.example'] = { state: 'open', last_updated: new Date().toISOString() };
  assert.equal(p._dashboardDoorCanOperate({ ...p._selectedDoor, enabled: true, lock_entity_id: 'lock.example' }), true);
  drag(primary);
  assert.equal(calls[0].service, 'lock_access_point');
});

test('doors without Open consent or capability keep their single existing slider', () => {
  for (const overrides of [{ open_enabled: false }, { supports_open: false }, { control_profile: 'garage_cover' }]) {
    const { primary, open, calls } = fixture(overrides);
    assert.equal(primary.hidden, false);
    assert.equal(open.hidden, true);
    drag(primary);
    assert.equal(calls[0].service, 'unlock_access_point');
  }
});

test('keyboard activation uses the focused slider and does not repeat commands', () => {
  const { open, calls } = fixture();
  open._handleKeyDown({ key: 'Enter', repeat: false, preventDefault() {} });
  open._handleKeyDown({ key: 'Enter', repeat: true, preventDefault() {} });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].service, 'open_access_point');
});
