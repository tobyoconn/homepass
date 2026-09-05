const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../custom_components/homepass/frontend/homepass-panel.js'), 'utf8');
const context = { HTMLElement: class {}, customElements: { get: () => true }, URL, console };
vm.runInNewContext(source.replace(/^import .*\n/, '').replaceAll('import.meta.url', JSON.stringify('http://localhost/homepass-panel.js')) + '\nglobalThis.Panel = HomePassPanel;', context);
const panel = () => Object.assign(Object.create(context.Panel.prototype), {
  _hass: { states: {} }, _batteryThresholds: { low: 30, critical: 10 },
});
const setBattery = (p, id, state) => { p._hass.states[id] = { state: String(state), attributes: { device_class: 'battery' } }; };

test('battery fills round to ten percent, thresholds agree at boundaries, unknown remains visible', () => {
  const p = panel();
  for (const [percentage, status] of [[0, 'critical'], [10, 'critical'], [11, 'low'], [30, 'low'], [31, 'normal'], [100, 'normal']]) {
    setBattery(p, 'sensor.lock', percentage);
    assert.equal(p._batteryReading(p._hass, 'sensor.lock').status, status);
  }
  setBattery(p, 'sensor.lock', 67);
  let markup = p._dashboardBatteryMarkup({ battery_entity_id: 'sensor.lock' });
  assert.match(markup, /height:70%/);
  assert.doesNotMatch(markup, /title=|onclick=|<button/);
  setBattery(p, 'sensor.lock', 'unavailable');
  markup = p._dashboardBatteryMarkup({ battery_entity_id: 'sensor.lock' });
  assert.match(markup, /dashboard-battery unknown/);
  assert.doesNotMatch(markup, /height:/);
  delete p._hass.states['sensor.lock'];
  assert.equal(p._batteryReading(p._hass, 'sensor.lock', 80, 'normal').status, 'unknown');
});

test('dashboard shows no invented batteries and keeps lock, sensor, accessory ordering', () => {
  const p = panel();
  assert.equal(p._dashboardBatteryMarkup({}), '');
  setBattery(p, 'sensor.lock', 90); setBattery(p, 'sensor.contact', 50); setBattery(p, 'sensor.keypad', 8);
  const door = { battery_entity_id: 'sensor.lock', door_sensor_battery_entity_id: 'sensor.contact', access_device_batteries: [{ battery_entity_id: 'sensor.keypad' }] };
  assert.deepEqual(Array.from(p._dashboardBatteries(door), r => r.entityId), ['sensor.lock', 'sensor.contact', 'sensor.keypad']);
  assert.equal((p._dashboardBatteryMarkup(door).match(/role="img"/g) || []).length, 3);
  door.door_sensor_battery_entity_id = 'sensor.lock';
  assert.equal(p._dashboardBatteries(door).length, 2);
});

test('multiple accessories retain the most urgent battery within three indicator limit', () => {
  const p = panel();
  setBattery(p, 'sensor.first', 60); setBattery(p, 'sensor.second', 4);
  const door = { access_device_batteries: [{ battery_entity_id: 'sensor.first' }, { battery_entity_id: 'sensor.second' }] };
  assert.equal(p._dashboardBatteries(door)[0].entityId, 'sensor.second');
});

test('binary battery and absent values never fabricate zero percent', () => {
  const p = panel();
  setBattery(p, 'binary_sensor.keypad', 'on');
  assert.equal(p._batteryReading(p._hass, 'binary_sensor.keypad').percentage, undefined);
  assert.equal(p._batteryReading(p._hass, 'binary_sensor.keypad').status, 'low');
  p._hass.states['lock.example'] = { state: 'locked', attributes: { battery_level: null } };
  assert.equal(p._batteryReading(p._hass, 'lock.example').status, 'unknown');
});

test('manual control requires a fresh explicit choice and preserves unlock-only doors', () => {
  const p = panel();
  p._selectedDoor = { control_profile: 'lock', lock_state: 'locked', availability: 'available', supports_open: true, open_enabled: true, entry_action: 'open' };
  assert.equal(p._availableDoorOperation(), undefined);
  p._manualEntryChoice = 'unlock';
  assert.equal(p._availableDoorOperation().service, 'unlock_access_point');
  p._manualEntryChoice = 'open';
  assert.equal(p._availableDoorOperation().service, 'open_access_point');
  assert.equal(p._availableDoorOperation().targetState, 'open');
  p._selectedDoor.open_enabled = false;
  assert.equal(p._availableDoorOperation().service, 'unlock_access_point');
});

test('onboarding suggestions require confirmation and never add questions to lock-only doors', () => {
  const p = panel();
  assert.equal(p._openPolicyMarkup({ id: 'yale', supports_open: false }, 'onboarding'), '');
  const door = { id: 'example', supports_open: true, recommended_entry_action: 'open' };
  const draft = p._openPolicyDraft(door, 'onboarding');
  assert.equal(draft.enabled, true); assert.equal(draft.entry, 'open'); assert.equal(draft.confirmed, false);
  assert.match(p._openPolicyMarkup(door, 'onboarding'), /I confirm/);
  assert.equal(p._openPolicyDraft({ id: 'unknown', supports_open: true }, 'onboarding').enabled, false);
});

test('unlocked is not accepted as a successful latch release', () => {
  const p = panel();
  p._doorOperationAccessPointId = 'example'; p._doorOperationTargetState = 'open';
  p._doorOperationState = 'WAITING_FOR_CONFIRMATION'; p._doorOperationAction = 'open';
  let completed = 0, failed = 0;
  p._completeDoorOperation = () => completed++;
  p._failDoorOperation = () => failed++;
  p._reconcileDoorOperationFromLiveState({ id: 'example', availability: 'available', lock_state: 'unlocked' });
  assert.equal(completed, 0); assert.equal(failed, 0);
  p._reconcileDoorOperationFromLiveState({ id: 'example', availability: 'available', lock_state: 'open' });
  assert.equal(completed, 1);
});
