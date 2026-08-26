import { HomepassNfcProvisioner, buildGoToTagsNtag424OperationBlob } from "./homepass-nfc-provisioner.js?version=1.16.5";

const DOMAIN = "homepass";
const CREATE_PERSON_ACTION = "create_person";
const CREATE_USER_ACTION = "create_user";
const DELETE_PERSON_ACTION = "delete_person";
const GET_PERSON_ACTION = "get_person";
const CREATE_NFC_ENROLLMENT_ACTION = "create_nfc_enrollment";
const GET_NFC_ENROLLMENT_STATUS_ACTION = "get_nfc_enrollment_status";
const LIST_NFC_ENROLLMENT_STATUSES_ACTION = "list_nfc_enrollment_statuses";
const REVOKE_NFC_ENROLLMENT_ACTION = "revoke_nfc_enrollment";
const UPDATE_NFC_ACCESS_ACTION = "update_nfc_access";
const LIST_NFC_TAGS_ACTION = "list_nfc_tags";
const REVOKE_NFC_TAG_ACTION = "revoke_nfc_tag";
const REINSTATE_NFC_TAG_ACTION = "reinstate_nfc_tag";
const DELETE_NFC_TAG_ACTION = "delete_nfc_tag";
const PREPARE_NFC_TAG_PROTECTION_ACTION = "prepare_nfc_tag_protection";
const CONFIRM_NFC_TAG_PROTECTION_ACTION = "confirm_nfc_tag_protection";
const GET_NUKI_FINGERPRINT_STATUS_ACTION = "get_nuki_fingerprint_status";
const GET_NUKI_STORAGE_STATUS_ACTION = "get_nuki_storage_status";
const START_NUKI_FINGERPRINT_ENROLLMENT_ACTION = "start_nuki_fingerprint_enrollment";
const COMPLETE_NUKI_FINGERPRINT_ENROLLMENT_ACTION = "complete_nuki_fingerprint_enrollment";
const GET_PERSON_POLICY_DETAILS_ACTION = "get_person_policy_details";
const GET_POLICY_EXPLANATION_ACTION = "get_policy_explanation";
const GET_DASHBOARD_ATTENTION_ACTION = "get_dashboard_attention";
const LIST_RECENT_ACTIVITY_ACTION = "list_recent_activity";
const GET_PERSON_SCHEDULE_ACTION = "get_person_schedule";
const GET_USER_SETUP_OPTIONS_ACTION = "get_user_setup_options";
const GIVE_ACCESS_ACTION = "give_access";
const LIST_ACCESS_POINTS_ACTION = "list_access_points";
const LIST_AVAILABLE_ACCESS_POINTS_ACTION = "list_available_access_points";
const ENROLL_ACCESS_POINT_ACTION = "enroll_access_point";
const ENROLL_HOME_ASSISTANT_ACCESS_POINT_ACTION = "enroll_home_assistant_access_point";
const UPDATE_ACCESS_POINT_ACTION = "update_access_point";
const REMOVE_ACCESS_POINT_ACTION = "remove_access_point";
const LOCK_ACCESS_POINT_ACTION = "lock_access_point";
const UNLOCK_ACCESS_POINT_ACTION = "unlock_access_point";
const GET_DOOR_DETAILS_ACTION = "get_door_details";
const LIST_ACCESS_DEVICES_ACTION = "list_access_devices";
const ADD_ACCESS_DEVICE_ACTION = "add_access_device";
const REMOVE_ACCESS_DEVICE_ACTION = "remove_access_device";
const LIST_PEOPLE_ACTION = "list_people";
const UPDATE_ACCESS_ACTION = "update_access";
const ASSIGN_USER_ACCESS_ACTION = "assign_user_access";
const RETRY_SYNCHRONIZATION_ACTION = "retry_synchronization";
const UPDATE_PERSON_ACTION = "update_person";
const SAVE_PERSON_SCHEDULE_ACTION = "save_person_schedule";
const GET_NOTIFICATION_PREFERENCES_ACTION = "get_notification_preferences";
const SAVE_NOTIFICATION_PREFERENCES_ACTION = "save_notification_preferences";
const GET_PROPERTY_SETTINGS_ACTION = "get_property_settings";
const SAVE_PROPERTY_SETTINGS_ACTION = "save_property_settings";
const CONFIGURE_NFC_ACTION = "configure_nfc";
const GET_ABOUT_ACTION = "get_about";
const UNSUPPORTED_SCHEDULE_MESSAGE =
  "This schedule uses date or time rules that this builder cannot edit safely. " +
  "It has not been changed. Cancel to go back.";
const REVEAL_PIN_COMMAND = "homepass/reveal_pin";
const VALIDATE_REPLACEMENT_PIN_COMMAND = "homepass/validate_replacement_pin";
const REPLACE_PIN_COMMAND = "homepass/replace_pin";
const ACCESS_UPDATE_POLL_INTERVAL = 1000;
const DOOR_RELATIVE_TIME_INTERVAL = 20000;
const DOOR_OPERATION_TIMEOUT = 10000;
const DOOR_OPERATION_SUCCESS_DURATION = 1000;
const REVEAL_TIMEOUT = 10000;
const REVEAL_REQUEST_TIMEOUT = 15000;
const NUKI_STORAGE_REQUEST_TIMEOUT = 55000;
const MAX_USER_DESCRIPTION_LENGTH = 160;
const MAX_PROPERTY_NAME_LENGTH = 60;
const SCHEDULE_WEEKDAYS = Object.freeze([
  { value: 1, shortLabel: "Mon", label: "Monday" },
  { value: 2, shortLabel: "Tue", label: "Tuesday" },
  { value: 3, shortLabel: "Wed", label: "Wednesday" },
  { value: 4, shortLabel: "Thu", label: "Thursday" },
  { value: 5, shortLabel: "Fri", label: "Friday" },
  { value: 6, shortLabel: "Sat", label: "Saturday" },
  { value: 7, shortLabel: "Sun", label: "Sunday" },
]);
const REPLACEMENT_VALIDATION_DELAY = 300;
const DASHBOARD_ACTIVITY_LIMIT = 25;
const DASHBOARD_ACTIVITY_PREVIEW_LIMIT = 5;
const REVEAL_COOLDOWN_MESSAGE =
  "PIN reveal is temporarily limited. Please wait a moment and try again.";
const MANAGE_ACCESS_STATE = Object.freeze({
  VIEW: "VIEW",
  EDIT_ACCESS: "EDIT_ACCESS",
  SAVING_ACCESS: "SAVING_ACCESS",
  VERIFYING_ACCESS: "VERIFYING_ACCESS",
  CHANGE_PIN: "CHANGE_PIN",
  CONFIRM_CHANGE_PIN: "CONFIRM_CHANGE_PIN",
  REPLACING_PIN: "REPLACING_PIN",
  SUCCESS: "SUCCESS",
  PARTIAL: "PARTIAL",
  ERROR: "ERROR",
});
const DOOR_OPERATION_STATE = Object.freeze({
  IDLE: "IDLE",
  SLIDING: "SLIDING",
  COMMAND_SENT: "COMMAND_SENT",
  WAITING_FOR_CONFIRMATION: "WAITING_FOR_CONFIRMATION",
  SUCCESS: "SUCCESS",
  FAILED: "FAILED",
});
const SLIDE_ACTION_STATE = Object.freeze({
  IDLE: "IDLE",
  SLIDING: "SLIDING",
});
const MANAGE_ACCESS_TRANSITIONS = Object.freeze({
  [MANAGE_ACCESS_STATE.VIEW]: new Set([
    MANAGE_ACCESS_STATE.EDIT_ACCESS,
    MANAGE_ACCESS_STATE.CHANGE_PIN,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.EDIT_ACCESS]: new Set([
    MANAGE_ACCESS_STATE.VIEW,
    MANAGE_ACCESS_STATE.SAVING_ACCESS,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.SAVING_ACCESS]: new Set([
    MANAGE_ACCESS_STATE.VERIFYING_ACCESS,
    MANAGE_ACCESS_STATE.SUCCESS,
    MANAGE_ACCESS_STATE.PARTIAL,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.VERIFYING_ACCESS]: new Set([
    MANAGE_ACCESS_STATE.SUCCESS,
    MANAGE_ACCESS_STATE.PARTIAL,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.CHANGE_PIN]: new Set([
    MANAGE_ACCESS_STATE.VIEW,
    MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN]: new Set([
    MANAGE_ACCESS_STATE.VIEW,
    MANAGE_ACCESS_STATE.CHANGE_PIN,
    MANAGE_ACCESS_STATE.REPLACING_PIN,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.REPLACING_PIN]: new Set([
    MANAGE_ACCESS_STATE.VIEW,
    MANAGE_ACCESS_STATE.EDIT_ACCESS,
    MANAGE_ACCESS_STATE.ERROR,
  ]),
  [MANAGE_ACCESS_STATE.SUCCESS]: new Set([MANAGE_ACCESS_STATE.VIEW]),
  [MANAGE_ACCESS_STATE.PARTIAL]: new Set([MANAGE_ACCESS_STATE.VIEW]),
  [MANAGE_ACCESS_STATE.ERROR]: new Set([
    MANAGE_ACCESS_STATE.VIEW,
    MANAGE_ACCESS_STATE.EDIT_ACCESS,
    MANAGE_ACCESS_STATE.SAVING_ACCESS,
    MANAGE_ACCESS_STATE.CHANGE_PIN,
    MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN,
  ]),
});
const REVEAL_DISCARD_REASONS = new Set([
  "access_point_changed",
  "connection_changed",
  "controller_detached",
  "credential_replaced",
  "dialog_closed",
  "eye_off_selected",
  "navigation",
  "panel_disconnected",
  "person_changed",
  "request_superseded",
  "session_changed",
  "session_missing",
  "state_reset",
  "state_changed",
  "target_missing",
  "unknown",
  "visibility_hidden",
]);
const PANEL_ASSET_VERSION = new URL(import.meta.url).searchParams.get("version") ?? "dev";
const PANEL_WEB_COMPONENT = `homepass-panel-${PANEL_ASSET_VERSION}`;
const SLIDE_ACTION_WEB_COMPONENT = `homepass-slide-action-${PANEL_ASSET_VERSION}`;
const NFC_PROVISIONER_WEB_COMPONENT = `homepass-nfc-provisioner-${PANEL_ASSET_VERSION}`;
if (!customElements.get(NFC_PROVISIONER_WEB_COMPONENT)) {
  customElements.define(
    NFC_PROVISIONER_WEB_COMPONENT,
    class extends HomepassNfcProvisioner {},
  );
}
const HOMEPASS_MARK_URL =
  `/homepass_static/assets/homepass-mark-concept-1.png?version=${PANEL_ASSET_VERSION}`;
const NFC_SYMBOL_URL =
  `/homepass_static/assets/nfc-symbol.svg?version=${PANEL_ASSET_VERSION}`;
const DOOR_STATUS_ICON_URLS = Object.freeze({
  CLOSED_LOCKED:
    `/homepass_static/assets/icons/door_closed_locked.svg?version=${PANEL_ASSET_VERSION}`,
  CLOSED_UNLOCKED:
    `/homepass_static/assets/icons/door_closed_unlocked.svg?version=${PANEL_ASSET_VERSION}`,
  LOCK_ONLY_LOCKED:
    `/homepass_static/assets/icons/door_lock_only_locked.svg?version=${PANEL_ASSET_VERSION}`,
  LOCK_ONLY_UNLOCKED:
    `/homepass_static/assets/icons/door_lock_only_unlocked.svg?version=${PANEL_ASSET_VERSION}`,
  OPEN_LOCKED:
    `/homepass_static/assets/icons/door_open_locked.svg?version=${PANEL_ASSET_VERSION}`,
  OPEN_UNLOCKED:
    `/homepass_static/assets/icons/door_open_unlocked.svg?version=${PANEL_ASSET_VERSION}`,
  UNKNOWN:
    `/homepass_static/assets/icons/door_unknown.svg?version=${PANEL_ASSET_VERSION}`,
});

function escapeHtml(value) {
  const entities = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return String(value).replace(/[&<>"']/g, (character) => entities[character]);
}

function doorStatusIconForState(lockState, doorState, availability) {
  if (!["available", "online"].includes(availability)) {
    return DOOR_STATUS_ICON_URLS.UNKNOWN;
  }
  if (doorState === undefined && lockState === "locked") {
    return DOOR_STATUS_ICON_URLS.LOCK_ONLY_LOCKED;
  }
  if (doorState === undefined && lockState === "unlocked") {
    return DOOR_STATUS_ICON_URLS.LOCK_ONLY_UNLOCKED;
  }
  const stateKey = `${doorState}:${lockState}`;
  const exactMatches = {
    "closed:locked": DOOR_STATUS_ICON_URLS.CLOSED_LOCKED,
    "closed:unlocked": DOOR_STATUS_ICON_URLS.CLOSED_UNLOCKED,
    "open:locked": DOOR_STATUS_ICON_URLS.OPEN_LOCKED,
    "open:unlocked": DOOR_STATUS_ICON_URLS.OPEN_UNLOCKED,
  };
  return exactMatches[stateKey] ?? DOOR_STATUS_ICON_URLS.UNKNOWN;
}

function doorStatusAccessibleText(
  displayName,
  lockState,
  doorState,
  availability,
  nfcEnabled = false,
) {
  const lockLabels = {
    jammed: "jammed",
    locked: "locked",
    locking: "locking",
    open: "open",
    opening: "opening",
    unlocked: "unlocked",
    unlocking: "unlocking",
  };
  const availabilityLabels = {
    available: "online",
    online: "online",
    offline: "offline",
    unavailable: "unavailable",
    unknown: "unknown",
  };
  const lockLabel = lockLabels[lockState] ?? "lock state unknown";
  const doorLabel = ["closed", "open"].includes(doorState)
    ? doorState
    : doorState === undefined
      ? "door position unavailable"
      : "door position unknown";
  const availabilityLabel = availabilityLabels[availability] ?? "availability unknown";
  const nfcLabel = nfcEnabled ? ", NFC tag enabled" : "";
  return `${displayName}: ${lockLabel}, ${doorLabel}, ${availabilityLabel}${nfcLabel}`;
}

function updateDoorStatusSymbol(symbol, door) {
  symbol.src = doorStatusIconForState(
    door.lock_state,
    door.door_state,
    door.availability,
  );
  symbol.alt = doorStatusAccessibleText(
    door.display_name,
    door.lock_state,
    door.door_state,
    door.availability,
    door.nfc_enabled,
  );
  const slot = symbol.parentElement;
  const nfcBadge = slot?.querySelector(".homepass-nfc-status-badge");
  if (nfcBadge) nfcBadge.hidden = !door.nfc_enabled;
}

function createDoorStatusSymbol(door, surfaceClass) {
  const slot = document.createElement("span");
  slot.className = "homepass-status-icon-slot";
  const symbol = document.createElement("img");
  symbol.className = `door-status-icon ${surfaceClass}`;
  symbol.decoding = "async";
  const nfcBadge = document.createElement("span");
  nfcBadge.className = "homepass-nfc-status-badge";
  nfcBadge.title = "HomePASS NFC tag enabled";
  nfcBadge.setAttribute("aria-hidden", "true");
  const nfcIcon = document.createElement("img");
  nfcIcon.src = NFC_SYMBOL_URL;
  nfcIcon.alt = "";
  nfcBadge.append(nfcIcon);
  updateDoorStatusSymbol(symbol, door);
  slot.append(symbol, nfcBadge);
  nfcBadge.hidden = !door.nfc_enabled;
  return { slot, symbol, nfcBadge };
}

class HomePassSlideAction extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._label = "Slide to confirm";
    this._disabled = false;
    this._busy = false;
    this._success = false;
    this._direction = "right";
    this._callback = undefined;
    this._progress = 0;
    this._pointerId = undefined;
    this._pointerStart = 0;
    this._pointerTravel = 1;
    this._activating = false;
    this._initialized = false;
  }

  connectedCallback() {
    if (!this._initialized) {
      this._initialized = true;
      this.shadowRoot.innerHTML = `
        <style>
          :host {
            display: block;
            min-width: 0;
          }

          .track {
            position: relative;
            box-sizing: border-box;
            display: grid;
            width: 100%;
            min-height: 64px;
            place-items: center;
            overflow: hidden;
            padding: 8px 72px;
            border: 1px solid var(--divider-color);
            border-radius: 32px;
            background: var(--secondary-background-color, var(--card-background-color));
            color: var(--primary-text-color);
            cursor: grab;
            font: inherit;
            touch-action: none;
            user-select: none;
          }

          .track:focus-visible {
            outline: 2px solid var(--primary-color);
            outline-offset: 3px;
          }

          .track:disabled {
            cursor: default;
            opacity: 0.78;
          }

          .thumb {
            position: absolute;
            left: 7px;
            display: grid;
            width: 48px;
            height: 48px;
            place-items: center;
            border-radius: 50%;
            background: var(--primary-color);
            color: var(--text-primary-color, white);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
            transition: transform 180ms ease;
            will-change: transform;
          }

          .track.sliding .thumb {
            transition: none;
          }

          .track.direction-left .thumb {
            right: 7px;
            left: auto;
          }

          .track.busy .thumb,
          .track.success .thumb {
            background: var(--primary-text-color);
            color: var(--card-background-color);
          }

          .copy {
            display: grid;
            gap: 2px;
            min-width: 0;
            text-align: center;
          }

          .label {
            overflow-wrap: anywhere;
            font-weight: 600;
          }

          .detail {
            color: var(--secondary-text-color);
            font-size: 12px;
          }

          .spinner {
            box-sizing: border-box;
            width: 20px;
            height: 20px;
            border: 2px solid currentColor;
            border-right-color: transparent;
            border-radius: 50%;
            animation: slide-action-spin 900ms linear infinite;
          }

          .arrow,
          .check {
            font-size: 22px;
            line-height: 1;
          }

          @keyframes slide-action-spin {
            to { transform: rotate(360deg); }
          }

          @media (prefers-reduced-motion: reduce) {
            .thumb { transition: none; }
            .spinner { animation: none; }
          }
        </style>
        <button id="track" class="track" type="button">
          <span id="thumb" class="thumb" aria-hidden="true">
            <span id="arrow" class="arrow">→</span>
            <span id="spinner" class="spinner" hidden></span>
            <span id="check" class="check" hidden>✓</span>
          </span>
          <span class="copy" role="status" aria-live="polite">
            <span id="label" class="label"></span>
            <span id="detail" class="detail" hidden>Waiting for Home Assistant…</span>
          </span>
        </button>
      `;
      const track = this.shadowRoot.querySelector("#track");
      this.shadowRoot
        .querySelector("#thumb")
        .addEventListener("pointerdown", (event) => this._handlePointerDown(event));
      track.addEventListener("pointermove", (event) => this._handlePointerMove(event));
      track.addEventListener("pointerup", (event) => this._handlePointerUp(event));
      track.addEventListener("pointercancel", () => this._cancelSlide());
      track.addEventListener("lostpointercapture", () => this._cancelSlide());
      track.addEventListener("keydown", (event) => this._handleKeyDown(event));
      track.addEventListener("click", (event) => this._handleClick(event));
    }
    this._sync();
  }

  set label(value) {
    this._label = String(value ?? "");
    this._sync();
  }

  get label() {
    return this._label;
  }

  set disabled(value) {
    this._disabled = Boolean(value);
    this._sync();
  }

  get disabled() {
    return this._disabled;
  }

  set busy(value) {
    this._busy = Boolean(value);
    if (!this._busy && !this._success) {
      this._activating = false;
      this._progress = 0;
    }
    this._sync();
  }

  get busy() {
    return this._busy;
  }

  set success(value) {
    this._success = Boolean(value);
    this._progress = this._success ? 1 : this._busy ? this._progress : 0;
    if (!this._success && !this._busy) this._activating = false;
    this._sync();
  }

  get success() {
    return this._success;
  }

  set direction(value) {
    this._direction = value === "left" ? "left" : "right";
    this._sync();
  }

  get direction() {
    return this._direction;
  }

  set callback(value) {
    this._callback = typeof value === "function" ? value : undefined;
  }

  get callback() {
    return this._callback;
  }

  focus(options) {
    this.shadowRoot.querySelector("#track")?.focus(options);
  }

  cancel() {
    const wasSliding = this._pointerId !== undefined;
    if (wasSliding) this._releasePointer(this._pointerId);
    this._progress = 0;
    this._activating = false;
    if (wasSliding) this._emitState(SLIDE_ACTION_STATE.IDLE);
    this._sync();
  }

  _canActivate() {
    return !this._disabled && !this._busy && !this._success && !this._activating;
  }

  _handlePointerDown(event) {
    if (!this._canActivate()) return;
    event.preventDefault();
    const track = this.shadowRoot.querySelector("#track");
    const thumb = this.shadowRoot.querySelector("#thumb");
    const trackBounds = track.getBoundingClientRect();
    const thumbBounds = thumb.getBoundingClientRect();
    this._pointerId = event.pointerId;
    this._pointerStart = event.clientX;
    this._pointerTravel = Math.max(trackBounds.width - thumbBounds.width - 14, 1);
    this._progress = 0;
    track.setPointerCapture?.(event.pointerId);
    this._emitState(SLIDE_ACTION_STATE.SLIDING);
    this._sync();
  }

  _handlePointerMove(event) {
    if (event.pointerId !== this._pointerId) return;
    this._updatePointerProgress(event.clientX);
    this._sync();
  }

  _updatePointerProgress(clientX) {
    if (!Number.isFinite(clientX)) return;
    const distance = this._direction === "left"
      ? this._pointerStart - clientX
      : clientX - this._pointerStart;
    this._progress = Math.min(1, Math.max(0, distance / this._pointerTravel));
  }

  _handlePointerUp(event) {
    if (event.pointerId !== this._pointerId) return;
    this._updatePointerProgress(event.clientX);
    const completed = this._progress === 1;
    this._releasePointer(event.pointerId);
    if (completed) {
      this._activate();
      return;
    }
    this._progress = 0;
    this._emitState(SLIDE_ACTION_STATE.IDLE);
    this._sync();
  }

  _cancelSlide() {
    if (this._pointerId === undefined) return;
    this._releasePointer(this._pointerId);
    this._progress = 0;
    this._emitState(SLIDE_ACTION_STATE.IDLE);
    this._sync();
  }

  _releasePointer(pointerId) {
    this._pointerId = undefined;
    const track = this.shadowRoot.querySelector("#track");
    if (!track.hasPointerCapture || track.hasPointerCapture(pointerId)) {
      track.releasePointerCapture?.(pointerId);
    }
  }

  _handleKeyDown(event) {
    if (!['Enter', ' '].includes(event.key) || event.repeat || !this._canActivate()) return;
    event.preventDefault();
    this._progress = 1;
    this._activate();
  }

  _handleClick(event) {
    // Pointer interaction must complete the slide. A zero-detail click is the
    // native activation generated by assistive technology or the keyboard.
    if (event.detail !== 0 || !this._canActivate()) return;
    event.preventDefault();
    this._progress = 1;
    this._activate();
  }

  _activate() {
    if (!this._canActivate()) return;
    this._activating = true;
    this._progress = 1;
    this._sync();
    this._callback?.();
  }

  _emitState(state) {
    this.dispatchEvent(new CustomEvent("slide-action-state-changed", {
      bubbles: true,
      composed: true,
      detail: { state },
    }));
  }

  _sync() {
    if (!this._initialized) return;
    const track = this.shadowRoot.querySelector("#track");
    const thumb = this.shadowRoot.querySelector("#thumb");
    const travel = Math.max(track.clientWidth - thumb.offsetWidth - 14, 0);
    const distance = (this._direction === "left" ? -1 : 1) * this._progress * travel;
    thumb.style.transform = `translateX(${distance}px)`;
    track.disabled = this._disabled;
    track.className = [
      "track",
      this._pointerId !== undefined ? "sliding" : "",
      this._direction === "left" ? "direction-left" : "",
      this._busy ? "busy" : "",
      this._success ? "success" : "",
    ].filter(Boolean).join(" ");
    track.setAttribute("aria-label", this._label);
    track.setAttribute(
      "aria-disabled",
      String(this._disabled || this._busy || this._success),
    );
    track.setAttribute("aria-busy", String(this._busy));
    this.shadowRoot.querySelector("#label").textContent = this._label;
    this.shadowRoot.querySelector("#detail").hidden = !this._busy;
    this.shadowRoot.querySelector("#spinner").hidden = !this._busy;
    this.shadowRoot.querySelector("#check").hidden = !this._success;
    const arrow = this.shadowRoot.querySelector("#arrow");
    arrow.hidden = this._busy || this._success;
    arrow.textContent = this._direction === "left" ? "←" : "→";
  }
}

class HomePassPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._currentPage = "dashboard";
    this._homePassFavicon = undefined;
    this._settingsLoading = false;
    this._settingsSaving = false;
    this._settingsError = undefined;
    this._settingsNotice = undefined;
    this._settingsData = undefined;
    this._settingsRequestGeneration = 0;
    this._nukiStorageLoading = false;
    this._nukiStorageError = undefined;
    this._nukiStorageStatus = undefined;
    this._propertySettingsLoading = false;
    this._propertySettingsSaving = false;
    this._propertySettingsError = undefined;
    this._propertySettingsNotice = undefined;
    this._propertySettingsData = undefined;
    this._propertySettingsRequestGeneration = 0;
    this._propertyName = "";
    this._savedPropertyName = "";
    this._aboutLoading = false;
    this._aboutError = undefined;
    this._aboutData = undefined;
    this._aboutRequestGeneration = 0;
    this._people = [];
    this._dashboardAccessPoints = [];
    this._dashboardDoorsLoading = true;
    this._dashboardDoorsError = undefined;
    this._accessDevices = [];
    this._availableAccessDevices = [];
    this._accessDevicesLoading = false;
    this._accessDevicesError = undefined;
    this._addAccessDeviceDialogOpen = false;
    this._addAccessDeviceDialogElement = undefined;
    this._selectedAccessDeviceCandidateId = "";
    this._selectedAccessDeviceDoorId = "";
    this._accessDeviceDisplayName = "";
    this._addingAccessDevice = false;
    this._removingAccessDeviceId = undefined;
    this._dashboardAttentionLoading = true;
    this._dashboardAttentionError = undefined;
    this._dashboardAttentionItems = [];
    this._dashboardAttentionRequestGeneration = 0;
    this._dashboardActivityLoading = true;
    this._dashboardActivityError = undefined;
    this._dashboardActivityEvents = [];
    this._dashboardActivityRequestGeneration = 0;
    this._dashboardActivityRequestPending = false;
    this._dashboardActivityRestoreRefreshFocus = false;
    this._dashboardActivityFilterGroups = [];
    this._dashboardActivitySelectedEventTypes = undefined;
    this._dashboardActivityDoorFilter = undefined;
    this._dashboardActivityPersonFilter = undefined;
    this._dashboardActivityFiltersOpen = false;
    this._dashboardActivityFilterFocusSelector = undefined;
    this._dashboardPropertyName = "";
    this._dashboardPropertyLoading = false;
    this._dashboardPropertyError = false;
    this._dashboardPropertyRequestGeneration = 0;
    this._doorControlDialogOpen = false;
    this._doorControlDialogElement = undefined;
    this._doorControlLoading = false;
    this._doorControlError = undefined;
    this._doorStatusRequestGeneration = 0;
    this._doorPolicyLoading = false;
    this._doorPolicyError = undefined;
    this._doorCurrentAccess = [];
    this._doorTemporarilyUnavailable = [];
    this._doorNoAccess = [];
    this._doorSynchronizationHistory = [];
    this._doorPolicyRequestGeneration = 0;
    this._doorRelativeTimeTimer = undefined;
    this._doorControlReturnFocusSelector = undefined;
    this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
    this._doorOperationAction = undefined;
    this._doorOperationTargetState = undefined;
    this._doorOperationError = undefined;
    this._doorOperationGeneration = 0;
    this._doorOperationTimeoutTimer = undefined;
    this._doorOperationSuccessTimer = undefined;
    this._doorOperationTimeoutMs = DOOR_OPERATION_TIMEOUT;
    this._doorOperationSawTransition = false;
    this._doorOperationAccessPointId = undefined;
    this._removeDoorConfirmationOpen = false;
    this._removeDoorConfirmationDialogElement = undefined;
    this._selectedDoorId = undefined;
    this._selectedDoor = undefined;
    this._editingDoorName = false;
    this._doorNameDraft = "";
    this._renamingDoor = false;
    this._doorRenameError = undefined;
    this._doorRenameNotice = undefined;
    this._doorSensorEditOpen = false;
    this._doorSensorEntityId = "";
    this._doorSensorInverted = false;
    this._doorSensorSaving = false;
    this._doorSensorError = undefined;
    this._doorSensorNotice = undefined;
    this._doorNfcSetupOpen = false;
    this._doorNfcOriginDraft = "";
    this._doorNfcConfiguring = false;
    this._doorNfcConfigurationError = undefined;
    this._doorNfcConfigurationNotice = undefined;
    this._doorNfcTags = [];
    this._doorNfcTagsLoading = false;
    this._doorNfcTagsError = undefined;
    this._doorNfcTagRevoking = undefined;
    this._doorNfcTagProtecting = undefined;
    this._doorNfcProtectionResult = undefined;
    this._removeDoorError = undefined;
    this._removingDoor = false;
    this._addDoorDialogOpen = false;
    this._addDoorDialogElement = undefined;
    this._availableAccessPoints = [];
    this._availableAccessPointsLoading = false;
    this._availableAccessPointsError = undefined;
    this._selectedAvailableAccessPointId = undefined;
    this._enrollingDoor = false;
    this._addDoorSource = "home_assistant";
    this._haDoorDevices = [];
    this._haDoorEntities = [];
    this._haDoorDeviceId = "";
    this._haDoorProfile = "garage_cover";
    this._haDoorControlEntityId = "";
    this._haDoorStatusEntityId = "";
    this._haDoorDisplayName = "";
    this._haDoorStatusInverted = false;
    this._haDoorPulseSeconds = 1;
    this._personScheduleViewOpen = false;
    this._scheduleForm = undefined;
    this._scheduleOriginalForm = undefined;
    this._effectiveSchedule = undefined;
    this._scheduleGroups = [];
    this._scheduleGroupEditorOpen = false;
    this._scheduleCreatingGroup = false;
    this._scheduleSelectedAccessPointIds = new Set();
    this._scheduleOriginalAccessPointIds = [];
    this._scheduleActiveGroupId = undefined;
    this._scheduleStatus = undefined;
    this._scheduleExpectation = undefined;
    this._scheduleSaveError = undefined;
    this._scheduleLoading = false;
    this._scheduleSaving = false;
    this._loading = true;
    this._loaded = false;
    this._error = undefined;
    this._detailsPersonId = undefined;
    this._selectedPerson = undefined;
    this._personCredentialStored = false;
    this._accessMetadata = [];
    this._detailsLoading = false;
    this._detailsError = undefined;
    this._nfcEnrollmentStatuses = new Map();
    this._nfcEnrollment = undefined;
    this._nfcEnrollmentLoading = false;
    this._nfcEnrollmentBusy = false;
    this._nfcEnrollmentError = undefined;
    this._nfcEnrollmentUrl = undefined;
    this._nfcEnrollmentQr = undefined;
    this._nfcEnrollmentExpiresAt = undefined;
    this._nfcEnrollmentSetupOpen = false;
    this._nfcEnrollmentOriginDraft = "";
    this._nfcEnrollmentConfiguring = false;
    this._nfcEnrollmentConfigurationError = undefined;
    this._nfcEnrollmentConfigurationNotice = undefined;
    this._nfcEnrollmentRequestGeneration = 0;
    this._nfcAccessSelection = new Set();
    this._nfcAccessSelectionInitialized = false;
    this._nfcAccessSaving = false;
    this._nfcAccessPoints = [];
    this._nukiFingerprintStatus = undefined;
    this._nukiFingerprintLoading = false;
    this._nukiFingerprintBusyDoorId = undefined;
    this._nukiFingerprintError = undefined;
    this._nukiFingerprintRequestGeneration = 0;
    this._personPolicyCurrentAccess = [];
    this._personPolicyTemporarilyUnavailable = [];
    this._personPolicyNoAccess = [];
    this._personSynchronizationHistory = [];
    this._personPolicyLoading = false;
    this._personPolicyError = undefined;
    this._personPolicyRequestGeneration = 0;
    this._synchronizationRecoveryGeneration = 0;
    this._synchronizationRecoveryPendingKey = undefined;
    this._synchronizationRecoveryResults = new Map();
    this._policyInspectorOpen = false;
    this._policyInspectorDialogElement = undefined;
    this._policyInspectorLoading = false;
    this._policyInspectorError = undefined;
    this._policyInspectorData = undefined;
    this._policyInspectorRequestGeneration = 0;
    this._policyInspectorSource = undefined;
    this._policyInspectorSourceIndex = undefined;
    this._giveAccessDialogOpen = false;
    this._manageAccessDialogOpen = false;
    this._manageAccessSessionSequence = 0;
    this._manageAccessSession = undefined;
    this._manageAccessDialogElement = undefined;
    this._manageAccessOpenSequence = 0;
    this._manageAccessOpenRequest = undefined;
    this._manageAccessMetadataCurrent = true;
    this._manageAccessRefreshError = undefined;
    this._revealCooldownTimer = undefined;
    this._revealCorrelationSequence = 0;
    this._activeRevealRequest = undefined;
    this._activeRevealTrace = undefined;
    this._changePinValue = "";
    this._changePinValid = false;
    this._changePinChanged = false;
    this._changePinValidationGeneration = 0;
    this._changePinValidationTimer = undefined;
    this._changePinError = undefined;
    this._changePinRetry = false;
    this._changePinRequirements = undefined;
    this._editAccessPointsLoading = false;
    this._editAccessPointsError = undefined;
    this._editAccessPendingIds = new Set();
    this._editAccessPollTimer = undefined;
    this._accessUpdateNotice = undefined;
    this._editAccessSelection = new Set();
    this._editNfcAccessSelection = new Set();
    this._editAccessScheduleMode = "permanent";
    this._editAccessScheduleId = "";
    this._editAccessSchedules = [];
    this._editAccessNewSchedule = this._defaultScheduleForm();
    this._editAccessPin = "";
    this._editAccessRequestId = undefined;
    this._accessPoints = [];
    this._accessPointsLoading = false;
    this._accessPointsError = undefined;
    this._selectedAccessPoint = undefined;
    this._giveAccessStep = "where";
    this._pinMode = "generated";
    this._pin = undefined;
    this._pinValidationError = undefined;
    this._provisioning = false;
    this._provisionError = undefined;
    this._provisionResult = undefined;
    this._quickPinControllers = new Map();
    this._quickPinRequestGeneration = 0;
    this._activeQuickPinPersonId = undefined;
    this._quickPinErrorPersonId = undefined;
    this._quickPinError = undefined;
    this._deleteDialogOpen = false;
    this._deleting = false;
    this._deleteError = undefined;
    this._dialogOpen = false;
    this._editing = false;
    this._saving = false;
    this._validationError = undefined;
    this._form = this._emptyForm();
    this._addUserWizardOpen = false;
    this._addUserOptions = { access_points: [], schedules: [] };
    this._addUserOptionsLoading = false;
    this._addUserOptionsError = undefined;
    this._addUserOptionsGeneration = 0;
    this._addUserSubmitting = false;
    this._addUserError = undefined;
    this._addUserResult = undefined;
    this._addUserRequestId = undefined;
    this._addUserReturnFocusSelector = undefined;
    this._addUserDialogElement = undefined;
    this._addUserForm = this._emptyAddUserForm();
    this._handleManageAccessDialogClick = this._handleManageAccessDialogClick.bind(this);
    this._handleRevealNavigation = () => {
      this._clearCredentialReveal("navigation");
      this._clearQuickPinReveals();
    };
    this._handleScheduleBeforeUnload = (event) => {
      if (!this._scheduleIsDirty()) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    };
    this._handleRevealVisibility = () => {
      if (document.hidden || document.visibilityState === "hidden") {
        this._clearCredentialReveal("visibility_hidden");
        this._clearQuickPinReveals();
      }
    };
  }

  set hass(hass) {
    const previousHass = this._hass;
    const connectionChanged = Boolean(
      previousHass?.connection && previousHass.connection !== hass.connection,
    );
    if (connectionChanged) {
      this._clearCredentialReveal("connection_changed");
      this._clearQuickPinReveals();
    }
    this._hass = hass;
    this._updateDashboardDoorCardsFromHass(previousHass, hass);
    if (this._doorControlDialogOpen) {
      this._updateDoorControlFromHass(previousHass, hass);
    }
    if (!this._loaded) {
      this._loaded = true;
      void this._loadPeople();
      void this._loadDoorsAndDevices();
      void this._loadDashboardAttention();
      void this._loadDashboardActivity();
      void this._loadDashboardPropertySettings();
    }
    if (connectionChanged && this._currentPage === "settings") {
      this._settingsRequestGeneration += 1;
      this._settingsData = undefined;
      this._settingsLoading = true;
      this._settingsSaving = false;
      this._settingsError = undefined;
      this._settingsNotice = undefined;
      this._render();
      void this._loadNotificationSettings();
    }
    if (connectionChanged && this._currentPage === "about") {
      this._aboutRequestGeneration += 1;
      this._aboutData = undefined;
      this._aboutLoading = true;
      this._aboutError = undefined;
      this._render();
      void this._loadAbout();
    }
  }

  _applyHomePassFavicon() {
    if (this._homePassFavicon?.isConnected) return;
    const favicon = document.createElement("link");
    favicon.rel = "icon";
    favicon.type = "image/svg+xml";
    favicon.href = "/homepass_static/assets/homepass-favicon.svg";
    favicon.dataset.homepassFavicon = "true";
    document.head.append(favicon);
    this._homePassFavicon = favicon;
  }

  _restoreHomePassFavicon() {
    this._homePassFavicon?.remove();
    this._homePassFavicon = undefined;
  }

  connectedCallback() {
    this._applyHomePassFavicon();
    window.addEventListener("location-changed", this._handleRevealNavigation);
    window.addEventListener("popstate", this._handleRevealNavigation);
    document.addEventListener("visibilitychange", this._handleRevealVisibility);
    window.addEventListener("beforeunload", this._handleScheduleBeforeUnload);
    this._render();
  }

  disconnectedCallback() {
    this._restoreHomePassFavicon();
    this._settingsRequestGeneration += 1;
    this._propertySettingsRequestGeneration += 1;
    this._aboutRequestGeneration += 1;
    this._dashboardPropertyRequestGeneration += 1;
    this._dashboardAttentionRequestGeneration += 1;
    this._cancelDashboardActivityRequest();
    this._resetSynchronizationRecovery();
    this._clearRevealCooldown();
    this._clearReplacementValidationTimer();
    this._clearAccessUpdatePoll();
    this._clearCredentialReveal("panel_disconnected");
    this._clearQuickPinReveals();
    this._resetAddUserWizard();
    this._stopDoorRelativeTimeTimer();
    this._resetDoorOperation();
    window.removeEventListener("location-changed", this._handleRevealNavigation);
    window.removeEventListener("popstate", this._handleRevealNavigation);
    document.removeEventListener("visibilitychange", this._handleRevealVisibility);
    window.removeEventListener("beforeunload", this._handleScheduleBeforeUnload);
  }

  async _loadPeople() {
    this._error = undefined;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_PEOPLE_ACTION,
        service_data: {},
        return_response: true,
      });
      this._people = result.response?.people ?? [];
      const nfcEnrollmentServiceAvailable = Boolean(
        this._hass?.services?.[DOMAIN]?.[LIST_NFC_ENROLLMENT_STATUSES_ACTION],
      );
      if (this._hass?.user?.is_admin && nfcEnrollmentServiceAvailable) {
        const nfcResult = await this._hass.callWS({
          type: "call_service",
          domain: DOMAIN,
          service: LIST_NFC_ENROLLMENT_STATUSES_ACTION,
          service_data: {},
          return_response: true,
        });
        const statuses = (nfcResult.response?.statuses ?? []).map(
          (status) => [status.person_id, status],
        );
        this._nfcEnrollmentStatuses = new Map(
          statuses,
        );
      } else {
        this._nfcEnrollmentStatuses = new Map();
      }
    } catch (_error) {
      this._error = "HomePASS could not load users. Try refreshing the page.";
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _loadDashboardAccessPoints({ render = true } = {}) {
    this._dashboardDoorsError = undefined;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_ACCESS_POINTS_ACTION,
        service_data: {},
        return_response: true,
      });
      this._dashboardAccessPoints = result.response?.access_points ?? [];
      const operationAccessPoint = this._dashboardAccessPoints.find(
        (door) => door.id === this._doorOperationAccessPointId,
      );
      if (operationAccessPoint) {
        this._reconcileDoorOperationFromLiveState(
          this._doorWithHassState(operationAccessPoint, this._hass),
        );
      }
      if (this._doorControlDialogOpen && this._selectedDoorId) {
        const selected = this._dashboardAccessPoints.find(
          (door) => door.id === this._selectedDoorId,
        );
        if (selected) {
          this._selectedDoor = this._doorWithHassState(selected, this._hass);
          this._reconcileDoorOperationFromLiveState();
        }
      }
    } catch (_error) {
      this._dashboardDoorsError = "Door information is unavailable right now.";
    } finally {
      this._dashboardDoorsLoading = false;
      if (render) this._render();
    }
  }

  async _loadAccessDevices({ render = true } = {}) {
    if (!this._hass?.user?.is_admin) return;
    this._accessDevicesError = undefined;
    this._accessDevicesLoading = true;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_ACCESS_DEVICES_ACTION,
        service_data: {},
        return_response: true,
      });
      this._accessDevices = result.response?.access_devices ?? [];
      this._availableAccessDevices = result.response?.available_devices ?? [];
    } catch (_error) {
      this._accessDevicesError = "Device information is unavailable right now.";
    } finally {
      this._accessDevicesLoading = false;
      if (render) this._render();
    }
  }

  async _openAddAccessDeviceDialog() {
    if (!this._hass?.user?.is_admin || this._addAccessDeviceDialogOpen) return;
    this._addAccessDeviceDialogOpen = true;
    this._selectedAccessDeviceCandidateId = "";
    this._selectedAccessDeviceDoorId = this._sortedDoors()[0]?.id ?? "";
    this._accessDeviceDisplayName = "";
    this._accessDevicesError = undefined;
    this._render();
    await this._loadAccessDevices();
  }

  _closeAddAccessDeviceDialog() {
    if (this._addingAccessDevice) return;
    this._addAccessDeviceDialogElement = undefined;
    this._addAccessDeviceDialogOpen = false;
    this._render();
  }

  async _addSelectedAccessDevice() {
    if (
      this._addingAccessDevice ||
      !this._selectedAccessDeviceCandidateId ||
      !this._selectedAccessDeviceDoorId
    ) return;
    this._addingAccessDevice = true;
    this._accessDevicesError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: ADD_ACCESS_DEVICE_ACTION,
        service_data: {
          device_id: this._selectedAccessDeviceCandidateId,
          access_point_id: this._selectedAccessDeviceDoorId,
          ...(this._accessDeviceDisplayName.trim()
            ? { display_name: this._accessDeviceDisplayName.trim() }
            : {}),
        },
        return_response: true,
      });
      this._addAccessDeviceDialogElement = undefined;
      this._addAccessDeviceDialogOpen = false;
      await this._loadAccessDevices({ render: false });
    } catch (error) {
      this._accessDevicesError = error?.message || "This device could not be added.";
    } finally {
      this._addingAccessDevice = false;
      this._render();
    }
  }

  async _removeAccessDevice(device) {
    if (!this._hass?.user?.is_admin || this._removingAccessDeviceId) return;
    if (!window.confirm(`Remove ${device.display_name} from HomePASS? The device will remain paired with Home Assistant.`)) return;
    this._removingAccessDeviceId = device.id;
    this._accessDevicesError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: REMOVE_ACCESS_DEVICE_ACTION,
        service_data: { access_device_id: device.id },
        return_response: true,
      });
      await this._loadAccessDevices({ render: false });
    } catch (_error) {
      this._accessDevicesError = "This device could not be removed from HomePASS.";
    } finally {
      this._removingAccessDeviceId = undefined;
      this._render();
    }
  }

  async _loadDashboardAttention() {
    const generation = ++this._dashboardAttentionRequestGeneration;
    this._dashboardAttentionLoading = true;
    this._dashboardAttentionError = undefined;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_DASHBOARD_ATTENTION_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._dashboardAttentionRequestOwns(generation)) return;
      const response = result.response;
      if (!this._isDashboardAttentionResponse(response)) {
        throw new Error("Invalid dashboard attention response");
      }
      this._dashboardAttentionItems = response.items;
    } catch (_error) {
      if (!this._dashboardAttentionRequestOwns(generation)) return;
      this._dashboardAttentionItems = [];
      this._dashboardAttentionError =
        "HomePASS could not check synchronization status.";
    } finally {
      if (this._dashboardAttentionRequestOwns(generation)) {
        this._dashboardAttentionLoading = false;
        this._render();
      }
    }
  }

  _dashboardAttentionRequestOwns(generation) {
    return (
      this._currentPage === "dashboard" &&
      !this._detailsPersonId &&
      this._dashboardAttentionRequestGeneration === generation
    );
  }

  _isDashboardAttentionResponse(response) {
    return Boolean(
      response &&
      Array.isArray(response.items) &&
      response.items.every(
        (item) =>
          item &&
          typeof item.person_id === "string" &&
          typeof item.access_point_id === "string" &&
          typeof item.person_name === "string" &&
          typeof item.door_name === "string" &&
          this._validSynchronizationPresentation(item.synchronization) &&
          ["warning", "error"].includes(item.synchronization.severity),
      ),
    );
  }

  _refreshDashboardAttention() {
    if (this._dashboardAttentionLoading) return;
    void this._loadDashboardAttention();
    this._render();
  }

  async _loadDashboardActivity() {
    if (this._dashboardActivityRequestPending) return;
    const generation = ++this._dashboardActivityRequestGeneration;
    this._dashboardActivityRequestPending = true;
    this._dashboardActivityLoading = true;
    this._dashboardActivityError = undefined;
    this._render();
    try {
      const serviceData = { limit: DASHBOARD_ACTIVITY_LIMIT };
      const eventTypes = this._dashboardActivityEventTypeIds();
      if (
        this._dashboardActivitySelectedEventTypes !== undefined &&
        this._dashboardActivitySelectedEventTypes.size !== eventTypes.length
      ) {
        serviceData.event_types = [...this._dashboardActivitySelectedEventTypes].sort();
      }
      if (this._dashboardActivityDoorFilter) {
        serviceData.access_point_id = this._dashboardActivityDoorFilter;
      }
      if (this._dashboardActivityPersonFilter) {
        serviceData.person_id = this._dashboardActivityPersonFilter;
      }
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_RECENT_ACTIVITY_ACTION,
        service_data: serviceData,
        return_response: true,
      });
      if (!this._dashboardActivityRequestOwns(generation)) return;
      const response = result.response;
      if (!this._isDashboardActivityResponse(response)) {
        throw new Error("Invalid Recent Activity response");
      }
      this._dashboardActivityEvents = response.events;
      if (Array.isArray(response.filter_groups)) {
        const previouslyAll =
          this._dashboardActivitySelectedEventTypes === undefined ||
          this._dashboardActivitySelectedEventTypes.size === eventTypes.length;
        this._dashboardActivityFilterGroups = response.filter_groups;
        const available = this._dashboardActivityEventTypeIds();
        if (previouslyAll) {
          this._dashboardActivitySelectedEventTypes = new Set(available);
        } else {
          this._dashboardActivitySelectedEventTypes = new Set(
            [...this._dashboardActivitySelectedEventTypes].filter((item) =>
              available.includes(item),
            ),
          );
        }
      }
    } catch (_error) {
      if (!this._dashboardActivityRequestOwns(generation)) return;
      this._dashboardActivityEvents = [];
      this._dashboardActivityError = "Recent activity is temporarily unavailable.";
    } finally {
      if (this._dashboardActivityRequestGeneration === generation) {
        this._dashboardActivityRequestPending = false;
      }
      if (this._dashboardActivityRequestOwns(generation)) {
        this._dashboardActivityLoading = false;
        const restoreRefreshFocus = this._dashboardActivityRestoreRefreshFocus;
        this._dashboardActivityRestoreRefreshFocus = false;
        this._render();
        if (restoreRefreshFocus) {
          queueMicrotask(() => {
            this.shadowRoot.querySelector("#refresh-recent-activity")?.focus();
          });
        }
        const filterFocusSelector = this._dashboardActivityFilterFocusSelector;
        this._dashboardActivityFilterFocusSelector = undefined;
        if (filterFocusSelector && this._dashboardActivityFiltersOpen) {
          queueMicrotask(() => this.shadowRoot.querySelector(filterFocusSelector)?.focus());
        }
      }
    }
  }

  _dashboardActivityRequestOwns(generation) {
    return (
      ["dashboard", "activity"].includes(this._currentPage) &&
      !this._detailsPersonId &&
      this._dashboardActivityRequestGeneration === generation
    );
  }

  _isDashboardActivityResponse(response) {
    return Boolean(
      response &&
      Array.isArray(response.events) &&
      response.events.every((event) => this._validDashboardActivity(event)) &&
      (response.filter_groups === undefined ||
        this._validDashboardActivityFilterGroups(response.filter_groups)),
    );
  }

  _validDashboardActivityFilterGroups(groups) {
    const groupIds = [];
    const ids = [];
    const valid = groups.every(
      (group) => {
        if (
          !group ||
          typeof group.id !== "string" ||
          !/^[a-z0-9_]+$/.test(group.id) ||
          typeof group.title !== "string" ||
          group.title.trim().length === 0 ||
          !Array.isArray(group.options) ||
          group.options.length === 0
        ) return false;
        groupIds.push(group.id);
        return group.options.every((option) => {
          if (
            !option ||
            typeof option.id !== "string" ||
            !/^[a-z0-9_]+$/.test(option.id) ||
            typeof option.title !== "string" ||
            option.title.trim().length === 0 ||
            (option.subgroup !== undefined &&
              (typeof option.subgroup !== "string" || option.subgroup.trim().length === 0))
          ) return false;
          ids.push(option.id);
          return true;
        });
      },
    );
    return valid &&
      groupIds.length === new Set(groupIds).size &&
      ids.length === new Set(ids).size;
  }

  _dashboardActivityEventTypeIds() {
    return this._dashboardActivityFilterGroups.flatMap((group) =>
      group.options.map((option) => option.id),
    );
  }

  _dashboardActivityActiveFilterCount() {
    const availableEventTypes = this._dashboardActivityEventTypeIds();
    const eventFilterActive =
      this._dashboardActivitySelectedEventTypes !== undefined &&
      this._dashboardActivitySelectedEventTypes.size !== availableEventTypes.length;
    return Number(eventFilterActive) +
      Number(Boolean(this._dashboardActivityDoorFilter)) +
      Number(Boolean(this._dashboardActivityPersonFilter));
  }

  _validDashboardActivity(event) {
    const optionalText = (value) => value === null || typeof value === "string";
    return Boolean(
      event &&
      typeof event.title === "string" &&
      typeof event.description === "string" &&
      ["info", "warning", "critical"].includes(event.severity) &&
      typeof event.category === "string" &&
      typeof event.occurred_at === "string" &&
      Number.isFinite(Date.parse(event.occurred_at)) &&
      optionalText(event.actor) &&
      optionalText(event.person_name) &&
      optionalText(event.door_name) &&
      Array.isArray(event.navigation) &&
      event.navigation.every(
        (reference) =>
          reference &&
          typeof reference.target === "string" &&
          typeof reference.id === "string",
      )
    );
  }

  _refreshDashboardActivity() {
    if (this._dashboardActivityRequestPending) return;
    this._dashboardActivityRestoreRefreshFocus = true;
    void this._loadDashboardActivity();
  }

  _refreshDashboardActivityAfterOperation() {
    if (!["dashboard", "activity"].includes(this._currentPage) || this._detailsPersonId) return;
    this._cancelDashboardActivityRequest();
    void this._loadDashboardActivity();
  }

  _cancelDashboardActivityRequest() {
    this._dashboardActivityRequestGeneration += 1;
    this._dashboardActivityRequestPending = false;
    this._dashboardActivityRestoreRefreshFocus = false;
  }

  _openDashboardActivityFilters() {
    this._dashboardActivityFiltersOpen = true;
    this._render();
  }

  _closeDashboardActivityFilters({ restoreFocus = true } = {}) {
    this._dashboardActivityFiltersOpen = false;
    this._render();
    if (restoreFocus) {
      queueMicrotask(() => this.shadowRoot.querySelector("#filter-recent-activity")?.focus());
    }
  }

  _reloadDashboardActivityForFilters(focusSelector) {
    this._dashboardActivityFilterFocusSelector = focusSelector;
    this._cancelDashboardActivityRequest();
    void this._loadDashboardActivity();
  }

  _toggleDashboardActivityEventFilter(eventType, checked) {
    const selected = new Set(
      this._dashboardActivitySelectedEventTypes ?? this._dashboardActivityEventTypeIds(),
    );
    if (checked) selected.add(eventType);
    else selected.delete(eventType);
    this._dashboardActivitySelectedEventTypes = selected;
    this._reloadDashboardActivityForFilters(`[data-activity-event-filter="${eventType}"]`);
  }

  _setDashboardActivityDoorFilter(accessPointId) {
    this._dashboardActivityDoorFilter = accessPointId || undefined;
    this._reloadDashboardActivityForFilters("#activity-door-filter");
  }

  _setDashboardActivityPersonFilter(personId) {
    this._dashboardActivityPersonFilter = personId || undefined;
    this._reloadDashboardActivityForFilters("#activity-person-filter");
  }

  _clearDashboardActivityFilters() {
    this._dashboardActivitySelectedEventTypes = new Set(
      this._dashboardActivityEventTypeIds(),
    );
    this._dashboardActivityDoorFilter = undefined;
    this._dashboardActivityPersonFilter = undefined;
    this._reloadDashboardActivityForFilters("#activity-filter-clear-all");
  }

  async _openPersonSchedule() {
    if (!this._selectedPerson) {
      return;
    }
    const personId = this._selectedPerson.person_id;
    this._personScheduleViewOpen = true;
    this._scheduleLoading = true;
    this._scheduleForm = undefined;
    this._scheduleOriginalForm = undefined;
    this._scheduleGroups = [];
    this._scheduleGroupEditorOpen = false;
    this._scheduleCreatingGroup = false;
    this._scheduleSelectedAccessPointIds = new Set();
    this._scheduleOriginalAccessPointIds = [];
    this._scheduleActiveGroupId = undefined;
    this._scheduleStatus = undefined;
    this._scheduleExpectation = undefined;
    this._scheduleSaveError = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_PERSON_SCHEDULE_ACTION,
        service_data: { person_id: personId },
        return_response: true,
      });
      if (!this._personScheduleViewOpen || this._detailsPersonId !== personId) {
        return;
      }
      const response = result.response ?? {};
      this._scheduleGroups = Array.isArray(response.schedule_groups)
        ? response.schedule_groups
        : [];
      const activeGroup = this._scheduleGroups[0];
      const activeSchedule = activeGroup?.schedule ?? response.schedule;
      const hasAssignedDoors = this._accessMetadata.length > 0;
      this._effectiveSchedule = activeSchedule;
      this._scheduleGroupEditorOpen = Boolean(activeGroup) || !hasAssignedDoors;
      this._scheduleCreatingGroup = false;
      this._scheduleActiveGroupId = activeGroup?.schedule?.schedule_id;
      this._scheduleSelectedAccessPointIds = new Set(activeGroup?.access_point_ids ?? []);
      this._scheduleOriginalAccessPointIds = [
        ...this._scheduleSelectedAccessPointIds,
      ].sort();
      this._scheduleExpectation = {
        personUpdatedAt: response.expected_person_updated_at,
        scheduleId: activeSchedule?.schedule_id ?? response.schedule_id,
        scheduleRevision:
          activeGroup?.expected_schedule_revision ?? response.expected_schedule_revision,
      };
      const unsupportedReason = this._scheduleUnsupportedReason(activeSchedule);
      if (unsupportedReason) {
        this._scheduleStatus = "unsupported";
        this._scheduleSaveError = unsupportedReason;
      } else {
        this._scheduleStatus = "ok";
        this._scheduleOriginalForm = this._scheduleFormFromBackend(activeSchedule);
        this._scheduleForm = this._cloneScheduleForm(this._scheduleOriginalForm);
      }
    } catch (error) {
      if (!this._personScheduleViewOpen || this._detailsPersonId !== personId) {
        return;
      }
      const message = String(error?.message ?? error ?? "");
      if (message.includes("person_schedule_conflict")) {
        this._scheduleStatus = "conflict";
        this._scheduleSaveError =
          "This user's access currently requires attention before their schedule can be updated.";
      } else {
        this._scheduleStatus = "error";
        this._scheduleSaveError = "Unable to load the schedule right now.";
      }
      this._scheduleOriginalForm = this._defaultScheduleForm();
      this._scheduleForm = this._cloneScheduleForm(this._scheduleOriginalForm);
    } finally {
      if (this._personScheduleViewOpen && this._detailsPersonId === personId) {
        this._scheduleLoading = false;
        this._render();
      }
    }
  }

  _closePersonSchedule({ confirmDiscard = true } = {}) {
    if (this._scheduleSaving) {
      return;
    }
    if (
      confirmDiscard &&
      this._scheduleIsDirty() &&
      !window.confirm("Discard your unsaved schedule changes?")
    ) {
      return;
    }
    this._personScheduleViewOpen = false;
    this._scheduleForm = undefined;
    this._scheduleOriginalForm = undefined;
    this._effectiveSchedule = undefined;
    this._scheduleGroups = [];
    this._scheduleGroupEditorOpen = false;
    this._scheduleCreatingGroup = false;
    this._scheduleSelectedAccessPointIds = new Set();
    this._scheduleOriginalAccessPointIds = [];
    this._scheduleActiveGroupId = undefined;
    this._scheduleStatus = undefined;
    this._scheduleExpectation = undefined;
    this._scheduleSaveError = undefined;
    this._render();
  }

  _cancelPersonSchedule() {
    if (this._scheduleOriginalForm) {
      this._scheduleForm = this._cloneScheduleForm(this._scheduleOriginalForm);
    }
    this._closePersonSchedule({ confirmDiscard: false });
  }

  _defaultScheduleForm() {
    return {
      validity: "permanent",
      startsDate: "",
      startsTime: "",
      endsDate: "",
      endsTime: "",
      accessHours: "24-hours",
      selectedDays: [],
      startTime: "09:00",
      endTime: "17:00",
    };
  }

  _cloneScheduleForm(form) {
    return { ...form, selectedDays: [...form.selectedDays] };
  }

  _toggleAllScheduleDays(form) {
    form.selectedDays = form.selectedDays.length === SCHEDULE_WEEKDAYS.length
      ? []
      : SCHEDULE_WEEKDAYS.map(({ value }) => value);
  }

  _scheduleUnsupportedReason(schedule) {
    if (!schedule) {
      return undefined;
    }
    if (schedule.enabled !== true) {
      return UNSUPPORTED_SCHEDULE_MESSAGE;
    }
    const hasValidFrom = Boolean(schedule.valid_from);
    const hasValidUntil = Boolean(schedule.valid_until);
    if (hasValidFrom !== hasValidUntil) {
      return UNSUPPORTED_SCHEDULE_MESSAGE;
    }
    if (
      (hasValidFrom && !this._scheduleDateTimeHasMinutePrecision(schedule.valid_from)) ||
      (hasValidUntil && !this._scheduleDateTimeHasMinutePrecision(schedule.valid_until))
    ) {
      return UNSUPPORTED_SCHEDULE_MESSAGE;
    }

    const rules = schedule.weekly_rules ?? [];
    if (!Array.isArray(rules)) {
      return UNSUPPORTED_SCHEDULE_MESSAGE;
    }
    if (
      rules.length > 0 &&
      schedule.time_zone !== (this._hass?.config?.time_zone ?? "UTC")
    ) {
      return UNSUPPORTED_SCHEDULE_MESSAGE;
    }
    const days = new Set();
    let sharedInterval;
    for (const rule of rules) {
      const day = Number(rule?.day_of_week);
      const start = this._scheduleRuleTime(rule?.start_time);
      const end = this._scheduleRuleTime(rule?.end_time);
      if (!Number.isInteger(day) || day < 1 || day > 7 || !start || !end) {
        return UNSUPPORTED_SCHEDULE_MESSAGE;
      }
      if (days.has(day) || end <= start) {
        return UNSUPPORTED_SCHEDULE_MESSAGE;
      }
      days.add(day);
      const interval = `${start}/${end}`;
      if (sharedInterval && interval !== sharedInterval) {
        return UNSUPPORTED_SCHEDULE_MESSAGE;
      }
      sharedInterval = interval;
    }
    return undefined;
  }

  _scheduleDateTimeHasMinutePrecision(value) {
    if (typeof value !== "string") {
      return false;
    }
    const parsed = new Date(value);
    return (
      !Number.isNaN(parsed.getTime()) &&
      parsed.getUTCSeconds() === 0 &&
      parsed.getUTCMilliseconds() === 0
    );
  }

  _scheduleRuleTime(value) {
    if (
      typeof value !== "string" ||
      !/^(?:[01]\d|2[0-3]):[0-5]\d(?::00)?$/.test(value)
    ) {
      return undefined;
    }
    return value.slice(0, 5);
  }

  _scheduleFormFromBackend(schedule) {
    if (!schedule) {
      return this._defaultScheduleForm();
    }
    const starts = this._scheduleLocalDateTime(schedule.valid_from);
    const ends = this._scheduleLocalDateTime(schedule.valid_until);
    const rules = schedule.weekly_rules ?? [];
    const firstRule = rules[0];
    return {
      validity: schedule.valid_from || schedule.valid_until ? "specific-dates" : "permanent",
      startsDate: starts.date,
      startsTime: starts.time,
      endsDate: ends.date,
      endsTime: ends.time,
      accessHours: rules.length > 0 ? "specific-hours" : "24-hours",
      selectedDays: [...new Set(rules.map((rule) => Number(rule.day_of_week)))].sort(
        (left, right) => left - right,
      ),
      startTime: firstRule?.start_time?.slice(0, 5) ?? "09:00",
      endTime: firstRule?.end_time?.slice(0, 5) ?? "17:00",
    };
  }

  _scheduleLocalDateTime(value) {
    if (!value) {
      return { date: "", time: "" };
    }
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: this._hass?.config?.time_zone ?? "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(new Date(value));
    const part = (type) => parts.find((item) => item.type === type)?.value ?? "";
    return {
      date: `${part("year")}-${part("month")}-${part("day")}`,
      time: `${part("hour")}:${part("minute")}`,
    };
  }

  _scheduleIsDirty() {
    return Boolean(
      this._scheduleForm &&
        this._scheduleOriginalForm &&
        (JSON.stringify(this._scheduleComparableForm(this._scheduleForm)) !==
          JSON.stringify(this._scheduleComparableForm(this._scheduleOriginalForm)) ||
          JSON.stringify([...this._scheduleSelectedAccessPointIds].sort()) !==
            JSON.stringify(this._scheduleOriginalAccessPointIds)),
    );
  }

  _scheduleComparableForm(form) {
    return {
      validity: form.validity,
      startsDate: form.validity === "specific-dates" ? form.startsDate : "",
      startsTime: form.validity === "specific-dates" ? form.startsTime : "",
      endsDate: form.validity === "specific-dates" ? form.endsDate : "",
      endsTime: form.validity === "specific-dates" ? form.endsTime : "",
      accessHours: form.accessHours,
      selectedDays: form.accessHours === "specific-hours" ? form.selectedDays : [],
      startTime: form.accessHours === "specific-hours" ? form.startTime : "",
      endTime: form.accessHours === "specific-hours" ? form.endTime : "",
    };
  }

  _scheduleValidationFor(form) {
    const errors = { dates: "", days: "", times: "" };
    if (!form) {
      return errors;
    }
    if (form.validity === "specific-dates") {
      if (!form.startsDate || !form.startsTime || !form.endsDate || !form.endsTime) {
        errors.dates = "Enter the start and end dates and times.";
      } else {
        const starts = `${form.startsDate}T${form.startsTime}`;
        const ends = `${form.endsDate}T${form.endsTime}`;
        if (ends <= starts) {
          errors.dates = "End date and time must be later than the start.";
        }
      }
    }
    if (form.accessHours === "specific-hours") {
      if (form.selectedDays.length === 0) {
        errors.days = "Select at least one day.";
      }
      if (!form.startTime || !form.endTime) {
        errors.times = "Enter a start and end time.";
      } else if (form.endTime <= form.startTime) {
        errors.times = "End time must be later than start time. Overnight hours are not supported.";
      }
    }
    return errors;
  }

  _scheduleValidation() {
    return this._scheduleValidationFor(this._scheduleForm);
  }

  _scheduleIsValid(form = this._scheduleForm) {
    return Object.values(this._scheduleValidationFor(form)).every((error) => !error) &&
      (this._accessMetadata.length === 0 || this._scheduleSelectedAccessPointIds.size > 0);
  }

  _schedulePolicyPayload(form) {
    const validity = form.validity === "specific-dates";
    const specificHours = form.accessHours === "specific-hours";
    return {
      time_zone: this._hass?.config?.time_zone ?? "UTC",
      valid_from: validity ? `${form.startsDate}T${form.startsTime}:00` : null,
      valid_until: validity ? `${form.endsDate}T${form.endsTime}:00` : null,
      weekly_rules: specificHours
        ? form.selectedDays.map((day) => ({
            day_of_week: day,
            start_time: form.startTime,
            end_time: form.endTime,
          }))
        : [],
      enabled: true,
    };
  }

  async _savePersonSchedule() {
    if (
      this._scheduleSaving ||
      !this._selectedPerson ||
      !this._scheduleExpectation ||
      !this._scheduleIsDirty() ||
      !this._scheduleIsValid() ||
      this._scheduleStatus !== "ok"
    ) {
      return;
    }
    const personId = this._selectedPerson.person_id;
    const form = this._scheduleForm;
    this._scheduleSaving = true;
    this._scheduleSaveError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: SAVE_PERSON_SCHEDULE_ACTION,
        service_data: {
          person_id: personId,
          ...this._schedulePolicyPayload(form),
          expected_person_updated_at: this._scheduleExpectation.personUpdatedAt,
          schedule_id: this._scheduleExpectation.scheduleId,
          expected_schedule_revision: this._scheduleExpectation.scheduleRevision,
          ...(this._accessMetadata.length > 0
            ? { access_point_ids: [...this._scheduleSelectedAccessPointIds] }
            : {}),
        },
        return_response: true,
      });
      this._scheduleOriginalForm = this._cloneScheduleForm(this._scheduleForm);
      this._scheduleSaving = false;
      await this._openPersonDetails(personId);
    } catch (error) {
      const message = String(error?.message ?? error ?? "");
      if (message.includes("person_schedule_conflict")) {
        this._scheduleStatus = "conflict";
        this._scheduleSaveError =
          "This user's access currently requires attention before their schedule can be updated.";
      } else if (message.includes("concurrent_person_schedule_update")) {
        this._scheduleStatus = "concurrent";
        this._scheduleSaveError =
          "This schedule was changed somewhere else.\n\nPlease reopen it and try again.";
      } else if (message.includes("person_schedule_validation")) {
        this._scheduleSaveError = "Review the schedule details and try again.";
      } else {
        this._scheduleSaveError = "Unable to save the schedule right now.";
      }
    } finally {
      this._scheduleSaving = false;
      if (this._personScheduleViewOpen) {
        this._render();
      }
    }
  }

  async _openPersonDetails(personId) {
    this._clearQuickPinReveals();
    if (this._currentPage === "dashboard") {
      this._dashboardAttentionRequestGeneration += 1;
      this._cancelDashboardActivityRequest();
    }
    this._resetPolicyInspectorState();
    this._resetSynchronizationRecovery();
    this._manageAccessOpenRequest = undefined;
    if (
      this._manageAccessSession &&
      this._manageAccessSession.personId !== personId
    ) {
      this._clearAccessUpdatePoll();
      this._clearCredentialReveal("person_changed");
      this._clearRevealCooldown();
      this._manageAccessDialogOpen = false;
      this._manageAccessSession = undefined;
      this._manageAccessDialogElement = undefined;
      this._resetChangePin();
      this._editAccessPointsError = undefined;
      this._editAccessPendingIds = new Set();
      this._editAccessSelection = new Set();
      this._editNfcAccessSelection = new Set();
    }
    this._detailsPersonId = personId;
    this._selectedPerson = undefined;
    this._personCredentialStored = false;
    this._accessMetadata = [];
    this._manageAccessMetadataCurrent = false;
    this._manageAccessRefreshError = undefined;
    this._detailsLoading = true;
    this._detailsError = undefined;
    this._nfcEnrollment = undefined;
    this._nfcEnrollmentLoading = true;
    this._nfcEnrollmentBusy = false;
    this._nfcEnrollmentError = undefined;
    this._nfcEnrollmentUrl = undefined;
    this._nfcEnrollmentQr = undefined;
    this._nfcEnrollmentExpiresAt = undefined;
    this._nfcEnrollmentSetupOpen = false;
    this._nfcEnrollmentOriginDraft = "";
    this._nfcEnrollmentConfiguring = false;
    this._nfcEnrollmentConfigurationError = undefined;
    this._nfcEnrollmentConfigurationNotice = undefined;
    this._nfcEnrollmentRequestGeneration += 1;
    this._nfcAccessSelection = new Set();
    this._nfcAccessSelectionInitialized = false;
    this._nfcAccessSaving = false;
    this._nfcAccessPoints = [];
    this._nukiFingerprintStatus = undefined;
    this._nukiFingerprintLoading = true;
    this._nukiFingerprintBusyDoorId = undefined;
    this._nukiFingerprintError = undefined;
    this._nukiFingerprintRequestGeneration += 1;
    this._personPolicyCurrentAccess = [];
    this._personPolicyTemporarilyUnavailable = [];
    this._personPolicyNoAccess = [];
    this._personSynchronizationHistory = [];
    this._personPolicyLoading = true;
    this._personPolicyError = undefined;
    this._personScheduleViewOpen = false;
    this._scheduleForm = undefined;
    this._scheduleOriginalForm = undefined;
    this._effectiveSchedule = undefined;
    this._scheduleGroups = [];
    this._scheduleGroupEditorOpen = false;
    this._scheduleCreatingGroup = false;
    this._scheduleSelectedAccessPointIds = new Set();
    this._scheduleOriginalAccessPointIds = [];
    this._scheduleActiveGroupId = undefined;
    this._scheduleStatus = undefined;
    this._scheduleExpectation = undefined;
    this._scheduleSaveError = undefined;
    this._render();
    void this._loadPersonPolicy(personId);
    void this._loadNfcEnrollment(personId);
    void this._loadNukiFingerprintStatus(personId);

    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_PERSON_ACTION,
        service_data: { person_id: personId },
        return_response: true,
      });
      if (this._detailsPersonId === personId) {
        this._selectedPerson = result.response?.person;
        this._accessMetadata = result.response?.access_metadata ?? [];
        this._personCredentialStored = result.response?.credential_stored === true ||
          this._accessMetadata.some((metadata) => metadata.credential_stored);
        this._manageAccessMetadataCurrent = true;
        this._manageAccessRefreshError = undefined;
        this._effectiveSchedule = result.response?.effective_schedule;
        this._scheduleGroups = Array.isArray(result.response?.schedule_groups)
          ? result.response.schedule_groups
          : [];
        this._scheduleStatus = result.response?.schedule_status;
      }
    } catch (_error) {
      if (this._detailsPersonId === personId) {
        this._detailsError = "HomePASS could not load this user. Try again.";
      }
    } finally {
      if (this._detailsPersonId === personId) {
        this._detailsLoading = false;
        this._initializeNfcAccessSelectionFromPinAccess();
        this._render();
      }
    }
  }

  _closePersonDetails() {
    this._resetPolicyInspectorState();
    this._resetSynchronizationRecovery();
    this._manageAccessOpenRequest = undefined;
    this._clearAccessUpdatePoll();
    this._clearCredentialReveal("person_changed");
    this._clearRevealCooldown();
    this._giveAccessDialogOpen = false;
    this._manageAccessDialogOpen = false;
    this._manageAccessSession = undefined;
    this._manageAccessDialogElement = undefined;
    this._resetChangePin();
    this._pin = undefined;
    this._provisionResult = undefined;
    this._deleteDialogOpen = false;
    this._deleteError = undefined;
    this._detailsPersonId = undefined;
    this._selectedPerson = undefined;
    this._personCredentialStored = false;
    this._accessMetadata = [];
    this._manageAccessMetadataCurrent = false;
    this._manageAccessRefreshError = undefined;
    this._detailsLoading = false;
    this._detailsError = undefined;
    this._nfcEnrollmentRequestGeneration += 1;
    this._nfcEnrollment = undefined;
    this._nfcEnrollmentLoading = false;
    this._nfcEnrollmentBusy = false;
    this._nfcEnrollmentError = undefined;
    this._nfcEnrollmentUrl = undefined;
    this._nfcEnrollmentQr = undefined;
    this._nfcEnrollmentExpiresAt = undefined;
    this._nfcEnrollmentSetupOpen = false;
    this._nfcEnrollmentOriginDraft = "";
    this._nfcEnrollmentConfiguring = false;
    this._nfcEnrollmentConfigurationError = undefined;
    this._nfcEnrollmentConfigurationNotice = undefined;
    this._nfcAccessSelection = new Set();
    this._nfcAccessSelectionInitialized = false;
    this._nfcAccessSaving = false;
    this._nfcAccessPoints = [];
    this._nukiFingerprintRequestGeneration += 1;
    this._nukiFingerprintStatus = undefined;
    this._nukiFingerprintLoading = false;
    this._nukiFingerprintBusyDoorId = undefined;
    this._nukiFingerprintError = undefined;
    this._personPolicyCurrentAccess = [];
    this._personPolicyTemporarilyUnavailable = [];
    this._personPolicyNoAccess = [];
    this._personSynchronizationHistory = [];
    this._personPolicyLoading = false;
    this._personPolicyError = undefined;
    this._personPolicyRequestGeneration += 1;
    this._accessUpdateNotice = undefined;
    this._personScheduleViewOpen = false;
    this._scheduleForm = undefined;
    this._scheduleOriginalForm = undefined;
    this._effectiveSchedule = undefined;
    this._scheduleGroups = [];
    this._scheduleGroupEditorOpen = false;
    this._scheduleCreatingGroup = false;
    this._scheduleSelectedAccessPointIds = new Set();
    this._scheduleOriginalAccessPointIds = [];
    this._scheduleActiveGroupId = undefined;
    this._scheduleStatus = undefined;
    this._scheduleExpectation = undefined;
    this._scheduleSaveError = undefined;
    if (this._currentPage === "dashboard") {
      this._dashboardAttentionLoading = true;
      this._dashboardActivityLoading = true;
      this._render();
      void this._loadPeople();
      void this._loadDashboardAttention();
      void this._loadDashboardActivity();
      return;
    }
    this._render();
    if (this._currentPage === "people") void this._loadPeople();
  }

  async _loadPersonPolicy(personId) {
    const generation = ++this._personPolicyRequestGeneration;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_PERSON_POLICY_DETAILS_ACTION,
        service_data: { person_id: personId },
        return_response: true,
      });
      if (!this._personPolicyRequestOwns(personId, generation)) return;
      const response = result.response ?? {};
      this._personPolicyCurrentAccess = Array.isArray(response.current_access)
        ? response.current_access
        : [];
      this._personPolicyTemporarilyUnavailable = Array.isArray(
        response.temporarily_unavailable,
      )
        ? response.temporarily_unavailable
        : [];
      this._personPolicyNoAccess = Array.isArray(response.no_access)
        ? response.no_access
        : [];
      this._personSynchronizationHistory = Array.isArray(response.synchronization_history)
        ? response.synchronization_history
        : [];
      if (!this._personSynchronizationHistory.every((event) => this._validHistoryEvent(event))) {
        throw new Error("Invalid Person Details history response");
      }
      if (
        ![
          ...this._personPolicyCurrentAccess,
          ...this._personPolicyTemporarilyUnavailable,
        ].every(
          (relationship) =>
            relationship.synchronization === undefined ||
            this._validSynchronizationPresentation(relationship.synchronization),
        )
      ) {
        throw new Error("Invalid Person Details synchronization response");
      }
      this._personPolicyError = undefined;
    } catch (_error) {
      if (!this._personPolicyRequestOwns(personId, generation)) return;
      this._personPolicyCurrentAccess = [];
      this._personPolicyTemporarilyUnavailable = [];
      this._personPolicyNoAccess = [];
      this._personSynchronizationHistory = [];
      this._personPolicyError =
        "Current access is unavailable right now. Close and reopen this user to try again.";
    } finally {
      if (this._personPolicyRequestOwns(personId, generation)) {
        this._personPolicyLoading = false;
        this._initializeNfcAccessSelectionFromPinAccess();
        this._render();
      }
    }
  }

  _personPolicyRequestOwns(personId, generation) {
    return (
      this._detailsPersonId === personId &&
      this._personPolicyRequestGeneration === generation
    );
  }

  _openDashboardPage() {
    this._clearQuickPinReveals();
    this._resetDoorControlDialogState();
    this._resetSynchronizationRecovery();
    this._currentPage = "dashboard";
    this._dashboardActivityFiltersOpen = false;
    this._dashboardAttentionLoading = true;
    this._cancelDashboardActivityRequest();
    this._dashboardActivityLoading = true;
    this._render();
    void this._loadPeople();
    void this._loadDashboardAttention();
    void this._loadDashboardActivity();
    void this._loadDashboardPropertySettings();
  }

  async _loadDashboardPropertySettings() {
    const generation = ++this._dashboardPropertyRequestGeneration;
    this._dashboardPropertyLoading = true;
    this._dashboardPropertyError = false;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_PROPERTY_SETTINGS_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._dashboardPropertyRequestOwns(generation)) return;
      if (!this._validPropertySettingsResponse(result.response)) {
        throw new Error("Invalid Property Settings response");
      }
      this._dashboardPropertyName = result.response.settings.property_name;
    } catch (_error) {
      if (!this._dashboardPropertyRequestOwns(generation)) return;
      this._dashboardPropertyName = "";
      this._dashboardPropertyError = true;
    } finally {
      if (this._dashboardPropertyRequestOwns(generation)) {
        this._dashboardPropertyLoading = false;
        this._render();
      }
    }
  }

  _dashboardPropertyRequestOwns(generation) {
    return (
      this._currentPage === "dashboard" &&
      this._dashboardPropertyRequestGeneration === generation
    );
  }

  _dashboardPropertyNameTemplate() {
    const name = this._dashboardPropertyName;
    if (!name) return "";
    return `<span class="dashboard-property-name" title="${escapeHtml(name)}" aria-label="Property: ${escapeHtml(name)}">${escapeHtml(name)}</span>`;
  }

  _openDoorsPage() {
    this._clearQuickPinReveals();
    this._resetDoorControlDialogState();
    this._resetSynchronizationRecovery();
    this._dashboardAttentionRequestGeneration += 1;
    this._cancelDashboardActivityRequest();
    this._dashboardActivityFiltersOpen = false;
    this._currentPage = "doors";
    this._dashboardDoorsLoading = true;
    this._accessDevicesLoading = Boolean(this._hass?.user?.is_admin);
    this._render();
    void this._loadDoorsAndDevices();
  }

  async _loadDoorsAndDevices() {
    await Promise.all([
      this._loadDashboardAccessPoints({ render: false }),
      this._hass?.user?.is_admin
        ? this._loadAccessDevices({ render: false })
        : Promise.resolve(),
    ]);
    this._render();
  }

  async _openDoorFromPerson(accessPointId) {
    if (!accessPointId) return;
    let accessPoint = this._dashboardAccessPoints.find(
      (door) => door.id === accessPointId,
    );
    if (!accessPoint) {
      try {
        const result = await this._hass.callWS({
          type: "call_service",
          domain: DOMAIN,
          service: LIST_ACCESS_POINTS_ACTION,
          service_data: {},
          return_response: true,
        });
        this._dashboardAccessPoints = result.response?.access_points ?? [];
        accessPoint = this._dashboardAccessPoints.find(
          (door) => door.id === accessPointId,
        );
      } catch (_error) {
        this._detailsError = "HomePASS could not open this Door. Try again.";
        this._render();
        return;
      }
    }
    if (!accessPoint) {
      this._detailsError = "This Door is no longer available in HomePASS.";
      this._render();
      return;
    }
    this._currentPage = "doors";
    this._closePersonDetails();
    this._openDoorControlDialog(accessPoint);
  }

  _openPeoplePage() {
    this._resetDoorControlDialogState();
    this._resetSynchronizationRecovery();
    this._dashboardAttentionRequestGeneration += 1;
    this._cancelDashboardActivityRequest();
    this._dashboardActivityFiltersOpen = false;
    this._currentPage = "people";
    this._render();
    void this._loadPeople();
  }

  _openActivityPage() {
    this._clearQuickPinReveals();
    this._resetDoorControlDialogState();
    this._resetSynchronizationRecovery();
    this._dashboardAttentionRequestGeneration += 1;
    this._cancelDashboardActivityRequest();
    this._dashboardActivityFiltersOpen = false;
    this._currentPage = "activity";
    this._dashboardActivityLoading = true;
    this._render();
    void this._loadDashboardActivity();
  }

  _openSettingsPage() {
    this._clearQuickPinReveals();
    this._resetDoorControlDialogState();
    this._resetSynchronizationRecovery();
    this._dashboardAttentionRequestGeneration += 1;
    this._cancelDashboardActivityRequest();
    this._dashboardActivityFiltersOpen = false;
    this._currentPage = "settings";
    this._settingsData = undefined;
    this._settingsLoading = true;
    this._settingsSaving = false;
    this._settingsError = undefined;
    this._settingsNotice = undefined;
    this._nukiStorageLoading = false;
    this._nukiStorageError = undefined;
    this._nukiStorageStatus = undefined;
    this._propertySettingsLoading = true;
    this._propertySettingsError = undefined;
    this._propertySettingsNotice = undefined;
    this._render();
    void this._loadNotificationSettings();
    void this._loadPropertySettings();
  }

  async _checkNukiStorage() {
    if (this._nukiStorageLoading || !this._hass?.user?.is_admin) return;
    this._nukiStorageLoading = true;
    this._nukiStorageError = undefined;
    this._render();
    let timeoutId;
    try {
      const result = await Promise.race([
        this._hass.callWS({
          type: "call_service",
          domain: DOMAIN,
          service: GET_NUKI_STORAGE_STATUS_ACTION,
          service_data: {},
          return_response: true,
        }),
        new Promise((_, reject) => {
          timeoutId = window.setTimeout(
            () => reject(new Error(
              "The Nuki keypad check timed out. Close the Nuki app, keep the lock within Bluetooth range, and try again.",
            )),
            NUKI_STORAGE_REQUEST_TIMEOUT,
          );
        }),
      ]);
      if (!this._validNukiStorageStatus(result.response)) {
        throw new Error("Invalid Nuki storage response");
      }
      this._nukiStorageStatus = result.response;
    } catch (error) {
      this._nukiStorageError = error?.message ||
        "HomePASS could not read the Nuki keypad. Keep the lock within Bluetooth range and try again.";
    } finally {
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      this._nukiStorageLoading = false;
      this._render();
    }
  }

  _validNukiStorageStatus(value) {
    return Boolean(
      value &&
      typeof value.configured === "boolean" &&
      value.pins &&
      Number.isInteger(value.pins.total) &&
      Number.isInteger(value.pins.managed) &&
      Number.isInteger(value.pins.existing) &&
      Array.isArray(value.pins.entries) &&
      value.fingerprints &&
      Number.isInteger(value.fingerprints.linked_count) &&
      Array.isArray(value.fingerprints.entries),
    );
  }

  _openAboutPage() {
    this._clearQuickPinReveals();
    this._resetDoorControlDialogState();
    this._resetSynchronizationRecovery();
    this._dashboardAttentionRequestGeneration += 1;
    this._cancelDashboardActivityRequest();
    this._dashboardActivityFiltersOpen = false;
    this._currentPage = "about";
    this._aboutData = undefined;
    this._aboutLoading = true;
    this._aboutError = undefined;
    this._render();
    void this._loadAbout();
  }

  async _loadAbout() {
    const generation = ++this._aboutRequestGeneration;
    this._aboutLoading = true;
    this._aboutError = undefined;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_ABOUT_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._aboutRequestOwns(generation)) return;
      if (!this._validAboutResponse(result.response)) {
        throw new Error("Invalid About response");
      }
      this._aboutData = result.response;
    } catch (_error) {
      if (!this._aboutRequestOwns(generation)) return;
      this._aboutData = undefined;
      this._aboutError = "HomePASS could not load About information.";
    } finally {
      if (this._aboutRequestOwns(generation)) {
        this._aboutLoading = false;
        this._render();
      }
    }
  }

  _aboutRequestOwns(generation) {
    return this._currentPage === "about" && this._aboutRequestGeneration === generation;
  }

  _validAboutResponse(data) {
    return Boolean(
      data &&
      data.product_name === "HomePASS" &&
      typeof data.tagline === "string" &&
      typeof data.version === "string" &&
      typeof data.property_name === "string" &&
      typeof data.home_assistant_version === "string" &&
      Number.isInteger(data.database_schema_version) &&
      typeof data.created_by === "string" &&
      typeof data.copyright === "string" &&
      (data.git_commit === null ||
        (typeof data.git_commit === "string" && /^[0-9a-f]{8}$/.test(data.git_commit))),
    );
  }

  async _loadPropertySettings() {
    const generation = ++this._propertySettingsRequestGeneration;
    this._propertySettingsLoading = true;
    this._propertySettingsSaving = false;
    this._propertySettingsError = undefined;
    this._propertySettingsNotice = undefined;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_PROPERTY_SETTINGS_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._propertySettingsRequestOwns(generation)) return;
      if (!this._validPropertySettingsResponse(result.response)) {
        throw new Error("Invalid Property Settings response");
      }
      this._propertySettingsData = result.response.settings;
      this._propertyName = result.response.settings.property_name;
      this._savedPropertyName = result.response.settings.property_name;
    } catch (_error) {
      if (!this._propertySettingsRequestOwns(generation)) return;
      this._propertySettingsData = undefined;
      this._propertySettingsError = "HomePASS could not load Property Settings.";
    } finally {
      if (this._propertySettingsRequestOwns(generation)) {
        this._propertySettingsLoading = false;
        this._render();
      }
    }
  }

  _propertySettingsRequestOwns(generation) {
    return (
      this._currentPage === "settings" &&
      this._propertySettingsRequestGeneration === generation
    );
  }

  _validPropertySettingsResponse(data) {
    return Boolean(
      data &&
      data.error === null &&
      data.settings &&
      typeof data.settings.property_name === "string",
    );
  }

  _normalizedPropertyName() {
    return String(this._propertyName ?? "").trim();
  }

  _propertyNameValidationMessage() {
    const value = String(this._propertyName ?? "");
    if (/[\u0000-\u001f\u007f-\u009f]/u.test(value)) {
      return "Property Name cannot contain control characters.";
    }
    if ([...value.trim()].length > MAX_PROPERTY_NAME_LENGTH) {
      return `Property Name must be ${MAX_PROPERTY_NAME_LENGTH} characters or fewer.`;
    }
    return undefined;
  }

  _propertySettingsCanSave() {
    return Boolean(
      this._propertySettingsData &&
      !this._propertySettingsSaving &&
      !this._propertyNameValidationMessage() &&
      this._normalizedPropertyName() !== this._savedPropertyName,
    );
  }

  _handlePropertyNameInput(event) {
    this._propertyName = event.target.value ?? "";
    this._propertySettingsError = undefined;
    this._propertySettingsNotice = undefined;
    this._syncPropertySettingsControls();
  }

  _syncPropertySettingsControls() {
    const input = this.shadowRoot.querySelector("#property-name");
    const error = this.shadowRoot.querySelector("#property-name-error");
    const save = this.shadowRoot.querySelector("#save-property-settings");
    const message = this._propertyNameValidationMessage();
    if (input) input.setAttribute("aria-invalid", String(Boolean(message)));
    if (error) {
      error.textContent = message ?? "";
      error.hidden = !message;
    }
    if (save) save.disabled = !this._propertySettingsCanSave();
  }

  async _savePropertySettings() {
    if (!this._propertySettingsCanSave()) return;
    const generation = ++this._propertySettingsRequestGeneration;
    this._propertySettingsSaving = true;
    this._propertySettingsError = undefined;
    this._propertySettingsNotice = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: SAVE_PROPERTY_SETTINGS_ACTION,
        service_data: {settings: {property_name: this._propertyName}},
        return_response: true,
      });
      if (!this._propertySettingsRequestOwns(generation)) return;
      const response = result.response;
      if (response && response.error) {
        const message = response.error.message;
        this._propertySettingsError =
          typeof message === "string" ? message : "Property Settings could not be saved.";
        return;
      }
      if (!this._validPropertySettingsResponse(response)) {
        throw new Error("Invalid Property Settings response");
      }
      this._propertySettingsData = response.settings;
      this._propertyName = response.settings.property_name;
      this._savedPropertyName = response.settings.property_name;
      this._dashboardPropertyName = response.settings.property_name;
      this._propertySettingsNotice = "Property Settings saved.";
    } catch (_error) {
      if (!this._propertySettingsRequestOwns(generation)) return;
      this._propertySettingsError = "HomePASS could not save Property Settings. Try again.";
    } finally {
      if (this._propertySettingsRequestOwns(generation)) {
        this._propertySettingsSaving = false;
        this._render();
      }
    }
  }

  async _loadNotificationSettings() {
    const generation = ++this._settingsRequestGeneration;
    this._settingsData = undefined;
    this._settingsLoading = true;
    this._settingsSaving = false;
    this._settingsError = undefined;
    this._settingsNotice = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_NOTIFICATION_PREFERENCES_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._settingsRequestOwns(generation)) return;
      if (!this._validNotificationSettings(result.response)) {
        throw new Error("Invalid notification settings response");
      }
      this._settingsData = result.response;
    } catch (_error) {
      if (!this._settingsRequestOwns(generation)) return;
      this._settingsData = undefined;
      this._settingsError = "HomePASS could not load notification settings.";
    } finally {
      if (this._settingsRequestOwns(generation)) {
        this._settingsLoading = false;
        this._render();
      }
    }
  }

  _settingsRequestOwns(generation) {
    return this._currentPage === "settings" && this._settingsRequestGeneration === generation;
  }

  _validNotificationSettings(data) {
    return Boolean(
      data &&
      data.preferences &&
      typeof data.preferences.enabled === "boolean" &&
      Array.isArray(data.preferences.selected_device_ids) &&
      data.preferences.events &&
      Array.isArray(data.devices) &&
      data.devices.every(
        (device) =>
          typeof device.id === "string" &&
          typeof device.display_name === "string" &&
          typeof device.selected === "boolean" &&
          typeof device.available === "boolean",
      ) &&
      Array.isArray(data.definitions) &&
      data.definitions.every(
        (definition) =>
          typeof definition.id === "string" &&
          typeof definition.category === "string" &&
          typeof definition.category_title === "string" &&
          typeof definition.title === "string" &&
          typeof definition.default_enabled === "boolean" &&
          typeof definition.supported === "boolean",
      ) &&
      data.event_support,
    );
  }

  async _saveNotificationSettings() {
    if (!this._settingsData || this._settingsSaving) return;
    const generation = ++this._settingsRequestGeneration;
    const enabled = this.shadowRoot.querySelector("#notifications-enabled").checked;
    const selectedDeviceIds = new Set(this._settingsData.preferences.selected_device_ids);
    for (const input of this.shadowRoot.querySelectorAll("[data-notification-device]")) {
      if (input.checked) selectedDeviceIds.add(input.value);
      else selectedDeviceIds.delete(input.value);
    }
    const events = { ...this._settingsData.preferences.events };
    for (const input of this.shadowRoot.querySelectorAll("[data-notification-event]")) {
      if (!input.disabled) events[input.value] = input.checked;
    }
    this._settingsSaving = true;
    this._settingsError = undefined;
    this._settingsNotice = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: SAVE_NOTIFICATION_PREFERENCES_ACTION,
        service_data: {
          preferences: {
            enabled,
            selected_device_ids: [...selectedDeviceIds].sort(),
            events,
          },
        },
        return_response: true,
      });
      if (!this._settingsRequestOwns(generation)) return;
      if (!this._validNotificationSettings(result.response)) {
        throw new Error("Invalid notification settings response");
      }
      this._settingsData = result.response;
      this._settingsNotice = "Notification preferences saved.";
    } catch (_error) {
      if (!this._settingsRequestOwns(generation)) return;
      this._settingsError = "HomePASS could not save notification settings. Try again.";
    } finally {
      if (this._settingsRequestOwns(generation)) {
        this._settingsSaving = false;
        this._render();
      }
    }
  }

  _openDashboardFromPersonDetails() {
    this._currentPage = "dashboard";
    this._closePersonDetails();
    void this._loadDashboardPropertySettings();
  }

  _openUsersFromPersonDetails() {
    this._currentPage = "people";
    this._closePersonDetails();
  }

  _openDoorControlDialog(door, returnFocusSelector = undefined) {
    if (this._doorControlDialogOpen && this._selectedDoorId === door.id) return;
    const commandPending = this._doorOperationCommandIsPending();
    this._resetPolicyInspectorState();
    this._resetSynchronizationRecovery();
    if (!commandPending) {
      this._resetDoorOperation();
    }
    this._selectedDoorId = door.id;
    this._selectedDoor = this._doorWithHassState(door, this._hass);
    this._doorControlLoading = true;
    this._doorControlError = undefined;
    this._doorPolicyLoading = true;
    this._doorPolicyError = undefined;
    this._doorCurrentAccess = [];
    this._doorTemporarilyUnavailable = [];
    this._doorNoAccess = [];
    this._doorSynchronizationHistory = [];
    this._editingDoorName = false;
    this._doorNameDraft = "";
    this._renamingDoor = false;
    this._doorRenameError = undefined;
    this._doorRenameNotice = undefined;
    this._doorSensorEditOpen = false;
    this._doorSensorEntityId = "";
    this._doorSensorInverted = false;
    this._doorSensorSaving = false;
    this._doorSensorError = undefined;
    this._doorSensorNotice = undefined;
    this._doorNfcSetupOpen = false;
    this._doorNfcTags = [];
    this._doorNfcTagsLoading = true;
    this._doorNfcTagsError = undefined;
    this._doorNfcTagRevoking = undefined;
    this._doorNfcTagProtecting = undefined;
    this._doorNfcProtectionResult = undefined;
    this._removeDoorError = undefined;
    this._removeDoorConfirmationOpen = false;
    this._doorControlReturnFocusSelector = returnFocusSelector;
    this._doorControlDialogOpen = true;
    this._render();
    this._startDoorRelativeTimeTimer();
    void Promise.all([
      this._loadDoorStatus(door.id, {render: false}),
      this._loadDoorPolicy(door.id, {render: false}),
      this._loadDoorNfcTags(door.id, {render: false}),
    ]).finally(() => {
      if (this._doorControlDialogOpen && this._selectedDoorId === door.id) {
        this._render();
      }
    });
  }

  _closeDoorControlDialog() {
    if (this._removingDoor) return;
    const returnFocusSelector = this._doorControlReturnFocusSelector;
    this._resetDoorControlDialogState();
    this._render();
    if (returnFocusSelector) {
      this.shadowRoot.querySelector(returnFocusSelector)?.focus();
    }
  }

  _openPersonFromDoor(personId) {
    if (typeof personId !== "string" || !personId.trim()) return;
    this._resetDoorControlDialogState();
    this._currentPage = "people";
    void this._openPersonDetails(personId);
  }

  _resetDoorControlDialogState() {
    this._resetPolicyInspectorState();
    this._resetSynchronizationRecovery();
    this._stopDoorRelativeTimeTimer();
    if (!this._doorOperationCommandIsPending()) {
      this._resetDoorOperation();
    }
    this._doorControlDialogElement = undefined;
    this._removeDoorConfirmationDialogElement = undefined;
    this._doorControlDialogOpen = false;
    this._removeDoorConfirmationOpen = false;
    this._doorControlLoading = false;
    this._doorControlError = undefined;
    this._doorStatusRequestGeneration += 1;
    this._doorPolicyRequestGeneration += 1;
    this._doorPolicyLoading = false;
    this._doorPolicyError = undefined;
    this._doorCurrentAccess = [];
    this._doorTemporarilyUnavailable = [];
    this._doorNoAccess = [];
    this._doorSynchronizationHistory = [];
    this._selectedDoorId = undefined;
    this._selectedDoor = undefined;
    this._editingDoorName = false;
    this._doorNameDraft = "";
    this._renamingDoor = false;
    this._doorRenameError = undefined;
    this._doorRenameNotice = undefined;
    this._doorSensorEditOpen = false;
    this._doorSensorEntityId = "";
    this._doorSensorInverted = false;
    this._doorSensorSaving = false;
    this._doorSensorError = undefined;
    this._doorSensorNotice = undefined;
    this._doorNfcSetupOpen = false;
    this._doorNfcTags = [];
    this._doorNfcTagsLoading = false;
    this._doorNfcTagsError = undefined;
    this._doorNfcTagRevoking = undefined;
    this._removeDoorError = undefined;
    this._doorControlReturnFocusSelector = undefined;
  }

  async _loadDoorStatus(accessPointId, {render = true} = {}) {
    const generation = ++this._doorStatusRequestGeneration;
    this._doorControlLoading = true;
    this._doorControlError = undefined;
    if (render) this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_ACCESS_POINTS_ACTION,
        service_data: {},
        return_response: true,
      });
      const accessPoints = result?.response?.access_points;
      const door = Array.isArray(accessPoints)
        ? accessPoints.find((item) => item?.id === accessPointId)
        : undefined;
      if (!door || typeof door.display_name !== "string") {
        throw new Error("Invalid Door status response");
      }
      if (!this._doorStatusRequestOwns(generation, accessPointId)) return;
      this._selectedDoor = this._doorWithHassState(door, this._hass);
      this._dashboardAccessPoints = this._dashboardAccessPoints.map((item) =>
        item.id === accessPointId ? this._selectedDoor : item,
      );
      this._reconcileDoorOperationFromLiveState();
    } catch (_error) {
      if (!this._doorStatusRequestOwns(generation, accessPointId)) return;
      this._doorControlError = "unavailable";
      if (!this._doorOperationCommandIsPending()) {
        this._resetDoorOperation();
      }
    } finally {
      if (!this._doorStatusRequestOwns(generation, accessPointId)) return;
      this._doorControlLoading = false;
      if (render && !this._doorNfcSetupOpen) this._render();
    }
  }

  _doorStatusRequestOwns(generation, accessPointId) {
    return Boolean(
      this._doorControlDialogOpen &&
      this._selectedDoorId === accessPointId &&
      this._doorStatusRequestGeneration === generation
    );
  }

  async _loadDoorPolicy(accessPointId, {render = true} = {}) {
    const generation = ++this._doorPolicyRequestGeneration;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_DOOR_DETAILS_ACTION,
        service_data: { access_point_id: accessPointId },
        return_response: true,
      });
      const response = result?.response;
      if (
        !response ||
        !Array.isArray(response.current_access) ||
        !Array.isArray(response.temporarily_unavailable) ||
        !Array.isArray(response.no_access) ||
        !Array.isArray(response.synchronization_history)
      ) {
        throw new Error("Invalid Door Details response");
      }
      const validPerson = (person, explanationRequired) =>
        person &&
        typeof person.person_id === "string" &&
        typeof person.display_name === "string" &&
        (!explanationRequired || typeof person.explanation === "string") &&
        (person.synchronization === undefined ||
          this._validSynchronizationPresentation(person.synchronization));
      if (
        !response.current_access.every((person) => validPerson(person, false)) ||
        !response.temporarily_unavailable.every(
          (person) =>
            validPerson(person, true) && ["warning", "error"].includes(person.severity),
        ) ||
        !response.no_access.every((person) => validPerson(person, true))
      ) {
        throw new Error("Invalid Door Details response");
      }
      if (!this._doorPolicyRequestOwns(generation, accessPointId)) return;
      this._doorCurrentAccess = response.current_access;
      this._doorTemporarilyUnavailable = response.temporarily_unavailable;
      this._doorNoAccess = response.no_access;
      if (!response.synchronization_history.every((event) => this._validHistoryEvent(event))) {
        throw new Error("Invalid Door Details history response");
      }
      this._doorSynchronizationHistory = response.synchronization_history;
    } catch (_error) {
      if (!this._doorPolicyRequestOwns(generation, accessPointId)) return;
      this._doorPolicyError =
        "Current access could not be loaded. Close and reopen this door to try again.";
    } finally {
      if (!this._doorPolicyRequestOwns(generation, accessPointId)) return;
      this._doorPolicyLoading = false;
      if (render && !this._doorNfcSetupOpen) this._render();
    }
  }

  _doorPolicyRequestOwns(generation, accessPointId) {
    return Boolean(
      this._doorControlDialogOpen &&
      this._selectedDoorId === accessPointId &&
      this._doorPolicyRequestGeneration === generation
    );
  }

  _startDoorNameEdit() {
    if (!this._hass?.user?.is_admin || this._renamingDoor || this._doorNfcSetupOpen) return;
    this._editingDoorName = true;
    this._doorNameDraft = this._selectedDoor?.display_name ?? "";
    this._doorRenameError = undefined;
    this._doorRenameNotice = undefined;
    this._render();
    requestAnimationFrame(() => {
      const input = this.shadowRoot.querySelector("#door-title-name-input");
      input?.focus();
      input?.select();
    });
  }

  _cancelDoorNameEdit() {
    if (this._renamingDoor) return;
    this._editingDoorName = false;
    this._doorNameDraft = "";
    this._doorRenameError = undefined;
    this._render();
    requestAnimationFrame(() => this.shadowRoot.querySelector("#edit-door-name")?.focus());
  }

  _openDoorNfcSetup() {
    if (!this._hass?.user?.is_admin || !this._selectedDoorId) return;
    this._editingDoorName = false;
    this._doorRenameError = undefined;
    this._doorNfcOriginDraft = "";
    this._doorNfcConfiguring = false;
    this._doorNfcConfigurationError = undefined;
    this._doorNfcConfigurationNotice = undefined;
    this._doorNfcSetupOpen = true;
    this._render();
  }

  _closeDoorNfcSetup() {
    this._doorNfcSetupOpen = false;
    this._doorNfcOriginDraft = "";
    this._doorNfcConfiguring = false;
    this._doorNfcConfigurationError = undefined;
    this._doorNfcConfigurationNotice = undefined;
    this._render();
    requestAnimationFrame(() => this.shadowRoot.querySelector("#open-door-nfc-setup")?.focus());
  }

  async _configureDoorNfc() {
    if (this._doorNfcConfiguring || !this._hass?.user?.is_admin) return;
    const publicOrigin = this._doorNfcOriginDraft.trim();
    let parsed;
    try {
      parsed = new URL(publicOrigin);
    } catch (_error) {
      parsed = undefined;
    }
    if (
      !parsed ||
      parsed.protocol !== "https:" ||
      !parsed.hostname ||
      !["", "/"].includes(parsed.pathname) ||
      parsed.search ||
      parsed.hash ||
      parsed.username ||
      parsed.password
    ) {
      this._doorNfcConfigurationError =
        "Enter the Nabu Casa HTTPS address without a path, query, or sign-in details.";
      this._doorNfcConfigurationNotice = undefined;
      this._render();
      return;
    }
    this._doorNfcConfiguring = true;
    this._doorNfcConfigurationError = undefined;
    this._doorNfcConfigurationNotice = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CONFIGURE_NFC_ACTION,
        service_data: { nfc_public_origin: publicOrigin },
        return_response: true,
      });
      this._doorNfcConfigurationNotice = "Address saved. HomePASS is enabling NFC…";
      this._render();
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline) {
        if (this._hass?.services?.[DOMAIN]?.[LIST_NFC_TAGS_ACTION]) {
          this._doorNfcConfigurationNotice = undefined;
          return;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 500));
      }
      this._doorNfcConfigurationNotice =
        "The address is saved. HomePASS is still restarting NFC; close and reopen this Door in a moment.";
    } catch (_error) {
      this._doorNfcConfigurationError =
        "HomePASS could not save this address. Check it and try again.";
      this._doorNfcConfigurationNotice = undefined;
    } finally {
      this._doorNfcConfiguring = false;
      if (this._doorControlDialogOpen && this._doorNfcSetupOpen) this._render();
    }
  }

  async _loadDoorNfcTags(accessPointId = this._selectedDoorId, {render = true} = {}) {
    if (!accessPointId || !this._hass?.user?.is_admin) return;
    const nfcTagServiceAvailable = Boolean(
      this._hass?.services?.[DOMAIN]?.[LIST_NFC_TAGS_ACTION],
    );
    if (!nfcTagServiceAvailable) {
      this._doorNfcTags = [];
      this._doorNfcTagsLoading = false;
      this._doorNfcTagsError = undefined;
      if (render && !this._doorNfcSetupOpen) this._render();
      return;
    }
    this._doorNfcTagsLoading = true;
    this._doorNfcTagsError = undefined;
    if (render && !this._doorNfcSetupOpen) this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_NFC_TAGS_ACTION,
        service_data: { access_point_id: accessPointId },
        return_response: true,
      });
      if (!this._doorControlDialogOpen || this._selectedDoorId !== accessPointId) return;
      this._doorNfcTags = Array.isArray(result.response?.tags)
        ? result.response.tags
        : [];
    } catch (_error) {
      if (!this._doorControlDialogOpen || this._selectedDoorId !== accessPointId) return;
      this._doorNfcTagsError = "HomePASS could not load the NFC tags for this Door.";
    } finally {
      if (this._doorControlDialogOpen && this._selectedDoorId === accessPointId) {
        this._doorNfcTagsLoading = false;
        if (render && !this._doorNfcSetupOpen) this._render();
      }
    }
  }

  async _revokeDoorNfcTag(publicId, uidHex) {
    if (!this._selectedDoorId || this._doorNfcTagRevoking) return;
    if (!window.confirm(
      `Temporarily disable NFC tag ${uidHex}? It will stop unlocking this Door until it is reinstated.`,
    )) return;
    this._doorNfcTagRevoking = publicId;
    this._doorNfcTagsError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: REVOKE_NFC_TAG_ACTION,
        service_data: {
          access_point_id: this._selectedDoorId,
          public_id: publicId,
        },
        return_response: true,
      });
      await Promise.all([
        this._loadDoorNfcTags(this._selectedDoorId, {render: false}),
        this._loadDoorStatus(this._selectedDoorId, {render: false}),
      ]);
    } catch (_error) {
      this._doorNfcTagsError = "HomePASS could not temporarily disable this NFC tag.";
    } finally {
      this._doorNfcTagRevoking = undefined;
      if (this._doorControlDialogOpen && !this._doorNfcSetupOpen) this._render();
    }
  }

  async _reinstateDoorNfcTag(publicId, uidHex) {
    if (!this._selectedDoorId || this._doorNfcTagRevoking) return;
    if (!window.confirm(
      `Reinstate NFC tag ${uidHex}? Authorized users will be able to use it at this Door again.`,
    )) return;
    await this._changeDoorNfcTagRegistration(
      publicId,
      REINSTATE_NFC_TAG_ACTION,
      "HomePASS could not reinstate this NFC tag.",
    );
  }

  async _deleteDoorNfcTag(publicId, uidHex) {
    if (!this._selectedDoorId || this._doorNfcTagRevoking) return;
    if (!window.confirm(
      `Permanently delete NFC tag ${uidHex} from HomePASS? This cannot be undone. The physical tag will need to be provisioned again before it can be used.`,
    )) return;
    await this._changeDoorNfcTagRegistration(
      publicId,
      DELETE_NFC_TAG_ACTION,
      "HomePASS could not delete this NFC tag.",
    );
  }

  async _prepareDoorNfcTagProtection(publicId, uidHex) {
    if (!this._selectedDoorId || this._doorNfcTagProtecting) return;
    this._doorNfcTagProtecting = publicId;
    this._doorNfcTagsError = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: PREPARE_NFC_TAG_PROTECTION_ACTION,
        service_data: {access_point_id: this._selectedDoorId, public_id: publicId},
        return_response: true,
      });
      const response = result?.response;
      if (
        !response?.ndef_url_template ||
        !response?.admin_key ||
        !response?.meta_read_key ||
        !response?.file_read_key
      ) {
        throw new Error("HomePASS returned an incomplete protection package.");
      }
      const doorName = this._selectedDoor?.display_name || "Door";
      const blob = buildGoToTagsNtag424OperationBlob(
        response,
        true,
        `HomePASS – ${doorName} protection`,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `homepass-protect-${uidHex.toLowerCase()}.gototags`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1_000);
      this._doorNfcProtectionResult = {publicId, uidHex};
    } catch (error) {
      this._doorNfcTagsError = error?.message ||
        "HomePASS could not prepare rewrite protection for this NFC tag.";
    } finally {
      this._doorNfcTagProtecting = undefined;
      this._render();
    }
  }

  async _confirmDoorNfcTagProtection(publicId) {
    if (!this._selectedDoorId || this._doorNfcTagProtecting) return;
    if (!window.confirm(
      "GoToTags must show green VERIFIED, one completed tag, and zero errors. Clicking OK only records that successful protection in HomePASS; it does not write to the tag again. Continue?",
    )) return;
    this._doorNfcTagProtecting = publicId;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CONFIRM_NFC_TAG_PROTECTION_ACTION,
        service_data: {access_point_id: this._selectedDoorId, public_id: publicId},
        return_response: true,
      });
      this._doorNfcProtectionResult = undefined;
      await this._loadDoorNfcTags(this._selectedDoorId, {render: false});
    } catch (error) {
      this._doorNfcTagsError = error?.message ||
        "HomePASS could not confirm rewrite protection for this NFC tag.";
    } finally {
      this._doorNfcTagProtecting = undefined;
      this._render();
    }
  }

  async _changeDoorNfcTagRegistration(publicId, service, failureMessage) {
    this._doorNfcTagRevoking = publicId;
    this._doorNfcTagsError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service,
        service_data: {
          access_point_id: this._selectedDoorId,
          public_id: publicId,
        },
        return_response: true,
      });
      await Promise.all([
        this._loadDoorNfcTags(this._selectedDoorId, {render: false}),
        this._loadDoorStatus(this._selectedDoorId, {render: false}),
      ]);
    } catch (_error) {
      this._doorNfcTagsError = failureMessage;
    } finally {
      this._doorNfcTagRevoking = undefined;
      if (this._doorControlDialogOpen && !this._doorNfcSetupOpen) this._render();
    }
  }

  _doorNfcTagsMarkup() {
    if (this._doorNfcTagsLoading) {
      return '<p role="status">Loading registered NFC tags…</p>';
    }
    if (this._doorNfcTagsError) {
      return `<p class="form-error" role="alert">${escapeHtml(this._doorNfcTagsError)}</p>`;
    }
    if (this._doorNfcTags.length === 0) {
      return '<p>No NTAG424 tags are registered to this Door.</p>';
    }
    return `<div class="door-nfc-tag-list">${this._doorNfcTags.map((tag) => `
      <div class="door-nfc-tag-item">
        <div class="door-nfc-tag-heading">
          <strong class="door-nfc-tag-uid">UID ${escapeHtml(tag.uid_hex)}</strong>
          <span class="door-nfc-tag-status ${tag.enabled ? "" : "revoked"}">${tag.enabled ? "Active" : "Temporarily disabled"}</span>
        </div>
        <span class="door-nfc-tag-meta">${tag.write_protected ? "Rewrite protected" : tag.protection_prepared ? "Protection prepared; not yet verified" : "Rewriting not protected"} · Registered ${escapeHtml(new Date(tag.created_at).toLocaleString())}${tag.last_counter == null ? "" : ` · Last tap counter ${Number(tag.last_counter)}`}</span>
        <div class="door-nfc-tag-actions">
          ${tag.write_protected || this._doorNfcProtectionResult?.publicId === tag.public_id ? "" : `<ha-button data-protect-nfc-tag="${escapeHtml(tag.public_id)}" data-nfc-tag-uid="${escapeHtml(tag.uid_hex)}" appearance="plain" ${this._doorNfcTagProtecting ? "disabled" : ""}>${this._doorNfcTagProtecting === tag.public_id ? "Preparing…" : tag.protection_prepared ? "Download protection file again" : "Protect rewriting"}</ha-button>`}
          ${tag.enabled
            ? `<ha-button data-revoke-nfc-tag="${escapeHtml(tag.public_id)}" data-nfc-tag-uid="${escapeHtml(tag.uid_hex)}" appearance="plain" ${this._doorNfcTagRevoking ? "disabled" : ""}>${this._doorNfcTagRevoking === tag.public_id ? "Disabling…" : "Temporarily disable"}</ha-button>`
            : `<ha-button data-reinstate-nfc-tag="${escapeHtml(tag.public_id)}" data-nfc-tag-uid="${escapeHtml(tag.uid_hex)}" appearance="plain" ${this._doorNfcTagRevoking ? "disabled" : ""}>${this._doorNfcTagRevoking === tag.public_id ? "Reinstating…" : "Reinstate"}</ha-button>`}
          <ha-button data-delete-nfc-tag="${escapeHtml(tag.public_id)}" data-nfc-tag-uid="${escapeHtml(tag.uid_hex)}" class="subtle-destructive-action" appearance="plain" ${this._doorNfcTagRevoking ? "disabled" : ""}>Delete permanently</ha-button>
        </div>
        ${this._doorNfcProtectionResult?.publicId === tag.public_id ? `<div class="door-nfc-protection-help"><strong>Ready-to-write protection file downloaded for UID ${escapeHtml(tag.uid_hex)}.</strong><ol><li>Double-click the downloaded <strong>.gototags</strong> file. GoToTags opens with one preconfigured row.</li><li>Confirm the row shows <strong>READY</strong> and <strong>Lock FALSE</strong>.</li><li>Keep the tag off the reader, press the upper Play button, wait for <strong>RUNNING</strong>, then place only UID <code>${escapeHtml(tag.uid_hex)}</code> flat on the reader.</li><li>Do not move it until GoToTags shows green <strong>VERIFIED</strong>, one completed tag, and zero errors. Do not enable permanent locking.</li><li>Remove it and confirm a phone tap still opens and unlocks this Door.</li></ol><p>When those checks pass, record the result in HomePASS. This button does not write to the tag again.</p><ha-button data-confirm-protected-nfc-tag="${escapeHtml(tag.public_id)}" appearance="filled">Record tag as protected</ha-button></div>` : ""}
      </div>`).join("")}</div>`;
  }

  async _saveDoorName() {
    if (!this._hass?.user?.is_admin || this._renamingDoor || !this._selectedDoorId) return;
    const input = this.shadowRoot.querySelector("#door-title-name-input");
    const displayName = input?.value?.trim() ?? "";
    this._doorNameDraft = displayName;
    this._doorRenameError = undefined;
    this._doorRenameNotice = undefined;
    if (!displayName) {
      this._doorRenameError = "Enter a name for this door.";
      this._render();
      return;
    }
    if (displayName.length > 80) {
      this._doorRenameError = "Door names must be 80 characters or fewer.";
      this._render();
      return;
    }
    if (displayName === this._selectedDoor?.display_name) {
      this._editingDoorName = false;
      this._doorNameDraft = "";
      this._doorRenameNotice = "Door name unchanged.";
      this._render();
      return;
    }

    this._renamingDoor = true;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: UPDATE_ACCESS_POINT_ACTION,
        service_data: {
          access_point_id: this._selectedDoorId,
          display_name: displayName,
        },
        return_response: true,
      });
      const updated = result?.response?.access_point;
      if (!updated || updated.id !== this._selectedDoorId ||
          typeof updated.display_name !== "string") {
        throw new Error("HomePASS returned an invalid Door response.");
      }
      this._selectedDoor = this._doorWithHassState(
        {...this._selectedDoor, ...updated},
        this._hass,
      );
      this._dashboardAccessPoints = this._dashboardAccessPoints.map((item) =>
        item.id === updated.id ? {...item, ...updated} : item,
      );
      this._availableAccessPoints = this._availableAccessPoints.map((item) =>
        item.id === updated.id ? {...item, ...updated} : item,
      );
      this._editingDoorName = false;
      this._doorNameDraft = "";
      this._doorRenameNotice = "Door name updated everywhere in HomePASS, including NFC pages.";
    } catch (error) {
      this._doorRenameError = error?.message || "HomePASS could not update the door name.";
    } finally {
      this._renamingDoor = false;
      this._render();
    }
  }

  _doorStatusCandidates() {
    return Object.keys(this._hass?.states ?? {})
      .filter((entityId) =>
        entityId !== this._selectedDoor?.lock_entity_id &&
        this._isDoorStatusEntity(entityId))
      .map((entityId) => ({
        entity_id: entityId,
        label: this._hass.states[entityId]?.attributes?.friendly_name ?? entityId,
      }))
      .sort((left, right) =>
        left.label.localeCompare(right.label) || left.entity_id.localeCompare(right.entity_id));
  }

  _isDoorStatusEntity(entityOrId) {
    const entityId = typeof entityOrId === "string"
      ? entityOrId : entityOrId?.entity_id;
    if (!entityId) return false;
    const domain = entityId.split(".", 1)[0];
    const state = this._hass?.states?.[entityId];
    const deviceClass = String(state?.attributes?.device_class ?? "").toLowerCase();
    const name = `${entityId} ${state?.attributes?.friendly_name ?? ""}`.toLowerCase();
    const looksLikeOpening = /(^|[\s._-])(door|window|gate|contact|opening)([\s._-]|$)/.test(name);
    if (domain === "lock") return true;
    if (domain === "cover") {
      return ["door", "garage"].includes(deviceClass) || looksLikeOpening;
    }
    if (domain === "input_boolean") return looksLikeOpening;
    if (domain === "binary_sensor") {
      return ["door", "window", "opening", "garage_door"].includes(deviceClass) ||
        looksLikeOpening;
    }
    if (domain === "sensor") {
      return looksLikeOpening && ["open", "closed", "on", "off"].includes(
        String(state?.state ?? "").toLowerCase(),
      );
    }
    return false;
  }

  _openDoorSensorEdit() {
    if (!this._hass?.user?.is_admin || this._doorSensorSaving || !this._selectedDoorId) return;
    this._doorSensorEditOpen = true;
    this._doorSensorEntityId = this._selectedDoor?.door_entity_id ?? "";
    this._doorSensorInverted = this._selectedDoor?.status_inverted === true;
    this._doorSensorError = undefined;
    this._doorSensorNotice = undefined;
    this._render();
  }

  _cancelDoorSensorEdit() {
    if (this._doorSensorSaving) return;
    this._doorSensorEditOpen = false;
    this._doorSensorEntityId = "";
    this._doorSensorInverted = false;
    this._doorSensorError = undefined;
    this._render();
  }

  async _saveDoorSensor() {
    if (!this._hass?.user?.is_admin || this._doorSensorSaving || !this._selectedDoorId) return;
    this._doorSensorSaving = true;
    this._doorSensorError = undefined;
    this._doorSensorNotice = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: UPDATE_ACCESS_POINT_ACTION,
        service_data: {
          access_point_id: this._selectedDoorId,
          status_entity_id: this._doorSensorEntityId,
          status_inverted: this._doorSensorEntityId ? this._doorSensorInverted : false,
        },
        return_response: true,
      });
      const updated = result?.response?.access_point;
      if (!updated || updated.id !== this._selectedDoorId) {
        throw new Error("HomePASS returned an invalid Door response.");
      }
      const mergeDoor = (door) => {
        if (door.id !== updated.id) return door;
        const merged = {...door, ...updated};
        if (!("door_entity_id" in updated)) delete merged.door_entity_id;
        return this._doorWithHassState(merged, this._hass);
      };
      this._selectedDoor = mergeDoor(this._selectedDoor);
      this._dashboardAccessPoints = this._dashboardAccessPoints.map(mergeDoor);
      this._doorSensorEditOpen = false;
      this._doorSensorNotice = this._doorSensorEntityId
        ? "Door sensor updated."
        : "Separate door sensor removed.";
      this._doorSensorEntityId = "";
      this._doorSensorInverted = false;
    } catch (error) {
      this._doorSensorError = error?.message ||
        "HomePASS could not update this door sensor.";
    } finally {
      this._doorSensorSaving = false;
      this._render();
    }
  }

  _markDoorNfcEnabled(accessPointId) {
    if (!accessPointId) return;
    const update = (item) => item.id === accessPointId
      ? {
          ...item,
          nfc_enabled: true,
          nfc_tag_count: Math.max(1, Number(item.nfc_tag_count) || 0),
        }
      : item;
    this._dashboardAccessPoints = this._dashboardAccessPoints.map(update);
    if (this._selectedDoor?.id === accessPointId) {
      this._selectedDoor = update(this._selectedDoor);
    }
    if (!this._doorNfcSetupOpen) this._render();
  }

  _openRemoveDoorConfirmation() {
    if (!this._hass?.user?.is_admin) return;
    if (
      !this._doorControlDialogOpen ||
      this._removeDoorConfirmationOpen ||
      this._doorOperationIsBusy() ||
      this._doorOperationState === DOOR_OPERATION_STATE.SUCCESS
    ) {
      return;
    }
    this._removeDoorError = undefined;
    this._removeDoorConfirmationOpen = true;
    this._render();
  }

  _closeRemoveDoorConfirmation() {
    if (this._removingDoor) return;
    this._removeDoorConfirmationDialogElement = undefined;
    this._removeDoorConfirmationOpen = false;
    this._removeDoorError = undefined;
    this._render();
  }

  async _openAddDoorDialog() {
    if (this._addDoorDialogOpen) return;
    if (!this._hass?.user?.is_admin) return;
    this._addDoorDialogOpen = true;
    this._availableAccessPoints = [];
    this._availableAccessPointsLoading = true;
    this._availableAccessPointsError = undefined;
    this._selectedAvailableAccessPointId = undefined;
    this._addDoorSource = "home_assistant";
    this._haDoorDevices = [];
    this._haDoorEntities = [];
    this._haDoorDeviceId = "";
    this._haDoorProfile = "garage_cover";
    this._haDoorControlEntityId = "";
    this._haDoorStatusEntityId = "";
    this._haDoorDisplayName = "";
    this._haDoorStatusInverted = false;
    this._haDoorPulseSeconds = 1;
    this._render();
    try {
      const [result, devices, entities] = await Promise.all([
        this._hass.callWS({
          type: "call_service", domain: DOMAIN,
          service: LIST_AVAILABLE_ACCESS_POINTS_ACTION,
          service_data: {}, return_response: true,
        }),
        this._hass.callWS({ type: "config/device_registry/list" }),
        this._hass.callWS({ type: "config/entity_registry/list" }),
      ]);
      this._availableAccessPoints = result.response?.access_points ?? [];
      this._haDoorDevices = Array.isArray(devices) ? devices : [];
      this._haDoorEntities = (Array.isArray(entities) ? entities : [])
        .filter((entity) => !entity.disabled_by && this._hass.states?.[entity.entity_id]);
    } catch (_error) {
      this._availableAccessPointsError =
        "Home Assistant devices could not be loaded. Confirm you are an administrator and try again.";
    } finally {
      this._availableAccessPointsLoading = false;
      this._render();
    }
  }

  _closeAddDoorDialog() {
    if (this._enrollingDoor) return;
    this._addDoorDialogElement = undefined;
    this._addDoorDialogOpen = false;
    this._availableAccessPoints = [];
    this._availableAccessPointsLoading = false;
    this._availableAccessPointsError = undefined;
    this._selectedAvailableAccessPointId = undefined;
    this._haDoorDevices = [];
    this._haDoorEntities = [];
    this._render();
  }

  _haDoorControlDomains() {
    return {
      lock: ["lock"], garage_cover: ["cover"],
      garage_toggle: ["button", "switch"],
      electric_strike: ["button", "switch", "lock"],
    }[this._haDoorProfile] ?? [];
  }

  _haDoorEntityLabel(entity) {
    return this._hass.states?.[entity.entity_id]?.attributes?.friendly_name
      ?? entity.name ?? entity.original_name ?? entity.entity_id;
  }

  _haDoorDeviceLabel(device) {
    return device.name_by_user ?? device.name ?? `${device.manufacturer ?? "Home Assistant"} device`;
  }

  _haDoorRelevantEntities(domains, sameDeviceOnly = true) {
    return this._haDoorEntities
      .filter((entity) =>
        (!sameDeviceOnly || !this._haDoorDeviceId || entity.device_id === this._haDoorDeviceId) &&
        domains.includes(entity.entity_id.split(".", 1)[0]))
      .sort((left, right) =>
        this._haDoorEntityLabel(left).localeCompare(this._haDoorEntityLabel(right)) ||
        left.entity_id.localeCompare(right.entity_id));
  }

  _haDoorCandidateDevices() {
    const relevantDeviceIds = new Set(
      this._haDoorEntities
        .filter((entity) => ["lock", "cover", "button", "switch"].includes(
          entity.entity_id.split(".", 1)[0]))
        .map((entity) => entity.device_id).filter(Boolean),
    );
    return this._haDoorDevices
      .filter((device) => relevantDeviceIds.has(device.id))
      .sort((left, right) => this._haDoorDeviceLabel(left).localeCompare(
        this._haDoorDeviceLabel(right)));
  }

  _haDoorManualFormValid() {
    const pulse = Number(this._haDoorPulseSeconds);
    const pulseValid = !["garage_toggle", "electric_strike"].includes(
      this._haDoorProfile,
    ) || (Number.isFinite(pulse) && pulse >= 0.1 && pulse <= 10);
    return Boolean(
      this._haDoorDeviceId && this._haDoorDisplayName.trim() &&
      this._haDoorControlEntityId &&
      this._haDoorControlDomains().includes(this._haDoorControlEntityId.split(".", 1)[0]) &&
      this._haDoorControlEntityId !== this._haDoorStatusEntityId && pulseValid
    );
  }

  async _enrollSelectedDoor() {
    if (this._enrollingDoor) return;
    const manual = this._addDoorSource === "home_assistant";
    if (manual ? !this._haDoorManualFormValid() : !this._selectedAvailableAccessPointId) return;
    this._enrollingDoor = true;
    this._availableAccessPointsError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: manual ? ENROLL_HOME_ASSISTANT_ACCESS_POINT_ACTION : ENROLL_ACCESS_POINT_ACTION,
        service_data: manual
          ? {
              display_name: this._haDoorDisplayName.trim(),
              device_id: this._haDoorDeviceId,
              control_profile: this._haDoorProfile,
              control_entity_id: this._haDoorControlEntityId,
              ...(this._haDoorStatusEntityId ? { status_entity_id: this._haDoorStatusEntityId } : {}),
              status_inverted: this._haDoorStatusInverted,
              pulse_seconds: Number(this._haDoorPulseSeconds),
            }
          : { access_point_id: this._selectedAvailableAccessPointId },
        return_response: true,
      });
      this._addDoorDialogElement = undefined;
      this._addDoorDialogOpen = false;
      this._dashboardDoorsLoading = true;
      await this._loadDashboardAccessPoints();
      this._refreshDashboardActivityAfterOperation();
    } catch (_error) {
      this._availableAccessPointsError =
        "This door could not be added. Check the selected entities and try again.";
    } finally {
      this._enrollingDoor = false;
      this._render();
    }
  }

  async _removeSelectedDoor() {
    if (!this._hass?.user?.is_admin) return;
    if (
      !this._selectedDoorId ||
      !this._selectedDoor ||
      !this._removeDoorConfirmationOpen ||
      this._removingDoor
    ) {
      return;
    }
    this._removingDoor = true;
    this._removeDoorError = undefined;
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: REMOVE_ACCESS_POINT_ACTION,
        service_data: { access_point_id: this._selectedDoorId },
        return_response: true,
      });
      this._resetDoorControlDialogState();
      this._dashboardDoorsLoading = true;
      await this._loadDashboardAccessPoints();
      this._refreshDashboardActivityAfterOperation();
    } catch (error) {
      this._removeDoorError = String(error?.message ?? error).includes(
        "still has access assigned",
      )
        ? "This door still has access assigned. Remove its access assignments before removing it from HomePASS."
        : "This door could not be removed from HomePASS. Try again.";
    } finally {
      this._removingDoor = false;
      this._render();
    }
  }

  _doorWithHassState(door, hass) {
    if (!door?.lock_entity_id || !hass?.states) return door;
    const projected = { ...door };
    const lock = hass.states[door.lock_entity_id];
    const contact = door.door_entity_id ? hass.states[door.door_entity_id] : undefined;

    delete projected.lock_state;
    delete projected.lock_last_updated;
    if (!lock || lock.state === "unknown") {
      projected.availability = "unknown";
    } else if (lock.state === "unavailable") {
      projected.availability = "unavailable";
    } else if (lock.state === "offline") {
      projected.availability = "offline";
    } else {
      projected.availability = "available";
      if (door.control_profile === "garage_cover") {
        projected.lock_state = { closed: "locked", closing: "locking", open: "unlocked", opening: "unlocking" }[lock.state];
      } else if (door.control_profile === "lock" && ["jammed", "locked", "locking", "open", "opening", "unlocked", "unlocking"].includes(lock.state)) {
        projected.lock_state = lock.state;
      }
      const lockTimestamp = Date.parse(lock.last_updated);
      if (Number.isFinite(lockTimestamp)) {
        projected.lock_last_updated = new Date(lockTimestamp).toISOString();
      }
    }

    delete projected.door_state;
    const contactValue = contact?.state?.toLowerCase();
    if (["on", "open", "opening", "unlocked"].includes(contactValue)) projected.door_state = door.status_inverted ? "closed" : "open";
    if (["off", "closed", "closing", "locked"].includes(contactValue)) projected.door_state = door.status_inverted ? "open" : "closed";
    if (["garage_toggle", "electric_strike"].includes(door.control_profile)) {
      if (projected.door_state === "open") projected.lock_state = "unlocked";
      if (projected.door_state === "closed") projected.lock_state = "locked";
      if (!projected.lock_state && door.control_profile === "electric_strike") projected.lock_state = "locked";
    }

    const timestamps = [lock?.last_updated, contact?.last_updated]
      .filter(Boolean)
      .map((value) => Date.parse(value))
      .filter(Number.isFinite);
    if (timestamps.length > 0) {
      projected.last_updated = new Date(Math.max(...timestamps)).toISOString();
    }
    const controllerBattery = this._batteryReading(
      hass,
      door.battery_entity_id,
      door.battery_percentage,
      door.battery_status,
    );
    const doorSensorBattery = this._batteryReading(
      hass,
      door.door_sensor_battery_entity_id,
      door.door_sensor_battery_percentage,
      door.door_sensor_battery_status,
    );
    for (const field of ["battery_percentage", "battery_status", "door_sensor_battery_percentage", "door_sensor_battery_status"]) {
      delete projected[field];
    }
    if (controllerBattery) {
      projected.battery_percentage = controllerBattery.percentage;
      projected.battery_status = controllerBattery.status;
    }
    if (doorSensorBattery) {
      projected.door_sensor_battery_percentage = doorSensorBattery.percentage;
      projected.door_sensor_battery_status = doorSensorBattery.status;
    }
    return projected;
  }

  _batteryReading(hass, entityId, fallbackPercentage, fallbackStatus) {
    let percentage = Number.isInteger(fallbackPercentage) ? fallbackPercentage : undefined;
    let status = ["normal", "low", "critical", "unknown"].includes(fallbackStatus)
      ? fallbackStatus
      : undefined;
    const state = entityId ? hass?.states?.[entityId] : undefined;
    if (state) {
      const numeric = [
        state.state,
        state.attributes?.battery_level,
        state.attributes?.battery_percentage,
        state.attributes?.battery,
      ]
        .map((value) => Number(value))
        .find((value) => Number.isFinite(value) && value >= 0 && value <= 100);
      if (numeric !== undefined) {
        percentage = Math.round(numeric);
        status = percentage <= 10 ? "critical" : percentage <= 20 ? "low" : "normal";
      } else if (state.attributes?.device_class === "battery" && entityId.startsWith("binary_sensor.")) {
        percentage = undefined;
        status = state.state === "on" ? "low" : state.state === "off" ? "normal" : "unknown";
      } else if (["unknown", "unavailable"].includes(state.state)) {
        percentage = undefined;
        status = "unknown";
      }
    }
    return percentage !== undefined || (status && status !== "unknown")
      ? { entityId, percentage, status: status ?? "unknown" }
      : undefined;
  }

  _batteryMarkup(reading, label = "Battery") {
    if (!reading) return "";
    const status = reading.status ?? "unknown";
    const icon = status === "critical"
      ? "mdi:battery-alert"
      : status === "low" ? "mdi:battery-low" : "mdi:battery";
    const value = reading.percentage !== undefined
      ? `${reading.percentage}%`
      : status === "critical" ? "critical" : status === "low" ? "low" : "OK";
    return `<span class="device-battery ${escapeHtml(status)}"><ha-icon icon="${icon}" aria-hidden="true"></ha-icon>${escapeHtml(label)} ${escapeHtml(value)}</span>`;
  }

  _updateDoorControlFromHass(previousHass, hass) {
    const door = this._selectedDoor;
    if (!door) return;
    const sourceIds = [
      door.lock_entity_id,
      door.door_entity_id,
      door.battery_entity_id,
      door.door_sensor_battery_entity_id,
    ].filter(Boolean);
    if (
      sourceIds.length === 0 ||
      sourceIds.every((entityId) => previousHass?.states?.[entityId] === hass.states?.[entityId])
    ) {
      return;
    }
    if (this._doorOperationState === DOOR_OPERATION_STATE.SLIDING) {
      this._cancelDoorSlide();
    }
    this._doorStatusRequestGeneration += 1;
    this._doorControlLoading = false;
    this._doorControlError = undefined;
    this._selectedDoor = this._doorWithHassState(door, hass);
    this._dashboardAccessPoints = this._dashboardAccessPoints.map((item) =>
      item.id === this._selectedDoorId ? this._selectedDoor : item,
    );
    this._reconcileDoorOperationFromLiveState();
    this._updateDoorControlDialog();
  }

  _updateDoorControlDialog() {
    if (
      !this._doorControlDialogOpen ||
      this._removeDoorConfirmationOpen ||
      this._doorNfcSetupOpen
    ) return;
    const title = this.shadowRoot.querySelector("#door-control-title");
    const loading = this.shadowRoot.querySelector("#door-control-loading");
    const error = this.shadowRoot.querySelector("#door-control-error");
    const status = this.shadowRoot.querySelector("#door-control-status");
    const door = this._selectedDoor;

    if (title) title.textContent = door?.display_name ?? "Door";
    loading.hidden = !this._doorControlLoading;
    error.hidden = !this._doorControlError;
    status.hidden = this._doorControlLoading || !door;
    if (!door || status.hidden) return;

    const unavailable = Boolean(this._doorControlError);
    const hasLastKnownState = Boolean(
      door.last_updated && (door.lock_state || door.door_state)
    );
    const stateSummary = this.shadowRoot.querySelector("#door-control-state-summary");
    const lastKnownHeading = this.shadowRoot.querySelector("#door-last-known-heading");
    stateSummary.hidden = unavailable && !hasLastKnownState;
    lastKnownHeading.hidden = !unavailable || !hasLastKnownState;

    const statusGraphic = this.shadowRoot.querySelector("#door-control-status-graphic");
    let statusIcon = statusGraphic?.querySelector(".door-dialog-status-icon");
    if (statusGraphic && !statusIcon) {
      const created = createDoorStatusSymbol(door, "door-dialog-status-icon");
      statusGraphic.append(created.slot);
      statusIcon = created.symbol;
    }
    if (statusIcon) updateDoorStatusSymbol(statusIcon, door);

    const primary = this.shadowRoot.querySelector("#door-control-lock-state");
    primary.textContent = this._doorPrimaryState(door);
    primary.className = `door-control-primary-state ${this._doorTone(door)}`;

    const contactRow = this.shadowRoot.querySelector("#door-control-contact-row");
    const contact = this.shadowRoot.querySelector("#door-control-contact-state");
    const contactLabel = door.door_state === "open"
      ? "Open"
      : door.door_state === "closed"
        ? "Closed"
        : undefined;
    contactRow.hidden = !contactLabel;
    contact.textContent = contactLabel ?? "";

    const availabilityRow = this.shadowRoot.querySelector("#door-control-availability-row");
    const availability = this.shadowRoot.querySelector("#door-control-availability");
    const availabilityLabel = unavailable
      ? hasLastKnownState ? "Availability unknown" : undefined
      : {
          available: "Online",
          unavailable: "Unavailable",
          offline: "Offline",
          unknown: "Unknown",
        }[door.availability];
    availabilityRow.hidden = !availabilityLabel;
    availability.textContent = availabilityLabel ?? "";
    this._updateDoorRelativeTime();
    this._updateDoorPolicySection();
    this._updateDoorOperationControls();
  }

  _updateDoorPolicySection() {
    const loading = this.shadowRoot.querySelector("#door-policy-loading");
    const error = this.shadowRoot.querySelector("#door-policy-error");
    const content = this.shadowRoot.querySelector("#door-policy-content");
    if (!loading || !error || !content) return;
    loading.hidden = !this._doorPolicyLoading;
    error.hidden = !this._doorPolicyError;
    error.textContent = this._doorPolicyError ?? "";
    content.hidden = this._doorPolicyLoading || Boolean(this._doorPolicyError);
    if (content.hidden) return;

    this.shadowRoot.querySelector("#door-current-access-title").textContent =
      `Current Access (${this._doorCurrentAccess.length})`;

    this._renderDoorPolicyList(
      this.shadowRoot.querySelector("#door-current-access-list"),
      this._doorCurrentAccess,
      "allowed",
      "No Users currently have access.",
      (person) => this._openPersonFromDoor(person.person_id),
      (person) => `Manage ${person.display_name}`,
    );
    this._renderSynchronizationHistory(
      this.shadowRoot.querySelector("#door-synchronization-history-list"),
      this._doorSynchronizationHistory,
    );
  }

  _validHistoryEvent(event) {
    return Boolean(
      event &&
      typeof event.title === "string" &&
      typeof event.description === "string" &&
      ["success", "info", "warning", "error"].includes(event.severity) &&
      typeof event.timestamp === "string" &&
      Number.isFinite(Date.parse(event.timestamp)),
    );
  }

  _renderSynchronizationHistory(container, events) {
    if (!container) return;
    container.textContent = "";
    if (events.length === 0) {
      const empty = document.createElement("p");
      empty.className = "synchronization-history-empty";
      empty.textContent = "No synchronization history yet.";
      container.append(empty);
      return;
    }
    for (const event of events) {
      const row = document.createElement("article");
      row.className = `synchronization-history-row ${event.severity}`;
      const time = document.createElement("time");
      time.dateTime = event.timestamp;
      time.textContent = new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(event.timestamp));
      const title = document.createElement("p");
      title.className = "synchronization-history-title";
      title.textContent = event.title;
      const description = document.createElement("p");
      description.textContent = event.description;
      row.append(time, title, description);
      container.append(row);
    }
  }

  _synchronizationHistoryCard(events) {
    const card = document.createElement("ha-card");
    card.className = "details-card synchronization-history-card";
    const disclosure = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `Synchronization History (${events.length})`;
    const list = document.createElement("div");
    list.className = "synchronization-history-list";
    this._renderSynchronizationHistory(list, events);
    disclosure.append(summary, list);
    card.append(disclosure);
    return card;
  }

  _renderDoorPolicyList(
    container,
    people,
    groupTone,
    emptyMessage,
    onSelect = undefined,
    selectLabel = undefined,
    decorateRelationship = undefined,
    onNameSelect = undefined,
  ) {
    if (!container) return;
    container.textContent = "";
    if (people.length === 0) {
      const empty = document.createElement("p");
      empty.className = "door-policy-empty";
      empty.textContent = emptyMessage;
      container.append(empty);
      return;
    }
    for (const [index, person] of people.entries()) {
      const tone = groupTone === "temporary" ? person.severity : groupTone;
      const relationship = document.createElement("div");
      relationship.className = "door-policy-relationship";
      const row = document.createElement(onSelect && !onNameSelect ? "button" : "div");
      row.className = `door-policy-row${onSelect ? " door-policy-selectable" : ""}`;
      if (onSelect) {
        if (row.tagName === "BUTTON") row.type = "button";
        else {
          row.setAttribute("role", "button");
          row.tabIndex = 0;
          row.addEventListener("keydown", (event) => {
            if (event.target !== row) return;
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onSelect(person, index);
            }
          });
        }
        row.setAttribute(
          "aria-label",
          selectLabel
            ? selectLabel(person, index)
            : `Explain why access is unavailable for ${person.display_name}`,
        );
        row.addEventListener("click", () => onSelect(person, index));
      }
      const icon = document.createElement("ha-icon");
      icon.className = `door-policy-icon ${tone}`;
      icon.setAttribute("icon", {
        allowed: "mdi:check-circle",
        warning: "mdi:clock-alert-outline",
        error: "mdi:alert-circle",
        neutral: "mdi:minus-circle-outline",
      }[tone]);
      icon.setAttribute("aria-hidden", "true");
      const copy = document.createElement("div");
      const name = document.createElement(onNameSelect ? "button" : "p");
      name.className = `door-policy-name homepass-entity-name${onNameSelect ? " person-door-link" : ""}`;
      name.textContent = person.display_name;
      if (onNameSelect) {
        name.type = "button";
        name.setAttribute("aria-label", `Open ${person.display_name} Door management`);
        name.addEventListener("click", (event) => {
          event.stopPropagation();
          onNameSelect(person, index);
        });
      }
      copy.append(name);
      if (person.explanation) {
        const explanation = document.createElement("p");
        explanation.className = "door-policy-explanation";
        explanation.textContent = person.explanation;
        copy.append(explanation);
      }
      row.append(icon, copy);
      if (onSelect) {
        const open = document.createElement("ha-icon");
        open.className = "door-policy-open-icon";
        open.setAttribute("icon", "mdi:chevron-right");
        open.setAttribute("aria-hidden", "true");
        row.append(open);
      }
      relationship.append(row);
      if (decorateRelationship) {
        decorateRelationship(relationship, person, index);
      }
      const synchronization = this._synchronizationRecoveryPresentation(person);
      if (synchronization) relationship.append(synchronization);
      container.append(relationship);
    }
  }

  _synchronizationRecoveryPresentation(relationship, sourceOverride = undefined) {
    const personId = relationship.person_id ?? this._detailsPersonId;
    const accessPointId = relationship.access_point_id ?? this._selectedDoorId;
    const source = sourceOverride ?? (relationship.person_id ? "door" : "person");
    const synchronization = relationship.synchronization;
    if (!personId || !accessPointId || !synchronization) return undefined;
    const key = `${personId}:${accessPointId}`;
    const pending = this._synchronizationRecoveryPendingKey === key;
    const result = this._synchronizationRecoveryResults.get(key);
    if (!pending && !result && synchronization.severity === "success") return undefined;

    const status = document.createElement("div");
    const severity = result?.severity ?? synchronization.severity;
    status.className = `synchronization-recovery ${severity}`;
    status.setAttribute("data-recovery-result-key", key);
    status.tabIndex = -1;
    status.setAttribute("role", result || pending ? "status" : "note");
    const title = document.createElement("p");
    title.className = "synchronization-recovery-title";
    title.textContent = pending
      ? "Retrying synchronization…"
      : result?.title ?? synchronization.title;
    const description = document.createElement("p");
    description.className = "synchronization-recovery-description";
    description.textContent = pending
      ? "HomePASS is safely checking this access with the lock."
      : result?.description ?? synchronization.description;
    status.append(title, description);

    const retryAllowed = result?.retry_allowed ?? synchronization.retry_allowed;
    if (retryAllowed || pending) {
      const retry = document.createElement("ha-button");
      retry.className = "synchronization-retry";
      retry.setAttribute("data-recovery-key", key);
      retry.disabled = pending;
      retry.textContent = pending ? "Retrying…" : "Retry";
      retry.addEventListener("click", () => {
        void this._retrySynchronization(personId, accessPointId, source);
      });
      status.append(retry);
    }
    return status;
  }

  async _retrySynchronization(personId, accessPointId, source) {
    const key = `${personId}:${accessPointId}`;
    if (this._synchronizationRecoveryPendingKey) return;
    const generation = ++this._synchronizationRecoveryGeneration;
    this._synchronizationRecoveryPendingKey = key;
    this._synchronizationRecoveryResults.delete(key);
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: RETRY_SYNCHRONIZATION_ACTION,
        service_data: {
          person_id: personId,
          access_point_id: accessPointId,
        },
        return_response: true,
      });
      const response = result?.response;
      if (
        !this._validSynchronizationRecovery(response) ||
        response.person_id !== personId ||
        response.access_point_id !== accessPointId
      ) {
        throw new Error("Invalid synchronization recovery response");
      }
      if (!this._synchronizationRecoveryOwns(generation, personId, accessPointId, source)) {
        return;
      }
      this._synchronizationRecoveryResults.set(key, response);
      if (source === "door") {
        await this._loadDoorPolicy(accessPointId);
      } else if (source === "person") {
        await this._loadPersonPolicy(personId);
      } else {
        await this._loadDashboardAttention();
        this._refreshDashboardActivityAfterOperation();
      }
    } catch (_error) {
      if (!this._synchronizationRecoveryOwns(generation, personId, accessPointId, source)) {
        return;
      }
      this._synchronizationRecoveryResults.set(key, {
        title: "Synchronization unavailable",
        description: "HomePASS could not safely retry this access. No success was assumed.",
        severity: "error",
        retry_allowed: false,
      });
      if (source === "dashboard") {
        await this._loadDashboardAttention();
      }
    } finally {
      if (!this._synchronizationRecoveryOwns(generation, personId, accessPointId, source)) {
        return;
      }
      this._synchronizationRecoveryPendingKey = undefined;
      this._render();
      queueMicrotask(() => {
        const target =
          this.shadowRoot.querySelector(`[data-recovery-key="${key}"]`) ??
          this.shadowRoot.querySelector(`[data-recovery-result-key="${key}"]`) ??
          (source === "dashboard"
            ? this.shadowRoot.querySelector("#dashboard-view-people")
            : undefined);
        target?.focus();
      });
    }
  }

  _validSynchronizationRecovery(response) {
    return Boolean(
      response &&
      typeof response.person_id === "string" &&
      typeof response.access_point_id === "string" &&
      typeof response.person_name === "string" &&
      typeof response.door_name === "string" &&
      typeof response.title === "string" &&
      typeof response.description === "string" &&
      ["success", "info", "warning", "error"].includes(response.severity) &&
      typeof response.retry_allowed === "boolean" &&
      typeof response.completed === "boolean" &&
      typeof response.in_progress === "boolean" &&
      response.synchronization &&
      this._validSynchronizationPresentation(response.synchronization)
    );
  }

  _validSynchronizationPresentation(presentation) {
    return Boolean(
      presentation &&
      typeof presentation.title === "string" &&
      typeof presentation.description === "string" &&
      ["success", "info", "warning", "error"].includes(presentation.severity) &&
      typeof presentation.retry_allowed === "boolean" &&
      typeof presentation.last_evaluated_at === "string"
    );
  }

  _synchronizationRecoveryOwns(generation, personId, accessPointId, source) {
    return Boolean(
      this._synchronizationRecoveryGeneration === generation &&
      ((source === "door" &&
        this._doorControlDialogOpen &&
        this._selectedDoorId === accessPointId) ||
        (source === "person" && this._detailsPersonId === personId) ||
        (source === "dashboard" &&
          this._currentPage === "dashboard" &&
          !this._detailsPersonId))
    );
  }

  _resetSynchronizationRecovery() {
    this._synchronizationRecoveryGeneration += 1;
    this._synchronizationRecoveryPendingKey = undefined;
    this._synchronizationRecoveryResults.clear();
  }

  _openPolicyInspector(personId, accessPointId, source, sourceIndex) {
    if (!personId || !accessPointId) return;
    this._policyInspectorOpen = true;
    this._policyInspectorLoading = true;
    this._policyInspectorError = undefined;
    this._policyInspectorData = undefined;
    this._policyInspectorSource = source;
    this._policyInspectorSourceIndex = sourceIndex;
    const generation = ++this._policyInspectorRequestGeneration;
    this._render();
    void this._loadPolicyExplanation(personId, accessPointId, generation);
  }

  async _loadPolicyExplanation(personId, accessPointId, generation) {
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_POLICY_EXPLANATION_ACTION,
        service_data: {
          person_id: personId,
          access_point_id: accessPointId,
        },
        return_response: true,
      });
      const response = result?.response;
      if (!this._validPolicyExplanation(response)) {
        throw new Error("Invalid policy explanation response");
      }
      if (!this._policyInspectorRequestOwns(generation, personId, accessPointId)) return;
      this._policyInspectorData = response;
      this._policyInspectorError = undefined;
    } catch (_error) {
      if (!this._policyInspectorRequestOwns(generation, personId, accessPointId)) return;
      this._policyInspectorData = undefined;
      this._policyInspectorError =
        "This policy explanation is unavailable right now. Close it and try again.";
    } finally {
      if (!this._policyInspectorRequestOwns(generation, personId, accessPointId)) return;
      this._policyInspectorLoading = false;
      this._render();
    }
  }

  _validPolicyExplanation(response) {
    const validity = response?.validity;
    const weekly = response?.weekly_hours;
    const current = response?.current_local;
    const nullableString = (value) => value === null || typeof value === "string";
    return Boolean(
      response &&
      response.title === "Access unavailable" &&
      typeof response.reason === "string" &&
      typeof response.person_name === "string" &&
      typeof response.door_name === "string" &&
      typeof response.schedule_name === "string" &&
      validity &&
      typeof validity.summary === "string" &&
      nullableString(validity.valid_from) &&
      nullableString(validity.valid_until) &&
      weekly &&
      ["always", "simple", "advanced"].includes(weekly.kind) &&
      typeof weekly.summary === "string" &&
      nullableString(weekly.days) &&
      nullableString(weekly.hours) &&
      current &&
      typeof current.day === "string" &&
      typeof current.date === "string" &&
      typeof current.time === "string" &&
      typeof current.time_zone === "string"
    );
  }

  _policyInspectorRequestOwns(generation, personId, accessPointId) {
    return Boolean(
      this._policyInspectorOpen &&
      this._policyInspectorRequestGeneration === generation &&
      ((this._policyInspectorSource === "door" &&
        this._selectedDoorId === accessPointId) ||
        (this._policyInspectorSource === "person" &&
          this._detailsPersonId === personId))
    );
  }

  _closePolicyInspector() {
    const source = this._policyInspectorSource;
    const sourceIndex = this._policyInspectorSourceIndex;
    this._resetPolicyInspectorState();
    this._render();
    const selector = source === "door"
      ? "#door-temporarily-unavailable-list .door-policy-selectable"
      : ".person-policy-card .door-policy-selectable";
    this.shadowRoot.querySelectorAll(selector)[sourceIndex]?.focus();
  }

  _resetPolicyInspectorState() {
    this._policyInspectorDialogElement = undefined;
    this._policyInspectorOpen = false;
    this._policyInspectorLoading = false;
    this._policyInspectorError = undefined;
    this._policyInspectorData = undefined;
    this._policyInspectorRequestGeneration += 1;
    this._policyInspectorSource = undefined;
    this._policyInspectorSourceIndex = undefined;
  }

  _updatePolicyInspectorDialog() {
    const loading = this.shadowRoot.querySelector("#policy-inspector-loading");
    const error = this.shadowRoot.querySelector("#policy-inspector-error");
    const content = this.shadowRoot.querySelector("#policy-inspector-content");
    if (!loading || !error || !content) return;
    loading.hidden = !this._policyInspectorLoading;
    error.hidden = !this._policyInspectorError;
    error.textContent = this._policyInspectorError ?? "";
    const data = this._policyInspectorData;
    content.hidden = this._policyInspectorLoading || Boolean(this._policyInspectorError) || !data;
    if (content.hidden) return;

    this.shadowRoot.querySelector("#policy-inspector-reason").textContent = data.reason;
    this.shadowRoot.querySelector("#policy-inspector-person").textContent = data.person_name;
    this.shadowRoot.querySelector("#policy-inspector-door").textContent = data.door_name;
    this.shadowRoot.querySelector("#policy-inspector-schedule").textContent = data.schedule_name;
    this.shadowRoot.querySelector("#policy-validity-summary").textContent =
      data.validity.summary;
    const validFromRow = this.shadowRoot.querySelector("#policy-valid-from-row");
    validFromRow.hidden = !data.validity.valid_from;
    this.shadowRoot.querySelector("#policy-valid-from").textContent =
      data.validity.valid_from ?? "";
    const validUntilRow = this.shadowRoot.querySelector("#policy-valid-until-row");
    validUntilRow.hidden = !data.validity.valid_until;
    this.shadowRoot.querySelector("#policy-valid-until").textContent =
      data.validity.valid_until ?? "";
    this.shadowRoot.querySelector("#policy-weekly-summary").textContent =
      data.weekly_hours.summary;
    const weeklyDays = this.shadowRoot.querySelector("#policy-weekly-days");
    weeklyDays.hidden = !data.weekly_hours.days;
    weeklyDays.textContent = data.weekly_hours.days ?? "";
    const weeklyHours = this.shadowRoot.querySelector("#policy-weekly-hours");
    weeklyHours.hidden = !data.weekly_hours.hours;
    weeklyHours.textContent = data.weekly_hours.hours ?? "";
    this.shadowRoot.querySelector("#policy-current-local").textContent =
      `${data.current_local.day}, ${data.current_local.date} at ${data.current_local.time}`;
    this.shadowRoot.querySelector("#policy-current-time-zone").textContent =
      `Schedule timezone: ${data.current_local.time_zone}`;
  }

  _relativeDoorTime(timestamp, now = Date.now()) {
    const updated = Date.parse(timestamp);
    if (!Number.isFinite(updated)) return "Unknown";
    const seconds = Math.max(0, Math.floor((now - updated) / 1000));
    if (seconds < 10) return "Just now";
    if (seconds < 60) return `${seconds} seconds ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ${hours === 1 ? "hour" : "hours"} ago`;
    if (hours < 48) return "Yesterday";
    const days = Math.floor(hours / 24);
    return `${days} days ago`;
  }

  _updateDoorRelativeTime() {
    const value = this.shadowRoot.querySelector("#door-last-updated-value");
    if (value) value.textContent = this._relativeDoorTime(this._selectedDoor?.last_updated);
  }

  _startDoorRelativeTimeTimer() {
    if (this._doorRelativeTimeTimer !== undefined) return;
    this._doorRelativeTimeTimer = window.setInterval(
      () => this._updateDoorRelativeTime(),
      DOOR_RELATIVE_TIME_INTERVAL,
    );
  }

  _stopDoorRelativeTimeTimer() {
    if (this._doorRelativeTimeTimer === undefined) return;
    window.clearInterval(this._doorRelativeTimeTimer);
    this._doorRelativeTimeTimer = undefined;
  }

  _availableDoorOperation() {
    if (this._doorControlLoading || this._doorControlError) return undefined;
    if (this._selectedDoor?.availability !== "available") return undefined;
    return this._doorOperationForState(this._selectedDoor);
  }

  _doorOperationForSelectedState() {
    return this._doorOperationForState(this._selectedDoor);
  }

  _doorOperationForState(door) {
    if (door?.control_profile === "electric_strike") {
      return { action: "release", service: UNLOCK_ACCESS_POINT_ACTION, targetState: undefined };
    }
    if (door?.control_profile === "garage_toggle" && !door.door_entity_id) {
      return { action: "operate", service: UNLOCK_ACCESS_POINT_ACTION, targetState: undefined };
    }
    if (door?.lock_state === "locked") {
      return {
        action: door.control_profile?.startsWith("garage_") ? "open" : "unlock",
        service: UNLOCK_ACCESS_POINT_ACTION,
        targetState: "unlocked",
      };
    }
    if (door?.lock_state === "unlocked") {
      return {
        action: door.control_profile?.startsWith("garage_") ? "close" : "lock",
        service: LOCK_ACCESS_POINT_ACTION,
        targetState: "locked",
      };
    }
    return undefined;
  }

  _doorOperationIsBusy() {
    return (
      this._doorOperationState === DOOR_OPERATION_STATE.SLIDING ||
      this._doorOperationCommandIsPending()
    );
  }

  _doorOperationCommandIsPending() {
    return [
      DOOR_OPERATION_STATE.COMMAND_SENT,
      DOOR_OPERATION_STATE.WAITING_FOR_CONFIRMATION,
    ].includes(this._doorOperationState);
  }

  _handleDoorSlideState(event) {
    if (event.detail?.state === SLIDE_ACTION_STATE.SLIDING) {
      if (
        this._doorOperationState === DOOR_OPERATION_STATE.IDLE ||
        this._doorOperationState === DOOR_OPERATION_STATE.FAILED
      ) {
        this._doorOperationState = DOOR_OPERATION_STATE.SLIDING;
        this._doorOperationError = undefined;
        const error = this.shadowRoot.querySelector("#door-operation-error");
        const remove = this.shadowRoot.querySelector("#open-remove-door-confirmation");
        if (error) error.hidden = true;
        if (remove) remove.disabled = true;
      }
      return;
    }
    if (this._doorOperationState === DOOR_OPERATION_STATE.SLIDING) {
      this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
      this._updateDoorOperationControls();
    }
  }

  async _beginDoorOperation() {
    if (
      ![
        DOOR_OPERATION_STATE.IDLE,
        DOOR_OPERATION_STATE.SLIDING,
        DOOR_OPERATION_STATE.FAILED,
      ].includes(this._doorOperationState) ||
      !this._doorControlDialogOpen ||
      !this._selectedDoorId
    ) {
      return;
    }
    const operation = this._availableDoorOperation();
    if (!operation) {
      this._cancelDoorSlide();
      this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
      this._doorOperationAction = undefined;
      this._doorOperationTargetState = undefined;
      this._doorOperationError = undefined;
      this._doorOperationSawTransition = false;
      this._doorOperationAccessPointId = undefined;
      this._updateDoorOperationControls();
      return;
    }

    await this._startDoorOperation(
      this._selectedDoor,
      this._selectedDoorId,
      operation,
    );
  }

  async _startDoorOperation(door, accessPointId, requestedOperation = undefined) {
    if (
      [DOOR_OPERATION_STATE.COMMAND_SENT, DOOR_OPERATION_STATE.WAITING_FOR_CONFIRMATION]
        .includes(this._doorOperationState) ||
      !door ||
      !accessPointId
    ) return;
    const operation = requestedOperation ?? this._doorOperationForState(door);
    if (!operation) return;

    this._clearDoorOperationTimers();
    const generation = ++this._doorOperationGeneration;
    const selectedDoorId = accessPointId;
    this._doorOperationState = DOOR_OPERATION_STATE.COMMAND_SENT;
    this._doorOperationAction = operation.action;
    this._doorOperationTargetState = operation.targetState;
    this._doorOperationAccessPointId = selectedDoorId;
    this._doorOperationError = undefined;
    this._doorOperationSawTransition = false;
    this._doorOperationTimeoutTimer = window.setTimeout(
      () => this._failDoorOperation(generation),
      this._doorOperationTimeoutMs,
    );
    this._updateDoorOperationSurfaces();

    try {
      const command = this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: operation.service,
        service_data: { access_point_id: selectedDoorId },
        return_response: true,
      });
      if (this._doorOperationOwns(generation, selectedDoorId)) {
        this._doorOperationState = DOOR_OPERATION_STATE.WAITING_FOR_CONFIRMATION;
        this._updateDoorOperationSurfaces();
      }
      const result = await command;
      if (!this._doorOperationOwns(generation, selectedDoorId)) return;
      if (result?.response?.confirmation_required === false) {
        this._completeDoorOperation(generation);
        return;
      }
      const currentAccessPoint = this._dashboardAccessPoints.find(
        (item) => item.id === selectedDoorId,
      ) ?? (this._selectedDoor?.id === selectedDoorId ? this._selectedDoor : undefined);
      const currentDoor = this._doorWithHassState(currentAccessPoint, this._hass);
      if (currentDoor?.lock_state === operation.targetState) {
        this._completeDoorOperation(generation);
        return;
      }
    } catch (_error) {
      if (this._doorOperationOwns(generation, selectedDoorId)) {
        this._failDoorOperation(generation);
      }
    }
  }

  _doorOperationOwns(generation, selectedDoorId = this._doorOperationAccessPointId) {
    return Boolean(
      this._doorOperationAccessPointId === selectedDoorId &&
      this._doorOperationGeneration === generation &&
      [
        DOOR_OPERATION_STATE.COMMAND_SENT,
        DOOR_OPERATION_STATE.WAITING_FOR_CONFIRMATION,
      ].includes(this._doorOperationState),
    );
  }

  _reconcileDoorOperationFromLiveState(door = this._selectedDoor) {
    if (!door || door.id !== this._doorOperationAccessPointId) return;
    const lockState = door.lock_state;
    if (this._doorOperationState === DOOR_OPERATION_STATE.SUCCESS) {
      if (
        door.availability === "available" &&
        lockState === this._doorOperationTargetState
      ) {
        return;
      }
      this._clearDoorOperationTimers();
      this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
      this._doorOperationAction = undefined;
      this._doorOperationTargetState = undefined;
      this._doorOperationError = undefined;
      this._doorOperationSawTransition = false;
      this._doorOperationAccessPointId = undefined;
      return;
    }
    if (this._doorOperationState === DOOR_OPERATION_STATE.FAILED) {
      if (lockState === this._doorOperationTargetState) {
        this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
        this._doorOperationAction = undefined;
        this._doorOperationTargetState = undefined;
        this._doorOperationError = undefined;
        this._doorOperationSawTransition = false;
        this._doorOperationAccessPointId = undefined;
      }
      return;
    }
    if (
      ![
        DOOR_OPERATION_STATE.COMMAND_SENT,
        DOOR_OPERATION_STATE.WAITING_FOR_CONFIRMATION,
      ].includes(this._doorOperationState)
    ) return;
    const generation = this._doorOperationGeneration;
    if (!this._doorOperationTargetState) return;
    if (door.availability !== "available" || !lockState) return;
    if (lockState === this._doorOperationTargetState) {
      this._completeDoorOperation(generation);
      return;
    }
    const expectedTransition = ["unlock", "open"].includes(this._doorOperationAction)
      ? "unlocking"
      : "locking";
    if (lockState === expectedTransition) {
      this._doorOperationSawTransition = true;
      return;
    }
    const originalState = ["unlock", "open"].includes(this._doorOperationAction) ? "locked" : "unlocked";
    if (lockState === originalState && !this._doorOperationSawTransition) return;
    this._failDoorOperation(generation);
  }

  _completeDoorOperation(generation) {
    if (!this._doorOperationOwns(generation)) return;
    this._clearDoorOperationTimeout();
    this._doorOperationState = DOOR_OPERATION_STATE.SUCCESS;
    this._doorOperationError = undefined;
    this._updateDoorOperationSurfaces();
    this._doorOperationSuccessTimer = window.setTimeout(() => {
      if (
        this._doorOperationGeneration !== generation ||
        this._doorOperationState !== DOOR_OPERATION_STATE.SUCCESS
      ) {
        return;
      }
      this._doorOperationSuccessTimer = undefined;
      this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
      this._doorOperationAction = undefined;
      this._doorOperationTargetState = undefined;
      this._doorOperationSawTransition = false;
      this._doorOperationAccessPointId = undefined;
      this._updateDoorOperationSurfaces();
    }, DOOR_OPERATION_SUCCESS_DURATION);
  }

  _failDoorOperation(generation) {
    if (!this._doorOperationOwns(generation)) return;
    this._clearDoorOperationTimeout();
    const action = this._doorOperationAction ?? "operate";
    this._doorOperationState = DOOR_OPERATION_STATE.FAILED;
    this._doorOperationError = {
      title: `Unable to ${action}.`,
      message: "The device did not confirm the requested state.",
    };
    this._updateDoorOperationSurfaces();
  }

  _updateDoorOperationControls() {
    if (!this._doorControlDialogOpen || this._removeDoorConfirmationOpen) return;
    const region = this.shadowRoot.querySelector("#door-operation-region");
    const slider = this.shadowRoot.querySelector("#door-slide-action");
    const error = this.shadowRoot.querySelector("#door-operation-error");
    const errorTitle = this.shadowRoot.querySelector("#door-operation-error-title");
    const errorMessage = this.shadowRoot.querySelector("#door-operation-error-message");
    const remove = this.shadowRoot.querySelector("#open-remove-door-confirmation");
    if (!region || !slider || !error) return;

    const available = this._availableDoorOperation();
    const unavailable = Boolean(this._doorControlLoading || this._doorControlError);
    const unavailableOperation = unavailable
      ? this._doorOperationForSelectedState()
      : undefined;
    const active = this._doorOperationAccessPointId === this._selectedDoorId;
    const busy = active && this._doorOperationCommandIsPending();
    const anotherDoorBusy = !active && this._doorOperationCommandIsPending();
    const success = active && this._doorOperationState === DOOR_OPERATION_STATE.SUCCESS;
    const failed = active && this._doorOperationState === DOOR_OPERATION_STATE.FAILED;
    const action = busy || success
      ? this._doorOperationAction
      : available?.action ?? unavailableOperation?.action;
    const showSlider = Boolean(available || unavailableOperation || busy || success);
    region.hidden = !showSlider && !failed;
    slider.hidden = !showSlider;
    error.hidden = !failed || !this._doorOperationError;
    errorTitle.textContent = this._doorOperationError?.title ?? "";
    errorMessage.textContent = this._doorOperationError?.message ?? "";
    if (remove) remove.disabled = this._doorOperationCommandIsPending() || success;

    if (!showSlider || !action) return;
    if (anotherDoorBusy) {
      slider.label = "Another door is updating";
    } else if (unavailable) {
      slider.label = "Status unavailable";
    } else if (success) {
      slider.label = ({ unlock: "Unlocked", lock: "Locked", open: "Opened", close: "Closed", release: "Released", operate: "Activated" })[action];
    } else if (busy) {
      slider.label = ({ unlock: "Unlocking…", lock: "Locking…", open: "Opening…", close: "Closing…", release: "Releasing…", operate: "Activating…" })[action];
    } else {
      slider.label = ({ unlock: "Slide to Unlock", lock: "Slide to Lock", open: "Slide to Open", close: "Slide to Close", release: "Slide to Release", operate: "Slide to Activate" })[action];
    }
    slider.direction = "right";
    slider.disabled = unavailable || anotherDoorBusy || (!available && !busy && !success);
    slider.busy = busy;
    slider.success = success;
  }

  _clearDoorOperationTimeout() {
    if (this._doorOperationTimeoutTimer === undefined) return;
    window.clearTimeout(this._doorOperationTimeoutTimer);
    this._doorOperationTimeoutTimer = undefined;
  }

  _clearDoorOperationTimers() {
    this._clearDoorOperationTimeout();
    if (this._doorOperationSuccessTimer !== undefined) {
      window.clearTimeout(this._doorOperationSuccessTimer);
      this._doorOperationSuccessTimer = undefined;
    }
  }

  _cancelDoorSlide() {
    this.shadowRoot?.querySelector?.("#door-slide-action")?.cancel?.();
    if (this._doorOperationState === DOOR_OPERATION_STATE.SLIDING) {
      this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
    }
  }

  _resetDoorOperation() {
    this._clearDoorOperationTimers();
    this._doorOperationGeneration += 1;
    this._doorOperationState = DOOR_OPERATION_STATE.IDLE;
    this._doorOperationAction = undefined;
    this._doorOperationTargetState = undefined;
    this._doorOperationError = undefined;
    this._doorOperationSawTransition = false;
    this._doorOperationAccessPointId = undefined;
  }

  async _openGiveAccessWizard() {
    if (!this._selectedPerson) {
      return;
    }
    this._giveAccessDialogOpen = true;
    this._accessPoints = [];
    this._accessPointsLoading = true;
    this._accessPointsError = undefined;
    this._selectedAccessPoint = undefined;
    this._giveAccessStep = "where";
    this._pinMode = "generated";
    this._pin = undefined;
    this._pinValidationError = undefined;
    this._provisioning = false;
    this._provisionError = undefined;
    this._provisionResult = undefined;
    this._mountGiveAccessDialog();

    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: LIST_ACCESS_POINTS_ACTION,
        service_data: {},
        return_response: true,
      });
      this._accessPoints = (result.response?.access_points ?? []).filter(
        (door) => door.capabilities?.pin !== false,
      );
    } catch (_error) {
      this._accessPointsError = "HomePASS could not load access points. Try again.";
    } finally {
      this._accessPointsLoading = false;
      this._updateGiveAccessDialog();
    }
  }

  _handleGiveAccessClick(event) {
    event.preventDefault();
    event.stopPropagation();
    window.setTimeout(() => void this._openGiveAccessWizard(), 0);
  }

  _currentManageAccessState() {
    return this._manageAccessSession?.state;
  }

  _transitionManageAccessState(nextState, context = {}) {
    const session = this._manageAccessSession;
    if (!session) {
      return false;
    }
    const currentState = session.state;
    if (currentState === nextState) {
      session.context = context;
      this._updateManageAccessDialog();
      return true;
    }
    if (!MANAGE_ACCESS_TRANSITIONS[currentState]?.has(nextState)) {
      throw new Error(`Invalid Manage Access transition: ${currentState} -> ${nextState}`);
    }
    if (currentState === MANAGE_ACCESS_STATE.VIEW) {
      this._clearCredentialReveal("state_changed");
    }
    session.state = nextState;
    session.stateEntryId += 1;
    session.context = context;
    this._updateManageAccessDialog();
    return true;
  }

  _captureManageAccessRequest(kind, expectedState) {
    const session = this._manageAccessSession;
    const expectedStates = Array.isArray(expectedState) ? expectedState : [expectedState];
    if (
      !this._manageAccessDialogOpen ||
      !session ||
      session.personId !== this._selectedPerson?.person_id ||
      !expectedStates.includes(session.state)
    ) {
      return undefined;
    }
    const sequence = (session.requestSequences[kind] ?? 0) + 1;
    session.requestSequences[kind] = sequence;
    return {
      sessionId: session.id,
      state: session.state,
      stateEntryId: session.stateEntryId,
      kind,
      sequence,
      personId: session.personId,
      accessPointId: session.accessPointId,
    };
  }

  _manageAccessOwnsRequest(ownership) {
    const session = this._manageAccessSession;
    return Boolean(
      this._manageAccessDialogOpen &&
      session &&
      session.id === ownership?.sessionId &&
      session.state === ownership.state &&
      session.stateEntryId === ownership.stateEntryId &&
      session.requestSequences[ownership.kind] === ownership.sequence &&
      session.personId === ownership.personId &&
      session.accessPointId === ownership.accessPointId &&
      session.personId === this._selectedPerson?.person_id,
    );
  }

  async _openManageAccessDialog() {
    if (
      !this._selectedPerson ||
      this._manageAccessDialogOpen ||
      this._manageAccessOpenRequest
    ) {
      return;
    }
    const personId = this._selectedPerson.person_id;
    const openRequest = {
      sequence: ++this._manageAccessOpenSequence,
      personId,
    };
    this._manageAccessOpenRequest = openRequest;
    try {
      if (
        !this._manageAccessMetadataCurrent ||
        this._manageAccessReplacementCapability() === "loading"
      ) {
        try {
          await this._refreshAccessState(personId);
        } catch (_error) {
          if (
            this._manageAccessOpenRequest === openRequest &&
            this._selectedPerson?.person_id === personId
          ) {
            this._manageAccessRefreshError =
              "HomePASS could not refresh access details. Close and reopen Manage Access to try again.";
          }
        }
      }
      if (
        this._manageAccessOpenRequest !== openRequest ||
        this._selectedPerson?.person_id !== personId
      ) {
        return;
      }
      const target = this._accessMetadata.find((metadata) => metadata.credential_stored);
      const discardReason = !this._manageAccessSession
        ? "session_missing"
        : this._manageAccessSession.personId !== personId
          ? "person_changed"
          : "access_point_changed";
      this._clearCredentialReveal(discardReason);
      this._beginManageAccessSession(
        personId,
        target?.access_point_id,
      );
      this._resetChangePin();
      this._manageAccessDialogOpen = true;
      this._render();
    } finally {
      if (this._manageAccessOpenRequest === openRequest) {
        this._manageAccessOpenRequest = undefined;
      }
    }
  }

  _closeManageAccessDialog() {
    if (!this._manageAccessDialogOpen) {
      return;
    }
    this._clearAccessUpdatePoll();
    this._clearCredentialReveal("dialog_closed");
    this._clearRevealCooldown();
    this._manageAccessDialogOpen = false;
    this._manageAccessSession = undefined;
    this._manageAccessDialogElement = undefined;
    this._resetChangePin();
    this._editAccessPointsError = undefined;
    this._editAccessPendingIds = new Set();
    this._editAccessSelection = new Set();
    this._editNfcAccessSelection = new Set();
    this._editNfcAccessSelection = new Set();
    this._editAccessScheduleMode = "permanent";
    this._editAccessScheduleId = "";
    this._editAccessSchedules = [];
    this._editAccessNewSchedule = this._defaultScheduleForm();
    this._editAccessPin = "";
    this._editAccessRequestId = undefined;
    this._render();
  }

  async _openEditAccessDialog() {
    if (!this._selectedPerson) {
      return;
    }
    if (
      !this._manageAccessDialogOpen ||
      this._manageAccessSession?.personId !== this._selectedPerson.person_id ||
      this._currentManageAccessState() !== MANAGE_ACCESS_STATE.VIEW
    ) {
      return;
    }
    this._accessUpdateNotice = undefined;
    this._editAccessPointsLoading = true;
    this._editAccessPointsError = undefined;
    this._editAccessPendingIds = new Set();
    this._editAccessScheduleMode = "permanent";
    this._editAccessScheduleId = "";
    this._editAccessSchedules = [];
    this._editAccessNewSchedule = this._defaultScheduleForm();
    this._editAccessPin = "";
    this._editAccessRequestId = this._newRevealRequestId();
    this._editAccessSelection = new Set(
      this._accessMetadata.map((metadata) => metadata.access_point_id),
    );
    this._editNfcAccessSelection = new Set(this._nfcAccessSelection);
    this._transitionManageAccessState(MANAGE_ACCESS_STATE.EDIT_ACCESS);
    const ownership = this._captureManageAccessRequest(
      "edit_access_load",
      MANAGE_ACCESS_STATE.EDIT_ACCESS,
    );
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_USER_SETUP_OPTIONS_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      const setupAccessPoints = result.response?.access_points ?? [];
      const accessPointsById = new Map(
        setupAccessPoints.map((door) => [this._userOptionAccessPointId(door), door]),
      );
      for (const door of this._nfcAccessPoints) {
        if (!accessPointsById.has(door.id)) accessPointsById.set(door.id, door);
      }
      this._accessPoints = [...accessPointsById.values()];
      this._editAccessSchedules = result.response?.schedules ?? [];
      if (!this._personHasStoredCredential()) {
        const currentScheduleId = this._selectedPerson?.schedule_id ?? "";
        const permanent = this._editAccessSchedules.find(
          (schedule) => schedule.name === "Permanent",
        );
        if (currentScheduleId && currentScheduleId !== permanent?.schedule_id) {
          this._editAccessScheduleMode = "existing";
          this._editAccessScheduleId = currentScheduleId;
        } else {
          this._editAccessScheduleMode = "permanent";
          this._editAccessScheduleId = permanent?.schedule_id ?? "";
        }
      }
      this._editAccessPointsLoading = false;
      this._updateManageAccessDialog();
    } catch (_error) {
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      this._editAccessPointsLoading = false;
      this._editAccessPointsError = "HomePASS could not load access points. Try again.";
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
        source: "edit_access",
        message: this._editAccessPointsError,
        retry: false,
      });
    }
  }

  _cancelEditAccess() {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (
      state !== MANAGE_ACCESS_STATE.EDIT_ACCESS &&
      !(state === MANAGE_ACCESS_STATE.ERROR && context.source === "edit_access")
    ) {
      return;
    }
    this._editAccessPointsError = undefined;
    this._editAccessSelection = new Set();
    this._editNfcAccessSelection = new Set();
    this._transitionManageAccessState(MANAGE_ACCESS_STATE.VIEW);
  }

  _resetChangePin() {
    this._clearReplacementValidationTimer();
    this._changePinValue = "";
    this._changePinValid = false;
    this._changePinChanged = false;
    this._changePinValidationGeneration += 1;
    this._changePinError = undefined;
    this._changePinRetry = false;
    this._changePinRequirements = undefined;
  }

  _editAccessScheduleError() {
    if (this._personHasStoredCredential() || this._editAccessSelection.size === 0 ||
        this._accessMetadata.length > 0) return undefined;
    if (this._editAccessScheduleMode === "existing") {
      return this._editAccessScheduleId ? undefined : "Choose a schedule.";
    }
    if (this._editAccessScheduleMode !== "new") return undefined;
    const errors = this._scheduleValidationFor(this._editAccessNewSchedule);
    return errors.dates || errors.days || errors.times || undefined;
  }

  _editAccessSchedulePayload() {
    if (this._editAccessScheduleMode === "new") {
      return {
        schedule: {
          mode: "new",
          definition: {
            name: `${this._selectedPerson.display_name} Schedule`,
            ...this._schedulePolicyPayload(this._editAccessNewSchedule),
          },
        },
      };
    }
    const scheduleId = this._editAccessScheduleMode === "existing"
      ? this._editAccessScheduleId
      : this._editAccessSchedules.find((schedule) => schedule.name === "Permanent")?.schedule_id;
    return { schedule_id: scheduleId };
  }

  _editAccessAssignmentReady() {
    if (this._editAccessSelection.size === 0) return false;
    if (!this._personHasStoredCredential() && !/^\d{4,10}$/.test(this._editAccessPin)) {
      return false;
    }
    if (this._editAccessScheduleError()) return false;
    if (this._editAccessScheduleMode === "new") return true;
    const selectedId = this._editAccessScheduleMode === "existing"
      ? this._editAccessScheduleId
      : this._editAccessSchedules.find((schedule) => schedule.name === "Permanent")?.schedule_id;
    const selected = this._editAccessSchedules.find(
      (schedule) => schedule.schedule_id === selectedId,
    );
    return Boolean(
      selected && (this._accessMetadata.length > 0 || selected.enabled !== false),
    );
  }

  _focusEditAccessInvalidField() {
    let selector;
    if (!this._personHasStoredCredential() && !/^\d{4,10}$/.test(this._editAccessPin)) {
      selector = "#assign-access-pin";
    } else if (this._editAccessScheduleMode === "existing") {
      selector = "#assign-access-schedule-id";
    } else if (this._editAccessScheduleMode === "new") {
      const form = this._editAccessNewSchedule;
      if (form.validity === "specific-dates") {
        for (const field of ["startsDate", "startsTime", "endsDate", "endsTime"]) {
          if (!form[field]) {
            selector = `#assign-access-${field}`;
            break;
          }
        }
        if (!selector && `${form.endsDate}T${form.endsTime}` <=
          `${form.startsDate}T${form.startsTime}`) selector = "#assign-access-endsDate";
      }
      if (!selector && form.accessHours === "specific-hours") {
        selector = form.selectedDays.length === 0
          ? ".manage-access-schedule .wizard-new-schedule input[type=checkbox]"
          : !form.startTime ? "#assign-access-startTime" : "#assign-access-endTime";
      }
    }
    if (selector) queueMicrotask(() => this.shadowRoot.querySelector(selector)?.focus());
  }

  _clearReplacementValidationTimer() {
    if (this._changePinValidationTimer !== undefined) {
      window.clearTimeout(this._changePinValidationTimer);
      this._changePinValidationTimer = undefined;
    }
  }

  async _saveAccessSelection() {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (
      !this._selectedPerson ||
      this._manageAccessSession?.personId !== this._selectedPerson.person_id ||
      (
        state !== MANAGE_ACCESS_STATE.EDIT_ACCESS &&
        !(state === MANAGE_ACCESS_STATE.ERROR && context.source === "edit_access" && context.retry)
      )
    ) {
      return;
    }
    const personId = this._selectedPerson.person_id;
    const scheduleError = this._editAccessScheduleError();
    if (scheduleError) {
      this._showAccessUpdateError(scheduleError);
      this._focusEditAccessInvalidField();
      return;
    }
    const needsPin = !this._personHasStoredCredential();
    if (needsPin && this._editAccessSelection.size > 0 && !/^\d{4,10}$/.test(this._editAccessPin)) {
      this._showAccessUpdateError("Enter a PIN containing 4 to 10 digits.");
      this._focusEditAccessInvalidField();
      return;
    }
    this._editAccessPointsError = undefined;
    this._accessUpdateNotice = undefined;
    this._transitionManageAccessState(MANAGE_ACCESS_STATE.SAVING_ACCESS);
    const ownership = this._captureManageAccessRequest(
      "edit_access_save",
      MANAGE_ACCESS_STATE.SAVING_ACCESS,
    );
    try {
      const assigningPin = needsPin && this._editAccessSelection.size > 0;
      if (!assigningPin && needsPin) {
        if (!await this._saveEditedNfcAccess(personId)) {
          throw new Error("nfc_access_save_failed");
        }
        this._finishAccessUpdate("Door access methods updated.");
        return;
      }
      const serviceData = assigningPin
        ? {
            request_id: this._editAccessRequestId,
            person_id: personId,
            access_point_ids: [...this._editAccessSelection],
            ...this._editAccessSchedulePayload(),
            ...(needsPin ? { pin: this._editAccessPin } : {}),
          }
        : {
            person_id: personId,
            access_point_ids: [...this._editAccessSelection],
          };
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: assigningPin ? ASSIGN_USER_ACCESS_ACTION : UPDATE_ACCESS_ACTION,
        service_data: serviceData,
        return_response: true,
      });
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      const response = result.response ?? {};
      if (assigningPin) {
        this._editAccessPin = "";
        if (
          !["completed", "needs_attention", "failed"].includes(response.status) ||
          !this._validUserAssignments(response.assignments, this._editAccessSelection)
        ) {
          throw new Error("invalid_assignment_response");
        }
        await this._refreshAccessState(personId, ownership);
        if (!this._manageAccessOwnsRequest(ownership)) return;
        const assignments = Array.isArray(response.assignments) ? response.assignments : [];
        const { assigned, already, attention, failed } =
          this._userAssignmentCounts(assignments);
        this._accessUpdateNotice = [
          assigned > 0
            ? `${assigned} ${assigned === 1 ? "door" : "doors"} assigned.`
            : "",
          already > 0 ? `${already} already assigned.` : "",
          failed > 0
            ? `Access was not added for ${failed} ${failed === 1 ? "door" : "doors"}. Use Manage Access to try again.`
            : "",
          attention > 0
            ? `${attention} ${attention === 1 ? "door needs" : "doors need"} synchronization attention.`
            : "",
        ].filter(Boolean).join(" ");
        if (failed === assignments.length) {
          const failedNames = assignments
            .filter((assignment) => assignment.status === "failed")
            .map((assignment) => assignment.display_name)
            .filter((name) => typeof name === "string" && name.length > 0);
          const message = failedNames.length === 1
            ? `HomePASS could not assign ${failedNames[0]}.`
            : "HomePASS could not assign the selected doors.";
          this._accessUpdateNotice = undefined;
          this._refreshPersonDetailsInPlace();
          this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
            source: "edit_access",
            message,
            retry: true,
            newRequestOnRetry: true,
          });
          return;
        }
        if (failed > 0 || attention > 0) {
          this._finishAccessUpdate(this._accessUpdateNotice, MANAGE_ACCESS_STATE.PARTIAL);
          return;
        }
        if (!await this._saveEditedNfcAccess(personId)) {
          this._finishAccessUpdate(
            `${this._accessUpdateNotice} NFC access could not be saved.`,
            MANAGE_ACCESS_STATE.PARTIAL,
          );
          return;
        }
        this._finishAccessUpdate(this._accessUpdateNotice);
        return;
      }
      if (response.status === "failed") {
        if (response.reason === "pin_incompatible") {
          this._showAccessUpdateError(
            "This saved PIN is not compatible with Nuki. Change it to six digits using 1–9, and do not begin with 12.",
            {errorCode: "pin_incompatible"},
          );
          return;
        }
        const failedAccessPointId = (response.access_points ?? [])
          .find((item) => item.status === "failed")?.access_point_id;
        const failedAccessPoint = this._accessPoints
          .find((item) => item.id === failedAccessPointId);
        this._showAccessUpdateError(
          failedAccessPoint?.display_name
            ? `HomePASS could not save access for ${failedAccessPoint.display_name}. Try again.`
            : "HomePASS could not save all access changes. Try again.",
        );
        return;
      }
      if (response.status === "pending_verification") {
        if (!await this._saveEditedNfcAccess(personId)) {
          throw new Error("nfc_access_save_failed");
        }
        this._editAccessPendingIds = new Set(
          (response.access_points ?? [])
            .filter((item) => item.status === "pending_verification")
            .map((item) => item.access_point_id),
        );
        this._transitionManageAccessState(MANAGE_ACCESS_STATE.VERIFYING_ACCESS);
        this._scheduleAccessUpdatePoll(personId);
        return;
      }
      if (response.status === "needs_attention" || response.status === "out_of_sync") {
        this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
          source: "edit_access",
          status: response.status,
          retry: true,
        });
        return;
      }
      if (!await this._saveEditedNfcAccess(personId)) {
        throw new Error("nfc_access_save_failed");
      }
      await this._refreshAccessState(personId, ownership);
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      this._finishAccessUpdate();
    } catch (_error) {
      if (this._manageAccessOwnsRequest(ownership)) {
        this._showAccessUpdateError("HomePASS could not save the access changes. Try again.");
      }
    }
  }

  async _saveEditedNfcAccess(personId) {
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: UPDATE_NFC_ACCESS_ACTION,
        service_data: {
          person_id: personId,
          access_point_ids: [...this._editNfcAccessSelection],
        },
        return_response: true,
      });
      const assigned = result.response?.access_point_ids ?? [];
      this._nfcAccessSelection = new Set(assigned);
      this._editNfcAccessSelection = new Set(assigned);
      this._nfcAccessSelectionInitialized = true;
      if (this._nfcEnrollment) {
        this._nfcEnrollment = {
          ...this._nfcEnrollment,
          access_count: assigned.length,
          access_point_ids: assigned,
        };
      }
      return true;
    } catch (_error) {
      return false;
    }
  }

  _showAccessUpdateError(message, context = {}) {
    this._accessUpdateNotice = undefined;
    this._editAccessPointsError = message;
    this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
      source: "edit_access",
      message,
      retry: true,
      ...context,
    });
  }

  async _refreshAccessState(personId, ownership = undefined) {
    const previousRefreshError = this._manageAccessRefreshError;
    const result = await this._hass.callWS({
      type: "call_service",
      domain: DOMAIN,
      service: GET_PERSON_ACTION,
      service_data: { person_id: personId },
      return_response: true,
    });
    const person = result.response?.person;
    const metadata = result.response?.access_metadata;
    if (
      this._detailsPersonId !== personId ||
      !person ||
      person.person_id !== personId ||
      !Array.isArray(metadata)
    ) {
      throw new Error("access_refresh_invalid");
    }
    if (ownership && !this._manageAccessOwnsRequest(ownership)) {
      return undefined;
    }
    // Person, target metadata, and runtime capabilities come from one canonical
    // response and are published together so the dialog never mixes revisions.
    const credentialStored = result.response?.credential_stored === true ||
      metadata.some((record) => record.credential_stored);
    const nextAccessState = { person, metadata, credentialStored };
    this._selectedPerson = nextAccessState.person;
    this._accessMetadata = nextAccessState.metadata;
    this._personCredentialStored = nextAccessState.credentialStored;
    this._manageAccessMetadataCurrent = true;
    this._manageAccessRefreshError = undefined;
    if (this._revealCooldownTimer === undefined) {
      this._currentRevealController()?.setBlocked(false);
      const errorElement = this.shadowRoot?.querySelector?.("#reveal-pin-error");
      if (errorElement && errorElement.textContent === previousRefreshError) {
        errorElement.hidden = true;
        errorElement.textContent = "";
      }
    }
    return this._accessMetadata;
  }

  _scheduleAccessUpdatePoll(personId) {
    this._clearAccessUpdatePoll();
    this._editAccessPollTimer = window.setTimeout(
      () => void this._pollAccessUpdate(personId),
      ACCESS_UPDATE_POLL_INTERVAL,
    );
  }

  async _pollAccessUpdate(personId) {
    this._editAccessPollTimer = undefined;
    if (
      !this._manageAccessDialogOpen ||
      this._currentManageAccessState() !== MANAGE_ACCESS_STATE.VERIFYING_ACCESS ||
      this._editAccessPendingIds.size === 0
    ) {
      return;
    }
    const ownership = this._captureManageAccessRequest(
      "edit_access_poll",
      MANAGE_ACCESS_STATE.VERIFYING_ACCESS,
    );
    try {
      const metadata = await this._refreshAccessState(personId, ownership);
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      const byAccessPoint = new Map(
        metadata.map((relationship) => [relationship.access_point_id, relationship]),
      );
      let terminalStatus;
      let stillPending = false;
      for (const accessPointId of this._editAccessPendingIds) {
        const relationship = byAccessPoint.get(accessPointId);
        if (!relationship) {
          continue;
        }
        if (
          relationship.synchronization_status === "pending" ||
          relationship.synchronization_status === "synchronizing"
        ) {
          stillPending = true;
        } else if (relationship.synchronization_status === "retry_required") {
          terminalStatus = "out_of_sync";
        } else if (
          relationship.synchronization_status === "manual_attention_required" ||
          relationship.synchronization_status === "unknown"
        ) {
          terminalStatus = "needs_attention";
        }
      }
      if (terminalStatus) {
        this._editAccessPendingIds = new Set();
        this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
          source: "edit_access",
          status: terminalStatus,
          retry: true,
        });
        return;
      }
      if (stillPending) {
        this._updateManageAccessDialog();
        this._scheduleAccessUpdatePoll(personId);
        return;
      }
      this._finishAccessUpdate();
    } catch (_error) {
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      // A Home Assistant restart may briefly interrupt the read-only poll while
      // the backend resumes persisted verification. Keep the pending UI and
      // reconnect through the normal action channel without repeating the lock
      // operation.
      this._editAccessPointsError =
        "Waiting for Home Assistant to reconnect and confirm the lock.";
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.VERIFYING_ACCESS, {
        message: this._editAccessPointsError,
      });
      this._scheduleAccessUpdatePoll(personId);
    }
  }

  _finishAccessUpdate(message = "Access updated.", terminalState = MANAGE_ACCESS_STATE.SUCCESS) {
    if (![MANAGE_ACCESS_STATE.SAVING_ACCESS, MANAGE_ACCESS_STATE.VERIFYING_ACCESS].includes(
      this._currentManageAccessState(),
    )) {
      return;
    }
    this._clearAccessUpdatePoll();
    this._editAccessPendingIds = new Set();
    this._editAccessSelection = new Set();
    this._accessUpdateNotice ??= "Access updated.";
    this._refreshPersonDetailsInPlace();
    this._editAccessPointsError = undefined;
    this._transitionManageAccessState(terminalState, {
      operation: "edit_access",
      message,
    });
  }

  _refreshPersonDetailsInPlace() {
    // Refresh details content without replacing the mounted access dialog.
    const content = this.shadowRoot.querySelector("#content");
    const title = this.shadowRoot.querySelector("#person-details-title");
    if (!content || !title || !this._detailsPersonId) {
      return;
    }
    content.textContent = "";
    this._renderPersonDetails();
  }

  _clearAccessUpdatePoll() {
    if (this._editAccessPollTimer !== undefined) {
      window.clearTimeout(this._editAccessPollTimer);
      this._editAccessPollTimer = undefined;
    }
  }

  _closeGiveAccessWizard() {
    this._giveAccessDialogOpen = false;
    this._accessPointsError = undefined;
    this._selectedAccessPoint = undefined;
    this._giveAccessStep = "where";
    this._pinMode = "generated";
    this._pin = undefined;
    this._pinValidationError = undefined;
    this._provisionError = undefined;
    this._provisionResult = undefined;
    this._render();
  }

  _continueGiveAccessWizard() {
    if (this._giveAccessStep === "where") {
      if (!this._selectedAccessPoint) {
        return;
      }
      this._giveAccessStep = "pin";
      this._pinMode = "generated";
      this._pin = this._generateSecurePin();
      this._pinValidationError = undefined;
      this._updateGiveAccessDialog();
      return;
    }
    if (this._giveAccessStep === "pin") {
      void this._provisionGiveAccess();
      return;
    }
    if (this._giveAccessStep === "result") {
      const personId = this._selectedPerson?.person_id;
      this._closeGiveAccessWizard();
      if (personId) {
        void this._openPersonDetails(personId);
      }
    }
  }

  _backGiveAccessWizard() {
    if (this._provisioning || this._giveAccessStep !== "pin") {
      return;
    }
    this._giveAccessStep = "where";
    this._pin = undefined;
    this._pinValidationError = undefined;
    this._provisionError = undefined;
    this._updateGiveAccessDialog();
  }

  _generateSecurePin() {
    // Six non-zero digits satisfy Nuki keypad constraints while remaining valid
    // for the existing Yale/Z-Wave path.
    const range = 9 ** 6;
    const limit = Math.floor(2 ** 32 / range) * range;
    const random = new Uint32Array(1);
    while (true) {
      do {
        crypto.getRandomValues(random);
      } while (random[0] >= limit);
      let value = random[0] % range;
      let pin = "";
      for (let index = 0; index < 6; index += 1) {
        pin = String((value % 9) + 1) + pin;
        value = Math.floor(value / 9);
      }
      if (!pin.startsWith("12") && !this._isTrivialPin(pin)) {
        return pin;
      }
    }
  }

  _isTrivialPin(pin) {
    if (/^(\d{1,3})\1+$/.test(pin)) {
      return true;
    }
    const ascending = "0123456789012345";
    const descending = "9876543210987654";
    return ascending.includes(pin) || descending.includes(pin);
  }

  _pinIsValid() {
    return typeof this._pin === "string" && /^[0-9]{4,10}$/.test(this._pin);
  }

  async _provisionGiveAccess() {
    if (
      this._provisioning ||
      !this._pinIsValid() ||
      !this._selectedPerson?.person_id ||
      !this._selectedAccessPoint?.id
    ) {
      if (!this._pinIsValid()) {
        this._pinValidationError = "Enter a PIN containing 4 to 10 digits.";
        this._updateGiveAccessDialog();
      }
      return;
    }

    this._provisioning = true;
    this._provisionError = undefined;
    this._updateGiveAccessDialog();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GIVE_ACCESS_ACTION,
        service_data: {
          person_id: this._selectedPerson.person_id,
          access_point_id: this._selectedAccessPoint.id,
          pin: this._pin,
        },
        return_response: true,
      });
      const response = result.response;
      if (response?.status === "verified" || response?.status === "inconclusive") {
        this._provisionResult = response;
        this._giveAccessStep = "result";
      } else {
        this._provisionError =
          "HomePASS could not create access. Check the lock and try again.";
      }
    } catch (_error) {
      this._provisionError = "HomePASS could not create access. Check the lock and try again.";
    } finally {
      this._provisioning = false;
      this._updateGiveAccessDialog();
    }
  }

  async _openAddPersonDialog() {
    if (this._addUserWizardOpen) return;
    this._clearQuickPinReveals();
    this._form = this._emptyForm();
    this._editing = false;
    this._validationError = undefined;
    this._dialogOpen = true;
    this._addUserWizardOpen = true;
    this._addUserForm = this._emptyAddUserForm();
    this._addUserOptions = { access_points: [], schedules: [] };
    this._addUserOptionsLoading = true;
    this._addUserOptionsError = undefined;
    this._addUserSubmitting = false;
    this._addUserError = undefined;
    this._addUserResult = undefined;
    this._addUserRequestId = this._newRevealRequestId();
    const openerId = this.shadowRoot.activeElement?.id;
    this._addUserReturnFocusSelector = [
      "add-person",
      "dashboard-add-person",
      "empty-add-person",
    ].includes(openerId)
      ? `#${openerId}`
      : this._currentPage === "dashboard"
        ? "#dashboard-add-person"
        : "#add-person";
    const generation = ++this._addUserOptionsGeneration;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_USER_SETUP_OPTIONS_ACTION,
        service_data: {},
        return_response: true,
      });
      if (!this._addUserWizardOwns(generation)) return;
      const response = result.response ?? {};
      if (!Array.isArray(response.access_points) || !Array.isArray(response.schedules)) {
        throw new Error("invalid_setup_options");
      }
      this._addUserOptions = {
        access_points: response.access_points,
        schedules: response.schedules,
      };
    } catch (_error) {
      if (!this._addUserWizardOwns(generation)) return;
      this._addUserOptionsError =
        "HomePASS could not load door and schedule options. Close and try again.";
    } finally {
      if (this._addUserWizardOwns(generation)) {
        this._addUserOptionsLoading = false;
        this._render();
      }
    }
  }

  _addUserWizardOwns(generation) {
    return this._addUserWizardOpen && this._addUserOptionsGeneration === generation;
  }

  _addUserSubmissionOwns(generation, requestId) {
    return (
      this._addUserWizardOwns(generation) &&
      this._addUserRequestId === requestId
    );
  }

  _userOptionAccessPointId(option) {
    return option?.id ?? option?.access_point_id;
  }

  _compatibleUserSchedules(schedules = this._addUserOptions.schedules) {
    return schedules.filter((schedule) => schedule.enabled !== false);
  }

  _validUserAssignments(assignments, requestedAccessPointIds) {
    if (!Array.isArray(assignments)) return false;
    const requested = new Set(requestedAccessPointIds);
    const seen = new Set();
    const validStatuses = new Set([
      "added",
      "already_assigned",
      "completed",
      "failed",
      "needs_attention",
      "out_of_sync",
      "pending_verification",
    ]);
    for (const assignment of assignments) {
      if (
        !assignment ||
        typeof assignment.access_point_id !== "string" ||
        !requested.has(assignment.access_point_id) ||
        seen.has(assignment.access_point_id) ||
        !validStatuses.has(assignment.status)
      ) {
        return false;
      }
      seen.add(assignment.access_point_id);
    }
    return seen.size === requested.size;
  }

  _userAssignmentCounts(assignments) {
    const counts = { assigned: 0, already: 0, attention: 0, failed: 0 };
    for (const assignment of assignments) {
      if (["added", "completed"].includes(assignment.status)) counts.assigned += 1;
      if (assignment.status === "already_assigned") counts.already += 1;
      if (
        ["needs_attention", "out_of_sync", "pending_verification"].includes(
          assignment.status,
        )
      ) counts.attention += 1;
      if (assignment.status === "failed") counts.failed += 1;
    }
    return counts;
  }

  _userCreationNotice(assignments) {
    const { attention, failed } = this._userAssignmentCounts(assignments);
    return [
      "User created.",
      failed > 0
        ? `Access was not added for ${failed} ${failed === 1 ? "door" : "doors"}. Use Manage Access to try again.`
        : "",
      attention > 0
        ? `${attention} ${attention === 1 ? "door needs" : "doors need"} synchronization attention.`
        : "",
      assignments.length > 0 && failed === 0 && attention === 0
        ? "Door synchronization status is shown below."
        : "",
    ].filter(Boolean).join(" ");
  }

  _emptyAddUserForm() {
    return {
      displayName: "",
      description: "",
      notes: "",
      pin: "",
      pinMode: "manual",
      accessPointIds: new Set(),
      scheduleMode: "permanent",
      existingScheduleId: "",
      newSchedule: this._defaultScheduleForm(),
    };
  }

  _resetAddUserWizard() {
    this._addUserOptionsGeneration += 1;
    this._addUserWizardOpen = false;
    this._addUserOptions = { access_points: [], schedules: [] };
    this._addUserOptionsLoading = false;
    this._addUserOptionsError = undefined;
    this._addUserSubmitting = false;
    this._addUserError = undefined;
    this._addUserResult = undefined;
    this._addUserRequestId = undefined;
    this._addUserReturnFocusSelector = undefined;
    this._addUserDialogElement = undefined;
    this._addUserForm = this._emptyAddUserForm();
  }

  _addUserDetailsError() {
    const form = this._addUserForm;
    if (!form.displayName.trim()) return "Enter a display name.";
    if (form.description.trim().length > MAX_USER_DESCRIPTION_LENGTH) {
      return `Description must be ${MAX_USER_DESCRIPTION_LENGTH} characters or fewer.`;
    }
    if (form.pin && !/^\d{4,10}$/.test(form.pin)) {
      return "Leave the PIN blank or enter 4 to 10 digits.";
    }
    if (form.accessPointIds.size > 0 && !form.pin) {
      return "Enter a PIN before assigning keypad door access.";
    }
    return undefined;
  }

  _addUserScheduleError() {
    if (this._addUserForm.accessPointIds.size === 0) return undefined;
    if (this._addUserForm.scheduleMode === "existing") {
      return this._addUserForm.existingScheduleId ? undefined : "Choose a schedule.";
    }
    if (this._addUserForm.scheduleMode !== "new") return undefined;
    const errors = this._scheduleValidationFor(this._addUserForm.newSchedule);
    return errors.dates || errors.days || errors.times || undefined;
  }

  _addUserFormError() {
    return this._addUserDetailsError() ?? this._addUserScheduleError();
  }

  _addUserInvalidFieldSelector() {
    if (this._addUserDetailsError()) {
      if (!this._addUserForm.displayName.trim()) return "#add-user-display-name";
      if (this._addUserForm.description.trim().length > MAX_USER_DESCRIPTION_LENGTH) {
        return "#add-user-description";
      }
      return "#add-user-pin";
    }
    if (this._addUserForm.scheduleMode === "existing") {
      return "#add-user-existing-schedule";
    }
    const schedule = this._addUserForm.newSchedule;
    if (schedule.validity === "specific-dates") {
      for (const field of ["startsDate", "startsTime", "endsDate", "endsTime"]) {
        if (!schedule[field]) return `#add-user-${field}`;
      }
      if (`${schedule.endsDate}T${schedule.endsTime}` <=
        `${schedule.startsDate}T${schedule.startsTime}`) {
        return "#add-user-endsDate";
      }
    }
    if (schedule.accessHours === "specific-hours") {
      if (schedule.selectedDays.length === 0) {
        return ".wizard-new-schedule input[type=checkbox]";
      }
      if (!schedule.startTime) return "#add-user-startTime";
      return "#add-user-endTime";
    }
    return "#add-user-schedule-section input";
  }

  _addUserCanSubmit() {
    return !this._addUserSubmitting &&
      !this._addUserOptionsLoading &&
      !this._addUserOptionsError &&
      !this._addUserFormError();
  }

  _syncAddUserCreateState() {
    const create = this.shadowRoot.querySelector("#create-add-user");
    if (create) create.disabled = !this._addUserCanSubmit();
    const error = this.shadowRoot.querySelector("#add-user-error");
    if (error) {
      error.hidden = !this._addUserError;
      error.textContent = this._addUserError ?? "";
    }
    const scheduleError = this.shadowRoot.querySelector("#add-user-schedule-error");
    if (scheduleError) {
      const message = this._addUserScheduleError();
      scheduleError.hidden = !message;
      scheduleError.textContent = message ?? "";
    }
  }

  _focusAddUserInvalidField() {
    const selector = this._addUserInvalidFieldSelector();
    queueMicrotask(() => this.shadowRoot.querySelector(selector)?.focus());
  }

  _submitAddUserForm() {
    if (this._addUserSubmitting || this._addUserOptionsLoading || this._addUserOptionsError) {
      return;
    }
    const error = this._addUserFormError();
    if (error) {
      this._addUserError = error;
      this._render();
      this._focusAddUserInvalidField();
      return;
    }
    void this._submitAddUser();
  }

  _addUserSchedulePayload() {
    const form = this._addUserForm;
    if (form.accessPointIds.size === 0 || form.scheduleMode === "permanent") {
      return { mode: "permanent" };
    }
    if (form.scheduleMode === "existing") {
      return { mode: "existing", schedule_id: form.existingScheduleId };
    }
    return {
      mode: "new",
      definition: {
        name: `${form.displayName.trim()} Schedule`,
        ...this._schedulePolicyPayload(form.newSchedule),
      },
    };
  }

  _friendlyAddUserError(error) {
    const message = String(error?.message ?? error ?? "").toLowerCase();
    if (message.includes("already used") || message.includes("different user details")) {
      return "This setup can no longer be retried safely. Close Add User and start again.";
    }
    if (message.includes("display name") || message.includes("duplicate")) {
      return "A user with this display name already exists. Change the name and try again.";
    }
    if (message.includes("pin") && (message.includes("digit") || message.includes("valid"))) {
      return "Enter a PIN containing 4 to 10 digits.";
    }
    if (message.includes("schedule")) {
      return "Review the selected schedule and try again.";
    }
    return "HomePASS could not confirm whether setup finished. Keep this window open and try Create User again.";
  }

  async _submitAddUser() {
    if (this._addUserSubmitting || !this._addUserWizardOpen || !this._addUserRequestId) return;
    const validationError = this._addUserFormError();
    if (validationError) {
      this._addUserError = validationError;
      this._render();
      this._focusAddUserInvalidField();
      return;
    }
    const generation = this._addUserOptionsGeneration;
    const requestId = this._addUserRequestId;
    this._addUserSubmitting = true;
    this._addUserError = undefined;
    this._render();
    const form = this._addUserForm;
    const requestedAccessPointIds = [...form.accessPointIds];
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CREATE_USER_ACTION,
        service_data: {
          request_id: requestId,
          display_name: form.displayName.trim(),
          description: form.description.trim() || null,
          notes: form.notes.trim() || null,
          ...(form.pin ? { pin: form.pin } : {}),
          access_point_ids: requestedAccessPointIds,
          schedule: this._addUserSchedulePayload(),
        },
        return_response: true,
      });
      if (result.response && typeof result.response === "object") result.response.pin = undefined;
      if (!this._addUserSubmissionOwns(generation, requestId)) return;
      const response = result.response ?? {};
      if (
        !response.person?.person_id ||
        !["created", "needs_attention"].includes(response.status) ||
        !this._validUserAssignments(response.assignments, requestedAccessPointIds)
      ) {
        throw new Error("create_user_failed");
      }
      form.pin = "";
      this._addUserResult = response;
      await this._loadPeople();
      if (!this._addUserSubmissionOwns(generation, requestId)) return;
      const personId = response.person.person_id;
      this._accessUpdateNotice = this._userCreationNotice(response.assignments);
      this._dialogOpen = false;
      this._resetAddUserWizard();
      await this._openPersonDetails(personId);
      this._refreshDashboardActivityAfterOperation();
    } catch (error) {
      if (!this._addUserSubmissionOwns(generation, requestId)) return;
      this._addUserError = this._friendlyAddUserError(error);
    } finally {
      if (!this._addUserSubmissionOwns(generation, requestId)) return;
      this._addUserSubmitting = false;
      this._render();
    }
  }

  _openEditPersonDialog() {
    if (!this._selectedPerson) {
      return;
    }
    this._form = {
      displayName: this._selectedPerson.display_name,
      description: this._selectedPerson.description ?? "",
      notes: this._selectedPerson.notes ?? "",
      enabled: this._selectedPerson.enabled,
    };
    this._deleteDialogOpen = false;
    this._editing = true;
    this._validationError = undefined;
    this._dialogOpen = true;
    this._render();
  }

  _closePersonDialog() {
    if (this._saving || this._addUserSubmitting) {
      return;
    }
    const returnFocusSelector = this._addUserWizardOpen
      ? this._addUserReturnFocusSelector
      : "#edit-person";
    this._dialogOpen = false;
    this._editing = false;
    this._validationError = undefined;
    this._resetAddUserWizard();
    this._render();
    queueMicrotask(() => this.shadowRoot.querySelector(returnFocusSelector)?.focus());
  }

  _openDeletePersonDialog() {
    if (!this._selectedPerson) {
      return;
    }
    this._dialogOpen = false;
    this._editing = false;
    this._deleteError = undefined;
    this._deleteDialogOpen = true;
    this._render();
  }

  _closeDeletePersonDialog() {
    if (this._deleting) {
      return;
    }
    this._deleteDialogOpen = false;
    this._deleteError = undefined;
    this._render();
  }

  async _deletePerson() {
    if (this._deleting) {
      return;
    }
    const personId = this._selectedPerson?.person_id;
    if (!personId) {
      this._deleteError = "This user is no longer available.";
      this._render();
      return;
    }

    this._deleting = true;
    this._deleteError = undefined;
    this._refreshDeleteDialog();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: DELETE_PERSON_ACTION,
        service_data: { person_id: personId },
      });
      this._deleteDialogOpen = false;
      this._detailsPersonId = undefined;
      this._selectedPerson = undefined;
      this._detailsLoading = false;
      this._detailsError = undefined;
      await this._loadPeople();
      this._refreshDashboardActivityAfterOperation();
    } catch (error) {
      const message = String(error?.message ?? error ?? "");
      this._deleteError = message.includes("could not remove access from every device")
        ? "HomePASS has not yet confirmed that the credential was removed from the device.\n\nWait a few seconds and try again."
        : "HomePASS could not delete this user. Try again.";
    } finally {
      this._deleting = false;
      if (this._deleteDialogOpen) {
        this._refreshDeleteDialog();
      }
    }
  }

  async _savePerson() {
    const displayName = this.shadowRoot.querySelector("#display-name").value.trim();
    const description = this.shadowRoot.querySelector("#description").value.trim();
    const notesValue = this.shadowRoot.querySelector("#notes").value.trim();
    const enabled = this.shadowRoot.querySelector("#enabled").checked;
    this._form = { displayName, description, notes: notesValue, enabled };

    if (!displayName) {
      this._validationError = "Enter a display name.";
      this._render();
      return;
    }
    if (description.length > MAX_USER_DESCRIPTION_LENGTH) {
      this._validationError =
        `Description must be ${MAX_USER_DESCRIPTION_LENGTH} characters or fewer.`;
      this._render();
      return;
    }

    this._saving = true;
    this._validationError = undefined;
    this._render();
    const editing = this._editing;
    const personId = this._selectedPerson?.person_id;
    try {
      const serviceData = {
        display_name: displayName,
        description: description || null,
        notes: editing ? notesValue : notesValue || null,
        enabled,
      };
      if (editing) {
        serviceData.person_id = personId;
      }
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: editing ? UPDATE_PERSON_ACTION : CREATE_PERSON_ACTION,
        service_data: serviceData,
        return_response: true,
      });
      this._dialogOpen = false;
      this._editing = false;
      this._form = this._emptyForm();
      if (editing && personId) {
        await this._openPersonDetails(personId);
        await this._loadPeople();
      } else {
        await this._loadPeople();
      }
      this._refreshDashboardActivityAfterOperation();
    } catch (error) {
      this._validationError = this._friendlySaveError(error, editing);
    } finally {
      this._saving = false;
      this._render();
    }
  }

  _friendlySaveError(error, editing) {
    const message = String(error?.message ?? error ?? "").toLowerCase();
    if (message.includes("display_name") || message.includes("display name")) {
      return "Enter a valid display name.";
    }
    if (message.includes("duplicate") || message.includes("already")) {
      return "A user with this display name already exists.";
    }
    return editing
      ? "HomePASS could not save these changes. Check the details and try again."
      : "HomePASS could not add this user. Check the details and try again.";
  }

  _render() {
    const previousDoorSlideAction = this.shadowRoot.querySelector("#door-slide-action");
    const restoreDoorSlideFocus = Boolean(
      previousDoorSlideAction &&
      (
        this.shadowRoot.activeElement === previousDoorSlideAction ||
        previousDoorSlideAction.shadowRoot?.activeElement
      ),
    );
    if (this._doorOperationState === DOOR_OPERATION_STATE.SLIDING) {
      this._cancelDoorSlide();
    }
    if (
      this._giveAccessDialogOpen &&
      this.shadowRoot.querySelector("#give-access-dialog")
    ) {
      this._updateGiveAccessDialog();
      return;
    }
    // Mark the old dialog obsolete before DOM replacement. Its custom-element
    // close callback may run while innerHTML is between the old and new trees.
    if (this._manageAccessDialogOpen) {
      this._manageAccessDialogElement = undefined;
    }
    if (this._addUserWizardOpen) {
      this._addUserDialogElement = undefined;
    }
    if (this._policyInspectorOpen) {
      this._policyInspectorDialogElement = undefined;
    }
    if (this._addDoorDialogOpen) {
      this._addDoorDialogElement = undefined;
    }
    if (this._doorControlDialogOpen) {
      this._doorControlDialogElement = undefined;
    }
    if (this._removeDoorConfirmationOpen) {
      this._removeDoorConfirmationDialogElement = undefined;
    }
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          /* Canonical blue sampled from the approved HomePASS logo artwork. */
          --homepass-logo-blue: rgb(0 73 232);
          --homepass-entity-color: color-mix(
            in srgb,
            var(--homepass-logo-blue) 70%,
            var(--primary-text-color) 30%
          );
          display: block;
          min-height: 100%;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }

        .app-shell {
          display: grid;
          grid-template-columns: 176px minmax(0, 1fr);
          min-height: 100vh;
        }

        .primary-navigation {
          display: flex;
          flex-direction: column;
          gap: 6px;
          padding: 28px 12px;
          border-right: 1px solid var(--divider-color);
          background: var(--card-background-color);
        }

        .primary-navigation button {
          display: flex;
          align-items: center;
          gap: 10px;
          min-height: 44px;
          padding: 0 12px;
          border: 0;
          border-radius: 10px;
          cursor: pointer;
          background: transparent;
          color: var(--primary-text-color);
          font: inherit;
          text-align: left;
        }

        .primary-navigation button[aria-current="page"] {
          background: color-mix(in srgb, var(--primary-color) 14%, transparent);
          color: var(--primary-color);
          font-weight: 600;
        }

        .primary-navigation button:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .top-level-page {
          width: 100%;
        }

        .top-level-page,
        .detail-page {
          box-sizing: border-box;
          max-width: 960px;
          margin: 0 auto;
          padding: 32px 24px 48px;
        }

        .settings-content,
        .about-content {
          display: grid;
          gap: 20px;
        }

        .settings-card {
          padding: 22px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          background: var(--card-background-color);
        }

        .settings-card h2,
        .settings-card h3 {
          margin-top: 0;
        }

        .property-settings-field {
          display: grid;
          gap: 8px;
          max-width: 520px;
        }

        .property-settings-field ha-input {
          width: 100%;
        }

        .settings-toggle,
        .settings-choice {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          min-height: 38px;
          cursor: pointer;
        }

        .settings-toggle input,
        .settings-choice input {
          width: 18px;
          height: 18px;
          margin: 2px 0 0;
          accent-color: var(--primary-color);
        }

        .settings-choice input:disabled {
          cursor: not-allowed;
        }

        .settings-groups {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 18px 28px;
          margin-top: 20px;
        }

        .settings-presets {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 6px;
          margin: 4px 0 10px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .settings-group h3 {
          margin-bottom: 10px;
          font-size: 16px;
        }

        .settings-device-list {
          display: grid;
          gap: 6px;
          margin-bottom: 18px;
        }

        .settings-helper,
        .settings-about dt {
          color: var(--secondary-text-color);
        }

        .settings-about {
          display: grid;
          grid-template-columns: max-content minmax(0, 1fr);
          gap: 8px 18px;
          margin: 0;
        }

        .settings-about dd {
          margin: 0;
        }

        .settings-actions {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 14px;
        }

        .settings-notice {
          margin: 0 auto 0 0;
          color: var(--success-color, #2e7d32);
        }

        header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 24px;
        }

        .people-header {
          align-items: flex-end;
          margin: -12px 0 24px;
        }

        .brand-kicker {
          display: flex;
          align-items: center;
          gap: 18px;
          margin: 0 0 16px;
          padding: 0;
          border: 0;
          background: transparent;
          box-shadow: none;
        }

        .brand-mark {
          display: block;
          flex: none;
          object-fit: contain;
        }

        .header-brand-mark-crop {
          display: block;
          flex: none;
          width: clamp(330px, 34vw, 390px);
          max-width: 100%;
          padding: 0;
          border: 0;
          background: transparent;
          box-shadow: none;
        }

        .header-brand-mark {
          width: 100%;
          height: auto;
        }

        .people-header h1 {
          font-size: 26px;
          font-weight: 500;
        }

        .people-header .subtitle {
          margin-top: 10px;
        }

        h1 {
          margin: 0;
          font-size: 28px;
          font-weight: 500;
        }

        .subtitle {
          margin: 6px 0 0;
          color: var(--secondary-text-color);
        }

        .add-person {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          min-height: 40px;
          padding: 0 16px;
          border: 0;
          border-radius: 20px;
          cursor: pointer;
          background: var(--primary-color);
          color: var(--text-primary-color);
          font: inherit;
          font-weight: 500;
        }

        .add-person:disabled {
          cursor: not-allowed;
          opacity: 0.55;
        }

        .edit-person {
          flex: none;
        }

        .subtle-destructive-action {
          --mdc-theme-primary: var(--error-color);
          color: var(--error-color);
        }

        .details-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .people-header-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .dashboard-header {
          display: block;
          margin: -12px 0 14px;
        }

        .dashboard-header-top {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          gap: 32px;
        }

        .dashboard-header-top .brand-kicker {
          margin-bottom: 0;
        }

        .dashboard-header .header-brand-mark-crop {
          /* Show source y=50..136: all alpha artwork plus 14 transparent pixels below it. */
          aspect-ratio: 425 / 86;
          contain: size;
          overflow: hidden;
        }

        .dashboard-header .header-brand-mark {
          transform: translateY(-26.88172043%);
        }

        .people-header:not(.dashboard-header) .header-brand-mark-crop {
          aspect-ratio: 425 / 86;
          contain: size;
          overflow: hidden;
        }

        .people-header:not(.dashboard-header) .header-brand-mark {
          transform: translateY(-26.88172043%);
        }

        .dashboard-header-actions {
          display: flex;
          flex: none;
          align-items: center;
          justify-content: flex-end;
          gap: 6px;
          padding-top: 4px;
          font-size: 14px;
        }

        .dashboard-header-tail {
          display: flex;
          flex: 1 1 auto;
          align-items: center;
          justify-content: flex-end;
          min-width: 0;
          gap: clamp(14px, 2vw, 24px);
          padding-bottom: clamp(10px, 1.1vw, 13px);
        }

        .dashboard-property-name {
          min-width: 0;
          max-width: min(24vw, 240px);
          overflow: hidden;
          color: var(--primary-text-color);
          font-size: clamp(16px, 1.6vw, 20px);
          font-weight: 500;
          line-height: 1.2;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .people {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
          gap: 14px;
        }

        .person-card,
        .state-card,
        .details-card,
        .dashboard-card {
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 16px);
          background: var(--card-background-color);
          box-shadow: var(--ha-card-box-shadow, none);
        }

        .person-card {
          position: relative;
          overflow: hidden;
          transition: box-shadow 160ms ease, transform 160ms ease;
        }

        .person-card:hover {
          box-shadow: 0 10px 28px color-mix(
            in srgb,
            var(--primary-text-color) 14%,
            transparent
          );
          transform: translateY(-2px);
        }

        .person {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          gap: 0 12px;
          align-items: center;
          box-sizing: border-box;
          width: 100%;
          min-height: 100%;
          padding: 16px 18px;
          border: 0;
          pointer-events: none;
          background: transparent;
          color: var(--primary-text-color);
          font: inherit;
          text-align: left;
        }

        .person-card:hover .person {
          background: color-mix(
            in srgb,
            var(--primary-color) 4%,
            var(--card-background-color)
          );
        }

        .person-card-open {
          position: absolute;
          z-index: 1;
          inset: 0;
          width: 100%;
          border: 0;
          cursor: pointer;
          background: transparent;
        }

        .person-card-open:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: -2px;
        }

        .person-name {
          overflow-wrap: anywhere;
          font-size: 18px;
          font-weight: 650;
          line-height: 1.25;
        }

        .homepass-entity-name {
          color: var(--homepass-entity-color);
        }

        .person-avatar {
          display: grid;
          width: 34px;
          height: 34px;
          border-radius: 50%;
          place-items: center;
          background: var(--secondary-background-color);
          color: var(--primary-color);
        }

        .person-avatar ha-icon {
          --mdc-icon-size: 21px;
        }

        .person-content {
          display: grid;
          gap: 5px;
          min-width: 0;
        }

        .person-heading {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px 16px;
        }

        .person-card-meta {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 6px 18px;
          min-width: 0;
        }

        .person-access-summary {
          display: grid;
          gap: 8px;
        }

        .person-summary-line {
          display: grid;
          grid-template-columns: 20px minmax(0, 1fr);
          gap: 10px;
          align-items: center;
          min-width: 0;
        }

        .person-summary-line ha-icon,
        .person-metric ha-icon {
          --mdc-icon-size: 18px;
          color: var(--secondary-text-color);
        }

        .person-summary-copy {
          display: grid;
          gap: 2px;
          min-width: 0;
        }

        .person-summary-primary {
          overflow: hidden;
          font-weight: 500;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .person-summary-secondary,
        .person-description,
        .person-notes {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .person-description {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }

        .person-metrics {
          display: flex;
          flex-wrap: wrap;
          gap: 10px 18px;
        }

        .person-metric {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .person-notes {
          margin: 0;
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }

        .person-status {
          display: inline-flex;
          align-items: center;
          min-height: 22px;
          padding: 0 9px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 650;
          line-height: 1;
          margin-left: 2px;
        }

        .person-status.enabled {
          background: #2e7d32;
          color: #fff;
        }

        .person-status.scheduled {
          background: #6a42a1;
          color: #fff;
        }

        .person-status.disabled {
          background: #757575;
          color: #fff;
        }

        .person-status.pending {
          background: #b26a00;
          color: #fff;
        }

        .person-chevron {
          align-self: center;
          margin-right: -4px;
          color: var(--secondary-text-color);
        }

        .person-chevron ha-icon {
          --mdc-icon-size: 22px;
        }

        .person-quick-pin {
          position: relative;
          z-index: 2;
          display: flex;
          align-items: center;
          gap: 6px;
          min-height: 32px;
          padding: 0;
          border: 0;
          pointer-events: none;
          background: var(--card-background-color);
        }

        .person-quick-pin-label {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .person-quick-pin-value {
          min-width: 3.8em;
          font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
          letter-spacing: 0.08em;
        }

        .person-quick-pin-toggle {
          display: grid;
          width: 36px;
          height: 36px;
          margin-left: 0;
          place-items: center;
          border: 0;
          border-radius: 50%;
          cursor: pointer;
          pointer-events: auto;
          background: transparent;
          color: var(--primary-color);
        }

        .person-quick-pin-toggle:hover {
          background: var(--secondary-background-color);
        }

        .person-quick-pin-toggle:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .person-quick-pin-toggle:disabled {
          cursor: wait;
          opacity: 0.6;
        }

        .person-quick-pin-toggle ha-icon {
          --mdc-icon-size: 20px;
        }

        .person-quick-pin-progress {
          margin-left: 0;
        }

        .person-quick-pin-progress:not([hidden]) + .person-quick-pin-toggle {
          margin-left: 0;
        }

        .person-quick-pin-error {
          flex-basis: 100%;
          color: var(--error-color);
          font-size: 12px;
        }

        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        .state-card {
          padding: 48px 24px;
          text-align: center;
          color: var(--secondary-text-color);
        }

        .state-card h2 {
          margin: 0 0 8px;
          color: var(--primary-text-color);
          font-size: 20px;
          font-weight: 500;
        }

        .state-card p {
          margin: 0;
        }

        .people-empty-state {
          display: grid;
          justify-items: center;
          gap: 12px;
          padding: 64px 24px;
        }

        .homepass-mark-placeholder {
          display: grid;
          min-width: 180px;
          min-height: 156px;
          margin-bottom: 4px;
          place-items: center;
        }

        .empty-brand-mark-crop {
          display: block;
          width: min(100%, 330px);
          padding: 0;
          border: 0;
          background: transparent;
          box-shadow: none;
        }

        .empty-brand-lockup {
          margin: 0;
        }

        .empty-brand-mark {
          width: 100%;
          height: auto;
        }

        .people-empty-state .add-person {
          margin-top: 12px;
        }

        .dialog-content {
          display: grid;
          gap: 20px;
          min-width: min(440px, calc(100vw - 64px));
          padding-top: 8px;
        }

        .dialog-content[hidden] {
          display: none !important;
        }

        .add-user-form {
          display: grid;
          width: min(680px, calc(100vw - 64px));
          max-width: 100%;
          gap: 14px;
          padding-top: 8px;
        }

        .add-user-section {
          display: grid;
          gap: 12px;
          padding: 0 0 14px;
          border-bottom: 1px solid var(--divider-color);
        }

        .add-user-section:last-of-type {
          padding-bottom: 0;
          border-bottom: 0;
        }

        .add-user-section h2 {
          margin: 0;
          font-size: 19px;
        }

        .wizard-help,
        .field-help {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .wizard-field {
          display: grid;
          gap: 7px;
        }

        .wizard-field > span:first-child,
        .wizard-door-options legend,
        .wizard-schedule-options legend {
          font-weight: 600;
        }

        .wizard-field input,
        .wizard-field textarea,
        .wizard-field select,
        .wizard-new-schedule input:not([type="radio"]):not([type="checkbox"]),
        .wizard-new-schedule select {
          box-sizing: border-box;
          width: 100%;
          min-height: 42px;
          padding: 8px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .wizard-field input:focus-visible,
        .wizard-field textarea:focus-visible,
        .wizard-field select:focus-visible,
        .wizard-door-option input:focus-visible,
        .wizard-schedule-options input:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .wizard-pin-row {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 12px;
          align-items: end;
        }

        .wizard-pin-row > button {
          min-height: 42px;
          padding: 0 14px;
          border: 1px solid var(--primary-color);
          border-radius: 20px;
          cursor: pointer;
          background: transparent;
          color: var(--primary-color);
          font: inherit;
        }

        .wizard-door-options,
        .wizard-schedule-options,
        .wizard-new-schedule {
          display: grid;
          gap: 10px;
          margin: 0;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
        }

        .manage-access-schedule {
          display: grid;
          gap: 14px;
          margin: 0;
          padding: 16px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
        }

        .manage-access-pin {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 8px 12px;
          align-items: end;
          margin-top: 14px;
        }

        .manage-access-pin .wizard-help {
          grid-column: 1 / -1;
        }

        .manage-access-generate-pin {
          min-height: 42px;
          padding: 0 14px;
          border: 1px solid var(--primary-color);
          border-radius: 20px;
          background: transparent;
          color: var(--primary-color);
          cursor: pointer;
          font: inherit;
        }

        .manage-access-generate-pin:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .wizard-door-option,
        .manage-access-schedule > label {
          display: flex;
          align-items: center;
          gap: 10px;
          min-height: 32px;
        }

        .wizard-new-schedule {
          margin-top: 2px;
          padding: 10px;
          background: transparent;
        }

        .wizard-option-group {
          display: grid;
          gap: 6px;
          margin: 0;
          padding: 0;
          border: 0;
        }

        .wizard-option-group legend {
          margin-bottom: 2px;
          font-size: 13px;
          font-weight: 600;
        }

        .wizard-radio-row {
          display: inline-flex;
          width: fit-content;
          min-height: 30px;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }

        .wizard-radio-row input[type="radio"] {
          box-sizing: border-box;
          flex: 0 0 auto;
          width: 18px;
          height: 18px;
          min-height: 0;
          margin: 0;
          padding: 0;
        }

        .wizard-date-time-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px 12px;
        }

        .wizard-new-schedule fieldset:not(.wizard-option-group) {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 6px;
          margin: 0;
          padding: 8px 0 0;
          border: 0;
        }

        .wizard-new-schedule fieldset:not(.wizard-option-group) label {
          display: flex;
          align-items: center;
          gap: 6px;
          min-height: 28px;
        }

        .manage-access-schedule select {
          box-sizing: border-box;
          width: 100%;
          min-height: 42px;
          padding: 8px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .manage-access-current-schedule {
          margin: 0;
          font-weight: 600;
        }

        .door-control-content {
          box-sizing: border-box;
          display: grid;
          width: min(580px, calc(100vw - 64px));
          max-width: 100%;
          max-height: min(70vh, 720px);
          gap: 20px;
          padding-top: 8px;
          padding-right: 4px;
          overflow-y: auto;
          overscroll-behavior: contain;
        }

        .door-control-error {
          display: grid;
          gap: 8px;
        }

        .door-control-error h3,
        .door-control-error p {
          margin: 0;
        }

        .door-control-content [hidden] {
          display: none !important;
        }

        #door-control-status {
          display: grid;
          gap: 20px;
        }

        #door-control-state-summary {
          display: grid;
          gap: 16px;
        }

        .door-control-state-layout {
          display: grid;
          grid-template-columns: 112px minmax(0, 1fr);
          gap: 22px;
          align-items: center;
        }

        .door-control-state-copy {
          display: grid;
          gap: 16px;
          min-width: 0;
        }

        .door-control-status-graphic {
          display: grid;
          place-items: center;
        }

        .door-control-status-graphic .homepass-status-icon-slot {
          width: 98px;
          height: 98px;
        }

        .door-control-primary-state {
          margin: 0;
          font-size: clamp(32px, 6vw, 44px);
          font-weight: 650;
          line-height: 1.1;
        }

        .door-control-primary-state.attention {
          color: var(--warning-color, #b26a00);
        }

        .door-control-primary-state.subdued {
          color: var(--secondary-text-color);
        }

        .door-control-primary-state.transitional {
          color: var(--primary-color);
        }

        .door-control-primary-state.error {
          color: var(--error-color);
        }

        .door-control-facts {
          display: grid;
          gap: 10px;
          margin: 0;
        }

        .door-control-facts > div {
          display: grid;
          grid-template-columns: minmax(120px, 0.45fr) minmax(0, 1fr);
          align-items: baseline;
          gap: 16px;
        }

        .door-control-facts dt {
          color: var(--secondary-text-color);
          overflow-wrap: anywhere;
        }

        .door-control-facts dd {
          margin: 0;
          overflow-wrap: anywhere;
          font-weight: 500;
        }

        .door-policy-section {
          display: grid;
          gap: 12px;
          padding-top: 20px;
          border-top: 1px solid var(--divider-color);
        }

        .door-policy-section h3 {
          margin: 0;
          font-size: 18px;
        }

        .person-policy-card {
          grid-column: 1 / -1;
        }

        .door-policy-content,
        .door-policy-list {
          display: grid;
          gap: 12px;
        }

        .door-policy-content {
          gap: 16px;
        }

        .door-policy-row {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr);
          align-items: start;
          gap: 10px;
        }

        .door-policy-relationship {
          display: grid;
          gap: 8px;
        }

        .synchronization-recovery {
          display: grid;
          gap: 4px;
          margin-left: 34px;
          padding: 8px 10px;
          border-left: 3px solid var(--divider-color);
          color: var(--secondary-text-color);
        }

        .synchronization-recovery.info {
          border-left-color: var(--info-color, var(--primary-color));
        }

        .synchronization-recovery.warning {
          border-left-color: var(--warning-color, #b26a00);
        }

        .synchronization-recovery.error {
          border-left-color: var(--error-color);
        }

        .synchronization-recovery-title,
        .synchronization-recovery-description {
          margin: 0;
        }

        .synchronization-recovery-title {
          color: var(--primary-text-color);
          font-weight: 600;
        }

        .synchronization-retry {
          justify-self: start;
          margin-top: 4px;
        }

        .door-policy-selectable {
          width: 100%;
          grid-template-columns: auto minmax(0, 1fr) auto;
          padding: 10px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: transparent;
          color: inherit;
          font: inherit;
          text-align: left;
          cursor: pointer;
        }

        .door-policy-selectable:hover {
          background: color-mix(in srgb, var(--primary-color) 7%, transparent);
        }

        .door-policy-selectable:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .door-policy-open-icon {
          align-self: center;
          color: var(--secondary-text-color);
        }

        .door-policy-icon.allowed {
          color: var(--success-color, #2e7d32);
        }

        .door-policy-icon.warning {
          color: var(--warning-color, #b26a00);
        }

        .door-policy-icon.error {
          color: var(--error-color);
        }

        .door-policy-icon.neutral {
          color: var(--secondary-text-color);
        }

        .door-policy-name,
        .door-policy-explanation,
        .door-policy-empty {
          margin: 0;
        }

        .door-policy-name {
          font-weight: 600;
        }

        .person-door-link {
          display: inline;
          padding: 0;
          border: 0;
          background: transparent;
          color: var(--primary-color);
          font: inherit;
          font-weight: 600;
          text-align: left;
          cursor: pointer;
        }

        .person-door-link:hover {
          text-decoration: underline;
        }

        .person-door-link:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 3px;
          border-radius: 3px;
        }

        .person-door-access-methods {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          margin-left: 34px;
        }

        .person-door-access-methods-label {
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .person-door-access-method {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          min-height: 28px;
          padding: 2px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 999px;
          font-size: 13px;
          font-weight: 600;
        }

        .person-door-access-method.active,
        .person-door-access-method.editable:has(input:checked) {
          border-color: color-mix(in srgb, var(--success-color, #2e7d32) 45%, var(--divider-color));
          background: color-mix(in srgb, var(--success-color, #2e7d32) 10%, transparent);
        }

        .person-door-access-schedule {
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 600;
        }

        .person-door-access-method.editable {
          cursor: pointer;
        }

        .person-door-access-method.editable input {
          margin: 0;
        }

        .manage-access-door-methods {
          display: grid;
          gap: 10px;
          margin: 0;
          padding: 12px 14px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
        }

        .manage-access-door-methods legend {
          display: flex;
          gap: 8px;
          align-items: center;
          padding: 0 4px;
          font-weight: 700;
        }

        .manage-access-method-options {
          display: flex;
          flex-wrap: wrap;
          gap: 10px 18px;
          margin-left: 26px;
        }

        .manage-access-method-options label {
          display: inline-flex;
          gap: 6px;
          align-items: center;
        }

        @media (forced-colors: active) {
          .homepass-entity-name {
            color: LinkText;
          }
        }

        .synchronization-history-disclosure,
        .synchronization-history-card details {
          border-top: 1px solid var(--divider-color);
          padding-top: 14px;
        }

        .synchronization-history-disclosure summary,
        .synchronization-history-card summary {
          cursor: pointer;
          font-weight: 650;
        }

        .synchronization-history-disclosure summary:focus-visible,
        .synchronization-history-card summary:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 3px;
        }

        .synchronization-history-list {
          display: grid;
          gap: 12px;
          margin-top: 12px;
        }

        .synchronization-history-row {
          display: grid;
          gap: 2px;
          padding-left: 10px;
          border-left: 3px solid var(--secondary-text-color);
        }

        .synchronization-history-row.success { border-color: var(--success-color, #2e7d32); }
        .synchronization-history-row.info { border-color: var(--primary-color); }
        .synchronization-history-row.warning { border-color: var(--warning-color, #b26a00); }
        .synchronization-history-row.error { border-color: var(--error-color); }

        .synchronization-history-row time,
        .synchronization-history-row p,
        .synchronization-history-empty {
          margin: 0;
        }

        .synchronization-history-row time,
        .synchronization-history-row p:last-child,
        .synchronization-history-empty {
          color: var(--secondary-text-color);
        }

        .synchronization-history-title {
          color: var(--primary-text-color) !important;
          font-weight: 600;
        }

        .door-policy-explanation,
        .door-policy-empty {
          color: var(--secondary-text-color);
        }

        .door-dialog-title-row {
          display: flex;
          min-width: 0;
          align-items: center;
          gap: 8px;
        }

        .door-dialog-title-row .homepass-entity-name {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .door-title-editor {
          display: grid;
          width: min(440px, calc(100vw - 150px));
          grid-template-columns: minmax(0, 1fr) auto auto;
          gap: 6px;
          align-items: center;
        }

        .door-title-editor input {
          box-sizing: border-box;
          width: 100%;
          min-width: 0;
          min-height: 40px;
          padding: 7px 10px;
          border: 1px solid var(--primary-color);
          border-radius: 9px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .door-title-editor input:focus-visible {
          outline: 2px solid color-mix(in srgb, var(--primary-color) 35%, transparent);
          outline-offset: 1px;
        }

        .door-title-icon-button {
          display: grid;
          flex: 0 0 36px;
          width: 36px;
          height: 36px;
          padding: 0;
          place-items: center;
          border: 0;
          border-radius: 50%;
          background: transparent;
          color: var(--primary-color);
          cursor: pointer;
        }

        .door-title-icon-button:hover {
          background: color-mix(in srgb, var(--primary-color) 10%, transparent);
        }

        .door-title-icon-button:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .door-title-icon-button:disabled {
          cursor: wait;
          opacity: 0.55;
        }

        .door-title-icon-button ha-icon {
          --mdc-icon-size: 21px;
        }

        .door-quick-actions {
          display: grid;
          gap: 9px;
        }

        .door-nfc-action {
          display: grid;
          width: 100%;
          grid-template-columns: 42px minmax(0, 1fr) auto;
          gap: 12px;
          align-items: center;
          padding: 12px 14px;
          border: 1px solid var(--divider-color);
          border-radius: 13px;
          background: color-mix(in srgb, var(--primary-color) 4%, var(--card-background-color));
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
          text-align: left;
          transition: border-color 140ms ease, background 140ms ease;
        }

        .door-nfc-action:hover {
          border-color: color-mix(in srgb, var(--primary-color) 45%, var(--divider-color));
          background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color));
        }

        .door-nfc-action:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .door-nfc-action-mark {
          display: grid;
          width: 42px;
          height: 42px;
          place-items: center;
          border-radius: 12px;
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }

        .door-nfc-action-mark img {
          display: block;
          width: 30px;
          height: 30px;
        }

        .door-nfc-action-copy {
          display: grid;
          gap: 2px;
          min-width: 0;
        }

        .door-nfc-action-copy strong {
          font-size: 15px;
        }

        .door-nfc-action-copy span {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .door-nfc-action > ha-icon {
          color: var(--secondary-text-color);
          --mdc-icon-size: 22px;
        }

        .door-rename-feedback {
          margin: 0;
          padding: 8px 11px;
          border-radius: 9px;
          font-size: 13px;
        }

        .door-rename-feedback.error {
          color: var(--error-color);
          background: color-mix(in srgb, var(--error-color) 9%, transparent);
        }

        .door-rename-feedback.notice {
          color: var(--success-color, #2e7d32);
          background: color-mix(in srgb, var(--success-color, #2e7d32) 9%, transparent);
        }

        .door-admin-footer {
          display: grid;
          justify-items: start;
          padding-top: 18px;
          border-top: 1px solid var(--divider-color);
        }

        .door-nfc-setup-content {
          gap: 16px;
        }

        .door-nfc-header-copy {
          display: grid;
          gap: 1px;
          min-width: 0;
        }

        .door-nfc-header-copy small {
          overflow: hidden;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 500;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .policy-inspector-content {
          display: grid;
          gap: 18px;
          min-width: min(440px, 82vw);
        }

        .policy-inspector-details {
          display: grid;
          gap: 18px;
        }

        .policy-inspector-reason {
          margin: 0;
          font-size: 18px;
          font-weight: 650;
        }

        .policy-inspector-facts {
          display: grid;
          gap: 12px;
          margin: 0;
        }

        .policy-inspector-facts > div {
          display: grid;
          grid-template-columns: minmax(110px, 0.4fr) minmax(0, 1fr);
          gap: 14px;
        }

        .policy-inspector-facts dt {
          color: var(--secondary-text-color);
        }

        .policy-inspector-facts dd,
        .policy-inspector-section p {
          margin: 0;
        }

        .policy-inspector-section {
          display: grid;
          gap: 5px;
          padding-top: 14px;
          border-top: 1px solid var(--divider-color);
        }

        .policy-inspector-section h3 {
          margin: 0 0 3px;
          font-size: 16px;
        }

        .policy-inspector-secondary {
          color: var(--secondary-text-color);
        }

        .door-operation-region {
          display: grid;
          gap: 14px;
          padding-top: 24px;
          border-top: 1px solid var(--divider-color);
        }

        .door-operation-error {
          display: grid;
          gap: 4px;
          color: var(--error-color);
        }

        .door-operation-error p {
          margin: 0;
        }

        .door-operation-error-title {
          font-weight: 600;
        }

        .credential-actions {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }

        .credential-reveal-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .credential-reveal-row .detail-value {
          min-width: 7em;
          font-family: monospace;
          font-size: 18px;
          letter-spacing: 0.12em;
        }

        .credential-visibility-toggle {
          display: inline-grid;
          width: 40px;
          height: 40px;
          padding: 0;
          border: 0;
          border-radius: 50%;
          place-items: center;
          cursor: pointer;
          background: transparent;
          color: var(--primary-text-color);
        }

        .credential-visibility-toggle:hover {
          background: var(--secondary-background-color);
        }

        .credential-visibility-toggle:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .credential-visibility-toggle:disabled {
          cursor: progress;
          opacity: 0.6;
        }

        .credential-visibility-toggle[aria-busy="true"] ha-icon {
          animation: homepass-spin 1s linear infinite;
        }

        @keyframes homepass-spin {
          to {
            transform: rotate(360deg);
          }
        }

        ha-input,
        ha-textarea {
          display: block;
          width: 100%;
        }

        ha-formfield {
          width: fit-content;
        }

        .form-error {
          margin: 0;
          color: var(--error-color);
        }

        .delete-person-error {
          white-space: pre-line;
        }

        .access-update-status {
          padding: 12px;
          border-radius: 8px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          white-space: pre-line;
        }

        .access-update-notice {
          margin: 0;
          padding: 12px;
          border-radius: 8px;
          background: var(--success-color, #43a04722);
          color: var(--primary-text-color);
        }

        .confirmation-message {
          margin: 0;
        }

        .confirmation-detail {
          margin: -8px 0 0;
          color: var(--secondary-text-color);
        }

        .delete-person-effects,
        .delete-person-access-points {
          margin: 0;
          padding-left: 24px;
        }

        .delete-person-effects {
          display: grid;
          gap: 12px;
        }

        .delete-person-access-points {
          margin-top: 4px;
        }

        .wizard-step {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
        }

        .wizard-question {
          margin: -8px 0 0;
          font-size: 20px;
          font-weight: 500;
        }

        .access-point-options {
          display: grid;
          gap: 14px;
          min-height: 48px;
        }

        .access-point-options > label,
        .dialog-content > label {
          display: grid;
          gap: 6px;
          color: var(--primary-text-color);
          font-size: 14px;
          font-weight: 500;
        }

        .access-point-options select,
        .access-point-options input[type="text"],
        .access-point-options input[type="number"],
        .dialog-content > label > select {
          box-sizing: border-box;
          width: 100%;
          min-height: 44px;
          padding: 8px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
          font-weight: 400;
        }

        .access-point-options .muted {
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 400;
        }

        .access-point-options [role="radiogroup"] {
          display: grid;
          gap: 8px;
        }

        .access-point-option {
          min-height: 40px;
          width: fit-content;
        }

        .access-point-option input[type="radio"] {
          width: 20px;
          height: 20px;
          margin: 0 12px 0 0;
          accent-color: var(--primary-color);
          cursor: pointer;
        }

        .assigned-access-point {
          display: grid;
          gap: 4px;
          padding: 8px 0;
        }

        .assigned-access-point-status {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .pin-display {
          padding: 16px;
          border-radius: 8px;
          background: var(--secondary-background-color);
          font-family: monospace;
          font-size: 28px;
          letter-spacing: 0.2em;
          text-align: center;
        }

        .pin-input {
          box-sizing: border-box;
          width: 100%;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .security-warning {
          padding: 12px;
          border-radius: 8px;
          background: var(--warning-color, #ffa60033);
        }

        .security-warning p,
        .success-information p {
          margin: 8px 0 0;
        }

        .success-information {
          padding: 12px;
          border-radius: 8px;
          background: var(--secondary-background-color);
        }

        .provisioning-status {
          display: flex;
          align-items: center;
          gap: 12px;
          color: var(--secondary-text-color);
        }

        .success-title {
          margin: 0;
          font-size: 22px;
          font-weight: 600;
        }

        .success-summary {
          display: grid;
          gap: 16px;
        }

        .success-label,
        .success-value,
        .confirmation-note {
          margin: 0;
        }

        .success-label {
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
        }

        .success-value {
          margin-top: 4px;
          font-size: 18px;
        }

        .details-title {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .details-title ha-icon-button-prev {
          flex: none;
        }

        .details-breadcrumb {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 4px;
          margin: 2px 0 8px;
          color: var(--secondary-text-color);
          font-size: 14px;
        }

        .details-breadcrumb ha-button {
          --mdc-typography-button-text-transform: none;
        }

        .details-breadcrumb [aria-current="page"] {
          overflow: hidden;
          max-width: min(260px, 40vw);
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
        }

        .details-card {
          padding: 22px;
        }

        .profile-card {
          grid-column: auto;
        }

        .details-card h2 {
          margin: 0 0 16px;
          font-size: 20px;
          font-weight: 600;
        }

          .nfc-enrollment-status,
          .nfc-enrollment-note {
            margin: 0 0 14px;
            color: var(--secondary-text-color);
            line-height: 1.45;
          }
          .nfc-enrollment-status strong {
            color: var(--primary-text-color);
          }
          .nuki-fingerprint-door {
            display: grid;
            gap: 10px;
            margin-top: 14px;
            padding: 16px;
            border: 1px solid var(--divider-color);
            border-radius: 14px;
          }
          .nuki-fingerprint-door h3,
          .nuki-fingerprint-door p,
          .nuki-fingerprint-door ol {
            margin: 0;
          }
          .nuki-fingerprint-door ol {
            display: grid;
            gap: 7px;
            padding-left: 22px;
            line-height: 1.45;
          }
          .nfc-enrollment-actions,
          .nfc-enrollment-share-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
          }
          .nfc-door-assignment {
            display: grid;
            gap: 10px;
            margin: 16px 0;
            padding: 16px;
            border: 1px solid var(--divider-color);
            border-radius: 14px;
          }
          .nfc-door-assignment legend {
            padding: 0 6px;
            font-weight: 700;
          }
          .nfc-passkey-list,
          .door-nfc-tag-list {
            display: grid;
            gap: 10px;
            margin-top: 10px;
          }
          .nfc-passkey-item,
          .door-nfc-tag-item {
            display: grid;
            gap: 4px;
            padding: 12px;
            border: 1px solid var(--divider-color);
            border-radius: 12px;
            background: var(--secondary-background-color);
          }
          .nfc-passkey-item span,
          .door-nfc-tag-meta {
            color: var(--secondary-text-color);
            font-size: 13px;
          }
          .door-nfc-tag-heading {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
          }
          .door-nfc-tag-uid {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            letter-spacing: 0.04em;
          }
          .door-nfc-tag-status {
            font-weight: 700;
          }
          .door-nfc-tag-status.revoked {
            color: var(--error-color);
          }
          .door-nfc-tag-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
          }
          .door-nfc-protection-help {
            display: grid;
            gap: 8px;
            margin-top: 8px;
            padding: 10px;
            border: 1px solid color-mix(in srgb, var(--primary-color) 28%, var(--divider-color));
            border-radius: 10px;
            background: var(--card-background-color);
          }
          .door-nfc-protection-help span {
            color: var(--secondary-text-color);
            font-size: 13px;
            line-height: 1.4;
          }
          .nfc-enrollment-link {
            display: block;
            margin: 12px 0 8px;
            overflow-wrap: anywhere;
          }
          .nfc-enrollment-qr-panel {
            display: grid;
            grid-template-columns: minmax(150px, 190px) minmax(0, 1fr);
            gap: 20px;
            align-items: center;
            margin: 16px 0;
            padding: 18px;
            border: 1px solid var(--divider-color);
            border-radius: 16px;
            background: var(--secondary-background-color);
          }
          .nfc-enrollment-qr {
            display: block;
            width: 100%;
            max-width: 190px;
            aspect-ratio: 1;
            padding: 8px;
            box-sizing: border-box;
            border-radius: 12px;
            background: #fff;
          }
          .nfc-enrollment-share {
            min-width: 0;
          }
          .nfc-enrollment-share > strong {
            display: block;
            font-size: 18px;
          }
          .nfc-enrollment-share > p {
            margin: 6px 0 0;
            color: var(--secondary-text-color);
            line-height: 1.45;
          }
          .nfc-enrollment-share-actions {
            margin-top: 12px;
          }
          .nfc-enrollment-download {
            display: inline-flex;
            min-height: 40px;
            align-items: center;
            padding: 0 10px;
            color: var(--primary-color);
            font-weight: 600;
            text-decoration: none;
          }
          @media (max-width: 620px) {
            .nfc-enrollment-qr-panel {
              grid-template-columns: 1fr;
            }
            .nfc-enrollment-qr {
              margin: 0 auto;
            }
          }

        .dashboard-content {
          display: grid;
          gap: 24px;
        }

        .doors-content {
          display: grid;
          gap: 32px;
        }

        .doors-devices-section {
          display: grid;
          gap: 16px;
        }

        .doors-devices-section-heading h2 {
          margin: 0;
          font-size: 22px;
        }

        .doors-devices-section-heading p {
          margin: 5px 0 0;
          color: var(--secondary-text-color);
        }

        .door-count {
          margin: 10px 0 0;
          color: var(--secondary-text-color);
          font-size: 14px;
        }

        .doors-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
          gap: 20px;
        }

        .access-device-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
          gap: 16px;
        }

        .access-device-card {
          display: grid;
          grid-template-columns: 44px minmax(0, 1fr);
          gap: 14px;
          align-items: start;
          padding: 20px;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 16px);
          background: var(--card-background-color);
        }

        .access-device-card > ha-icon {
          width: 32px;
          height: 32px;
          padding: 6px;
          border-radius: 12px;
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
          color: var(--primary-color);
        }

        .access-device-card h3,
        .access-device-card p {
          margin: 0;
        }

        .access-device-card p {
          margin-top: 5px;
          color: var(--secondary-text-color);
        }

        .access-device-status {
          display: inline-block;
          margin-top: 10px;
          padding: 4px 9px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 700;
        }

        .access-device-status.ready {
          background: color-mix(in srgb, var(--success-color, #4caf50) 16%, transparent);
          color: var(--success-color, #2e7d32);
        }

        .access-device-status.pending {
          background: color-mix(in srgb, var(--warning-color, #f59e0b) 16%, transparent);
          color: var(--warning-color, #9a5b00);
        }

        .device-battery {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          margin-top: 8px;
          color: var(--secondary-text-color);
          font-size: 13px;
          font-weight: 600;
        }

        .device-battery ha-icon {
          --mdc-icon-size: 18px;
        }

        .device-battery.low {
          color: var(--warning-color, #b26a00);
        }

        .device-battery.critical {
          color: var(--error-color);
        }

        .device-pairing-empty {
          display: grid;
          grid-template-columns: 36px minmax(0, 1fr);
          gap: 12px;
          align-items: start;
          padding: 16px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          background: var(--secondary-background-color);
        }

        .device-pairing-empty p {
          margin: 5px 0 0;
          color: var(--secondary-text-color);
        }

        .door-associated-device-list {
          display: grid;
          gap: 10px;
        }

        .door-associated-device {
          display: grid;
          grid-template-columns: 28px minmax(0, 1fr);
          gap: 10px;
          align-items: center;
          padding: 10px 0;
          border-bottom: 1px solid var(--divider-color);
        }

        .door-associated-device:last-child {
          border-bottom: 0;
        }

        .door-associated-device div,
        .door-associated-device span {
          display: block;
        }

        .door-associated-device span {
          margin-top: 3px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .door-associated-device .device-battery {
          display: inline-flex;
        }

        .door-page-card {
          display: grid;
          grid-template-columns: 60px minmax(0, 1fr);
          min-height: 168px;
          align-items: center;
          gap: 18px;
          padding: 28px;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 16px);
          background: var(--card-background-color);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.08));
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
          text-align: left;
          transition:
            box-shadow 160ms ease,
            transform 160ms ease;
        }

        .door-page-card:hover {
          box-shadow: var(--ha-card-box-shadow, 0 8px 20px rgba(0, 0, 0, 0.14));
          transform: translateY(-2px);
        }

        .door-page-card:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 3px;
        }

        .door-page-card h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          overflow-wrap: anywhere;
        }

        .door-page-card-copy {
          display: grid;
          min-width: 0;
          align-content: center;
          gap: 6px;
        }

        .door-lock-state {
          margin: 0;
          font-size: 26px;
          font-weight: 600;
          line-height: 1.2;
        }

        .door-page-card.attention .door-lock-state,
        .door-contact-state.open {
          color: var(--warning-color, #b26a00);
        }

        .door-page-card.subdued .door-lock-state {
          color: var(--secondary-text-color);
        }

        .door-page-card.error .door-lock-state {
          color: var(--error-color);
        }

        .door-contact-state {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 15px;
        }

        .door-battery-state {
          margin: 0;
        }

        .dashboard-section {
          display: grid;
          gap: 10px;
        }

        .dashboard-section-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
        }

        .dashboard-section-heading h2 {
          margin: 0;
          font-size: 22px;
          font-weight: 600;
        }

        .dashboard-section-heading p {
          margin: 4px 0 0;
          color: var(--secondary-text-color);
        }

        .dashboard-section-actions {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 4px;
        }

        .dashboard-activity-filter-popover {
          position: fixed;
          inset: auto;
          width: min(380px, calc(100vw - 32px));
          max-height: min(620px, calc(100dvh - 32px));
          margin: 0;
          padding: 18px;
          overflow: auto;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          background: var(--ha-card-background, var(--card-background-color));
          box-shadow: 0 12px 32px rgba(0, 0, 0, 0.24);
          color: var(--primary-text-color);
          font: inherit;
        }

        .dashboard-activity-filter-popover::backdrop {
          background: transparent;
        }

        .dashboard-activity-filter-popover h3,
        .dashboard-activity-filter-popover h4 {
          margin: 0;
        }

        .dashboard-activity-filter-popover h3 {
          font-size: 18px;
        }

        .dashboard-activity-filter-popover h4 {
          font-size: 14px;
          font-weight: 600;
        }

        .dashboard-activity-filter-section {
          display: grid;
          gap: 10px;
          margin-top: 18px;
        }

        .dashboard-activity-event-groups {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px 18px;
        }

        .dashboard-activity-event-group {
          display: grid;
          gap: 7px;
          min-width: 0;
          margin: 0;
          padding: 0;
          border: 0;
        }

        .dashboard-activity-event-group legend {
          margin-bottom: 7px;
          color: var(--secondary-text-color);
          font-size: 13px;
          font-weight: 600;
        }

        .dashboard-activity-filter-subgroup {
          margin: 1px 0 0;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 600;
        }

        .dashboard-activity-filter-option {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          min-width: 0;
          cursor: pointer;
          font-size: 14px;
          line-height: 1.35;
        }

        .dashboard-activity-filter-option input {
          flex: 0 0 auto;
          width: 16px;
          height: 16px;
          margin: 1px 0 0;
          accent-color: var(--primary-color);
        }

        .dashboard-activity-filter-option input:focus-visible,
        .dashboard-activity-filter-field select:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .dashboard-activity-filter-selects {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .dashboard-activity-filter-field {
          display: grid;
          gap: 5px;
          min-width: 0;
          font-size: 13px;
          font-weight: 600;
        }

        .dashboard-activity-filter-field select {
          width: 100%;
          min-width: 0;
          min-height: 38px;
          padding: 7px 28px 7px 9px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
          font-weight: 400;
        }

        .dashboard-activity-filter-help {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 14px;
        }

        .dashboard-activity-filter-footer {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          margin-top: 20px;
          padding-top: 10px;
          border-top: 1px solid var(--divider-color);
        }

        .dashboard-activity-filter-empty {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
        }

        .dashboard-attention-list {
          display: grid;
          overflow: hidden;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          background: var(--ha-card-background, var(--card-background-color));
        }

        .dashboard-attention-item {
          display: grid;
          gap: 8px;
          padding: 13px 16px;
          border-left: 4px solid var(--warning-color, #b26a00);
        }

        .dashboard-attention-item + .dashboard-attention-item {
          border-top: 1px solid var(--divider-color);
        }

        .dashboard-attention-item.error {
          border-left-color: var(--error-color, #db4437);
        }

        .dashboard-attention-relationship {
          margin: 0;
          font-weight: 600;
        }

        .dashboard-attention-navigation {
          display: flex;
          flex-wrap: wrap;
          gap: 6px 14px;
        }

        .dashboard-attention-navigation button {
          padding: 2px 0;
          border: 0;
          background: transparent;
          color: var(--primary-color);
          cursor: pointer;
          font: inherit;
          font-size: 13px;
          text-decoration: underline;
          text-underline-offset: 2px;
        }

        .dashboard-attention-navigation button:focus-visible {
          border-radius: 2px;
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .dashboard-attention-failure {
          margin: 0;
          color: var(--secondary-text-color);
        }

        .dashboard-activity-state {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 14px;
        }

        .dashboard-activity-list,
        .dashboard-activity-date-group {
          display: grid;
          gap: 12px;
        }

        .dashboard-activity-list {
          gap: 20px;
        }

        .dashboard-activity-date-heading {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 14px;
          font-weight: 600;
        }

        .dashboard-activity-rows {
          display: grid;
          overflow: hidden;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          background: var(--ha-card-background, var(--card-background-color));
        }

        .dashboard-activity-row {
          display: grid;
          grid-template-columns: 26px minmax(0, 1fr) auto;
          gap: 12px;
          align-items: start;
          min-width: 0;
          padding: 13px 16px;
          border: 0;
          border-left: 3px solid transparent;
          background: transparent;
          color: inherit;
          font: inherit;
          text-align: left;
        }

        .dashboard-activity-row + .dashboard-activity-row {
          border-top: 1px solid var(--divider-color);
        }

        button.dashboard-activity-row {
          cursor: pointer;
        }

        button.dashboard-activity-row:hover {
          background: var(--secondary-background-color);
        }

        button.dashboard-activity-row:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: -3px;
        }

        .dashboard-activity-row.warning {
          border-left-color: var(--warning-color, #b26a00);
        }

        .dashboard-activity-row.critical {
          border-left-color: var(--error-color, #db4437);
        }

        .dashboard-activity-icon {
          margin-top: 2px;
          color: var(--secondary-text-color);
        }

        .dashboard-activity-row.warning .dashboard-activity-icon {
          color: var(--warning-color, #b26a00);
        }

        .dashboard-activity-row.critical .dashboard-activity-icon {
          color: var(--error-color, #db4437);
        }

        .dashboard-activity-copy {
          display: grid;
          min-width: 0;
          gap: 3px;
        }

        .dashboard-activity-title,
        .dashboard-activity-description {
          margin: 0;
          overflow-wrap: anywhere;
        }

        .dashboard-activity-title {
          font-weight: 600;
        }

        .dashboard-activity-description,
        .dashboard-activity-time {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .dashboard-activity-time {
          white-space: nowrap;
        }

        .door-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
          gap: 14px;
        }

        .dashboard-people {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }

        .door-card {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 12px;
          min-height: 94px;
          padding: 16px 18px;
        }

        .door-card-open {
          display: grid;
          grid-template-columns: 76px minmax(0, 1fr);
          gap: 14px;
          align-items: center;
          min-width: 0;
          padding: 0;
          border: 0;
          appearance: none;
          background: transparent;
          color: inherit;
          cursor: pointer;
          font: inherit;
          text-align: left;
          transition: box-shadow 160ms ease, transform 160ms ease;
        }

        .door-card-open:hover {
          transform: translateY(-2px);
        }

        .door-card-open:focus-visible,
        .dashboard-door-action:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 3px;
        }

        .homepass-status-icon-slot {
          position: relative;
          display: grid;
          width: 60px;
          height: 60px;
          place-items: center;
        }

        .homepass-nfc-status-badge {
          position: absolute;
          right: -5px;
          bottom: -5px;
          display: grid;
          width: 25px;
          height: 25px;
          place-items: center;
          border: 2px solid var(--card-background-color);
          border-radius: 50%;
          background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color));
          box-shadow: 0 2px 7px rgba(0, 0, 0, 0.16);
        }

        .homepass-nfc-status-badge[hidden] {
          display: none !important;
        }

        .homepass-nfc-status-badge img {
          display: block;
          width: 19px;
          height: 19px;
        }

        .door-card-identity {
          display: grid;
          min-width: 0;
          place-items: center;
        }

        .door-status-icon {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .door-card-copy {
          display: grid;
          align-content: center;
          gap: 3px;
        }

        .door-card h3 {
          margin: 0;
          font-size: 19px;
          font-weight: 650;
          overflow-wrap: anywhere;
          text-align: left;
        }

        .dashboard-door-lock-state,
        .dashboard-door-contact-state {
          margin: 0;
        }

        .dashboard-door-lock-state {
          font-size: 16px;
          font-weight: 500;
        }

        .dashboard-door-contact-state {
          color: var(--secondary-text-color);
          font-size: 15px;
        }

        .door-management-state,
        .dashboard-empty-message {
          margin: 0;
          color: var(--secondary-text-color);
        }

        .door-management-state {
          font-size: 13px;
        }

        .dashboard-door-control {
          display: grid;
          align-content: center;
          justify-items: end;
          gap: 5px;
          min-width: 70px;
        }

        .dashboard-door-action {
          min-width: 82px;
          min-height: 40px;
          padding: 0 14px;
          border: 1px solid color-mix(in srgb, var(--primary-color) 44%, transparent);
          border-radius: 999px;
          background: color-mix(in srgb, var(--primary-color) 11%, var(--card-background-color));
          color: var(--primary-color);
          cursor: pointer;
          font: inherit;
          font-size: 13px;
          font-weight: 650;
          transition: background 160ms ease, border-color 160ms ease;
        }

        .dashboard-door-action:hover:not(:disabled) {
          background: color-mix(in srgb, var(--primary-color) 18%, var(--card-background-color));
        }

        .dashboard-door-action[data-confirmation="true"]::after {
          content: "…";
        }

        .dashboard-door-action:disabled {
          cursor: not-allowed;
          opacity: 0.48;
        }

        .dashboard-door-switch-status {
          max-width: 92px;
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 11px;
          line-height: 1.25;
          text-align: right;
        }

        .dashboard-door-switch-status.error {
          color: var(--error-color);
        }

        .dashboard-person-card .person {
          padding: 14px 16px;
        }

        .dashboard-person-card .person-content {
          gap: 5px;
        }

        .dashboard-person-card .person-notes {
          display: none;
        }

        .dashboard-empty-card {
          padding: 24px;
        }

        .dashboard-empty-card {
          display: grid;
          gap: 8px;
        }

        .dashboard-empty-card h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .detail-fields {
          display: grid;
          gap: 16px;
        }

        .detail-field {
          display: grid;
          gap: 4px;
        }

        .detail-label {
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
        }

        .detail-value {
          margin: 0;
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }

        .summary-card {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr);
          gap: 16px;
          align-items: start;
        }

        .summary-card ha-icon {
          color: var(--primary-color);
        }

        .summary-card h2 {
          margin-bottom: 8px;
        }

        .summary-card p {
          margin: 0;
          color: var(--secondary-text-color);
        }

        .schedule-entry-copy {
          display: grid;
          gap: 4px;
        }

        .schedule-entry-action {
          margin-top: 16px;
        }

        .local-timezone-note {
          margin: 20px 0 0;
          color: var(--secondary-text-color);
        }

        .schedule-builder {
          display: grid;
          gap: 16px;
        }

        .schedule-section {
          padding: 24px;
        }

        .schedule-section h2 {
          margin: 0 0 16px;
          font-size: 20px;
          font-weight: 500;
        }

        .schedule-options {
          display: flex;
          flex-wrap: wrap;
          gap: 20px;
          margin: 0;
          padding: 0;
          border: 0;
        }

        .schedule-option {
          display: inline-flex;
          align-items: center;
          min-height: 44px;
          cursor: pointer;
        }

        .schedule-option input {
          width: 20px;
          height: 20px;
          margin: 0 10px 0 0;
          accent-color: var(--primary-color);
        }

        .schedule-input-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-top: 20px;
        }

        .schedule-native-field {
          display: grid;
          gap: 6px;
        }

        .schedule-native-field label {
          font-size: 13px;
          font-weight: 500;
        }

        .schedule-native-field input {
          box-sizing: border-box;
          width: 100%;
          min-height: 44px;
          padding: 8px 10px;
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          color-scheme: light dark;
          font: inherit;
        }

        .schedule-native-field input:focus-visible,
        .weekday-button:focus-visible,
        .all-days-button:focus-visible,
        .schedule-group-button:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .weekday-options {
          display: grid;
          grid-template-columns: repeat(7, minmax(48px, 1fr));
          gap: 8px;
        }

        .all-days-button {
          width: fit-content;
          min-height: 36px;
          margin: 0 0 12px;
          padding: 6px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
        }

        .schedule-group-options,
        .schedule-door-options {
          display: grid;
          gap: 10px;
        }

        .schedule-group-button {
          min-height: 44px;
          padding: 10px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
          text-align: left;
        }

        .schedule-group-button[aria-pressed="true"] {
          border: 2px solid var(--primary-color);
        }

        .schedule-group-button.add {
          color: var(--primary-color);
        }

        .schedule-door-options {
          margin: 0;
          padding: 0;
          border: 0;
        }

        .schedule-door-options label {
          display: flex;
          align-items: center;
          gap: 10px;
          min-height: 40px;
        }

        .schedule-helper,
        .schedule-pin-note {
          color: var(--secondary-text-color);
        }

        .weekday-button {
          min-height: 48px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          cursor: pointer;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
          font-weight: 500;
        }

        .weekday-button[aria-pressed="true"] {
          border: 2px solid var(--primary-color);
          background: var(--primary-color);
          color: var(--text-primary-color);
        }

        .weekday-button[aria-pressed="true"]::before {
          content: "✓ ";
        }

        .schedule-error {
          margin: 12px 0 0;
          color: var(--error-color);
        }

        .schedule-input-grid .schedule-error {
          grid-column: 1 / -1;
        }

        .schedule-builder-footer {
          display: grid;
          gap: 12px;
          justify-items: end;
          padding-top: 8px;
        }

        .schedule-builder-status {
          min-height: 20px;
          margin: 0;
          color: var(--secondary-text-color);
        }

        .schedule-builder-actions {
          display: flex;
          gap: 8px;
        }

        .schedule-persistence-note {
          max-width: 560px;
          margin: 0;
          color: var(--secondary-text-color);
          text-align: right;
          white-space: pre-line;
        }

        @media (max-width: 720px) {
          .app-shell {
            grid-template-columns: 1fr;
          }

          .primary-navigation {
            position: fixed;
            inset: auto 0 0;
            z-index: 10;
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 2px;
            padding: 6px 4px calc(6px + env(safe-area-inset-bottom));
            border-right: 0;
            border-top: 1px solid var(--divider-color);
            box-shadow: 0 -4px 18px rgb(0 0 0 / 10%);
          }

          .primary-navigation button {
            display: grid;
            min-width: 0;
            min-height: 52px;
            justify-items: center;
            align-content: center;
            gap: 2px;
            padding: 4px 2px;
            font-size: 11px;
            line-height: 1.1;
            text-align: center;
          }

          .top-level-page,
          .detail-page {
            padding-bottom: calc(92px + env(safe-area-inset-bottom));
          }

          .settings-groups {
            grid-template-columns: 1fr;
          }
          .dashboard-header-top {
            flex-direction: column;
            align-items: stretch;
            gap: 16px;
          }

          .dashboard-header-tail {
            width: 100%;
            padding-bottom: 0;
          }

          .dashboard-property-name {
            flex: 1 1 auto;
            max-width: none;
          }

          .dashboard-header {
            margin-top: -8px;
            margin-bottom: 11px;
          }

          .dashboard-header-actions {
            align-self: stretch;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .dashboard-header-actions ha-button {
            width: 100%;
          }

          .homepass-status-icon-slot {
            width: 54px;
            height: 54px;
          }

          .dashboard-people {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 600px) {
          .top-level-page,
          .detail-page {
            padding: 24px 16px 32px;
          }

          .dashboard-header {
            margin-top: -6px;
          }

          .dashboard-header-tail {
            align-items: stretch;
            flex-direction: column;
            gap: 10px;
          }

          .dashboard-property-name {
            overflow-wrap: anywhere;
            white-space: normal;
          }

          header {
            align-items: flex-start;
            flex-direction: column;
          }

          .people-header {
            gap: 20px;
          }

          .people-header .add-person {
            align-self: stretch;
            justify-content: center;
          }

          .person-details-header .details-actions {
            align-self: stretch;
            flex-wrap: wrap;
            justify-content: flex-end;
          }

          .add-user-form {
            width: calc(100vw - 48px);
          }

          .wizard-pin-row,
          .wizard-date-time-grid,
          .manage-access-pin {
            grid-template-columns: 1fr;
          }

          .manage-access-pin .wizard-help {
            grid-column: 1;
          }

          .wizard-pin-row > button {
            justify-self: start;
          }

          .wizard-new-schedule fieldset:not(.wizard-option-group) {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .people-header-actions {
            align-self: stretch;
            justify-content: flex-end;
          }

          .dashboard-content {
            gap: 24px;
          }

          .dashboard-people {
            grid-template-columns: 1fr;
          }

          .doors-grid {
            grid-template-columns: 1fr;
          }

          .door-page-card {
            min-height: 0;
            padding: 24px;
          }

          .door-control-content {
            width: calc(100vw - 48px);
            max-height: calc(100dvh - 168px);
          }

          .door-title-editor {
            width: calc(100vw - 112px);
            grid-template-columns: minmax(112px, 1fr) 34px 34px;
          }

          .door-title-icon-button {
            width: 34px;
            height: 34px;
            flex-basis: 34px;
          }

          .door-nfc-action {
            padding: 11px 12px;
          }

          .door-control-facts > div {
            grid-template-columns: 1fr;
            gap: 4px;
          }

          .door-control-state-layout {
            grid-template-columns: 82px minmax(0, 1fr);
            gap: 16px;
          }

          .door-control-status-graphic .homepass-status-icon-slot {
            width: 74px;
            height: 74px;
          }

          .dashboard-section-heading {
            align-items: flex-start;
          }

          .dashboard-activity-event-groups,
          .dashboard-activity-filter-selects {
            grid-template-columns: 1fr;
          }

          .dashboard-activity-filter-popover {
            max-height: calc(100dvh - 24px);
          }

          .dashboard-activity-row {
            grid-template-columns: 26px minmax(0, 1fr);
          }

          .dashboard-activity-time {
            grid-column: 2;
            white-space: normal;
          }

          .door-card,
          .dashboard-empty-card {
            padding: 16px;
          }

          .homepass-status-icon-slot {
            width: 48px;
            height: 48px;
          }

          .header-brand-mark {
            width: 100%;
            height: auto;
          }

          .header-brand-mark-crop {
            width: clamp(288px, 92vw, 350px);
          }

          .brand-kicker {
            gap: 12px;
          }

          .person {
            padding: 24px;
          }

          .details-grid {
            grid-template-columns: 1fr;
          }

          .profile-card {
            grid-column: auto;
          }

          .schedule-input-grid {
            grid-template-columns: 1fr;
          }

          .weekday-options {
            grid-template-columns: repeat(4, minmax(48px, 1fr));
          }

          .schedule-builder-footer {
            justify-items: stretch;
          }

          .schedule-builder-actions {
            justify-content: flex-end;
          }

          .schedule-persistence-note {
            text-align: left;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
          }
        }
      </style>
      ${this._pageTemplate()}
      ${this._dialogOpen ? this._dialogTemplate() : ""}
      ${this._deleteDialogOpen ? this._deleteDialogTemplate() : ""}
      ${this._manageAccessDialogOpen ? this._manageAccessDialogTemplate() : ""}
      ${this._doorControlDialogOpen && !this._removeDoorConfirmationOpen ? this._doorControlDialogTemplate() : ""}
      ${this._doorControlDialogOpen && this._removeDoorConfirmationOpen ? this._removeDoorConfirmationTemplate() : ""}
      ${this._addDoorDialogOpen ? this._addDoorDialogTemplate() : ""}
      ${this._addAccessDeviceDialogOpen ? this._addAccessDeviceDialogTemplate() : ""}
      ${this._policyInspectorOpen ? this._policyInspectorTemplate() : ""}
    `;

    for (const navigation of this.shadowRoot.querySelectorAll("[data-primary-page]")) {
      navigation.addEventListener("click", () => this._navigatePrimary(navigation.dataset.primaryPage));
    }

    if (this._detailsPersonId && this._personScheduleViewOpen) {
      this.shadowRoot
        .querySelector("#back-to-person")
        .addEventListener("click", () => this._closePersonSchedule());
      this._renderPersonSchedule();
    } else if (this._detailsPersonId) {
      this.shadowRoot
        .querySelector("#person-details-dashboard")
        .addEventListener("click", () => this._openDashboardFromPersonDetails());
      this.shadowRoot
        .querySelector("#person-details-users")
        .addEventListener("click", () => this._openUsersFromPersonDetails());
      const edit = this.shadowRoot.querySelector("#edit-person");
      edit.disabled = this._detailsLoading || !this._selectedPerson;
      edit.addEventListener("click", () => this._openEditPersonDialog());
      const deletePerson = this.shadowRoot.querySelector("#delete-person");
      deletePerson.disabled = this._detailsLoading || !this._selectedPerson;
      deletePerson.addEventListener("click", () => this._openDeletePersonDialog());
      const accessAction = this.shadowRoot.querySelector("#access-action");
      accessAction.disabled = this._detailsLoading || !this._selectedPerson;
      accessAction.addEventListener("click", () => void this._openManageAccessDialog());
      this._renderPersonDetails();
    } else if (this._currentPage === "doors") {
      this.shadowRoot
        .querySelector("#doors-to-dashboard")
        .addEventListener("click", () => this._openDashboardPage());
      this.shadowRoot
        .querySelector("#doors-to-people")
        .addEventListener("click", () => this._openPeoplePage());
      this.shadowRoot
        .querySelector("#add-door")
        .addEventListener("click", () => void this._openAddDoorDialog());
      this.shadowRoot
        .querySelector("#add-access-device")
        ?.addEventListener("click", () => void this._openAddAccessDeviceDialog());
      this._renderDoors();
    } else if (this._currentPage === "people") {
      this.shadowRoot
        .querySelector("#back-to-dashboard")
        .addEventListener("click", () => this._openDashboardPage());
      this.shadowRoot
        .querySelector("#people-to-doors")
        .addEventListener("click", () => this._openDoorsPage());
      this.shadowRoot
        .querySelector("#add-person")
        .addEventListener("click", () => this._openAddPersonDialog());
      this._renderPeople();
      if (this._dialogOpen) {
        this._configureDialog();
      }
    } else if (this._currentPage === "activity") {
      this._renderActivityPage();
    } else if (this._currentPage === "settings") {
      const checkNukiStorage = this.shadowRoot.querySelector("#check-nuki-storage");
      if (checkNukiStorage) {
        checkNukiStorage.addEventListener("click", () => void this._checkNukiStorage());
      }
      const propertyName = this.shadowRoot.querySelector("#property-name");
      if (propertyName) {
        propertyName.addEventListener("input", (event) => this._handlePropertyNameInput(event));
      }
      const propertySave = this.shadowRoot.querySelector("#save-property-settings");
      if (propertySave) {
        propertySave.addEventListener("click", () => void this._savePropertySettings());
      }
      const propertyRetry = this.shadowRoot.querySelector("#retry-property-settings");
      if (propertyRetry) {
        propertyRetry.addEventListener("click", () => void this._loadPropertySettings());
      }
      const save = this.shadowRoot.querySelector("#save-notification-settings");
      if (save) save.addEventListener("click", () => void this._saveNotificationSettings());
      const retry = this.shadowRoot.querySelector("#retry-notification-settings");
      if (retry) retry.addEventListener("click", () => void this._loadNotificationSettings());
      this.shadowRoot.querySelectorAll("[data-notification-preset]").forEach((button) => {
        button.addEventListener("click", () => this._applyNotificationPreset(button.dataset.notificationPreset));
      });
      this._syncPropertySettingsControls();
    } else if (this._currentPage === "about") {
      const retry = this.shadowRoot.querySelector("#retry-about");
      if (retry) retry.addEventListener("click", () => void this._loadAbout());
    } else {
      this.shadowRoot
        .querySelector("#dashboard-add-person")
        .addEventListener("click", () => this._openAddPersonDialog());
      this.shadowRoot
        .querySelector("#dashboard-view-people")
        .addEventListener("click", () => this._openPeoplePage());
      this._renderDashboard();
      if (this._dialogOpen) {
        this._configureDialog();
      }
    }
    if (this._addAccessDeviceDialogOpen) {
      const dialog = this.shadowRoot.querySelector("#add-access-device-dialog");
      this._addAccessDeviceDialogElement = dialog;
      dialog?.addEventListener("closed", () => {
        if (this._addAccessDeviceDialogElement !== dialog) return;
        this._closeAddAccessDeviceDialog();
      });
      this.shadowRoot.querySelector("#cancel-add-access-device")
        ?.addEventListener("click", () => this._closeAddAccessDeviceDialog());
      this.shadowRoot.querySelector("#confirm-add-access-device")
        ?.addEventListener("click", () => void this._addSelectedAccessDevice());
      this.shadowRoot.querySelector("#refresh-access-devices")
        ?.addEventListener("click", () => void this._loadAccessDevices());
      for (const option of this.shadowRoot.querySelectorAll(
        'input[name="available-access-device"]',
      )) {
        option.addEventListener("change", () => {
          this._selectedAccessDeviceCandidateId = option.value;
          const candidate = this._availableAccessDevices.find(
            (item) => item.home_assistant_device_id === option.value,
          );
          if (!this._accessDeviceDisplayName) {
            this._accessDeviceDisplayName = candidate?.display_name ?? "";
          }
          this._render();
        });
      }
      this.shadowRoot.querySelector("#access-device-door")
        ?.addEventListener("change", (event) => {
          this._selectedAccessDeviceDoorId = event.target.value;
          this.shadowRoot.querySelector("#confirm-add-access-device").disabled = !(
            this._selectedAccessDeviceCandidateId && this._selectedAccessDeviceDoorId
          );
        });
      this.shadowRoot.querySelector("#access-device-display-name")
        ?.addEventListener("input", (event) => {
          this._accessDeviceDisplayName = event.target.value;
        });
    }
    if (this._detailsPersonId && this._dialogOpen) {
      this._configureDialog();
    }
    if (this._detailsPersonId && this._deleteDialogOpen) {
      this._configureDeleteDialog();
    }
    if (this._detailsPersonId && this._manageAccessDialogOpen) {
      this._configureManageAccessDialog();
    }
    if (this._doorControlDialogOpen && !this._removeDoorConfirmationOpen) {
      const dialog = this.shadowRoot.querySelector("#door-control-dialog");
      this._doorControlDialogElement = dialog;
      dialog.addEventListener("closed", () => {
        if (this._doorControlDialogElement !== dialog) return;
        this._closeDoorControlDialog();
      });
      this.shadowRoot
        .querySelector("#close-door-control")
        .addEventListener("click", () => this._closeDoorControlDialog());
      if (this._doorNfcSetupOpen) {
        this.shadowRoot
          .querySelector("#back-door-nfc-setup")
          ?.addEventListener("click", () => this._closeDoorNfcSetup());
        this.shadowRoot
          .querySelector(NFC_PROVISIONER_WEB_COMPONENT)
          ?.addEventListener("homepass-nfc-tag-prepared", (event) => {
            this._markDoorNfcEnabled(event.detail?.access_point_id);
            void this._loadDoorNfcTags(event.detail?.access_point_id);
          });
        this.shadowRoot
          .querySelector(NFC_PROVISIONER_WEB_COMPONENT)
          ?.addEventListener("homepass-nfc-tag-protected", (event) => {
            void this._loadDoorNfcTags(event.detail?.access_point_id);
          });
        const nfcOrigin = this.shadowRoot.querySelector("#door-nfc-public-origin");
        nfcOrigin?.addEventListener("input", (event) => {
          this._doorNfcOriginDraft = event.target.value;
          this._doorNfcConfigurationError = undefined;
          const save = this.shadowRoot.querySelector("#save-door-nfc-configuration");
          if (save) save.disabled = !this._doorNfcOriginDraft.trim();
        });
        this.shadowRoot
          .querySelector("#save-door-nfc-configuration")
          ?.addEventListener("click", () => void this._configureDoorNfc());
      } else {
        this.shadowRoot
          .querySelector("#refresh-door-control")
          ?.addEventListener("click", () => void this._loadDoorStatus(this._selectedDoorId));
        this.shadowRoot
          .querySelector("#open-remove-door-confirmation")
          ?.addEventListener("click", () => this._openRemoveDoorConfirmation());
        this.shadowRoot
          .querySelector("#edit-door-name")
          ?.addEventListener("click", () => this._startDoorNameEdit());
        this.shadowRoot
          .querySelector("#save-homepass-door-name")
          ?.addEventListener("click", () => void this._saveDoorName());
        this.shadowRoot
          .querySelector("#cancel-homepass-door-name")
          ?.addEventListener("click", () => this._cancelDoorNameEdit());
        this.shadowRoot
          .querySelector("#open-door-nfc-setup")
          ?.addEventListener("click", () => this._openDoorNfcSetup());
        this.shadowRoot
          .querySelector("#edit-door-sensor")
          ?.addEventListener("click", () => this._openDoorSensorEdit());
        this.shadowRoot
          .querySelector("#cancel-door-sensor")
          ?.addEventListener("click", () => this._cancelDoorSensorEdit());
        this.shadowRoot
          .querySelector("#save-door-sensor")
          ?.addEventListener("click", () => void this._saveDoorSensor());
        const statusEntity = this.shadowRoot.querySelector("#edit-door-status-entity");
        statusEntity?.addEventListener("change", () => {
          this._doorSensorEntityId = statusEntity.value;
          if (!statusEntity.value) this._doorSensorInverted = false;
          this._doorSensorError = undefined;
          this._render();
        });
        const statusInverted = this.shadowRoot.querySelector("#edit-door-status-inverted");
        statusInverted?.addEventListener("change", () => {
          this._doorSensorInverted = statusInverted.checked;
          this._doorSensorError = undefined;
        });
        for (const revoke of this.shadowRoot.querySelectorAll("[data-revoke-nfc-tag]")) {
          revoke.addEventListener("click", () => void this._revokeDoorNfcTag(
            revoke.dataset.revokeNfcTag,
            revoke.dataset.nfcTagUid,
          ));
        }
        for (const reinstate of this.shadowRoot.querySelectorAll("[data-reinstate-nfc-tag]")) {
          reinstate.addEventListener("click", () => void this._reinstateDoorNfcTag(
            reinstate.dataset.reinstateNfcTag,
            reinstate.dataset.nfcTagUid,
          ));
        }
        for (const remove of this.shadowRoot.querySelectorAll("[data-delete-nfc-tag]")) {
          remove.addEventListener("click", () => void this._deleteDoorNfcTag(
            remove.dataset.deleteNfcTag,
            remove.dataset.nfcTagUid,
          ));
        }
        for (const protect of this.shadowRoot.querySelectorAll("[data-protect-nfc-tag]")) {
          protect.addEventListener("click", () => void this._prepareDoorNfcTagProtection(
            protect.dataset.protectNfcTag,
            protect.dataset.nfcTagUid,
          ));
        }
        for (const confirm of this.shadowRoot.querySelectorAll("[data-confirm-protected-nfc-tag]")) {
          confirm.addEventListener("click", () => void this._confirmDoorNfcTagProtection(
            confirm.dataset.confirmProtectedNfcTag,
          ));
        }
        const nameInput = this.shadowRoot.querySelector("#door-title-name-input");
        nameInput?.addEventListener("input", () => {
          this._doorNameDraft = nameInput.value;
        });
        nameInput?.addEventListener("keydown", (event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            this._cancelDoorNameEdit();
          } else if (event.key === "Enter") {
            event.preventDefault();
            void this._saveDoorName();
          }
        });
        const slideAction = this.shadowRoot.querySelector("#door-slide-action");
        slideAction.callback = () => void this._beginDoorOperation();
        slideAction.addEventListener(
          "slide-action-state-changed",
          (event) => this._handleDoorSlideState(event),
        );
        this._updateDoorControlDialog();
        if (restoreDoorSlideFocus) slideAction.focus();
      }
    }
    if (this._removeDoorConfirmationOpen) {
      const dialog = this.shadowRoot.querySelector("#remove-door-confirmation");
      this._removeDoorConfirmationDialogElement = dialog;
      dialog.addEventListener("closed", () => {
        if (this._removeDoorConfirmationDialogElement !== dialog) return;
        this._closeRemoveDoorConfirmation();
      });
      this.shadowRoot
        .querySelector("#cancel-remove-door")
        .addEventListener("click", () => this._closeRemoveDoorConfirmation());
      this.shadowRoot
        .querySelector("#confirm-remove-door")
        .addEventListener("click", () => void this._removeSelectedDoor());
    }
    if (this._addDoorDialogOpen) {
      const dialog = this.shadowRoot.querySelector("#add-door-dialog");
      this._addDoorDialogElement = dialog;
      dialog.addEventListener("closed", () => {
        // Async loading and page refreshes rebuild this dialog. Home Assistant's
        // detached old element can emit `closed` after its replacement mounts;
        // only the element that currently owns the session may close it.
        if (this._addDoorDialogElement !== dialog) return;
        this._closeAddDoorDialog();
      });
      this.shadowRoot
        .querySelector("#cancel-add-door")
        .addEventListener("click", () => this._closeAddDoorDialog());
      this.shadowRoot
        .querySelector("#confirm-add-door")
        .addEventListener("click", () => void this._enrollSelectedDoor());
      const source = this.shadowRoot.querySelector("#add-door-source");
      source?.addEventListener("change", () => {
        this._addDoorSource = source.value;
        this._availableAccessPointsError = undefined;
        this._render();
      });
      const profile = this.shadowRoot.querySelector("#ha-door-profile");
      profile?.addEventListener("change", () => {
        this._haDoorProfile = profile.value;
        this._haDoorControlEntityId = "";
        this._render();
      });
      const device = this.shadowRoot.querySelector("#ha-door-device");
      device?.addEventListener("change", () => {
        this._haDoorDeviceId = device.value;
        this._haDoorControlEntityId = "";
        this._haDoorStatusEntityId = "";
        const selectedDevice = this._haDoorDevices.find((item) => item.id === this._haDoorDeviceId);
        if (!this._haDoorDisplayName && selectedDevice) {
          this._haDoorDisplayName = this._haDoorDeviceLabel(selectedDevice);
        }
        this._render();
      });
      const control = this.shadowRoot.querySelector("#ha-door-control-entity");
      control?.addEventListener("change", () => {
        this._haDoorControlEntityId = control.value;
        const name = this.shadowRoot.querySelector("#ha-door-display-name");
        if (!this._haDoorDisplayName) {
          const entity = this._haDoorEntities.find((item) => item.entity_id === control.value);
          this._haDoorDisplayName = entity ? this._haDoorEntityLabel(entity) : "";
          if (name) name.value = this._haDoorDisplayName;
        }
        this.shadowRoot.querySelector("#confirm-add-door").disabled = !this._haDoorManualFormValid();
      });
      const status = this.shadowRoot.querySelector("#ha-door-status-entity");
      status?.addEventListener("change", () => {
        this._haDoorStatusEntityId = status.value;
        if (!status.value) this._haDoorStatusInverted = false;
        const inverted = this.shadowRoot.querySelector("#ha-door-status-inverted");
        if (inverted) {
          inverted.disabled = !status.value;
          if (!status.value) inverted.checked = false;
        }
        this.shadowRoot.querySelector("#confirm-add-door").disabled = !this._haDoorManualFormValid();
      });
      const name = this.shadowRoot.querySelector("#ha-door-display-name");
      name?.addEventListener("input", () => {
        this._haDoorDisplayName = name.value;
        this.shadowRoot.querySelector("#confirm-add-door").disabled = !this._haDoorManualFormValid();
      });
      const inverted = this.shadowRoot.querySelector("#ha-door-status-inverted");
      inverted?.addEventListener("change", () => { this._haDoorStatusInverted = inverted.checked; });
      const pulse = this.shadowRoot.querySelector("#ha-door-pulse-seconds");
      pulse?.addEventListener("input", () => {
        this._haDoorPulseSeconds = pulse.value;
        this.shadowRoot.querySelector("#confirm-add-door").disabled = !this._haDoorManualFormValid();
      });
      for (const option of this.shadowRoot.querySelectorAll('input[name="available-door"]')) {
        option.addEventListener("change", () => {
          this._selectedAvailableAccessPointId = option.value;
          this._render();
        });
      }
    }
    if (this._policyInspectorOpen) {
      const dialog = this.shadowRoot.querySelector("#policy-inspector-dialog");
      this._policyInspectorDialogElement = dialog;
      dialog.addEventListener("closed", () => {
        if (this._policyInspectorDialogElement !== dialog) return;
        this._closePolicyInspector();
      });
      const close = this.shadowRoot.querySelector("#close-policy-inspector");
      close.addEventListener("click", () => this._closePolicyInspector());
      this._updatePolicyInspectorDialog();
      close.focus();
    }
  }

  _navigatePrimary(page) {
    if (page === this._currentPage && !this._detailsPersonId) return;
    if (this._detailsPersonId) {
      this._currentPage = page;
      if (page === "settings") this._settingsLoading = true;
      if (page === "settings") this._propertySettingsLoading = true;
      this._closePersonDetails();
      if (page === "doors") void this._loadDoorsAndDevices();
      if (page === "dashboard") void this._loadDashboardPropertySettings();
      if (page === "activity") {
        this._cancelDashboardActivityRequest();
        this._dashboardActivityLoading = true;
        void this._loadDashboardActivity();
      }
      if (page === "settings") void this._loadNotificationSettings();
      if (page === "settings") void this._loadPropertySettings();
      if (page === "about") {
        this._aboutData = undefined;
        this._aboutLoading = true;
        void this._loadAbout();
      }
      return;
    }
    if (page === "dashboard") this._openDashboardPage();
    if (page === "doors") this._openDoorsPage();
    if (page === "people") this._openPeoplePage();
    if (page === "activity") this._openActivityPage();
    if (page === "settings") this._openSettingsPage();
    if (page === "about") this._openAboutPage();
  }

  _pageTemplate() {
    let content;
    if (this._detailsPersonId && this._personScheduleViewOpen) {
      content = this._personSchedulePageTemplate();
    } else if (this._detailsPersonId) {
      content = this._detailsPageTemplate();
    } else if (this._currentPage === "doors") {
      content = this._doorsPageTemplate();
    } else if (this._currentPage === "activity") {
      content = this._activityPageTemplate();
    } else if (this._currentPage === "settings") {
      content = this._settingsPageTemplate();
    } else if (this._currentPage === "about") {
      content = this._aboutPageTemplate();
    } else {
      content = this._currentPage === "people"
        ? this._peoplePageTemplate()
        : this._dashboardPageTemplate();
    }
    return `<div class="app-shell">${this._primaryNavigationTemplate()}${content}</div>`;
  }

  _primaryNavigationTemplate() {
    const current = this._detailsPersonId ? "people" : this._currentPage;
    const item = (page, icon, label) => `
      <button type="button" data-primary-page="${page}" ${current === page ? 'aria-current="page"' : ""}>
        <ha-icon icon="${icon}"></ha-icon><span>${label}</span>
      </button>`;
    return `
      <nav class="primary-navigation" aria-label="HomePASS">
        ${item("dashboard", "mdi:view-dashboard-outline", "Dashboard")}
        ${item("people", "mdi:account-group-outline", "Users")}
        ${item("doors", "mdi:door-open", "Doors & Devices")}
        ${item("activity", "mdi:history", "Activity")}
        ${item("settings", "mdi:cog-outline", "Settings")}
        ${item("about", "mdi:information-outline", "About")}
      </nav>`;
  }

  _dashboardPageTemplate() {
    return `
      <main class="page top-level-page">
        <header class="people-header dashboard-header">
          <div class="dashboard-header-top">
            ${this._homePassBrandLockup()}
            <div class="dashboard-header-tail">
              ${this._dashboardPropertyNameTemplate()}
              <div class="dashboard-header-actions" aria-label="Dashboard quick actions">
                <ha-button id="dashboard-view-people" appearance="plain">
                  <ha-icon icon="mdi:account-group-outline" slot="start"></ha-icon>
                  View Users
                </ha-button>
                <ha-button id="dashboard-add-person" appearance="filled">
                  <ha-icon icon="mdi:account-plus" slot="start"></ha-icon>
                  Add User
                </ha-button>
              </div>
            </div>
          </div>
        </header>
        <section id="content" class="dashboard-content" aria-live="polite"></section>
      </main>
    `;
  }

  _doorsPageTemplate() {
    return `
      <main class="page top-level-page">
        <header class="people-header doors-header">
          <div>
            ${this._homePassBrandLockup()}
            <h1>Doors &amp; Devices</h1>
            <p id="door-count" class="door-count" aria-live="polite"></p>
          </div>
          <div class="people-header-actions">
            <ha-button id="doors-to-dashboard" appearance="plain">
              <ha-icon icon="mdi:view-dashboard-outline" slot="start"></ha-icon>
              Dashboard
            </ha-button>
            <ha-button id="doors-to-people" appearance="plain">
              <ha-icon icon="mdi:account-group-outline" slot="start"></ha-icon>
              Users
            </ha-button>
            <ha-button id="add-door" appearance="filled" ${!this._hass?.user?.is_admin ? "disabled" : ""}>
              <ha-icon icon="mdi:door-open" slot="start"></ha-icon>
              Add Door
            </ha-button>
            <ha-button id="add-access-device" appearance="filled" ${!this._hass?.user?.is_admin ? "disabled" : ""}>
              <ha-icon icon="mdi:dialpad" slot="start"></ha-icon>
              Add Keypad
            </ha-button>
          </div>
        </header>
        <section id="content" class="doors-content" aria-live="polite"></section>
      </main>
    `;
  }

  _peoplePageTemplate() {
    return `
      <main class="page top-level-page">
        <header class="people-header">
          <div>
            ${this._homePassBrandLockup()}
            <h1>Users</h1>
            <p class="subtitle">Manage users who can access your home.</p>
          </div>
          <div class="people-header-actions">
            <ha-button id="back-to-dashboard" appearance="plain">
              <ha-icon icon="mdi:view-dashboard-outline" slot="start"></ha-icon>
              Dashboard
            </ha-button>
            <ha-button id="people-to-doors" appearance="plain">
              <ha-icon icon="mdi:door" slot="start"></ha-icon>
              Doors &amp; Devices
            </ha-button>
            <button id="add-person" class="add-person" type="button">
              <ha-icon icon="mdi:plus"></ha-icon>
              Add User
            </button>
          </div>
        </header>
        <section id="content" aria-live="polite"></section>
      </main>
    `;
  }

  _settingsPageTemplate() {
    return `
      <main class="page top-level-page">
        <header class="people-header">
          <div>
            ${this._homePassBrandLockup()}
            <h1>Settings</h1>
            <p class="subtitle">Choose how HomePASS works for your home.</p>
          </div>
        </header>
        <section class="settings-content" aria-live="polite">
          ${this._settingsContentTemplate()}
        </section>
      </main>`;
  }

  _activityPageTemplate() {
    return `
      <main class="page top-level-page">
        <header class="people-header">
          <div>
            ${this._homePassBrandLockup()}
            <h1>Activity</h1>
            <p class="subtitle">Review recent HomePASS activity.</p>
          </div>
        </header>
        <section id="activity-content" class="dashboard-content" aria-live="polite"></section>
      </main>`;
  }

  _aboutPageTemplate() {
    return `
      <main class="page top-level-page">
        <header class="people-header about-header">
          <div>
            ${this._homePassBrandLockup()}
            <h1>HomePASS</h1>
            <p class="subtitle">Secure Access Management for Home Assistant</p>
          </div>
        </header>
        <section class="about-content" aria-live="polite">
          ${this._aboutContentTemplate()}
        </section>
      </main>`;
  }

  _aboutContentTemplate() {
    if (this._aboutLoading && !this._aboutData) {
      return '<section class="settings-card" role="status">Loading About information…</section>';
    }
    if (this._aboutError && !this._aboutData) {
      return `
        <section class="settings-card" role="alert">
          <h2>About unavailable</h2>
          <p>${escapeHtml(this._aboutError)}</p>
          <ha-button id="retry-about" appearance="plain">Retry</ha-button>
        </section>`;
    }
    const about = this._aboutData;
    if (!about) return "";
    return `
      <section class="settings-card" aria-labelledby="about-release-heading">
        <h2 id="about-release-heading">About</h2>
        <dl class="settings-about">
          <dt>Version</dt><dd>${escapeHtml(about.version)}</dd>
          <dt>Property</dt><dd>${escapeHtml(about.property_name || "Not configured")}</dd>
          <dt>Home Assistant</dt><dd>${escapeHtml(about.home_assistant_version)}</dd>
          <dt>Database Schema</dt><dd>${escapeHtml(about.database_schema_version)}</dd>
          <dt>Created by</dt><dd>${escapeHtml(about.created_by)}</dd>
          <dt>Copyright</dt><dd>${escapeHtml(about.copyright)}</dd>
          ${about.git_commit ? `<dt>Git Commit</dt><dd>${escapeHtml(about.git_commit)}</dd>` : ""}
        </dl>
      </section>`;
  }

  _settingsContentTemplate() {
    return `${this._accessSetupTemplate()}${this._nukiStorageTemplate()}${this._propertySettingsTemplate()}${this._notificationSettingsTemplate()}`;
  }

  _accessSetupTemplate() {
    if (!this._hass?.user?.is_admin) return "";
    return `
      <section class="settings-card" aria-labelledby="access-setup-heading">
        <h2 id="access-setup-heading">Access setup</h2>
        <p>Set up each part once, then manage day-to-day access from HomePASS.</p>
        <ol>
          <li>Add the Matter lock on <strong>Doors &amp; Devices</strong>.</li>
          <li>Add an optional contact sensor from the Door details screen.</li>
          <li>Pair HomePASS directly to Nuki in the integration options for keypad PINs, schedules and activity. No Nuki Web account is required.</li>
        </ol>
        <p class="settings-helper">Fingerprint scanning is the one Nuki-app step. HomePASS guides the scan and records which HomePASS user owns it.</p>
        <a href="/config/integrations/integration/homepass">Open HomePASS integration options</a>
      </section>`;
  }

  _nukiStorageTemplate() {
    if (!this._hass?.user?.is_admin) return "";
    const status = this._nukiStorageStatus;
    let result = "";
    if (status && !status.configured) {
      result = '<p class="settings-helper" role="status">Local Nuki keypad management is not configured yet.</p>';
    } else if (status?.configured) {
      const pins = status.pins.entries.length
        ? `<ul>${status.pins.entries.map((entry) => `
            <li><strong>${escapeHtml(entry.name)}</strong> — ${entry.enabled ? "enabled" : "disabled"} — Nuki ID ${escapeHtml(entry.nuki_id)} — ${entry.management === "homepass" ? "HomePASS-managed" : "existing"}</li>`).join("")}</ul>`
        : '<p class="settings-helper">No keypad PINs are stored.</p>';
      const fingerprints = status.fingerprints.entries.length
        ? `<ul>${status.fingerprints.entries.map((entry) => `
            <li><strong>${escapeHtml(entry.person_name)}</strong> — ${escapeHtml(entry.door_name)} — ${escapeHtml(entry.status.replaceAll("_", " "))}</li>`).join("")}</ul>`
        : '<p class="settings-helper">No fingerprints are currently linked to HomePASS users.</p>';
      result = `
        <div role="status">
          <h3>PINs on the lock</h3>
          <p><strong>${status.pins.total}</strong> total: ${status.pins.managed} HomePASS-managed and ${status.pins.existing} existing.</p>
          ${pins}
          <h3>Fingerprint links</h3>
          <p><strong>${status.fingerprints.linked_count}</strong> linked to HomePASS users.</p>
          ${fingerprints}
          <p class="settings-helper">Nuki's local connection does not provide a complete list of fingerprints stored on the keypad. Unknown fingerprints must still be reviewed in the Nuki app; HomePASS shows only links it can attribute.</p>
        </div>`;
    }
    return `
      <section class="settings-card" aria-labelledby="nuki-storage-heading">
        <h2 id="nuki-storage-heading">Nuki keypad storage</h2>
        <p>Read the lock now to see stored PINs and HomePASS-linked fingerprint status. PIN digits and biometric data are never displayed.</p>
        ${this._nukiStorageError ? `<p class="form-error" role="alert">${escapeHtml(this._nukiStorageError)}</p>` : ""}
        <ha-button id="check-nuki-storage" appearance="filled" ${this._nukiStorageLoading ? "disabled" : ""}>
          <ha-icon icon="mdi:shield-search" slot="start"></ha-icon>
          ${this._nukiStorageLoading ? "Checking…" : "Check PIN & fingerprint status"}
        </ha-button>
        ${this._nukiStorageLoading ? '<p class="settings-helper" role="status">Reading the lock over Bluetooth. This normally takes 10–50 seconds.</p>' : ""}
        ${result}
        <p class="settings-helper">To remove a PIN that HomePASS does not manage, open the integration options, keep the current Nuki settings, and continue to <strong>Review existing Nuki PINs</strong>.</p>
        <a href="/config/integrations/integration/homepass">Open HomePASS integration options</a>
      </section>`;
  }

  _propertySettingsTemplate() {
    if (this._propertySettingsLoading && !this._propertySettingsData) {
      return '<section class="settings-card" role="status">Loading Property Settings…</section>';
    }
    if (this._propertySettingsError && !this._propertySettingsData) {
      return `
        <section class="settings-card" role="alert">
          <h2>Property</h2>
          <p>${escapeHtml(this._propertySettingsError)}</p>
          <ha-button id="retry-property-settings" appearance="plain">Retry</ha-button>
        </section>`;
    }
    if (!this._propertySettingsData) return "";
    const validationMessage = this._propertyNameValidationMessage();
    return `
      <section class="settings-card" aria-labelledby="property-heading">
        <h2 id="property-heading">Property</h2>
        <div class="property-settings-field">
          <ha-input id="property-name" label="Property Name"
            value="${escapeHtml(this._propertyName)}"
            aria-describedby="property-name-helper property-name-error"
            aria-invalid="${String(Boolean(validationMessage))}"></ha-input>
          <p id="property-name-helper" class="settings-helper">
            This name identifies this HomePASS installation on the dashboard and in notifications.
          </p>
          <p id="property-name-error" class="form-error" role="alert" ${validationMessage ? "" : "hidden"}>${escapeHtml(validationMessage ?? "")}</p>
        </div>
        <div class="settings-actions">
          ${this._propertySettingsNotice ? `<p class="settings-notice" role="status">${escapeHtml(this._propertySettingsNotice)}</p>` : ""}
          ${this._propertySettingsError ? `<p class="form-error" role="alert">${escapeHtml(this._propertySettingsError)}</p>` : ""}
          <ha-button id="save-property-settings" appearance="filled" ${this._propertySettingsCanSave() ? "" : "disabled"}>${this._propertySettingsSaving ? "Saving…" : "Save"}</ha-button>
        </div>
      </section>`;
  }

  _notificationSettingsTemplate() {
    if (this._settingsLoading && !this._settingsData) {
      return '<section class="settings-card" role="status">Loading notification settings…</section>';
    }
    if (this._settingsError && !this._settingsData) {
      return `
        <section class="settings-card" role="alert">
          <h2>Settings unavailable</h2>
          <p>${escapeHtml(this._settingsError)}</p>
          <ha-button id="retry-notification-settings" appearance="plain">Retry</ha-button>
        </section>`;
    }
    const data = this._settingsData;
    if (!data) return "";
    const preferences = data.preferences;
    const selected = new Set(preferences.selected_device_ids);
    const devices = data.devices.length
      ? data.devices.map((device) => `
          <label class="settings-choice">
            <input type="checkbox" data-notification-device value="${escapeHtml(device.id)}" ${selected.has(device.id) ? "checked" : ""} />
            <span>${escapeHtml(device.display_name)}${device.available ? "" : " — Currently unavailable"}</span>
          </label>`).join("")
      : '<p class="settings-helper">No Home Assistant Companion devices were found.</p>';
    const groupedDefinitions = new Map();
    for (const definition of data.definitions) {
      const group = groupedDefinitions.get(definition.category) ?? {
        title: definition.category_title,
        definitions: [],
      };
      group.definitions.push(definition);
      groupedDefinitions.set(definition.category, group);
    }
    const groups = [...groupedDefinitions.values()].map((group) => `
      <section class="settings-group">
        <h3>${escapeHtml(group.title)}</h3>
        ${group.definitions.map((definition) => {
          const supported = definition.supported;
          return `
            <label class="settings-choice">
              <input type="checkbox" data-notification-event value="${escapeHtml(definition.id)}" ${supported && preferences.events[definition.id] ? "checked" : ""} ${supported ? "" : "disabled"} />
              <span>${escapeHtml(definition.title)}${supported ? "" : " — Not supported by your current locks"}</span>
            </label>`;
        }).join("")}
      </section>`).join("");
    return `
      <section class="settings-card" aria-labelledby="notifications-heading">
        <h2 id="notifications-heading">Notifications</h2>
        <p class="settings-helper">Choose which new HomePASS activity is sent to your Companion devices.</p>
        <label class="settings-toggle">
          <input id="notifications-enabled" type="checkbox" ${preferences.enabled ? "checked" : ""} />
          <span><strong>Enable Notifications</strong><br /><span class="settings-helper">Keep preferences editable while suppressing future delivery globally.</span></span>
        </label>
        <h3>Notification Devices</h3>
        <div class="settings-device-list">${devices}</div>
        <h3>Notification Events</h3>
        <div class="settings-presets" role="group" aria-label="Notification presets">
          <span>Quick selection</span>
          <ha-button appearance="plain" data-notification-preset="recommended">Recommended</ha-button>
          <ha-button appearance="plain" data-notification-preset="security">Security only</ha-button>
          <ha-button appearance="plain" data-notification-preset="all">All supported</ha-button>
          <ha-button appearance="plain" data-notification-preset="none">None</ha-button>
        </div>
        <div class="settings-groups">${groups}</div>
        <div class="settings-actions">
          ${this._settingsNotice ? `<p class="settings-notice" role="status">${escapeHtml(this._settingsNotice)}</p>` : ""}
          ${this._settingsError ? `<p class="form-error" role="alert">${escapeHtml(this._settingsError)}</p>` : ""}
          <ha-button id="save-notification-settings" appearance="filled" ${this._settingsSaving ? "disabled" : ""}>${this._settingsSaving ? "Saving…" : "Save"}</ha-button>
        </div>
      </section>`;
  }

  _applyNotificationPreset(preset) {
    if (!this._settingsData) return;
    const definitions = new Map(
      this._settingsData.definitions.map((definition) => [definition.id, definition]),
    );
    for (const input of this.shadowRoot.querySelectorAll("[data-notification-event]")) {
      if (input.disabled) continue;
      const definition = definitions.get(input.value);
      input.checked = preset === "all" ||
        (preset === "recommended" && definition?.default_enabled === true) ||
        (preset === "security" && definition?.category === "security");
    }
    this._settingsNotice = "Selection updated. Choose Save to apply it.";
    const notice = this.shadowRoot.querySelector(".settings-notice");
    if (notice) notice.textContent = this._settingsNotice;
  }

  _doorControlDialogTemplate() {
    const name = this._selectedDoor?.display_name ?? "Door";
    const tagCount = Math.max(0, Number(this._selectedDoor?.nfc_tag_count) || 0);
    const nfcTagServiceAvailable = Boolean(
      this._hass?.services?.[DOMAIN]?.[LIST_NFC_TAGS_ACTION],
    );
    if (this._doorNfcSetupOpen) {
      return `
        <ha-dialog id="door-control-dialog" open>
          <ha-dialog-header slot="header">
            <div class="door-dialog-title-row" slot="title">
              <button id="back-door-nfc-setup" class="door-title-icon-button" type="button"
                aria-label="Back to ${escapeHtml(name)}">
                <ha-icon icon="mdi:arrow-left" aria-hidden="true"></ha-icon>
              </button>
              <span class="door-nfc-header-copy">
                <span>Set up NFC tag</span>
                <small class="homepass-entity-name">${escapeHtml(name)}</small>
              </span>
            </div>
          </ha-dialog-header>
          <div class="door-control-content door-nfc-setup-content">
            ${nfcTagServiceAvailable ? `<${NFC_PROVISIONER_WEB_COMPONENT}
                access-point-id="${escapeHtml(this._selectedDoorId ?? "")}"
                door-name="${escapeHtml(name)}"
              ></${NFC_PROVISIONER_WEB_COMPONENT}>` : `
              <section class="door-nfc-tags" aria-labelledby="nfc-setup-required-title">
                <h3 id="nfc-setup-required-title">NFC setup required</h3>
                <p>HomePASS needs the secure Nabu Casa HTTPS address before it can create
                  an NFC tag for this Door.</p>
                <label>Nabu Casa HTTPS address
                  <input id="door-nfc-public-origin" type="url" autocomplete="url"
                    placeholder="https://example.ui.nabu.casa"
                    value="${escapeHtml(this._doorNfcOriginDraft)}"
                    ${this._doorNfcConfiguring ? "disabled" : ""} />
                </label>
                <p class="muted">In Home Assistant, open Settings → Home Assistant Cloud to find this address.</p>
                ${this._doorNfcConfigurationError ? `<p class="form-error" role="alert">${escapeHtml(this._doorNfcConfigurationError)}</p>` : ""}
                ${this._doorNfcConfigurationNotice ? `<p class="door-rename-feedback notice" role="status">${escapeHtml(this._doorNfcConfigurationNotice)}</p>` : ""}
                <div class="settings-actions">
                  <ha-button id="save-door-nfc-configuration" appearance="filled"
                    ${this._doorNfcConfiguring || !this._doorNfcOriginDraft.trim() ? "disabled" : ""}>
                    ${this._doorNfcConfiguring ? "Enabling NFC…" : "Continue"}
                  </ha-button>
                </div>
              </section>`}
          </div>
          <ha-dialog-footer slot="footer">
            <ha-button id="close-door-control" appearance="plain"
              slot="secondaryAction">Close</ha-button>
          </ha-dialog-footer>
        </ha-dialog>`;
    }
    const title = this._editingDoorName ? `
      <div class="door-title-editor" slot="title">
        <input id="door-title-name-input" maxlength="80" autocomplete="off"
          aria-label="HomePASS door name" value="${escapeHtml(this._doorNameDraft)}"
          ${this._renamingDoor ? "disabled" : ""} />
        <button id="save-homepass-door-name" class="door-title-icon-button" type="button"
          aria-label="Save Door name" title="Save Door name" ${this._renamingDoor ? "disabled" : ""}>
          <ha-icon icon="${this._renamingDoor ? "mdi:progress-clock" : "mdi:check"}" aria-hidden="true"></ha-icon>
        </button>
        <button id="cancel-homepass-door-name" class="door-title-icon-button" type="button"
          aria-label="Cancel Door name editing" title="Cancel" ${this._renamingDoor ? "disabled" : ""}>
          <ha-icon icon="mdi:close" aria-hidden="true"></ha-icon>
        </button>
      </div>` : `
      <div class="door-dialog-title-row" slot="title">
        <span id="door-control-title" class="homepass-entity-name">${escapeHtml(name)}</span>
        ${this._hass?.user?.is_admin ? `<button id="edit-door-name" class="door-title-icon-button"
          type="button" aria-label="Edit Door name" title="Edit Door name">
          <ha-icon icon="mdi:pencil-outline" aria-hidden="true"></ha-icon>
        </button>` : ""}
      </div>`;
    return `
      <ha-dialog id="door-control-dialog" open>
        <ha-dialog-header slot="header">
          ${title}
        </ha-dialog-header>
        <div class="door-control-content">
          <div id="door-control-loading" role="status" hidden>Loading door status…</div>
          <div id="door-control-error" class="door-control-error" role="alert" hidden>
            <h3>Current status unavailable</h3>
            <p>HomePASS could not retrieve the latest status for this door.</p>
            <ha-button id="refresh-door-control" appearance="plain">Refresh</ha-button>
          </div>
          <div id="door-control-status" aria-live="polite">
            <section id="door-control-state-summary">
              <div class="door-control-state-layout">
                <div id="door-control-status-graphic" class="door-control-status-graphic"></div>
                <div class="door-control-state-copy">
                  <h3 id="door-last-known-heading" hidden>Last known status</h3>
                  <p id="door-control-lock-state" class="door-control-primary-state"></p>
                  <dl class="door-control-facts">
                    <div id="door-control-contact-row" hidden>
                      <dt>Door</dt>
                      <dd id="door-control-contact-state"></dd>
                    </div>
                    <div id="door-control-availability-row" hidden>
                      <dt>Availability</dt>
                      <dd id="door-control-availability"></dd>
                    </div>
                    <div id="door-control-updated-row">
                      <dt id="door-last-updated-label">Updated</dt>
                      <dd id="door-last-updated-value">Unknown</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </section>
            <div id="door-operation-region" class="door-operation-region" hidden>
              <${SLIDE_ACTION_WEB_COMPONENT} id="door-slide-action">
              </${SLIDE_ACTION_WEB_COMPONENT}>
              <div id="door-operation-error" class="door-operation-error" role="alert" hidden>
                <p id="door-operation-error-title" class="door-operation-error-title"></p>
                <p id="door-operation-error-message"></p>
              </div>
            </div>
            ${this._hass?.user?.is_admin ? `<div class="door-quick-actions">
              <button id="open-door-nfc-setup" class="door-nfc-action" type="button">
                <span class="door-nfc-action-mark" aria-hidden="true">
                  <img src="${NFC_SYMBOL_URL}" alt="" />
                </span>
                <span class="door-nfc-action-copy">
                  <strong>Set up NFC tag</strong>
                  <span>${nfcTagServiceAvailable
                    ? (tagCount > 0 ? `${tagCount} enabled NFC ${tagCount === 1 ? "tag" : "tags"}` : "Prepare a secure NTAG424 DNA tag")
                    : "One-time Nabu Casa setup required"}</span>
                </span>
                <ha-icon icon="mdi:chevron-right" aria-hidden="true"></ha-icon>
              </button>
              ${nfcTagServiceAvailable ? `<section class="door-nfc-tags" aria-labelledby="registered-nfc-tags-title">
                <h3 id="registered-nfc-tags-title">Registered NFC tags</h3>
                ${this._doorNfcTagsMarkup()}
              </section>` : ""}
              ${this._doorRenameError ? `<p class="door-rename-feedback error" role="alert">${escapeHtml(this._doorRenameError)}</p>` : ""}
              ${this._doorRenameNotice ? `<p class="door-rename-feedback notice" role="status">${escapeHtml(this._doorRenameNotice)}</p>` : ""}
            </div>` : ""}
            <section class="door-policy-section" aria-labelledby="door-devices-title">
              <h3 id="door-devices-title">Devices</h3>
              ${this._selectedDoorDevicesMarkup()}
            </section>
            <section class="door-policy-section" aria-labelledby="door-current-access-title">
              <h3 id="door-current-access-title">Current Access (0)</h3>
              <div id="door-policy-loading" role="status">Loading current access…</div>
              <div id="door-policy-error" role="alert" hidden></div>
              <div id="door-policy-content" class="door-policy-content" hidden>
                <div id="door-current-access-list" class="door-policy-list"></div>
                <details class="synchronization-history-disclosure">
                  <summary>Synchronization History</summary>
                  <div id="door-synchronization-history-list"
                    class="synchronization-history-list"></div>
                </details>
              </div>
            </section>
            ${this._hass?.user?.is_admin ? `<section class="door-admin-footer">
              <ha-button id="open-remove-door-confirmation" class="subtle-destructive-action"
                appearance="plain" variant="danger">Remove from HomePASS</ha-button>
            </section>` : ""}
          </div>
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="close-door-control" appearance="plain"
            slot="secondaryAction">Close</ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _selectedDoorDevicesMarkup() {
    const door = this._selectedDoor;
    if (!door) return "<p>Device information is unavailable.</p>";
    const controller = {
      lock: ["Smart lock", "mdi:lock-outline"],
      garage_cover: ["Garage door controller", "mdi:garage-variant"],
      garage_toggle: ["Garage door relay", "mdi:electric-switch"],
      electric_strike: ["Electric strike", "mdi:electric-switch"],
    }[door.control_profile] ?? ["Door controller", "mdi:door"];
    const accessories = this._accessDevices.filter(
      (device) => device.access_point_id === door.id,
    );
    const statusEntity = door.door_entity_id
      ? this._hass?.states?.[door.door_entity_id]
      : undefined;
    const statusName = statusEntity?.attributes?.friendly_name ?? door.door_entity_id;
    const statusState = door.door_state === "open"
      ? "Open"
      : door.door_state === "closed" ? "Closed" : "Status unavailable";
    const candidates = this._doorStatusCandidates().map((entity) =>
      `<option value="${escapeHtml(entity.entity_id)}" ${this._doorSensorEntityId === entity.entity_id ? "selected" : ""}>${escapeHtml(entity.label)} — ${escapeHtml(entity.entity_id)}</option>`).join("");
    const canSaveSensor = Boolean(this._doorSensorEntityId || door.door_entity_id);
    const saveSensorLabel = !this._doorSensorEntityId && door.door_entity_id
      ? "Remove sensor" : "Save sensor";
    const controllerBattery = this._batteryReading(
      this._hass,
      door.battery_entity_id,
      door.battery_percentage,
      door.battery_status,
    );
    const sensorBattery = this._batteryReading(
      this._hass,
      door.door_sensor_battery_entity_id,
      door.door_sensor_battery_percentage,
      door.door_sensor_battery_status,
    );
    const sensorEditor = this._doorSensorEditOpen ? `
      <div class="detail-fields">
        <label>Door sensor
          <select id="edit-door-status-entity" ${this._doorSensorSaving ? "disabled" : ""}>
            <option value="">Choose a door or contact sensor…</option>${candidates}
          </select>
        </label>
        <p class="muted">Only likely door, window, contact, lock and cover entities are shown. Zigbee2MQTT, ZHA and Thread/Matter sensors all work once their entity is available in Home Assistant.</p>
        <label class="access-point-option">
          <input id="edit-door-status-inverted" type="checkbox"
            ${this._doorSensorInverted ? "checked" : ""}
            ${!this._doorSensorEntityId || this._doorSensorSaving ? "disabled" : ""} />
          <span>Reverse open and closed status</span>
        </label>
        ${this._doorSensorError ? `<p class="form-error" role="alert">${escapeHtml(this._doorSensorError)}</p>` : ""}
        <div class="settings-actions">
          <ha-button id="cancel-door-sensor" appearance="plain" ${this._doorSensorSaving ? "disabled" : ""}>Cancel</ha-button>
          <ha-button id="save-door-sensor" appearance="filled" ${this._doorSensorSaving || !canSaveSensor ? "disabled" : ""}>${this._doorSensorSaving ? "Saving…" : saveSensorLabel}</ha-button>
        </div>
      </div>` : "";
    return `<div class="door-associated-device-list">
      <div class="door-associated-device">
        <ha-icon icon="${controller[1]}" aria-hidden="true"></ha-icon>
        <div><strong>${controller[0]}</strong><span>Operates this Door</span>${this._batteryMarkup(controllerBattery)}</div>
      </div>
      ${door.door_entity_id ? `<div class="door-associated-device">
        <ha-icon icon="mdi:door-closed" aria-hidden="true"></ha-icon>
        <div><strong>${escapeHtml(statusName ?? "Open/closed sensor")}</strong><span>${statusState}${door.status_inverted ? " · Reversed" : ""}</span>${this._batteryMarkup(sensorBattery)}</div>
      </div>` : ""}
      ${accessories.map((device) => `<div class="door-associated-device">
        <ha-icon icon="mdi:dialpad" aria-hidden="true"></ha-icon>
        <div><strong>${escapeHtml(device.display_name)}</strong><span>${device.setup_state === "ready" ? (device.available ? "Ready" : "Offline") : "Awaiting hardware test"}</span>${this._batteryMarkup(this._batteryReading(this._hass, device.battery_entity_id, device.battery_percentage, device.battery_status))}</div>
      </div>`).join("")}
      ${accessories.length === 0 && this._hass?.user?.is_admin ? '<p class="muted">No accessory devices are associated with this Door.</p>' : ""}
      ${this._hass?.user?.is_admin && door.capabilities?.status_editable === true
        ? `<ha-button id="edit-door-sensor" appearance="plain" ${this._doorSensorEditOpen ? "disabled" : ""}>${door.door_entity_id ? "Change door sensor" : "Add door sensor"}</ha-button>`
        : ""}
      ${sensorEditor}
      ${this._doorSensorNotice ? `<p class="door-rename-feedback notice" role="status">${escapeHtml(this._doorSensorNotice)}</p>` : ""}
    </div>`;
  }

  _policyInspectorTemplate() {
    return `
      <ha-dialog id="policy-inspector-dialog" open aria-labelledby="policy-inspector-title">
        <ha-dialog-header slot="header">
          <span id="policy-inspector-title" slot="title">Access unavailable</span>
        </ha-dialog-header>
        <div class="policy-inspector-content">
          <p id="policy-inspector-loading" role="status">Loading policy details…</p>
          <p id="policy-inspector-error" role="alert" hidden></p>
          <div id="policy-inspector-content" class="policy-inspector-details" hidden>
            <p id="policy-inspector-reason" class="policy-inspector-reason"></p>
            <dl class="policy-inspector-facts">
              <div><dt>User</dt><dd id="policy-inspector-person" class="homepass-entity-name"></dd></div>
              <div><dt>Door</dt><dd id="policy-inspector-door" class="homepass-entity-name"></dd></div>
              <div><dt>Schedule</dt><dd id="policy-inspector-schedule"></dd></div>
            </dl>
            <section class="policy-inspector-section" aria-labelledby="policy-validity-title">
              <h3 id="policy-validity-title">Schedule validity</h3>
              <p id="policy-validity-summary"></p>
              <dl class="policy-inspector-facts">
                <div id="policy-valid-from-row" hidden>
                  <dt>Valid from</dt><dd id="policy-valid-from"></dd>
                </div>
                <div id="policy-valid-until-row" hidden>
                  <dt>Valid until</dt><dd id="policy-valid-until"></dd>
                </div>
              </dl>
            </section>
            <section class="policy-inspector-section" aria-labelledby="policy-weekly-title">
              <h3 id="policy-weekly-title">Allowed weekly hours</h3>
              <p id="policy-weekly-summary"></p>
              <p id="policy-weekly-days" hidden></p>
              <p id="policy-weekly-hours" hidden></p>
            </section>
            <section class="policy-inspector-section" aria-labelledby="policy-current-title">
              <h3 id="policy-current-title">Current local time</h3>
              <p id="policy-current-local"></p>
              <p id="policy-current-time-zone" class="policy-inspector-secondary"></p>
            </section>
          </div>
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="close-policy-inspector" appearance="filled"
            slot="primaryAction">Close</ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _removeDoorConfirmationTemplate() {
    const name = this._selectedDoor?.display_name ?? "this door";
    return `
      <ha-dialog id="remove-door-confirmation" open>
        <ha-dialog-header slot="header">
          <span slot="title">Remove ${escapeHtml(name)} from HomePASS?</span>
        </ha-dialog-header>
        <div class="dialog-content">
          <p>HomePASS will stop managing this door. The lock will remain available in Home Assistant and may be added again later.</p>
          ${this._removeDoorError ? `<p class="form-error" role="alert">${escapeHtml(this._removeDoorError)}</p>` : ""}
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="cancel-remove-door" appearance="plain" slot="secondaryAction"
            ${this._removingDoor ? "disabled" : ""}>Cancel</ha-button>
          <ha-button id="confirm-remove-door" class="subtle-destructive-action"
            variant="danger" slot="primaryAction" ${this._removingDoor ? "disabled" : ""}>
            ${this._removingDoor ? "Removing…" : "Remove from HomePASS"}
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _addDoorDialogTemplate() {
    const options = this._availableAccessPoints
      .map(
        (door) => `<label class="access-point-option">
          <input type="radio" name="available-door" value="${escapeHtml(door.id)}" ${this._selectedAvailableAccessPointId === door.id ? "checked" : ""} />
          <span>${escapeHtml(door.display_name)}${door.availability === "unavailable" ? " — Unavailable" : ""}${door.door_state ? " — DoorSense available" : ""}</span>
        </label>`,
      )
      .join("");
    const discoveredContent = this._availableAccessPointsLoading
      ? "<p>Loading compatible locks…</p>"
      : options || "<p>No automatically compatible locks are currently available.</p>";
    const deviceOptions = this._haDoorCandidateDevices()
      .map((device) => `<option value="${escapeHtml(device.id)}" ${this._haDoorDeviceId === device.id ? "selected" : ""}>${escapeHtml(this._haDoorDeviceLabel(device))}</option>`).join("");
    const controlOptions = this._haDoorRelevantEntities(this._haDoorControlDomains())
      .map((entity) => `<option value="${escapeHtml(entity.entity_id)}" ${this._haDoorControlEntityId === entity.entity_id ? "selected" : ""}>${escapeHtml(this._haDoorEntityLabel(entity))} — ${escapeHtml(entity.entity_id)}</option>`).join("");
    const statusOptions = this._haDoorRelevantEntities([
      "binary_sensor", "cover", "lock", "sensor", "input_boolean",
    ], false).filter((entity) =>
      entity.entity_id !== this._haDoorControlEntityId &&
      this._isDoorStatusEntity(entity))
      .map((entity) => `<option value="${escapeHtml(entity.entity_id)}" ${this._haDoorStatusEntityId === entity.entity_id ? "selected" : ""}>${escapeHtml(this._haDoorEntityLabel(entity))} — ${escapeHtml(entity.entity_id)}</option>`).join("");
    const pulseNeeded = ["garage_toggle", "electric_strike"].includes(this._haDoorProfile);
    const manualContent = this._availableAccessPointsLoading
      ? "<p>Loading Home Assistant devices…</p>"
      : `<div class="access-point-options">
          <label>Door type
            <select id="ha-door-profile">
              <option value="lock" ${this._haDoorProfile === "lock" ? "selected" : ""}>Smart lock (including Tuya / LocalTuya)</option>
              <option value="garage_cover" ${this._haDoorProfile === "garage_cover" ? "selected" : ""}>Garage or roller door — open/close control</option>
              <option value="garage_toggle" ${this._haDoorProfile === "garage_toggle" ? "selected" : ""}>Garage or roller door — pulse/toggle control</option>
              <option value="electric_strike" ${this._haDoorProfile === "electric_strike" ? "selected" : ""}>Electric strike — momentary release</option>
            </select>
          </label>
          <label>Home Assistant device<select id="ha-door-device">
            <option value="">Select a device…</option>${deviceOptions}</select></label>
          <label>Control entity<select id="ha-door-control-entity" ${!this._haDoorDeviceId ? "disabled" : ""}>
            <option value="">Select the entity HomePASS should operate…</option>${controlOptions}</select></label>
          <label>Door sensor <span class="muted">(recommended)</span>
            <select id="ha-door-status-entity" ${!this._haDoorDeviceId ? "disabled" : ""}>
              <option value="">Choose a door or contact sensor…</option>${statusOptions}</select></label>
          <p class="muted">Optional. HomePASS hides unrelated temperature, phone and appliance sensors. Zigbee2MQTT, ZHA and Thread/Matter door sensors are supported through their Home Assistant entity.</p>
          <label>Door name<input id="ha-door-display-name" type="text" maxlength="80" value="${escapeHtml(this._haDoorDisplayName)}" placeholder="e.g. West Roller Door" /></label>
          <label class="access-point-option"><input id="ha-door-status-inverted" type="checkbox" ${this._haDoorStatusInverted ? "checked" : ""} ${!this._haDoorStatusEntityId ? "disabled" : ""} /><span>Reverse open and closed status</span></label>
          ${pulseNeeded ? `<label>Relay pulse duration (seconds)<input id="ha-door-pulse-seconds" type="number" min="0.1" max="10" step="0.1" value="${escapeHtml(String(this._haDoorPulseSeconds))}" /></label>` : ""}
          <p class="muted">Capabilities: HomePASS app control enabled. PIN and NFC are enabled only when this individual device binding exposes them.</p>
        </div>`;
    const content = this._addDoorSource === "home_assistant"
      ? manualContent
      : `<p>HomePASS-compatible locks discovered automatically</p><div class="access-point-options" role="radiogroup">${discoveredContent}</div>`;
    const canSubmit = this._addDoorSource === "home_assistant"
      ? this._haDoorManualFormValid() : Boolean(this._selectedAvailableAccessPointId);
    return `<ha-dialog id="add-door-dialog" open>
      <ha-dialog-header slot="header"><span slot="title">Add Door</span></ha-dialog-header>
      <div class="dialog-content">
        <label>Add from<select id="add-door-source">
          <option value="home_assistant" ${this._addDoorSource === "home_assistant" ? "selected" : ""}>Existing Home Assistant device</option>
          <option value="automatic" ${this._addDoorSource === "automatic" ? "selected" : ""}>Automatically discovered compatible lock</option>
        </select></label>
        ${this._availableAccessPointsError ? `<p class="form-error" role="alert">${escapeHtml(this._availableAccessPointsError)}</p>` : ""}
        ${content}
      </div>
      <ha-dialog-footer slot="footer">
        <ha-button id="cancel-add-door" appearance="plain" slot="secondaryAction">Cancel</ha-button>
        <ha-button id="confirm-add-door" appearance="filled" slot="primaryAction" ${!canSubmit || this._enrollingDoor ? "disabled" : ""}>${this._enrollingDoor ? "Adding…" : "Add Door"}</ha-button>
      </ha-dialog-footer>
    </ha-dialog>`;
  }

  _addAccessDeviceDialogTemplate() {
    const candidates = this._availableAccessDevices.map((device) => `
      <label class="access-point-option">
        <input type="radio" name="available-access-device"
          value="${escapeHtml(device.home_assistant_device_id)}"
          ${this._selectedAccessDeviceCandidateId === device.home_assistant_device_id ? "checked" : ""} />
        <span><strong>${escapeHtml(device.display_name)}</strong><br />${escapeHtml(device.manufacturer)} ${escapeHtml(device.model)}${device.available ? "" : " — Currently unavailable"}</span>
      </label>`).join("");
    const doors = this._sortedDoors().map((door) => `
      <option value="${escapeHtml(door.id)}" ${this._selectedAccessDeviceDoorId === door.id ? "selected" : ""}>${escapeHtml(door.display_name)}</option>`).join("");
    const canAdd = Boolean(
      this._selectedAccessDeviceCandidateId && this._selectedAccessDeviceDoorId,
    );
    const selectedDoor = this._dashboardAccessPoints.find(
      (door) => door.id === this._selectedAccessDeviceDoorId,
    );
    const keypadInstructions = ["garage_cover", "garage_toggle"].includes(
      selectedDoor?.control_profile,
    )
      ? "After adding it, give a User PIN access to this Door. Enter that PIN on the keypad and press either padlock button to activate the garage door. HomePASS ignores the other buttons."
      : "After adding it, give a User PIN access to this Door. Enter that PIN on the keypad and press the unlocked padlock to unlock or the locked padlock to lock. HomePASS ignores the other buttons.";
    return `
      <ha-dialog id="add-access-device-dialog" open>
        <ha-dialog-header slot="header"><span slot="title">Add keypad</span></ha-dialog-header>
        <div class="dialog-content">
          <p>A keypad adds another way to use an existing Door; it does not create a second Door.</p>
          <div class="device-pairing-empty">
            <ha-icon icon="mdi:bluetooth" aria-hidden="true"></ha-icon>
            <div><strong>Nuki keypad</strong>
            <p>Pair it to the Nuki lock in the Nuki app. HomePASS manages its PINs and schedules automatically after the lock is paired in the HomePASS integration options—do not add the keypad separately here.</p></div>
          </div>
          ${this._accessDevicesLoading ? "<p>Looking for compatible paired devices…</p>" : ""}
          ${this._accessDevicesError ? `<p class="form-error" role="alert">${escapeHtml(this._accessDevicesError)}</p>` : ""}
          ${!this._accessDevicesLoading && !candidates ? `
            <div class="device-pairing-empty">
              <ha-icon icon="mdi:zigbee" aria-hidden="true"></ha-icon>
              <div><strong>No supported keypad found</strong>
              <p>Pair the Frient KEPZB-110 with Home Assistant first, then return here and choose Refresh.</p></div>
            </div>
            <ha-button id="refresh-access-devices" appearance="plain">Refresh devices</ha-button>` : `
            <fieldset class="access-point-options"><legend>Choose a paired keypad</legend>${candidates}</fieldset>
            <label>Door<select id="access-device-door"><option value="">Choose a Door…</option>${doors}</select></label>
            <label>Device name <span class="muted">(optional)</span><input id="access-device-display-name" maxlength="80" value="${escapeHtml(this._accessDeviceDisplayName)}" placeholder="e.g. Garage keypad" /></label>
            <p class="muted">${keypadInstructions}</p>`}
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="cancel-add-access-device" appearance="plain" slot="secondaryAction">Cancel</ha-button>
          <ha-button id="confirm-add-access-device" appearance="filled" slot="primaryAction" ${!canAdd || this._addingAccessDevice ? "disabled" : ""}>${this._addingAccessDevice ? "Adding…" : "Add keypad"}</ha-button>
        </ha-dialog-footer>
      </ha-dialog>`;
  }

  _homePassBrandLockup(variant = "header") {
    const emptyState = variant === "empty";
    return `
      <p class="brand-kicker${emptyState ? " empty-brand-lockup" : ""}">
        <span class="${emptyState ? "empty-brand-mark-crop" : "header-brand-mark-crop"}">
          <img
            class="brand-mark ${emptyState ? "empty-brand-mark" : "header-brand-mark"}"
            src="${HOMEPASS_MARK_URL}"
            alt="HomePASS"
          />
        </span>
      </p>
    `;
  }

  _personSchedulePageTemplate() {
    return `
      <main class="page detail-page">
        <header>
          <div class="details-title">
            <ha-icon-button-prev
              id="back-to-person"
              label="Back to user details"
            ></ha-icon-button-prev>
            <div>
              <h1 id="person-schedule-title">Schedule</h1>
              <p id="person-schedule-subtitle" class="subtitle"></p>
            </div>
          </div>
        </header>
        <section id="content" aria-live="polite"></section>
      </main>
    `;
  }

  _detailsPageTemplate() {
    return `
      <main class="page detail-page">
        ${
          this._accessUpdateNotice
            ? `<p id="access-update-notice" class="access-update-notice" role="status">${escapeHtml(this._accessUpdateNotice)}</p>`
            : ""
        }
        <header class="people-header person-details-header">
          <div>
            ${this._homePassBrandLockup()}
            <nav class="details-breadcrumb" aria-label="User Details navigation">
              <ha-button id="person-details-dashboard" appearance="plain"
                aria-label="Go to HomePASS Dashboard">
                <ha-icon icon="mdi:view-dashboard-outline" slot="start"></ha-icon>
                Dashboard
              </ha-button>
              <span aria-hidden="true">/</span>
              <ha-button id="person-details-users" appearance="plain"
                aria-label="Go to Users">
                <ha-icon icon="mdi:account-group-outline" slot="start"></ha-icon>
                Users
              </ha-button>
              <span aria-hidden="true">/</span>
              <span id="person-details-current" class="homepass-entity-name" aria-current="page">User Details</span>
            </nav>
            <div class="details-title">
              <div>
                <h1 id="person-details-title" class="homepass-entity-name">User Details</h1>
                <p class="subtitle">User profile and access</p>
              </div>
            </div>
          </div>
          <div class="details-actions">
            <ha-button
              id="delete-person"
              class="subtle-destructive-action"
              appearance="plain"
            >
              <ha-icon icon="mdi:trash-can-outline" slot="start"></ha-icon>
              Delete User
            </ha-button>
            <ha-button id="edit-person" class="edit-person" appearance="plain">
              <ha-icon icon="mdi:pencil" slot="start"></ha-icon>
              Edit User
            </ha-button>
            <ha-button id="access-action" appearance="filled">
              <ha-icon icon="mdi:key-plus" slot="start"></ha-icon>
              Edit Door Access
            </ha-button>
          </div>
        </header>
        <section id="content" aria-live="polite"></section>
      </main>
    `;
  }

  _renderDashboard() {
    const content = this.shadowRoot.querySelector("#content");
    const sections = [
      this._dashboardAttentionSection(),
      this._dashboardDoorsSection(),
      this._dashboardPeopleSection(),
      this._dashboardRecentActivitySection(),
    ].filter(Boolean);
    content.append(...sections);
    this._showDashboardActivityFilters();
  }

  _renderActivityPage() {
    const content = this.shadowRoot.querySelector("#activity-content");
    content.append(this._dashboardRecentActivitySection());
    this._showDashboardActivityFilters();
  }

  _renderDoors() {
    const content = this.shadowRoot.querySelector("#content");
    const count = this.shadowRoot.querySelector("#door-count");
    const doorSection = document.createElement("section");
    doorSection.className = "doors-devices-section";
    const doorHeading = document.createElement("div");
    doorHeading.className = "doors-devices-section-heading";
    doorHeading.innerHTML = "<div><h2>Doors</h2><p>The entrances and openings HomePASS can control.</p></div>";
    doorSection.append(doorHeading);
    if (this._dashboardDoorsLoading) {
      count.textContent = "Loading doors…";
      doorSection.append(this._stateCard("Loading doors…"));
      content.append(doorSection);
      return;
    }
    if (this._dashboardDoorsError) {
      count.textContent = "";
      doorSection.append(this._stateCard(this._dashboardDoorsError, "Unable to load doors"));
      content.append(doorSection);
      return;
    }

    const doors = this._sortedDoors();
    const accessoryCount = this._accessDevices.length;
    count.textContent = `${this._doorCountLabel(doors.length)} · ${accessoryCount} ${accessoryCount === 1 ? "accessory" : "accessories"}`;
    if (doors.length === 0) {
      doorSection.append(this._stateCard(
        "Ask a HomePASS administrator to add an existing Home Assistant door or lock.",
        "No doors added",
      ));
      doorSection.append(this._dashboardAction("Add Door", "mdi:door-open", "plain", () => void this._openAddDoorDialog()));
      content.append(doorSection);
      return;
    }

    const grid = document.createElement("div");
    grid.className = "doors-grid";
    for (const door of doors) {
      grid.append(this._doorPageCard(door));
    }
    doorSection.append(grid);
    content.append(doorSection, this._accessDevicesSection(doors));
  }

  _accessDevicesSection(doors) {
    const section = document.createElement("section");
    section.className = "doors-devices-section";
    const heading = document.createElement("div");
    heading.className = "doors-devices-section-heading";
    heading.innerHTML = "<div><h2>Devices</h2><p>Door controllers and accessories associated with HomePASS.</p></div>";
    section.append(heading);
    const grid = document.createElement("div");
    grid.className = "access-device-grid";
    for (const door of doors) {
      grid.append(this._operatingDeviceCard(door));
    }
    for (const device of this._accessDevices) {
      grid.append(this._accessDeviceCard(device));
    }
    if (this._accessDevicesLoading) {
      grid.append(this._stateCard("Looking for paired access devices…"));
    } else if (this._accessDevicesError) {
      grid.append(this._stateCard(this._accessDevicesError, "Accessories unavailable"));
    } else if (this._hass?.user?.is_admin && this._accessDevices.length === 0) {
      const empty = this._stateCard(
        "Nuki keypads are managed through their paired Nuki lock. A standalone Frient keypad can be paired through ZHA and then added here.",
        "No standalone keypads added",
      );
      grid.append(empty);
    }
    section.append(grid);
    return section;
  }

  _operatingDeviceCard(door) {
    const profile = {
      lock: ["Smart lock", "mdi:lock-outline"],
      garage_cover: ["Garage door controller", "mdi:garage-variant"],
      garage_toggle: ["Garage door relay", "mdi:electric-switch"],
      electric_strike: ["Electric strike", "mdi:electric-switch"],
    }[door.control_profile] ?? ["Door controller", "mdi:door"];
    const card = document.createElement("article");
    card.className = "access-device-card";
    const battery = this._batteryReading(
      this._hass,
      door.battery_entity_id,
      door.battery_percentage,
      door.battery_status,
    );
    card.innerHTML = `
      <ha-icon icon="${profile[1]}" aria-hidden="true"></ha-icon>
      <div><h3>${escapeHtml(profile[0])}</h3>
      <p class="homepass-entity-name">${escapeHtml(door.display_name)}</p>
      <span class="access-device-status ${door.availability === "available" ? "ready" : "pending"}">${door.availability === "available" ? "Online" : "Currently unavailable"}</span>
      ${this._batteryMarkup(battery)}</div>`;
    return card;
  }

  _accessDeviceCard(device) {
    const ready = device.setup_state === "ready";
    const door = this._dashboardAccessPoints.find(
      (candidate) => candidate.id === device.access_point_id,
    );
    const testInstructions = ["garage_cover", "garage_toggle"].includes(
      door?.control_profile,
    )
      ? "Assign a User PIN access to this Door. Enter that PIN, then press either padlock button to activate the garage door. The first approved test completes setup automatically."
      : "Assign a User PIN access to this Door. Enter that PIN, then press the unlocked padlock to unlock or the locked padlock to lock. The first approved test completes setup automatically.";
    const card = document.createElement("article");
    card.className = "access-device-card";
    const battery = this._batteryReading(
      this._hass,
      device.battery_entity_id,
      device.battery_percentage,
      device.battery_status,
    );
    card.innerHTML = `
      <ha-icon icon="mdi:dialpad" aria-hidden="true"></ha-icon>
      <div><h3>${escapeHtml(device.display_name)}</h3>
      <p>Keypad for <span class="homepass-entity-name">${escapeHtml(device.access_point_name)}</span></p>
      <span class="access-device-status ${ready && device.available ? "ready" : "pending"}">${ready ? (device.available ? "Ready" : "Offline") : "Finish setup after hardware test"}</span>
      ${this._batteryMarkup(battery)}
      ${ready ? "" : `<p class="muted">${testInstructions}</p>`}
      ${this._hass?.user?.is_admin ? `<ha-button class="remove-access-device" appearance="plain" ${this._removingAccessDeviceId === device.id ? "disabled" : ""}>${this._removingAccessDeviceId === device.id ? "Removing…" : "Remove"}</ha-button>` : ""}</div>`;
    card.querySelector(".remove-access-device")?.addEventListener(
      "click",
      () => void this._removeAccessDevice(device),
    );
    return card;
  }

  _doorCountLabel(count) {
    return `${count} ${count === 1 ? "door" : "doors"}`;
  }

  _sortedDoors() {
    return [...this._dashboardAccessPoints].sort((left, right) => {
      const priority = this._doorAttentionPriority(left) - this._doorAttentionPriority(right);
      if (priority !== 0) return priority;
      const displayOrder = left.display_name.localeCompare(right.display_name, "en", {
        sensitivity: "base",
      });
      if (displayOrder !== 0) return displayOrder;
      return left.id.localeCompare(right.id);
    });
  }

  _doorAttentionPriority(door) {
    if (door.availability === "offline" || door.availability === "unavailable") return 0;
    if (door.door_state === "open" || door.lock_state === "open" || door.lock_state === "opening") {
      return 1;
    }
    if (door.lock_state === "unlocked" || door.lock_state === "unlocking") return 2;
    if (door.lock_state === "locked" || door.lock_state === "locking") return 3;
    return 4;
  }

  _doorPrimaryState(door) {
    if (door.availability === "offline") return "Offline";
    if (door.availability === "unavailable") return "Unavailable";
    if (door.availability === "unknown") return "Unknown";
    const labels = {
      jammed: "Jammed",
      locked: "Locked",
      locking: "Locking",
      open: "Open",
      opening: "Opening",
      unlocked: "Unlocked",
      unlocking: "Unlocking",
    };
    return labels[door.lock_state] ?? "Unknown";
  }

  _doorTone(door) {
    if (
      door.availability === "offline" ||
      door.availability === "unavailable"
    ) {
      return "subdued";
    }
    if (door.lock_state === "jammed") return "error";
    if (["locking", "opening", "unlocking"].includes(door.lock_state)) {
      return "transitional";
    }
    if (
      door.door_state === "open" ||
      door.lock_state === "open" ||
      door.lock_state === "opening" ||
      door.lock_state === "unlocked" ||
      door.lock_state === "unlocking"
    ) {
      return "attention";
    }
    if (door.availability === "unknown") return "subdued";
    if (!door.lock_state) return "subdued";
    return "secure";
  }

  _doorPageCard(accessPoint) {
    const door = this._doorWithHassState(accessPoint, this._hass);
    const card = document.createElement("button");
    card.type = "button";
    card.id = `door-card-${accessPoint.id}`;
    card.className = `door-page-card ${this._doorTone(door)}`;
    const { slot } = createDoorStatusSymbol(door, "door-page-status-icon");
    const copy = document.createElement("div");
    copy.className = "door-page-card-copy";
    const heading = document.createElement("h2");
    heading.className = "door-page-name homepass-entity-name";
    heading.textContent = door.display_name;
    const state = document.createElement("p");
    state.className = "door-lock-state";
    const contact = document.createElement("p");
    contact.className = "door-contact-state";
    const battery = document.createElement("p");
    battery.className = "door-battery-state";
    copy.append(heading, state, contact, battery);
    card.append(slot, copy);
    this._updateDoorPageCard(card, door);
    card.addEventListener("click", () =>
      this._openDoorControlDialog(accessPoint, `#door-card-${accessPoint.id}`),
    );
    return card;
  }

  _updateDoorPageCard(card, door) {
    const symbol = card.querySelector(".door-page-status-icon");
    const heading = card.querySelector(".door-page-name");
    const lockState = card.querySelector(".door-lock-state");
    const contactState = card.querySelector(".door-contact-state");
    const batteryState = card.querySelector(".door-battery-state");
    if (!symbol || !heading || !lockState || !contactState || !batteryState) return;

    const accessibleStatus = doorStatusAccessibleText(
      door.display_name,
      door.lock_state,
      door.door_state,
      door.availability,
    );
    updateDoorStatusSymbol(symbol, door);
    heading.textContent = door.display_name;
    lockState.textContent = this._doorPrimaryState(door);
    const contactLabel = door.door_state === "open"
      ? "Door open"
      : door.door_state === "closed"
        ? "Door closed"
        : undefined;
    contactState.hidden = !contactLabel;
    contactState.className = `door-contact-state${contactLabel ? ` ${door.door_state}` : ""}`;
    contactState.textContent = contactLabel ?? "";
    const battery = this._batteryReading(
      this._hass,
      door.battery_entity_id,
      door.battery_percentage,
      door.battery_status,
    );
    batteryState.innerHTML = this._batteryMarkup(battery);
    batteryState.hidden = !battery;
    card.className = `door-page-card ${this._doorTone(door)}`;
    card.setAttribute("aria-label", accessibleStatus);
  }

  _dashboardDoorsSection() {
    const viewAllLabel = this._dashboardDoorsLoading || this._dashboardDoorsError
      ? "View All"
      : `View All (${this._dashboardAccessPoints.length})`;
    const viewAll = this._dashboardAction(
      viewAllLabel,
      "mdi:arrow-right",
      "plain",
      () => this._openDoorsPage(),
    );
    const { section, body } = this._dashboardSection(
      "Doors",
      undefined,
      viewAll,
    );
    if (this._dashboardDoorsLoading) {
      body.append(this._dashboardEmptyCard("Loading doors…"));
      return section;
    }
    if (this._dashboardDoorsError) {
      body.append(this._dashboardEmptyCard("Doors unavailable", this._dashboardDoorsError));
      return section;
    }
    if (this._dashboardAccessPoints.length === 0) {
      body.append(
        this._dashboardEmptyCard(
          "No managed doors yet",
          "Managed doors will appear here when they are configured.",
        ),
      );
      return section;
    }
    const doors = document.createElement("div");
    doors.className = "door-grid";
    for (const accessPoint of this._dashboardAccessPoints) {
      doors.append(this._dashboardDoorCard(accessPoint));
    }
    body.append(doors);
    return section;
  }

  _dashboardAttentionSection() {
    if (
      !this._dashboardAttentionError &&
      this._dashboardAttentionItems.length === 0
    ) {
      return undefined;
    }
    const refresh = this._dashboardAction(
      "Refresh",
      "mdi:refresh",
      "plain",
      () => this._refreshDashboardAttention(),
    );
    refresh.id = "refresh-dashboard-attention";
    refresh.disabled = this._dashboardAttentionLoading;
    refresh.setAttribute("aria-label", "Refresh synchronization attention");
    const { section, body } = this._dashboardSection(
      "Attention",
      undefined,
      refresh,
    );
    section.id = "dashboard-attention";
    if (this._dashboardAttentionError) {
      const failure = document.createElement("p");
      failure.className = "dashboard-attention-failure";
      failure.setAttribute("role", "status");
      failure.textContent = this._dashboardAttentionError;
      body.append(failure);
      return section;
    }
    const items = document.createElement("div");
    items.className = "dashboard-attention-list";
    this._dashboardAttentionItems.forEach((item, index) => {
      items.append(this._dashboardAttentionItem(item, index));
    });
    body.append(items);
    return section;
  }

  _dashboardAttentionItem(item, index) {
    const relationship = document.createElement("div");
    relationship.id = `dashboard-attention-item-${index}`;
    relationship.className = `dashboard-attention-item ${item.synchronization.severity}`;
    const summary = document.createElement("p");
    summary.className = "dashboard-attention-relationship";
    summary.textContent = `${item.person_name} access to ${item.door_name}`;
    const navigation = document.createElement("div");
    navigation.className = "dashboard-attention-navigation";
    const viewPerson = document.createElement("button");
    viewPerson.type = "button";
    viewPerson.textContent = `View ${item.person_name}`;
    viewPerson.setAttribute("aria-label", `View ${item.person_name} user details`);
    viewPerson.addEventListener("click", () => void this._openPersonDetails(item.person_id));
    const viewDoor = document.createElement("button");
    viewDoor.type = "button";
    viewDoor.textContent = `View ${item.door_name}`;
    viewDoor.setAttribute("aria-label", `View ${item.door_name} door details`);
    viewDoor.addEventListener("click", () => {
      const existing = this._dashboardAccessPoints.find(
        (accessPoint) => accessPoint.id === item.access_point_id,
      );
      this._openDoorControlDialog(
        existing ?? {
          id: item.access_point_id,
          display_name: item.door_name,
          enabled: true,
        },
        `#dashboard-attention-item-${index} button`,
      );
    });
    navigation.append(viewPerson, viewDoor);
    relationship.append(summary, navigation);
    const synchronization = this._synchronizationRecoveryPresentation(item, "dashboard");
    if (synchronization) relationship.append(synchronization);
    return relationship;
  }

  _dashboardDoorCard(accessPoint) {
    const door = this._doorWithHassState(accessPoint, this._hass);
    const card = document.createElement("article");
    card.id = `dashboard-door-card-${accessPoint.id}`;
    card.className = "dashboard-card door-card";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "door-card-open";
    open.id = `dashboard-door-open-${accessPoint.id}`;
    const identity = document.createElement("div");
    identity.className = "door-card-identity";
    const { slot: statusIconSlot } = createDoorStatusSymbol(
      door,
      "dashboard-door-status-icon",
    );
    const copy = document.createElement("div");
    copy.className = "door-card-copy";
    const heading = document.createElement("h3");
    heading.className = "dashboard-door-name homepass-entity-name";
    const lockState = document.createElement("p");
    lockState.className = "dashboard-door-lock-state";
    const contactState = document.createElement("p");
    contactState.className = "dashboard-door-contact-state";
    const managementState = document.createElement("p");
    managementState.className = "door-management-state";
    identity.append(statusIconSlot);
    copy.append(heading, lockState, contactState, managementState);
    open.append(identity, copy);
    const control = document.createElement("div");
    control.className = "dashboard-door-control";
    const actionButton = document.createElement("button");
    actionButton.type = "button";
    actionButton.className = "dashboard-door-action";
    actionButton.id = `dashboard-door-action-${accessPoint.id}`;
    const operationStatus = document.createElement("p");
    operationStatus.className = "dashboard-door-switch-status";
    operationStatus.id = `dashboard-door-switch-status-${accessPoint.id}`;
    operationStatus.setAttribute("role", "status");
    operationStatus.setAttribute("aria-live", "polite");
    actionButton.setAttribute("aria-describedby", operationStatus.id);
    control.append(actionButton, operationStatus);
    card.append(open, control);
    this._updateDashboardDoorCard(card, door);
    open.addEventListener("click", () =>
      this._openDoorControlDialog(
        accessPoint,
        `#dashboard-door-open-${accessPoint.id}`,
      ),
    );
    actionButton.addEventListener("click", (event) => {
      event.stopPropagation();
      void this._beginDashboardDoorOperation(accessPoint.id);
    });
    return card;
  }

  _updateDashboardDoorCard(card, door) {
    const statusIcon = card.querySelector(".dashboard-door-status-icon");
    const heading = card.querySelector(".dashboard-door-name");
    const lockState = card.querySelector(".dashboard-door-lock-state");
    const contactState = card.querySelector(".dashboard-door-contact-state");
    const managementState = card.querySelector(".door-management-state");
    const open = card.querySelector(".door-card-open");
    const actionButton = card.querySelector(".dashboard-door-action");
    const operationStatus = card.querySelector(".dashboard-door-switch-status");
    if (
      !statusIcon || !heading || !lockState || !contactState || !managementState ||
      !open || !actionButton || !operationStatus
    ) return;

    const accessibleStatus = doorStatusAccessibleText(
      door.display_name,
      door.lock_state,
      door.door_state,
      door.availability,
    );
    const managementLabel = door.enabled ? "" : "HomePASS management is disabled";
    updateDoorStatusSymbol(statusIcon, door);
    heading.textContent = door.display_name;
    lockState.textContent = this._doorPrimaryState(door);
    const contactLabel = door.door_state === "open"
      ? "Open"
      : door.door_state === "closed"
        ? "Closed"
        : undefined;
    contactState.hidden = !contactLabel;
    contactState.textContent = contactLabel ?? "";
    managementState.hidden = !managementLabel;
    managementState.textContent = managementLabel;
    open.setAttribute(
      "aria-label",
      [accessibleStatus, managementLabel].filter(Boolean).join(". "),
    );
    this._updateDashboardDoorAction(actionButton, operationStatus, door);
  }

  _dashboardDoorCanOperate(door) {
    const liveLock = door?.lock_entity_id
      ? this._hass?.states?.[door.lock_entity_id]
      : undefined;
    const liveStateMatches = door?.control_profile === "lock"
      ? liveLock?.state === door.lock_state
      : door?.control_profile === "garage_cover"
        ? ({ closed: "locked", open: "unlocked" })[liveLock?.state] === door.lock_state
        : Boolean(liveLock);
    const stateCanOperate = ["electric_strike", "garage_toggle"].includes(door?.control_profile) && !door?.door_entity_id
      ? true : ["locked", "unlocked"].includes(door?.lock_state);
    return Boolean(
      door?.enabled === true &&
      door.availability === "available" &&
      stateCanOperate && liveStateMatches &&
      Number.isFinite(Date.parse(liveLock?.last_updated)),
    );
  }

  _updateDashboardDoorAction(actionButton, status, door) {
    const active = this._doorOperationAccessPointId === door.id;
    const busy = active && [
      DOOR_OPERATION_STATE.COMMAND_SENT,
      DOOR_OPERATION_STATE.WAITING_FOR_CONFIRMATION,
    ].includes(this._doorOperationState);
    const failed = active && this._doorOperationState === DOOR_OPERATION_STATE.FAILED;
    const anotherDoorBusy = this._doorOperationIsBusy() && !active;
    const stable = this._dashboardDoorCanOperate(door);
    const operation = stable ? this._doorOperationForState(door) : undefined;
    const confirmationRequired = ["unlock", "open", "release", "operate"].includes(
      operation?.action,
    );
    const actionLabel = ({
      lock: "Lock",
      unlock: "Unlock",
      open: "Open",
      close: "Close",
      release: "Release",
      operate: "Activate",
    })[operation?.action] ?? "Unavailable";
    actionButton.textContent = actionLabel;
    actionButton.setAttribute("data-confirmation", String(confirmationRequired));
    actionButton.setAttribute("data-known-state", String(stable));
    actionButton.setAttribute("aria-busy", String(busy));
    actionButton.disabled = !stable || busy || anotherDoorBusy;
    actionButton.setAttribute("aria-disabled", String(actionButton.disabled));
    actionButton.setAttribute(
      "aria-label",
      stable
        ? `${actionLabel} ${door.display_name}${confirmationRequired ? "; confirmation required" : ""}`
        : busy
          ? `${door.display_name} control updating`
          : `${door.display_name} control unavailable`,
    );
    status.className = `dashboard-door-switch-status${failed ? " error" : ""}`;
    if (busy) {
      status.textContent = ({ lock: "Locking…", unlock: "Unlocking…", open: "Opening…", close: "Closing…", release: "Releasing…", operate: "Activating…" })[this._doorOperationAction] ?? "Updating…";
    } else if (failed && !stable) {
      status.textContent = "Not confirmed. Status unavailable.";
    } else if (failed) {
      status.textContent = "Not confirmed. Try again.";
    } else if (anotherDoorBusy) {
      status.textContent = "Another door is updating.";
    } else if (!stable) {
      status.textContent = "Control unavailable";
    } else {
      status.textContent = "";
    }
  }

  async _beginDashboardDoorOperation(accessPointId) {
    if (
      this._currentPage !== "dashboard" ||
      this._detailsPersonId ||
      this._doorOperationIsBusy()
    ) return;
    const accessPoint = this._dashboardAccessPoints.find((item) => item.id === accessPointId);
    const door = this._doorWithHassState(accessPoint, this._hass);
    if (!this._dashboardDoorCanOperate(door)) return;
    const operation = this._doorOperationForState(door);
    if (["unlock", "open", "release", "operate"].includes(operation?.action)) {
      this._openDoorControlDialog(
        accessPoint,
        `#dashboard-door-action-${accessPointId}`,
      );
      return;
    }
    this._clearPreviousDashboardDoorFailure(accessPointId);
    await this._startDoorOperation(door, accessPointId, operation);
  }

  _clearPreviousDashboardDoorFailure(nextAccessPointId) {
    const previousAccessPointId = this._doorOperationAccessPointId;
    if (
      this._doorOperationState !== DOOR_OPERATION_STATE.FAILED ||
      !previousAccessPointId ||
      previousAccessPointId === nextAccessPointId
    ) return;
    this._resetDoorOperation();
    const previous = this._dashboardAccessPoints.find(
      (item) => item.id === previousAccessPointId,
    );
    const previousCard = this.shadowRoot.querySelector(
      `#dashboard-door-card-${previousAccessPointId}`,
    );
    if (previous && previousCard) {
      this._updateDashboardDoorCard(
        previousCard,
        this._doorWithHassState(previous, this._hass),
      );
    }
  }

  _updateDoorOperationSurfaces() {
    if (this._doorControlDialogOpen) {
      this._updateDoorOperationControls();
    }
    for (const accessPoint of this._dashboardAccessPoints) {
      const card = this.shadowRoot.querySelector(
        `#dashboard-door-card-${accessPoint.id}`,
      );
      if (card) {
        this._updateDashboardDoorCard(card, this._doorWithHassState(accessPoint, this._hass));
      }
    }
  }

  _updateDashboardDoorCardsFromHass(previousHass, hass) {
    const updateDashboardCards = Boolean(
      this._currentPage === "dashboard" &&
      !this._detailsPersonId &&
      !this._dashboardDoorsLoading &&
      !this._dashboardDoorsError,
    );
    const updateDoorCards = Boolean(
      this._currentPage === "doors" &&
      !this._dashboardDoorsLoading &&
      !this._dashboardDoorsError,
    );
    for (const accessPoint of this._dashboardAccessPoints) {
      const sourceIds = [
        accessPoint.lock_entity_id,
        accessPoint.door_entity_id,
        accessPoint.battery_entity_id,
        accessPoint.door_sensor_battery_entity_id,
      ].filter(Boolean);
      if (
        sourceIds.length === 0 ||
        sourceIds.every(
          (entityId) => previousHass?.states?.[entityId] === hass?.states?.[entityId],
        )
      ) {
        continue;
      }
      const door = this._doorWithHassState(accessPoint, hass);
      if (this._doorOperationAccessPointId === accessPoint.id) {
        this._reconcileDoorOperationFromLiveState(door);
      }
      if (updateDashboardCards) {
        const dashboardCard = this.shadowRoot.querySelector(
          `#dashboard-door-card-${accessPoint.id}`,
        );
        if (dashboardCard) {
          this._updateDashboardDoorCard(dashboardCard, door);
        }
      }
      if (updateDoorCards) {
        const doorCard = this.shadowRoot.querySelector(`#door-card-${accessPoint.id}`);
        if (doorCard) {
          this._updateDoorPageCard(doorCard, door);
        }
      }
    }
  }

  _dashboardPeopleSection() {
    const viewAllLabel = this._loading || this._error
      ? "View All"
      : `View All (${this._people.length})`;
    const viewAll = this._dashboardAction(
      viewAllLabel,
      "mdi:arrow-right",
      "plain",
      () => this._openPeoplePage(),
    );
    const { section, body } = this._dashboardSection(
      "Users",
      "Users whose access is managed by HomePASS.",
      viewAll,
    );
    if (this._loading) {
      body.append(this._dashboardEmptyCard("Loading users…"));
      return section;
    }
    if (this._error) {
      body.append(this._dashboardEmptyCard("Users unavailable", this._error));
      return section;
    }
    if (this._people.length === 0) {
      body.append(
        this._dashboardEmptyCard(
          "No users yet",
          "Add your first user to begin managing access to your home.",
        ),
      );
      return section;
    }
    const people = document.createElement("div");
    people.className = "dashboard-people";
    for (const person of this._people.slice(0, 6)) {
      const card = this._personCard(person);
      card.className += " dashboard-person-card";
      people.append(card);
    }
    body.append(people);
    return section;
  }

  _dashboardRecentActivitySection() {
    const activeFilterCount = this._dashboardActivityActiveFilterCount();
    const filter = this._dashboardAction(
      activeFilterCount > 0 ? `Filter (${activeFilterCount})` : "Filter",
      "mdi:filter-variant",
      "plain",
      () => this._openDashboardActivityFilters(),
    );
    filter.id = "filter-recent-activity";
    filter.setAttribute("aria-label", activeFilterCount > 0
      ? `Filter recent activity, ${activeFilterCount} active filter groups`
      : "Filter recent activity");
    filter.setAttribute("aria-haspopup", "true");
    filter.setAttribute("aria-expanded", String(this._dashboardActivityFiltersOpen));
    filter.setAttribute("aria-controls", "dashboard-activity-filters");
    const refresh = this._dashboardAction(
      "Refresh",
      "mdi:refresh",
      "plain",
      () => this._refreshDashboardActivity(),
    );
    refresh.id = "refresh-recent-activity";
    refresh.disabled = this._dashboardActivityRequestPending;
    refresh.setAttribute("aria-label", "Refresh recent activity");
    const actions = document.createElement("div");
    actions.className = "dashboard-section-actions";
    if (this._currentPage === "dashboard") {
      actions.append(this._dashboardAction(
        "View all",
        "mdi:arrow-right",
        "plain",
        () => this._openActivityPage(),
      ));
    }
    actions.append(filter, refresh);
    const { section, body } = this._dashboardSection(
      "Recent Activity",
      undefined,
      actions,
    );
    section.id = "dashboard-recent-activity";
    section.append(this._dashboardActivityFilterPopover());
    if (this._dashboardActivityLoading) {
      body.append(this._dashboardActivityState("Loading recent activity…", "status"));
      return section;
    }
    if (this._dashboardActivityError) {
      body.append(this._dashboardActivityState(this._dashboardActivityError, "status"));
      return section;
    }
    if (this._dashboardActivityEvents.length === 0) {
      if (activeFilterCount > 0) {
        const empty = document.createElement("div");
        empty.className = "dashboard-activity-filter-empty";
        empty.append(
          this._dashboardActivityState("No activity matches the current filters.", "status"),
          this._dashboardAction(
            "Clear Filters",
            "mdi:filter-remove-outline",
            "plain",
            () => this._clearDashboardActivityFilters(),
          ),
        );
        body.append(empty);
      } else {
        body.append(this._dashboardActivityState("No recent activity yet.", "status"));
      }
      return section;
    }

    const list = document.createElement("div");
    list.className = "dashboard-activity-list";
    const visibleEvents = this._currentPage === "dashboard"
      ? this._dashboardActivityEvents.slice(0, DASHBOARD_ACTIVITY_PREVIEW_LIMIT)
      : this._dashboardActivityEvents;
    this._activityGroups(visibleEvents).forEach((group, groupIndex) => {
      const dateGroup = document.createElement("section");
      dateGroup.className = "dashboard-activity-date-group";
      const heading = document.createElement("h3");
      heading.className = "dashboard-activity-date-heading";
      heading.textContent = group.label;
      const rows = document.createElement("div");
      rows.className = "dashboard-activity-rows";
      group.events.forEach((event, eventIndex) => {
        rows.append(this._activityRow(event, groupIndex, eventIndex));
      });
      dateGroup.append(heading, rows);
      list.append(dateGroup);
    });
    body.append(list);
    return section;
  }

  _dashboardActivityFilterPopover() {
    const popover = document.createElement("div");
    popover.id = "dashboard-activity-filters";
    popover.className = "dashboard-activity-filter-popover";
    popover.setAttribute("popover", "auto");
    popover.setAttribute("aria-labelledby", "dashboard-activity-filter-title");

    const heading = document.createElement("h3");
    heading.id = "dashboard-activity-filter-title";
    heading.textContent = "Filter Recent Activity";
    popover.append(heading);

    const eventSection = document.createElement("section");
    eventSection.className = "dashboard-activity-filter-section";
    const eventHeading = document.createElement("h4");
    eventHeading.textContent = "Event Type";
    eventSection.append(eventHeading);
    if (this._dashboardActivityFilterGroups.length === 0) {
      const unavailable = document.createElement("p");
      unavailable.className = "dashboard-activity-filter-help";
      unavailable.textContent = "Event filters are unavailable right now.";
      eventSection.append(unavailable);
    } else {
      const selected = this._dashboardActivitySelectedEventTypes ?? new Set(
        this._dashboardActivityEventTypeIds(),
      );
      const groups = document.createElement("div");
      groups.className = "dashboard-activity-event-groups";
      for (const group of this._dashboardActivityFilterGroups) {
        const fieldset = document.createElement("fieldset");
        fieldset.className = "dashboard-activity-event-group";
        const legend = document.createElement("legend");
        legend.textContent = group.title;
        fieldset.append(legend);
        let currentSubgroup;
        for (const option of group.options) {
          if (option.subgroup && option.subgroup !== currentSubgroup) {
            const subgroup = document.createElement("div");
            subgroup.className = "dashboard-activity-filter-subgroup";
            subgroup.textContent = option.subgroup;
            fieldset.append(subgroup);
            currentSubgroup = option.subgroup;
          }
          const label = document.createElement("label");
          label.className = "dashboard-activity-filter-option";
          const input = document.createElement("input");
          input.type = "checkbox";
          input.checked = selected.has(option.id);
          input.setAttribute("data-activity-event-filter", option.id);
          input.addEventListener("change", () => {
            this._toggleDashboardActivityEventFilter(option.id, input.checked);
          });
          const text = document.createElement("span");
          text.textContent = option.title;
          label.append(input, text);
          fieldset.append(label);
        }
        groups.append(fieldset);
      }
      eventSection.append(groups);
    }

    const relationshipSection = document.createElement("section");
    relationshipSection.className = "dashboard-activity-filter-section";
    const relationshipHeading = document.createElement("h4");
    relationshipHeading.textContent = "Relationship";
    const selects = document.createElement("div");
    selects.className = "dashboard-activity-filter-selects";
    selects.append(
      this._dashboardActivityFilterSelect({
        id: "activity-door-filter",
        label: "Door",
        allLabel: "All Doors",
        selected: this._dashboardActivityDoorFilter,
        options: [...this._dashboardAccessPoints]
          .sort((left, right) =>
            left.display_name.localeCompare(right.display_name, "en", {
              sensitivity: "base",
            }) || left.id.localeCompare(right.id),
          )
          .map((door) => ({ id: door.id, label: door.display_name })),
        onChange: (value) => this._setDashboardActivityDoorFilter(value),
      }),
      this._dashboardActivityFilterSelect({
        id: "activity-person-filter",
        label: "User",
        allLabel: "All Users",
        selected: this._dashboardActivityPersonFilter,
        options: [...this._people]
          .sort((left, right) =>
            left.display_name.localeCompare(right.display_name, "en", {
              sensitivity: "base",
            }) || left.person_id.localeCompare(right.person_id),
          )
          .map((person) => ({ id: person.person_id, label: person.display_name })),
        onChange: (value) => this._setDashboardActivityPersonFilter(value),
      }),
    );
    relationshipSection.append(relationshipHeading, selects);

    const footer = document.createElement("div");
    footer.className = "dashboard-activity-filter-footer";
    const clear = this._dashboardAction(
      "Clear All",
      "mdi:filter-remove-outline",
      "plain",
      () => this._clearDashboardActivityFilters(),
    );
    clear.id = "activity-filter-clear-all";
    clear.disabled = this._dashboardActivityActiveFilterCount() === 0;
    const close = this._dashboardAction(
      "Close",
      "mdi:close",
      "plain",
      () => this._closeDashboardActivityFilters(),
    );
    close.id = "activity-filter-close";
    footer.append(clear, close);
    popover.append(eventSection, relationshipSection, footer);
    popover.addEventListener("keydown", (event) =>
      this._handleDashboardActivityFilterKeydown(event, popover));
    popover.addEventListener("toggle", (event) => {
      if (
        event.newState !== "closed" ||
        !this._dashboardActivityFiltersOpen ||
        this.shadowRoot.querySelector("#dashboard-activity-filters") !== popover
      ) return;
      this._dashboardActivityFiltersOpen = false;
      const filterButton = this.shadowRoot.querySelector("#filter-recent-activity");
      filterButton?.setAttribute("aria-expanded", "false");
      filterButton?.focus();
    });
    return popover;
  }

  _dashboardActivityFilterSelect({ id, label, allLabel, selected, options, onChange }) {
    const field = document.createElement("label");
    field.className = "dashboard-activity-filter-field";
    const text = document.createElement("span");
    text.textContent = label;
    const select = document.createElement("select");
    select.id = id;
    select.value = selected ?? "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = allLabel;
    select.append(all);
    for (const option of options) {
      const item = document.createElement("option");
      item.value = option.id;
      item.textContent = option.label;
      select.append(item);
    }
    select.value = selected ?? "";
    select.addEventListener("change", () => onChange(select.value));
    field.append(text, select);
    return field;
  }

  _handleDashboardActivityFilterKeydown(event, popover) {
    if (event.key === "Escape") {
      event.preventDefault();
      this._closeDashboardActivityFilters();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...popover.querySelectorAll("ha-button, input, select")]
      .filter((element) => !element.disabled);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && this.shadowRoot.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && this.shadowRoot.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  _showDashboardActivityFilters() {
    if (!this._dashboardActivityFiltersOpen) return;
    const popover = this.shadowRoot.querySelector("#dashboard-activity-filters");
    const button = this.shadowRoot.querySelector("#filter-recent-activity");
    if (!popover || !button) return;
    button.setAttribute("aria-expanded", "true");
    let anchorBottom;
    if (typeof button.getBoundingClientRect === "function") {
      const rect = button.getBoundingClientRect();
      const viewportWidth = Number(globalThis.innerWidth) || 1024;
      const width = Math.min(380, viewportWidth - 32);
      anchorBottom = rect.bottom;
      popover.style.left = `${Math.max(16, Math.min(rect.right - width, viewportWidth - width - 16))}px`;
    }
    if (typeof popover.showPopover === "function") popover.showPopover();
    if (anchorBottom !== undefined && typeof popover.getBoundingClientRect === "function") {
      const viewportHeight = Number(globalThis.innerHeight) || 768;
      const popoverHeight = popover.getBoundingClientRect().height;
      popover.style.top = `${Math.max(16, Math.min(anchorBottom + 8, viewportHeight - popoverHeight - 16))}px`;
    }
    const focusSelector = this._dashboardActivityFilterFocusSelector;
    queueMicrotask(() => {
      const focusTarget = focusSelector
        ? popover.querySelector(focusSelector)
        : popover.querySelector("input, select, ha-button");
      focusTarget?.focus();
    });
  }

  _dashboardActivityState(message, role) {
    const state = document.createElement("p");
    state.className = "dashboard-activity-state";
    state.setAttribute("role", role);
    state.textContent = message;
    return state;
  }

  _activityGroups(events) {
    const groups = new Map();
    const now = this._activityNow();
    for (const event of events) {
      const date = new Date(event.occurred_at);
      const key = this._activityDateKey(date);
      if (!groups.has(key)) {
        groups.set(key, {
          label: this._activityDateLabel(date, now),
          events: [],
        });
      }
      groups.get(key).events.push(event);
    }
    return [...groups.values()];
  }

  _activityTimezone() {
    const configured = this._hass?.config?.time_zone ?? "UTC";
    try {
      new Intl.DateTimeFormat("en-US", { timeZone: configured }).format();
      return configured;
    } catch (_error) {
      return "UTC";
    }
  }

  _activityDateParts(date) {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: this._activityTimezone(),
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(date);
    const value = (type) => Number(parts.find((part) => part.type === type)?.value);
    return { year: value("year"), month: value("month"), day: value("day") };
  }

  _activityDateKey(date) {
    const { year, month, day } = this._activityDateParts(date);
    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  _activityDateLabel(date, now) {
    const current = this._activityDateParts(now);
    const occurred = this._activityDateParts(date);
    const currentDay = Date.UTC(current.year, current.month - 1, current.day) / 86400000;
    const occurredDay = Date.UTC(occurred.year, occurred.month - 1, occurred.day) / 86400000;
    if (occurredDay === currentDay) return "Today";
    if (occurredDay === currentDay - 1) return "Yesterday";
    return new Intl.DateTimeFormat(undefined, {
      timeZone: this._activityTimezone(),
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(date);
  }

  _activityNow() {
    return new Date();
  }

  _activityTime(occurredAt) {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: this._activityTimezone(),
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(occurredAt));
  }

  _activitySeverity(severity) {
    return {
      info: { icon: "mdi:information-outline", label: "Information" },
      warning: { icon: "mdi:alert-outline", label: "Needs attention" },
      critical: { icon: "mdi:alert-circle-outline", label: "Important" },
    }[severity];
  }

  _activityNavigation(event) {
    for (const reference of event.navigation) {
      if (reference.target === "person") {
        const person = this._people.find((item) => item.person_id === reference.id);
        if (person) return { target: "person", item: person };
      }
      if (reference.target === "door") {
        const door = this._dashboardAccessPoints.find((item) => item.id === reference.id);
        if (door) return { target: "door", item: door };
      }
    }
    return undefined;
  }

  _activityRow(event, groupIndex, eventIndex) {
    const navigation = this._activityNavigation(event);
    const row = document.createElement(navigation ? "button" : "article");
    const rowId = `dashboard-activity-${groupIndex}-${eventIndex}`;
    row.id = rowId;
    row.className = `dashboard-activity-row ${event.severity}`;
    if (navigation) {
      row.type = "button";
      const destination = navigation.target === "person"
        ? `${navigation.item.display_name} user details`
        : `${navigation.item.display_name} door details`;
      row.setAttribute("aria-label", `${event.title}. Open ${destination}.`);
      row.addEventListener("click", () => {
        if (navigation.target === "person") {
          void this._openPersonDetails(navigation.item.person_id);
          return;
        }
        this._openDoorControlDialog(navigation.item, `#${rowId}`);
      });
    }

    const severity = this._activitySeverity(event.severity);
    const icon = document.createElement("ha-icon");
    icon.className = "dashboard-activity-icon";
    icon.setAttribute("icon", severity.icon);
    icon.setAttribute("aria-label", severity.label);
    const copy = document.createElement("div");
    copy.className = "dashboard-activity-copy";
    const title = document.createElement("p");
    title.className = "dashboard-activity-title";
    this._setActivityBrandedText(
      title,
      event.title,
      event.person_name,
      event.door_name,
    );
    copy.append(title);
    const normalizedTitle = event.title.trim().replace(/[.!?]+$/, "").toLocaleLowerCase();
    const normalizedDescription = event.description
      ?.trim()
      .replace(/[.!?]+$/, "")
      .toLocaleLowerCase();
    if (normalizedDescription && normalizedDescription !== normalizedTitle) {
      const description = document.createElement("p");
      description.className = "dashboard-activity-description";
      this._setActivityBrandedText(
        description,
        event.description.trim(),
        event.person_name,
        event.door_name,
      );
      copy.append(description);
    }
    const time = document.createElement("time");
    time.className = "dashboard-activity-time";
    time.dateTime = event.occurred_at;
    time.textContent = this._activityTime(event.occurred_at);
    row.append(icon, copy, time);
    return row;
  }

  _setActivityBrandedText(container, text, personName, doorName) {
    container.textContent = "";
    const matches = [personName, doorName]
      .filter((name) => typeof name === "string" && name.length > 0)
      .flatMap((name) => {
        const occurrences = [];
        let searchFrom = 0;
        while (searchFrom < text.length) {
          const start = text.indexOf(name, searchFrom);
          if (start < 0) break;
          occurrences.push({ name, start, end: start + name.length });
          searchFrom = start + name.length;
        }
        return occurrences;
      })
      .sort((left, right) => left.start - right.start || right.end - left.end);
    if (matches.length === 0) {
      container.textContent = text;
      return;
    }
    const appendText = (value) => {
      if (!value) return;
      const segment = document.createElement("span");
      segment.textContent = value;
      container.append(segment);
    };
    let cursor = 0;
    for (const match of matches) {
      if (match.start < cursor) continue;
      appendText(text.slice(cursor, match.start));
      const name = document.createElement("span");
      name.className = "homepass-entity-name";
      name.textContent = match.name;
      container.append(name);
      cursor = match.end;
    }
    appendText(text.slice(cursor));
  }

  _dashboardSection(title, description, action = undefined) {
    const section = document.createElement("section");
    section.className = "dashboard-section";
    const header = document.createElement("div");
    header.className = "dashboard-section-heading";
    const copy = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = title;
    copy.append(heading);
    if (description) {
      const subtitle = document.createElement("p");
      subtitle.textContent = description;
      copy.append(subtitle);
    }
    header.append(copy);
    if (action) header.append(action);
    const body = document.createElement("div");
    section.append(header, body);
    return { section, body };
  }

  _dashboardEmptyCard(title, message = undefined) {
    const card = document.createElement("ha-card");
    card.className = "dashboard-card dashboard-empty-card";
    const heading = document.createElement("h3");
    heading.textContent = title;
    card.append(heading);
    if (message) {
      const description = document.createElement("p");
      description.className = "dashboard-empty-message";
      description.textContent = message;
      card.append(description);
    }
    return card;
  }

  _dashboardAction(label, iconName, appearance, handler) {
    const action = document.createElement("ha-button");
    action.setAttribute("appearance", appearance);
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", iconName);
    icon.setAttribute("slot", "start");
    const text = document.createElement("span");
    text.textContent = label;
    action.append(icon, text);
    action.addEventListener("click", handler);
    return action;
  }

  _renderPeople() {
    const content = this.shadowRoot.querySelector("#content");
    if (this._loading) {
      content.append(this._stateCard("Loading users…"));
      return;
    }
    if (this._error) {
      content.append(this._stateCard(this._error, "Unable to load users"));
      return;
    }
    if (this._people.length === 0) {
      content.append(this._peopleEmptyState());
      return;
    }

    const people = document.createElement("div");
    people.className = "people";
    for (const person of this._people) {
      people.append(this._personCard(person));
    }
    content.append(people);
  }

  _renderPersonDetails() {
    const content = this.shadowRoot.querySelector("#content");
    if (this._detailsLoading) {
      content.append(this._stateCard("Loading user details…"));
      return;
    }
    if (this._detailsError || !this._selectedPerson) {
      content.append(
        this._stateCard(
          this._detailsError ?? "This user is no longer available.",
          "Unable to load user",
        ),
      );
      return;
    }

    const person = this._selectedPerson;
    this.shadowRoot.querySelector("#person-details-title").textContent = person.display_name;
    this.shadowRoot.querySelector("#person-details-current").textContent = person.display_name;

    const details = document.createElement("div");
    details.className = "details-grid";

    const profile = document.createElement("ha-card");
    profile.className = "details-card profile-card";
    const profileHeading = document.createElement("h2");
    profileHeading.textContent = "Profile";
    const fields = document.createElement("div");
    fields.className = "detail-fields";
    fields.append(this._detailField("Display name", person.display_name));
    if (person.description) {
      fields.append(this._detailField("Description", person.description));
    }

    const status = document.createElement("span");
    const statusName = this._personStatus(person);
    status.className = `person-status ${statusName.toLowerCase()}`;
    status.textContent = statusName;
    fields.append(this._detailField("Status", status));
    if (person.notes) {
      fields.append(this._detailField("Notes", person.notes));
    }
    profile.append(profileHeading, fields);
    details.append(profile);

    details.append(
      this._personPolicyCard(),
      this._credentialSummaryCard(),
      this._nukiFingerprintCard(),
      this._nfcEnrollmentCard(),
      this._personScheduleSummaryCard(),
      this._synchronizationHistoryCard(this._personSynchronizationHistory),
    );
    content.append(details);
  }

  async _loadNukiFingerprintStatus(personId = this._selectedPerson?.person_id) {
    if (!personId) return;
    const generation = ++this._nukiFingerprintRequestGeneration;
    this._nukiFingerprintLoading = true;
    this._nukiFingerprintError = undefined;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_NUKI_FINGERPRINT_STATUS_ACTION,
        service_data: { person_id: personId },
        return_response: true,
      });
      if (this._detailsPersonId !== personId ||
          generation !== this._nukiFingerprintRequestGeneration) return;
      this._nukiFingerprintStatus = result.response ?? {
        person_id: personId,
        fingerprint_data_stored: false,
        doors: [],
      };
    } catch (_error) {
      if (this._detailsPersonId !== personId ||
          generation !== this._nukiFingerprintRequestGeneration) return;
      this._nukiFingerprintError =
        "HomePASS could not load Nuki fingerprint status. Try refreshing this user.";
    } finally {
      if (this._detailsPersonId === personId &&
          generation === this._nukiFingerprintRequestGeneration) {
        this._nukiFingerprintLoading = false;
        this._render();
      }
    }
  }

  async _changeNukiFingerprintEnrollment(action, accessPointId) {
    const personId = this._selectedPerson?.person_id;
    if (!personId || this._nukiFingerprintBusyDoorId) return;
    this._nukiFingerprintBusyDoorId = accessPointId;
    this._nukiFingerprintError = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: action,
        service_data: {
          person_id: personId,
          access_point_id: accessPointId,
        },
        return_response: true,
      });
      if (this._detailsPersonId === personId) {
        this._nukiFingerprintStatus = result.response;
      }
    } catch (_error) {
      if (this._detailsPersonId === personId) {
        this._nukiFingerprintError =
          "HomePASS could not update fingerprint setup. Confirm this user's Nuki PIN is synchronized and try again.";
      }
    } finally {
      if (this._detailsPersonId === personId) {
        this._nukiFingerprintBusyDoorId = undefined;
        this._render();
      }
    }
  }

  _nukiFingerprintCard() {
    const card = document.createElement("ha-card");
    card.className = "details-card nuki-fingerprint-card";
    const heading = document.createElement("h2");
    heading.textContent = "Nuki fingerprint";
    card.append(heading);

    const privacy = document.createElement("p");
    privacy.className = "nfc-enrollment-note";
    privacy.textContent =
      "The fingerprint stays on the Nuki keypad. HomePASS stores only which user and PIN authorization it belongs to—never biometric data.";
    card.append(privacy);

    if (this._nukiFingerprintLoading) {
      const loading = document.createElement("p");
      loading.setAttribute("role", "status");
      loading.textContent = "Loading fingerprint status…";
      card.append(loading);
      return card;
    }
    if (this._nukiFingerprintError) {
      const error = document.createElement("p");
      error.setAttribute("role", "alert");
      error.textContent = this._nukiFingerprintError;
      card.append(error);
    }

    const doors = Array.isArray(this._nukiFingerprintStatus?.doors)
      ? this._nukiFingerprintStatus.doors
      : [];
    if (doors.length === 0) {
      const empty = document.createElement("p");
      empty.textContent =
        "Assign and synchronize a PIN for this user on a Nuki door first. The fingerprint is linked to that PIN in Nuki.";
      card.append(empty);
      return card;
    }

    for (const door of doors) {
      const section = document.createElement("section");
      section.className = "nuki-fingerprint-door";
      const doorHeading = document.createElement("h3");
      doorHeading.textContent = door.door_name;
      section.append(doorHeading);

      const status = document.createElement("p");
      status.setAttribute("role", "status");
      const statusLabels = {
        not_started: "Not set up",
        awaiting_nuki_app: "Ready for the Nuki app",
        enrolled_unverified: "Waiting for first fingerprint use",
        confirmed: "Fingerprint confirmed",
        failed: "Setup needs attention",
      };
      status.textContent = statusLabels[door.status] ?? "Status unavailable";
      section.append(status);

      if (door.status === "awaiting_nuki_app") {
        const steps = document.createElement("ol");
        for (const instruction of [
          "Open this lock in the Nuki app and choose Keypad.",
          "Open this user's PIN entry, choose Add fingerprint, and follow the scan prompts at the keypad.",
          "Return here when the Nuki app says enrollment is complete.",
        ]) {
          const step = document.createElement("li");
          step.textContent = instruction;
          steps.append(step);
        }
        section.append(steps);
      } else if (door.status === "enrolled_unverified") {
        const help = document.createElement("p");
        help.textContent =
          "Setup is recorded. HomePASS will confirm the link automatically when this fingerprint next unlocks the door through the local Nuki connection.";
        section.append(help);
      } else if (door.status === "confirmed") {
        const confirmed = document.createElement("p");
        confirmed.textContent =
          "HomePASS can attribute matching Nuki fingerprint unlock events to this user.";
        section.append(confirmed);
      }

      if (this._hass?.user?.is_admin) {
        const actions = document.createElement("div");
        actions.className = "nfc-enrollment-actions";
        if (door.status === "not_started" || door.status === "failed") {
          const start = document.createElement("ha-button");
          start.setAttribute("appearance", "filled");
          start.disabled = Boolean(this._nukiFingerprintBusyDoorId);
          start.textContent = "Set up fingerprint";
          start.addEventListener("click", () => void this._changeNukiFingerprintEnrollment(
            START_NUKI_FINGERPRINT_ENROLLMENT_ACTION,
            door.access_point_id,
          ));
          actions.append(start);
        } else if (door.status === "awaiting_nuki_app") {
          const complete = document.createElement("ha-button");
          complete.setAttribute("appearance", "filled");
          complete.disabled = Boolean(this._nukiFingerprintBusyDoorId);
          complete.textContent = "I finished in Nuki";
          complete.addEventListener("click", () => void this._changeNukiFingerprintEnrollment(
            COMPLETE_NUKI_FINGERPRINT_ENROLLMENT_ACTION,
            door.access_point_id,
          ));
          actions.append(complete);
        }
        const refresh = document.createElement("ha-button");
        refresh.setAttribute("appearance", "plain");
        refresh.disabled = Boolean(this._nukiFingerprintBusyDoorId);
        refresh.textContent = "Refresh status";
        refresh.addEventListener("click", () => void this._loadNukiFingerprintStatus());
        actions.append(refresh);
        section.append(actions);
      }
      card.append(section);
    }
    return card;
  }

  async _requestNfcEnrollmentStatus(personId) {
    const result = await this._hass.callWS({
      type: "call_service",
      domain: DOMAIN,
      service: GET_NFC_ENROLLMENT_STATUS_ACTION,
      service_data: { person_id: personId },
      return_response: true,
    });
    return result.response ?? {
      person_id: personId,
      enrolled: false,
      credential_count: 0,
      access_count: 0,
      access_point_ids: [],
    };
  }

  _nfcEnrollmentServicesAvailable() {
    return Boolean(
      this._hass?.services?.[DOMAIN]?.[CREATE_NFC_ENROLLMENT_ACTION] &&
      this._hass?.services?.[DOMAIN]?.[GET_NFC_ENROLLMENT_STATUS_ACTION],
    );
  }

  async _loadNfcEnrollment(personId = this._selectedPerson?.person_id) {
    if (!personId) return;
    const generation = ++this._nfcEnrollmentRequestGeneration;
    this._nfcEnrollmentLoading = true;
    this._nfcEnrollmentError = undefined;
    try {
      if (!this._nfcEnrollmentServicesAvailable()) {
        if (this._detailsPersonId !== personId ||
            generation !== this._nfcEnrollmentRequestGeneration) return;
        const status = {
          person_id: personId,
          enrolled: false,
          credential_count: 0,
          access_count: 0,
          access_point_ids: [],
        };
        this._nfcEnrollment = status;
        this._nfcAccessPoints = [];
        this._nfcAccessSelection = new Set();
        this._nfcAccessSelectionInitialized = true;
        this._nfcEnrollmentStatuses.set(personId, status);
        return;
      }
      const [status, accessPointResult] = await Promise.all([
        this._requestNfcEnrollmentStatus(personId),
        this._hass.callWS({
          type: "call_service",
          domain: DOMAIN,
          service: LIST_ACCESS_POINTS_ACTION,
          service_data: {},
          return_response: true,
        }),
      ]);
      if (this._detailsPersonId !== personId ||
          generation !== this._nfcEnrollmentRequestGeneration) return;
      this._nfcEnrollment = status;
      this._nfcAccessPoints = (accessPointResult.response?.access_points ?? []).filter(
        (door) => door.enabled !== false && door.capabilities?.nfc !== false,
      );
      const assigned = Array.isArray(status.access_point_ids)
        ? status.access_point_ids
        : [];
      if (status.enrolled === true || assigned.length > 0) {
        this._nfcAccessSelection = new Set(assigned);
        this._nfcAccessSelectionInitialized = true;
      } else {
        this._initializeNfcAccessSelectionFromPinAccess();
      }
      this._nfcEnrollmentStatuses.set(personId, status);
    } catch (_error) {
      if (this._detailsPersonId !== personId ||
          generation !== this._nfcEnrollmentRequestGeneration) return;
      this._nfcEnrollmentError =
        "HomePASS could not load NFC enrollment status. Confirm that NFC is configured.";
    } finally {
      if (this._detailsPersonId === personId &&
          generation === this._nfcEnrollmentRequestGeneration) {
        this._nfcEnrollmentLoading = false;
        this._render();
      }
    }
  }

  _initializeNfcAccessSelectionFromPinAccess() {
    if (
      this._nfcAccessSelectionInitialized ||
      this._nfcEnrollment?.enrolled === true ||
      this._detailsLoading ||
      this._nfcAccessPoints.length === 0
    ) return;
    const compatibleDoorIds = new Set(this._nfcAccessPoints.map((door) => door.id));
    const pinDoorIds = new Set(
      this._accessMetadata.map((metadata) => metadata.access_point_id),
    );
    this._nfcAccessSelection = new Set(
      [...pinDoorIds].filter((accessPointId) => compatibleDoorIds.has(accessPointId)),
    );
    this._nfcAccessSelectionInitialized = true;
  }

  async _saveNfcAccess({ reload = true, render = true } = {}) {
    const personId = this._selectedPerson?.person_id;
    if (!personId || this._nfcAccessSaving) return;
    this._nfcAccessSaving = true;
    this._nfcEnrollmentError = undefined;
    if (render) this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: UPDATE_NFC_ACCESS_ACTION,
        service_data: {
          person_id: personId,
          access_point_ids: [...this._nfcAccessSelection],
        },
        return_response: true,
      });
      const assigned = result.response?.access_point_ids ?? [];
      this._nfcAccessSelection = new Set(assigned);
      this._nfcAccessSelectionInitialized = true;
      if (this._nfcEnrollment) {
        this._nfcEnrollment = {
          ...this._nfcEnrollment,
          access_count: assigned.length,
          access_point_ids: assigned,
        };
      }
      if (reload) await this._loadNfcEnrollment(personId);
      return true;
    } catch (_error) {
      this._nfcEnrollmentError =
        "HomePASS could not save these NFC Door assignments. Try again.";
      return false;
    } finally {
      this._nfcAccessSaving = false;
      if (render && this._detailsPersonId === personId) this._render();
    }
  }

  async _createNfcEnrollment() {
    const personId = this._selectedPerson?.person_id;
    if (!personId || this._nfcEnrollmentBusy) return;
    if (!this._nfcEnrollmentServicesAvailable()) {
      this._nfcEnrollmentSetupOpen = true;
      this._nfcEnrollmentOriginDraft = "";
      this._nfcEnrollmentConfigurationError = undefined;
      this._nfcEnrollmentConfigurationNotice = undefined;
      this._nfcEnrollmentError = undefined;
      this._render();
      requestAnimationFrame(() =>
        this.shadowRoot.querySelector("#user-nfc-public-origin")?.focus());
      return;
    }
    this._nfcEnrollmentBusy = true;
    this._nfcEnrollmentError = undefined;
    this._nfcEnrollmentUrl = undefined;
    this._nfcEnrollmentQr = undefined;
    this._nfcEnrollmentExpiresAt = undefined;
    this._render();
    try {
      if (
        this._nfcAccessSelection.size > 0 &&
        !await this._saveNfcAccess({ reload: false, render: false })
      ) return;
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CREATE_NFC_ENROLLMENT_ACTION,
        service_data: { person_id: personId, expires_in_hours: 24 },
        return_response: true,
      });
      this._nfcEnrollmentUrl = result.response?.enrollment_url;
      this._nfcEnrollmentQr = result.response?.qr_code;
      this._nfcEnrollmentExpiresAt = result.response?.expires_at;
      if (!this._nfcEnrollmentUrl) {
        throw new Error("The enrollment link was not returned");
      }
    } catch (_error) {
      this._nfcEnrollmentError =
        "HomePASS could not create the NFC enrollment link. Try again.";
    } finally {
      this._nfcEnrollmentBusy = false;
      if (this._detailsPersonId === personId) this._render();
    }
  }

  _cancelNfcEnrollmentSetup() {
    if (this._nfcEnrollmentConfiguring) return;
    this._nfcEnrollmentSetupOpen = false;
    this._nfcEnrollmentOriginDraft = "";
    this._nfcEnrollmentConfigurationError = undefined;
    this._nfcEnrollmentConfigurationNotice = undefined;
    this._render();
  }

  async _configureNfcEnrollment() {
    const personId = this._selectedPerson?.person_id;
    if (!personId || this._nfcEnrollmentConfiguring || !this._hass?.user?.is_admin) return;
    const publicOrigin = this._nfcEnrollmentOriginDraft.trim();
    let parsed;
    try {
      parsed = new URL(publicOrigin);
    } catch (_error) {
      parsed = undefined;
    }
    if (
      !parsed ||
      parsed.protocol !== "https:" ||
      !parsed.hostname ||
      !["", "/"].includes(parsed.pathname) ||
      parsed.search ||
      parsed.hash ||
      parsed.username ||
      parsed.password
    ) {
      this._nfcEnrollmentConfigurationError =
        "Enter the Nabu Casa HTTPS address without a path, query, or sign-in details.";
      this._nfcEnrollmentConfigurationNotice = undefined;
      this._render();
      return;
    }
    this._nfcEnrollmentConfiguring = true;
    this._nfcEnrollmentConfigurationError = undefined;
    this._nfcEnrollmentConfigurationNotice = undefined;
    this._render();
    let ready = false;
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CONFIGURE_NFC_ACTION,
        service_data: { nfc_public_origin: publicOrigin },
        return_response: true,
      });
      this._nfcEnrollmentConfigurationNotice =
        "Address saved. HomePASS is enabling NFC…";
      this._render();
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline) {
        if (this._nfcEnrollmentServicesAvailable()) {
          ready = true;
          break;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 500));
      }
      if (!ready) {
        this._nfcEnrollmentConfigurationNotice =
          "The address is saved. HomePASS is still enabling NFC; try Continue again in a moment.";
      }
    } catch (_error) {
      this._nfcEnrollmentConfigurationError =
        "HomePASS could not save this address. Check it and try again.";
      this._nfcEnrollmentConfigurationNotice = undefined;
    } finally {
      this._nfcEnrollmentConfiguring = false;
      if (this._detailsPersonId === personId) this._render();
    }
    if (!ready || this._detailsPersonId !== personId) return;
    this._nfcEnrollmentSetupOpen = false;
    this._nfcEnrollmentOriginDraft = "";
    this._nfcEnrollmentConfigurationNotice = undefined;
    await this._loadNfcEnrollment(personId);
    if (this._detailsPersonId === personId) await this._createNfcEnrollment();
  }

  async _revokeNfcEnrollment() {
    const person = this._selectedPerson;
    if (!person || this._nfcEnrollmentBusy) return;
    const confirmed = window.confirm(
      `Revoke NFC enrollment for ${person.display_name}? This removes all passkeys, pending enrollment links, and NFC Door assignments for this user.`,
    );
    if (!confirmed) return;
    this._nfcEnrollmentBusy = true;
    this._nfcEnrollmentError = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: REVOKE_NFC_ENROLLMENT_ACTION,
        service_data: { person_id: person.person_id },
        return_response: true,
      });
      const status = result.response ?? {
        person_id: person.person_id,
        enrolled: false,
        credential_count: 0,
        access_count: 0,
        access_point_ids: [],
      };
      this._nfcEnrollment = status;
      this._nfcEnrollmentStatuses.set(person.person_id, status);
      this._nfcEnrollmentUrl = undefined;
      this._nfcEnrollmentQr = undefined;
      this._nfcEnrollmentExpiresAt = undefined;
      this._nfcAccessSelection = new Set();
      this._nfcAccessSelectionInitialized = false;
      this._initializeNfcAccessSelectionFromPinAccess();
    } catch (_error) {
      this._nfcEnrollmentError =
        "HomePASS could not revoke NFC enrollment. Try again.";
    } finally {
      this._nfcEnrollmentBusy = false;
      if (this._detailsPersonId === person.person_id) this._render();
    }
  }

  _setTemporaryButtonLabel(button, label) {
    const original = button.textContent;
    button.textContent = label;
    window.setTimeout(() => {
      if (button.isConnected) button.textContent = original;
    }, 2200);
  }

  async _copyTextToClipboard(value) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const input = document.createElement("textarea");
    input.value = value;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.append(input);
    input.select();
    const copied = document.execCommand("copy");
    input.remove();
    if (!copied) throw new Error("Clipboard access is unavailable");
  }

  async _copyNfcEnrollmentLink(button) {
    if (!this._nfcEnrollmentUrl) return;
    try {
      await this._copyTextToClipboard(this._nfcEnrollmentUrl);
      this._setTemporaryButtonLabel(button, "Link copied");
    } catch (error) {
      this._nfcEnrollmentError = "The link could not be copied. Open the enrollment page and copy it from the address bar.";
      this._render();
    }
  }

  async _shareNfcEnrollment(button) {
    if (!this._nfcEnrollmentUrl) return;
    try {
      if (navigator.share) {
        await navigator.share({
          title: "HomePASS NFC enrollment",
          text: "Use this secure, single-use link to set up your HomePASS passkey.",
          url: this._nfcEnrollmentUrl,
        });
        return;
      }
      await this._copyTextToClipboard(this._nfcEnrollmentUrl);
      this._setTemporaryButtonLabel(button, "Link copied");
    } catch (error) {
      if (error?.name === "AbortError") return;
      this._nfcEnrollmentError = "The enrollment link could not be shared. Try Copy link instead.";
      this._render();
    }
  }

  async _nfcEnrollmentQrPng() {
    if (!this._nfcEnrollmentQr) throw new Error("QR code is unavailable");
    const image = new Image();
    image.src = this._nfcEnrollmentQr;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 1024;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("QR rendering is unavailable");
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    return await new Promise((resolve, reject) => {
      canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("QR rendering failed")), "image/png");
    });
  }

  async _copyNfcEnrollmentQr(button) {
    try {
      if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
        throw new Error("Image clipboard access is unavailable");
      }
      const png = await this._nfcEnrollmentQrPng();
      await navigator.clipboard.write([new ClipboardItem({ "image/png": png })]);
      this._setTemporaryButtonLabel(button, "QR copied");
    } catch (error) {
      this._nfcEnrollmentError = "The QR image could not be copied in this browser. Use Download QR instead.";
      this._render();
    }
  }

  _nfcEnrollmentCard() {
    const card = document.createElement("ha-card");
    card.className = "details-card nfc-enrollment-card";
    const heading = document.createElement("h2");
    heading.textContent = "NFC enrollment";
    card.append(heading);

    if (this._nfcEnrollmentSetupOpen) {
      const setupHeading = document.createElement("h3");
      setupHeading.textContent = "NFC setup required";
      const explanation = document.createElement("p");
      explanation.textContent =
        "HomePASS needs the secure Nabu Casa HTTPS address before it can create an NFC enrollment link.";
      const field = document.createElement("div");
      field.className = "wizard-field";
      const label = document.createElement("label");
      label.htmlFor = "user-nfc-public-origin";
      label.textContent = "Nabu Casa HTTPS address";
      const input = document.createElement("input");
      input.id = "user-nfc-public-origin";
      input.type = "url";
      input.autocomplete = "url";
      input.placeholder = "https://example.ui.nabu.casa";
      input.value = this._nfcEnrollmentOriginDraft;
      input.disabled = this._nfcEnrollmentConfiguring;
      const help = document.createElement("p");
      help.className = "nfc-enrollment-note";
      help.textContent =
        "In Home Assistant, open Settings → Home Assistant Cloud to find this address.";
      field.append(label, input);
      card.append(setupHeading, explanation, field, help);
      if (this._nfcEnrollmentConfigurationError) {
        const error = document.createElement("p");
        error.setAttribute("role", "alert");
        error.textContent = this._nfcEnrollmentConfigurationError;
        card.append(error);
      }
      if (this._nfcEnrollmentConfigurationNotice) {
        const notice = document.createElement("p");
        notice.setAttribute("role", "status");
        notice.textContent = this._nfcEnrollmentConfigurationNotice;
        card.append(notice);
      }
      const actions = document.createElement("div");
      actions.className = "nfc-enrollment-actions";
      const continueButton = document.createElement("ha-button");
      continueButton.setAttribute("appearance", "filled");
      continueButton.disabled =
        this._nfcEnrollmentConfiguring || !this._nfcEnrollmentOriginDraft.trim();
      continueButton.textContent = this._nfcEnrollmentConfiguring
        ? "Enabling NFC…"
        : "Continue";
      continueButton.addEventListener("click", () => void this._configureNfcEnrollment());
      const cancel = document.createElement("ha-button");
      cancel.setAttribute("appearance", "plain");
      cancel.disabled = this._nfcEnrollmentConfiguring;
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", () => this._cancelNfcEnrollmentSetup());
      input.addEventListener("input", () => {
        this._nfcEnrollmentOriginDraft = input.value;
        this._nfcEnrollmentConfigurationError = undefined;
        continueButton.disabled = !input.value.trim();
      });
      actions.append(continueButton, cancel);
      card.append(actions);
      return card;
    }

    if (this._nfcEnrollmentLoading) {
      const loading = document.createElement("p");
      loading.setAttribute("role", "status");
      loading.textContent = "Loading NFC enrollment status…";
      card.append(loading);
      return card;
    }

    if (this._nfcEnrollmentError) {
      const error = document.createElement("p");
      error.setAttribute("role", "alert");
      error.textContent = this._nfcEnrollmentError;
      card.append(error);
    }

    const status = this._nfcEnrollment;
    const enrolled = status?.enrolled === true;
    const credentialCount = Number(status?.credential_count ?? 0);
    const accessCount = Number(status?.access_count ?? 0);
    const summary = document.createElement("p");
    summary.className = "nfc-enrollment-status";
    const label = document.createElement("strong");
    label.textContent = enrolled ? "Enrolled" : "Not enrolled";
    summary.append(label);
    summary.append(
      enrolled
        ? ` · ${credentialCount} ${credentialCount === 1 ? "passkey" : "passkeys"} · ${accessCount} NFC ${accessCount === 1 ? "door" : "doors"}`
        : accessCount > 0
          ? ` · ${accessCount} door ${accessCount === 1 ? "permission" : "permissions"} saved · Enrollment pending`
          : " · Create a secure, single-use passkey enrollment link for this user.",
    );
    card.append(summary);

    if (!enrolled && this._hass?.user?.is_admin) {
      const assignment = document.createElement("fieldset");
      assignment.className = "nfc-door-assignment";
      const legend = document.createElement("legend");
      legend.textContent = "Choose NFC doors";
      const help = document.createElement("p");
      help.className = "nfc-enrollment-note";
      help.textContent =
        "Door selection is optional. NFC-capable doors where this user already has PIN access are pre-selected, and more can be assigned later.";
      assignment.append(legend, help);
      if (this._nfcAccessPoints.length === 0) {
        const empty = document.createElement("p");
        empty.textContent =
          "No NFC-capable doors are available yet. You can still enroll this user now and assign Doors later.";
        assignment.append(empty);
      } else {
        for (const door of this._nfcAccessPoints) {
          const field = document.createElement("ha-formfield");
          field.setAttribute("label", door.display_name);
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = this._nfcAccessSelection.has(door.id);
          checkbox.disabled = this._nfcAccessSaving || this._nfcEnrollmentBusy;
          checkbox.addEventListener("change", () => {
            if (checkbox.checked) this._nfcAccessSelection.add(door.id);
            else this._nfcAccessSelection.delete(door.id);
          });
          field.append(checkbox);
          assignment.append(field);
        }
      }
      card.append(assignment);
    }

    if (this._nfcEnrollmentUrl) {
      const note = document.createElement("p");
      note.className = "nfc-enrollment-note";
      note.textContent = "Enrollment link created. Show this QR code to the user, or share the secure single-use link with them.";
      card.append(note);

      const qrPanel = document.createElement("div");
      qrPanel.className = "nfc-enrollment-qr-panel";
      if (this._nfcEnrollmentQr) {
        const qr = document.createElement("img");
        qr.className = "nfc-enrollment-qr";
        qr.src = this._nfcEnrollmentQr;
        qr.alt = "QR code for this HomePASS NFC enrollment link";
        qrPanel.append(qr);
      }

      const share = document.createElement("div");
      share.className = "nfc-enrollment-share";
      const qrTitle = document.createElement("strong");
      qrTitle.textContent = "Scan to enroll";
      const qrHelp = document.createElement("p");
      qrHelp.textContent = "Open the phone camera and scan the code. No HomePASS or Home Assistant app is required.";
      const link = document.createElement("a");
      link.className = "nfc-enrollment-link";
      link.href = this._nfcEnrollmentUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Open enrollment page";

      const shareActions = document.createElement("div");
      shareActions.className = "nfc-enrollment-share-actions";
      const copyLink = document.createElement("ha-button");
      copyLink.setAttribute("appearance", "plain");
      copyLink.textContent = "Copy link";
      copyLink.addEventListener("click", () => void this._copyNfcEnrollmentLink(copyLink));
      const shareLink = document.createElement("ha-button");
      shareLink.setAttribute("appearance", "plain");
      shareLink.textContent = "Share";
      shareLink.addEventListener("click", () => void this._shareNfcEnrollment(shareLink));
      shareActions.append(copyLink, shareLink);

      if (this._nfcEnrollmentQr) {
        const copyQr = document.createElement("ha-button");
        copyQr.setAttribute("appearance", "plain");
        copyQr.textContent = "Copy QR";
        copyQr.addEventListener("click", () => void this._copyNfcEnrollmentQr(copyQr));
        const downloadQr = document.createElement("a");
        downloadQr.className = "nfc-enrollment-download";
        downloadQr.href = this._nfcEnrollmentQr;
        const safeName = String(this._selectedPerson?.display_name || "user").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "");
        downloadQr.download = "HomePASS-" + (safeName || "user") + "-NFC-enrollment.svg";
        downloadQr.textContent = "Download QR";
        shareActions.append(copyQr, downloadQr);
      }

      share.append(qrTitle, qrHelp, link, shareActions);
      qrPanel.append(share);
      card.append(qrPanel);
      if (this._nfcEnrollmentExpiresAt) {
        const expires = document.createElement("p");
        expires.className = "nfc-enrollment-note";
        expires.textContent = "Link expires " + new Date(this._nfcEnrollmentExpiresAt).toLocaleString() + ".";
        card.append(expires);
      }
    }

    const actions = document.createElement("div");
    actions.className = "nfc-enrollment-actions";
    const primary = document.createElement("ha-button");
    primary.setAttribute("appearance", enrolled ? "plain" : "filled");
    primary.disabled = this._nfcEnrollmentBusy || this._nfcAccessSaving;
    primary.textContent = enrolled ? "Revoke NFC enrollment" : "Create NFC enrollment";
    if (enrolled) primary.classList.add("subtle-destructive-action");
    primary.addEventListener("click", () => {
      if (enrolled) void this._revokeNfcEnrollment();
      else void this._createNfcEnrollment();
    });
    const refresh = document.createElement("ha-button");
    refresh.setAttribute("appearance", "plain");
    refresh.disabled = this._nfcEnrollmentBusy;
    refresh.textContent = "Refresh status";
    refresh.addEventListener("click", () => void this._loadNfcEnrollment());
    actions.append(primary, refresh);
    card.append(actions);
    return card;
  }

  _personPolicyCard() {
    const card = document.createElement("ha-card");
    card.className = "details-card person-policy-card";
    const heading = document.createElement("h2");
    heading.textContent = "Door access";
    card.append(heading);

    if (this._personPolicyLoading) {
      const loading = document.createElement("p");
      loading.setAttribute("role", "status");
      loading.textContent = "Loading current access…";
      card.append(loading);
      return card;
    }
    if (this._personPolicyError) {
      const error = document.createElement("p");
      error.setAttribute("role", "alert");
      error.textContent = this._personPolicyError;
      card.append(error);
      return card;
    }

    const content = document.createElement("div");
    content.className = "door-policy-content";
    const doorCount =
      this._personPolicyCurrentAccess.length +
      this._personPolicyTemporarilyUnavailable.length +
      this._personPolicyNoAccess.length;
    if (doorCount === 0) {
      const empty = document.createElement("p");
      empty.className = "door-policy-empty";
      empty.textContent = "No doors are configured in HomePASS.";
      content.append(empty);
    }
    const nfcDoorIds = this._nfcAccessSelection;
    const nfcEnrolled = this._nfcEnrollment?.enrolled === true;
    const nfcOnlyAccess = nfcEnrolled
      ? this._personPolicyNoAccess.filter(
          (door) => nfcDoorIds.has(door.access_point_id),
        )
      : [];
    const pendingNfcAccess = nfcEnrolled
      ? []
      : this._personPolicyNoAccess
          .filter((door) => nfcDoorIds.has(door.access_point_id))
          .map((door) => ({
            ...door,
            explanation: "Door permission saved · NFC enrollment pending",
          }));
    const availableAccess = [...this._personPolicyCurrentAccess, ...nfcOnlyAccess];
    const temporarilyUnavailable = [
      ...this._personPolicyTemporarilyUnavailable,
      ...pendingNfcAccess,
    ];
    const noAccess = this._personPolicyNoAccess.filter(
      (door) => !nfcDoorIds.has(door.access_point_id),
    ).map((door) => ({
      ...door,
      explanation: "No access method assigned",
    }));
    const groups = [
      [
        `Available now (${availableAccess.length})`,
        availableAccess,
        "allowed",
        "This user cannot currently access any doors.",
        false,
      ],
      [
        `Temporarily Unavailable (${temporarilyUnavailable.length})`,
        temporarilyUnavailable,
        "temporary",
        "No doors are temporarily unavailable.",
        true,
      ],
      [
        `No access (${noAccess.length})`,
        noAccess,
        "neutral",
        "Every door has an access method assigned.",
        false,
      ],
    ].filter(([, doors], index) => index === 0 || doors.length > 0);
    for (const [title, doors, tone, emptyMessage, inspectable] of groups) {
      const section = document.createElement("section");
      const groupHeading = document.createElement("h3");
      groupHeading.textContent = title;
      const list = document.createElement("div");
      list.className = "door-policy-list";
      this._renderDoorPolicyList(
        list,
        doors,
        tone,
        emptyMessage,
        inspectable
          ? (door, index) =>
              this._openPolicyInspector(
                this._detailsPersonId,
                door.access_point_id,
                "person",
                index,
              )
          : undefined,
        undefined,
        (relationship, door) => this._appendPersonDoorAccessMethods(relationship, door),
        (door) => void this._openDoorFromPerson(door.access_point_id),
      );
      section.append(groupHeading, list);
      content.append(section);
    }
    card.append(content);
    return card;
  }

  _appendPersonDoorAccessMethods(relationship, door) {
    const accessPointId = door.access_point_id;
    if (!accessPointId) return;
    const hasPinAccess = this._hasAccessTo(accessPointId);
    const nfcCapable = this._nfcAccessPoints.some(
      (accessPoint) => accessPoint.id === accessPointId,
    );
    const nfcAssigned = this._nfcAccessSelection.has(accessPointId);
    if (!hasPinAccess && !nfcAssigned) return;

    const methods = document.createElement("div");
    methods.className = "person-door-access-methods";
    const label = document.createElement("span");
    label.className = "person-door-access-methods-label";
    label.textContent = "Access methods";
    methods.append(label);

    if (hasPinAccess) {
      const pin = document.createElement("span");
      pin.className = "person-door-access-method active";
      pin.textContent = "PIN";
      methods.append(pin);
    }

    if (nfcCapable && nfcAssigned) {
      const nfc = document.createElement("span");
      const nfcEnrolled = this._nfcEnrollment?.enrolled === true;
      nfc.className = `person-door-access-method ${nfcEnrolled ? "active" : ""}`;
      nfc.textContent = nfcEnrolled ? "NFC" : "NFC — enrollment pending";
      methods.append(nfc);
    }

    const fingerprint = this._nukiFingerprintStatus?.doors?.find(
      (candidate) => candidate.access_point_id === accessPointId &&
        ["enrolled_unverified", "confirmed"].includes(candidate.status),
    );
    if (fingerprint) {
      const fingerprintMethod = document.createElement("span");
      fingerprintMethod.className = `person-door-access-method ${fingerprint.status === "confirmed" ? "active" : ""}`;
      fingerprintMethod.textContent = fingerprint.status === "confirmed"
        ? "Fingerprint"
        : "Fingerprint — confirmation pending";
      methods.append(fingerprintMethod);
    }

    const scheduleGroup = this._scheduleGroups.find(
      (group) => Array.isArray(group.access_point_ids) &&
        group.access_point_ids.includes(accessPointId),
    );
    const scheduleName = scheduleGroup?.schedule?.name;
    if (scheduleName) {
      const schedule = document.createElement("span");
      schedule.className = "person-door-access-schedule";
      schedule.textContent = `Schedule: ${scheduleName}`;
      methods.append(schedule);
    }

    relationship.append(methods);
  }

  _renderPersonSchedule() {
    const content = this.shadowRoot.querySelector("#content");
    if (this._detailsLoading || this._scheduleLoading) {
      content.append(this._stateCard("Loading schedule…"));
      return;
    }
    if (this._detailsError || !this._selectedPerson) {
      content.append(
        this._stateCard(
          this._detailsError ?? "This user is no longer available.",
          "Unable to load schedule",
        ),
      );
      return;
    }

    const person = this._selectedPerson;
    this.shadowRoot.querySelector("#person-schedule-subtitle").textContent =
      `Manage when ${person.display_name} can access the property.`;

    const builder = document.createElement("form");
    builder.className = "schedule-builder";
    builder.noValidate = true;
    builder.addEventListener("submit", (event) => event.preventDefault());
    const hasAssignedDoors = this._accessMetadata.length > 0;
    builder.append(
      hasAssignedDoors
        ? this._scheduleGroupsSection()
        : this._scheduleBeforeDoorAccessSection(),
    );
    if (this._scheduleGroupEditorOpen && this._scheduleStatus !== "unsupported") {
      const form = this._scheduleForm ?? this._defaultScheduleForm();
      this._scheduleForm = form;
      builder.append(
        ...(hasAssignedDoors ? [this._scheduleDoorsSection()] : []),
        this._scheduleChoiceSection(
          "Validity",
          "schedule-validity",
          [
            ["permanent", "Permanent"],
            ["specific-dates", "Specific Dates"],
          ],
          form.validity,
          (value) => {
            this._scheduleForm.validity = value;
            this._render();
          },
          form.validity === "specific-dates" ? this._scheduleDateFields() : undefined,
        ),
        this._scheduleChoiceSection(
          "Access Hours",
          "schedule-access-hours",
          [
            ["24-hours", "24 Hours"],
            ["specific-hours", "Specific Hours"],
          ],
          form.accessHours,
          (value) => {
            this._scheduleForm.accessHours = value;
            this._render();
          },
        ),
      );

      if (form.accessHours === "specific-hours") {
        builder.append(this._scheduleDaysSection(), this._scheduleTimeSection());
      }
    }
    if (this._scheduleGroupEditorOpen) {
      builder.append(this._scheduleBuilderFooter());
    }
    content.append(builder);
  }

  _scheduleBeforeDoorAccessSection() {
    const section = document.createElement("ha-card");
    section.className = "schedule-section schedule-groups";
    const heading = document.createElement("h2");
    heading.textContent = "User schedule";
    const help = document.createElement("p");
    help.className = "schedule-helper";
    help.textContent =
      "No door access is assigned yet. Set the schedule now and HomePASS will apply it when door access is added later.";
    section.append(heading, help);
    return section;
  }

  _scheduleGroupsSection() {
    const section = document.createElement("ha-card");
    section.className = "schedule-section schedule-groups";
    const heading = document.createElement("h2");
    heading.textContent = "Schedule groups";
    const help = document.createElement("p");
    help.className = "schedule-helper";
    help.textContent =
      "Each group applies one schedule to any subset of this user's assigned doors.";
    const groups = document.createElement("div");
    groups.className = "schedule-group-options";
    for (const group of this._scheduleGroups) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "schedule-group-button";
      button.setAttribute(
        "aria-pressed",
        String(group.schedule?.schedule_id === this._scheduleActiveGroupId),
      );
      const names = (group.access_point_ids ?? []).map(
        (accessPointId) =>
          this._accessMetadata.find(
            (metadata) => metadata.access_point_id === accessPointId,
          )?.access_point_display_name ?? "Door",
      );
      button.textContent = `${group.schedule?.name ?? "Schedule"} · ${names.length} ${
        names.length === 1 ? "door" : "doors"
      }${names.length ? ` · ${names.join(", ")}` : ""}`;
      button.disabled = this._scheduleSaving;
      button.addEventListener("click", () => this._selectScheduleGroup(group));
      groups.append(button);
    }
    const add = document.createElement("button");
    add.id = "add-schedule-group";
    add.type = "button";
    add.className = "schedule-group-button add";
    add.setAttribute("aria-pressed", String(this._scheduleCreatingGroup));
    add.textContent = this._scheduleCreatingGroup
      ? "New schedule group"
      : "Add schedule group";
    add.disabled = this._scheduleSaving;
    add.addEventListener("click", () => this._startScheduleGroup());
    groups.append(add);
    if (this._scheduleGroups.length === 0 && !this._scheduleCreatingGroup) {
      const empty = document.createElement("p");
      empty.className = "schedule-helper schedule-group-empty";
      empty.textContent =
        "Select Add schedule group to choose doors and define their access hours.";
      groups.append(empty);
    }
    section.append(heading, help, groups);
    return section;
  }

  _selectScheduleGroup(group) {
    if (this._scheduleSaving || !group?.schedule) return;
    if (
      this._scheduleIsDirty() &&
      !window.confirm("Discard your unsaved schedule changes?")
    ) {
      return;
    }
    this._effectiveSchedule = group.schedule;
    this._scheduleGroupEditorOpen = true;
    this._scheduleCreatingGroup = false;
    this._scheduleActiveGroupId = group.schedule.schedule_id;
    this._scheduleSelectedAccessPointIds = new Set(group.access_point_ids ?? []);
    this._scheduleOriginalAccessPointIds = [
      ...this._scheduleSelectedAccessPointIds,
    ].sort();
    this._scheduleExpectation = {
      ...this._scheduleExpectation,
      scheduleId: group.schedule.schedule_id,
      scheduleRevision:
        group.expected_schedule_revision ?? group.schedule.revision,
    };
    this._scheduleOriginalForm = this._scheduleFormFromBackend(group.schedule);
    this._scheduleForm = this._cloneScheduleForm(this._scheduleOriginalForm);
    this._scheduleSaveError = this._scheduleUnsupportedReason(group.schedule);
    this._scheduleStatus = this._scheduleSaveError ? "unsupported" : "ok";
    this._render();
  }

  _startScheduleGroup() {
    if (this._scheduleSaving) return;
    if (this._scheduleCreatingGroup) return;
    if (
      this._scheduleIsDirty() &&
      !window.confirm("Discard your unsaved schedule changes?")
    ) {
      return;
    }
    this._scheduleGroupEditorOpen = true;
    this._scheduleCreatingGroup = true;
    this._scheduleActiveGroupId = undefined;
    this._scheduleSelectedAccessPointIds = new Set();
    this._scheduleOriginalAccessPointIds = [];
    this._scheduleOriginalForm = this._defaultScheduleForm();
    this._scheduleForm = this._cloneScheduleForm(this._scheduleOriginalForm);
    this._scheduleSaveError = undefined;
    this._scheduleStatus = "ok";
    this._render();
    const editorHeading = this.shadowRoot.querySelector?.("#schedule-group-editor-heading");
    editorHeading?.focus();
    editorHeading?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  _scheduleDoorsSection() {
    const section = document.createElement("ha-card");
    section.className = "schedule-section";
    const heading = document.createElement("h2");
    heading.id = "schedule-group-editor-heading";
    heading.tabIndex = -1;
    heading.textContent = this._scheduleCreatingGroup
      ? "Create schedule group"
      : "Doors in this group";
    const choices = document.createElement("fieldset");
    choices.className = "schedule-door-options";
    const legend = document.createElement("legend");
    legend.textContent = "Select one or more assigned doors";
    choices.append(legend);
    for (const [index, metadata] of this._accessMetadata.entries()) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `schedule-door-${index}`;
      input.value = metadata.access_point_id;
      input.checked = this._scheduleSelectedAccessPointIds.has(metadata.access_point_id);
      input.disabled = this._scheduleSaving || this._scheduleStatus !== "ok";
      input.addEventListener("change", () => {
        if (input.checked) {
          this._scheduleSelectedAccessPointIds.add(metadata.access_point_id);
        } else {
          this._scheduleSelectedAccessPointIds.delete(metadata.access_point_id);
        }
        this._render();
      });
      const name = document.createElement("span");
      name.textContent = metadata.access_point_display_name;
      label.append(input, name);
      choices.append(label);
    }
    const note = document.createElement("p");
    note.className = "schedule-helper";
    note.textContent =
      "A door belongs to one schedule group. Adding it here moves only that door when you save.";
    section.append(heading, choices, note);
    if (this._accessMetadata.length > 0 && this._scheduleSelectedAccessPointIds.size === 0) {
      section.append(this._scheduleError("schedule-doors-error", "Select at least one door."));
    }
    return section;
  }

  _scheduleChoiceSection(title, name, choices, selected, onChange, extra) {
    const section = document.createElement("ha-card");
    section.className = "schedule-section";
    section.setAttribute("role", "region");
    section.setAttribute("aria-labelledby", `${name}-heading`);
    const heading = document.createElement("h2");
    heading.id = `${name}-heading`;
    heading.textContent = title;
    const options = document.createElement("fieldset");
    options.className = "schedule-options";
    options.setAttribute("aria-label", title);
    for (const [value, label] of choices) {
      const option = document.createElement("label");
      option.className = "schedule-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = name;
      input.value = value;
      input.checked = selected === value;
      input.disabled = this._scheduleSaving || this._scheduleStatus !== "ok";
      input.addEventListener("change", () => onChange(value));
      option.append(input, label);
      options.append(option);
    }
    section.append(heading, options);
    if (extra) {
      section.append(extra);
    }
    return section;
  }

  _scheduleDateFields() {
    const fields = document.createElement("div");
    fields.className = "schedule-input-grid";
    fields.append(
      this._scheduleNativeInput("starts-date", "Starts date", "date", "startsDate"),
      this._scheduleNativeInput("starts-time", "Starts time", "time", "startsTime"),
      this._scheduleNativeInput("ends-date", "Ends date", "date", "endsDate"),
      this._scheduleNativeInput("ends-time", "Ends time", "time", "endsTime"),
    );
    const error = this._scheduleValidation().dates;
    if (error) {
      fields.append(this._scheduleError("schedule-dates-error", error));
    }
    return fields;
  }

  _scheduleNativeInput(id, label, type, field) {
    const wrapper = document.createElement("div");
    wrapper.className = "schedule-native-field";
    const inputLabel = document.createElement("label");
    inputLabel.htmlFor = id;
    inputLabel.textContent = label;
    const input = document.createElement("input");
    input.id = id;
    input.type = type;
    input.value = this._scheduleForm[field];
    input.disabled = this._scheduleSaving || this._scheduleStatus !== "ok";
    if (type === "time") {
      input.step = "60";
    }
    const errorId = field === "startTime" || field === "endTime"
      ? "schedule-times-error"
      : "schedule-dates-error";
    input.setAttribute("aria-describedby", errorId);
    input.addEventListener("change", () => {
      this._scheduleForm[field] = input.value;
      this._render();
    });
    wrapper.append(inputLabel, input);
    return wrapper;
  }

  _scheduleDaysSection() {
    const section = document.createElement("ha-card");
    section.className = "schedule-section";
    section.setAttribute("role", "region");
    section.setAttribute("aria-labelledby", "schedule-days-heading");
    const heading = document.createElement("h2");
    heading.id = "schedule-days-heading";
    heading.textContent = "Days";
    const allDays = document.createElement("button");
    allDays.id = "toggle-all-schedule-days";
    allDays.type = "button";
    allDays.className = "all-days-button";
    const everyDaySelected = this._scheduleForm.selectedDays.length === SCHEDULE_WEEKDAYS.length;
    allDays.textContent = everyDaySelected ? "Clear All" : "All Days";
    allDays.disabled = this._scheduleSaving || this._scheduleStatus !== "ok";
    allDays.addEventListener("click", () => {
      this._toggleAllScheduleDays(this._scheduleForm);
      this._render();
    });
    const days = document.createElement("div");
    days.className = "weekday-options";
    days.setAttribute("role", "group");
    days.setAttribute("aria-label", "Allowed days");
    days.setAttribute("aria-describedby", "schedule-days-error");
    for (const { value, shortLabel } of SCHEDULE_WEEKDAYS) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "weekday-button";
      button.textContent = shortLabel;
      button.disabled = this._scheduleSaving || this._scheduleStatus !== "ok";
      button.setAttribute("aria-pressed", String(this._scheduleForm.selectedDays.includes(value)));
      button.addEventListener("click", () => {
        const selected = new Set(this._scheduleForm.selectedDays);
        if (selected.has(value)) {
          selected.delete(value);
        } else {
          selected.add(value);
        }
        this._scheduleForm.selectedDays = [...selected].sort((left, right) => left - right);
        this._render();
      });
      days.append(button);
    }
    section.append(heading, allDays, days);
    const error = this._scheduleValidation().days;
    if (error) {
      section.append(this._scheduleError("schedule-days-error", error));
    }
    return section;
  }

  _scheduleTimeSection() {
    const section = document.createElement("ha-card");
    section.className = "schedule-section";
    section.setAttribute("role", "region");
    section.setAttribute("aria-labelledby", "schedule-time-heading");
    const heading = document.createElement("h2");
    heading.id = "schedule-time-heading";
    heading.textContent = "Time";
    const fields = document.createElement("div");
    fields.className = "schedule-input-grid";
    fields.append(
      this._scheduleNativeInput("schedule-start-time", "Start time", "time", "startTime"),
      this._scheduleNativeInput("schedule-end-time", "End time", "time", "endTime"),
    );
    const timezone = document.createElement("p");
    timezone.className = "schedule-helper";
    timezone.textContent = `Times use ${this._hass?.config?.time_zone ?? "UTC"}.`;
    const pinNote = document.createElement("p");
    pinNote.className = "schedule-pin-note";
    pinNote.textContent =
      "The user's PIN will be disabled outside the selected access hours.";
    section.append(heading, fields, timezone, pinNote);
    const error = this._scheduleValidation().times;
    if (error) {
      section.append(this._scheduleError("schedule-times-error", error));
    }
    return section;
  }

  _scheduleError(id, message) {
    const error = document.createElement("p");
    error.id = id;
    error.className = "schedule-error";
    error.setAttribute("role", "alert");
    error.textContent = message;
    return error;
  }

  _scheduleBuilderFooter() {
    const footer = document.createElement("div");
    footer.className = "schedule-builder-footer";
    const status = document.createElement("p");
    status.className = "schedule-builder-status";
    status.setAttribute("role", "status");
    status.textContent = this._scheduleSaving
      ? "Saving schedule…"
      : this._scheduleIsDirty()
        ? "Unsaved changes"
        : "";
    const explanation = document.createElement("p");
    explanation.className = "schedule-persistence-note";
    explanation.setAttribute("role", this._scheduleSaveError ? "alert" : "status");
    explanation.textContent = this._scheduleSaveError ?? "";
    const actions = document.createElement("div");
    actions.className = "schedule-builder-actions";
    const cancel = document.createElement("ha-button");
    cancel.id = "cancel-person-schedule";
    cancel.setAttribute("appearance", "plain");
    cancel.disabled = this._scheduleSaving;
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => this._cancelPersonSchedule());
    const save = document.createElement("ha-button");
    save.id = "save-person-schedule";
    save.disabled =
      !this._scheduleIsValid() ||
      !this._scheduleIsDirty() ||
      this._scheduleSaving ||
      this._scheduleStatus !== "ok";
    save.textContent = this._scheduleSaving ? "Saving…" : "Save";
    save.setAttribute(
      "title",
      this._scheduleStatus === "unsupported"
        ? "This schedule cannot be edited in this builder."
        : this._scheduleIsValid()
          ? "Save this user's schedule."
          : "Fix the schedule validation errors before saving.",
    );
    save.addEventListener("click", () => void this._savePersonSchedule());
    actions.append(cancel, save);
    footer.append(status, explanation, actions);
    return footer;
  }

  _addUserDialogTemplate() {
    return `
      <ha-dialog id="add-user-dialog" open aria-labelledby="add-user-title">
        <ha-dialog-header slot="header">
          <span id="add-user-title" slot="title">Add User</span>
        </ha-dialog-header>
        <div class="add-user-form">
          <div id="add-user-form-content"></div>
          <p id="add-user-error" class="form-error" role="alert" hidden></p>
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="cancel-add-user" appearance="plain" slot="secondaryAction">
            Cancel
          </ha-button>
          <ha-button id="create-add-user" slot="primaryAction"
            aria-describedby="add-user-error"
            aria-busy="${this._addUserSubmitting}">
            ${this._addUserSubmitting ? "Creating…" : "Create User"}
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _configureAddUserDialog() {
    const dialog = this.shadowRoot.querySelector("#add-user-dialog");
    if (!dialog) return;
    this._addUserDialogElement = dialog;
    const cancel = this.shadowRoot.querySelector("#cancel-add-user");
    const create = this.shadowRoot.querySelector("#create-add-user");
    cancel.disabled = this._addUserSubmitting;
    cancel.addEventListener("click", () => this._closePersonDialog());
    create.addEventListener("click", () => this._submitAddUserForm());
    dialog.addEventListener("closed", () => {
      if (this._addUserDialogElement !== dialog) return;
      this._closePersonDialog();
    });
    this._renderAddUserForm();
    this._syncAddUserCreateState();
  }

  _renderAddUserForm() {
    const content = this.shadowRoot.querySelector("#add-user-form-content");
    const error = this.shadowRoot.querySelector("#add-user-error");
    if (!content || !error) return;
    content.className = "dialog-content";
    error.hidden = !this._addUserError;
    error.textContent = this._addUserError ?? "";
    if (this._addUserOptionsLoading) {
      const loading = document.createElement("p");
      loading.setAttribute("role", "status");
      loading.textContent = "Preparing user setup…";
      content.append(loading);
      return;
    }
    if (this._addUserOptionsError) {
      const heading = document.createElement("h2");
      heading.id = "add-user-form-heading";
      heading.tabIndex = -1;
      heading.textContent = "Setup unavailable";
      const message = document.createElement("p");
      message.setAttribute("role", "alert");
      message.textContent = this._addUserOptionsError;
      content.append(heading, message);
      return;
    }
    const details = document.createElement("section");
    details.className = "add-user-section";
    details.setAttribute("aria-labelledby", "add-user-details-heading");
    this._renderAddUserDetails(details);
    const access = document.createElement("section");
    access.className = "add-user-section";
    access.setAttribute("aria-labelledby", "add-user-access-heading");
    this._renderAddUserAccess(access);
    content.append(details, access);
    if (this._addUserForm.accessPointIds.size > 0) {
      const schedule = document.createElement("section");
      schedule.className = "add-user-section";
      schedule.setAttribute("aria-labelledby", "add-user-schedule-heading");
      this._renderAddUserSchedule(schedule);
      content.append(schedule);
    }
    if (this._addUserSubmitting) {
      const pending = document.createElement("p");
      pending.className = "wizard-pending";
      pending.setAttribute("role", "status");
      pending.setAttribute("aria-live", "polite");
      pending.textContent = "Creating the user and setting up access…";
      content.append(pending);
    }
  }

  _addUserSectionHeading(content, id, title, description) {
    const heading = document.createElement("h2");
    heading.id = id;
    heading.textContent = title;
    content.append(heading);
    if (description) {
      const copy = document.createElement("p");
      copy.className = "wizard-help";
      copy.textContent = description;
      content.append(copy);
    }
  }

  _wizardInput(id, labelText, value, { type = "text", maximum } = {}) {
    const wrapper = document.createElement("label");
    wrapper.className = "wizard-field";
    wrapper.htmlFor = id;
    const label = document.createElement("span");
    label.textContent = labelText;
    const input = document.createElement("input");
    input.id = id;
    input.type = type;
    input.value = value;
    input.disabled = this._addUserSubmitting;
    if (maximum) input.maxLength = maximum;
    wrapper.append(label, input);
    return { wrapper, input };
  }

  _renderAddUserDetails(content) {
    this._addUserSectionHeading(
      content,
      "add-user-details-heading",
      "User Details",
      "Add the information HomePASS needs to identify this user.",
    );
    const name = this._wizardInput(
      "add-user-display-name",
      "Display Name",
      this._addUserForm.displayName,
    );
    name.input.required = true;
    name.input.autocomplete = "name";
    name.input.addEventListener("input", () => {
      this._addUserForm.displayName = name.input.value;
      this._addUserError = undefined;
      this._syncAddUserCreateState();
    });
    const description = this._wizardInput(
      "add-user-description",
      "Description (optional)",
      this._addUserForm.description,
      { maximum: MAX_USER_DESCRIPTION_LENGTH },
    );
    description.input.setAttribute(
      "aria-describedby",
      "add-user-description-help",
    );
    description.input.addEventListener("input", () => {
      this._addUserForm.description = description.input.value;
      this._addUserError = undefined;
      this._syncAddUserCreateState();
    });
    const descriptionHelp = document.createElement("span");
    descriptionHelp.id = "add-user-description-help";
    descriptionHelp.className = "field-help";
    descriptionHelp.textContent =
      `Informational only · ${MAX_USER_DESCRIPTION_LENGTH} characters maximum`;
    description.wrapper.append(descriptionHelp);
    const notesLabel = document.createElement("label");
    notesLabel.className = "wizard-field";
    notesLabel.htmlFor = "add-user-notes";
    const notesText = document.createElement("span");
    notesText.textContent = "Notes (optional)";
    const notes = document.createElement("textarea");
    notes.id = "add-user-notes";
    notes.rows = 3;
    notes.value = this._addUserForm.notes;
    notes.disabled = this._addUserSubmitting;
    notes.addEventListener("input", () => {
      this._addUserForm.notes = notes.value;
      this._syncAddUserCreateState();
    });
    notesLabel.append(notesText, notes);
    const pinRow = document.createElement("div");
    pinRow.className = "wizard-pin-row";
    const pin = this._wizardInput(
      "add-user-pin",
      "PIN (optional)",
      this._addUserForm.pin,
      { type: "password", maximum: 10 },
    );
    pin.input.minLength = 4;
    pin.input.inputMode = "numeric";
    pin.input.autocomplete = "new-password";
    pin.input.pattern = "[0-9]*";
    pin.input.setAttribute("aria-describedby", "add-user-pin-help");
    pin.input.addEventListener("input", () => {
      this._addUserForm.pin = pin.input.value;
      this._addUserForm.pinMode = "manual";
      this._addUserError = undefined;
      this._syncAddUserCreateState();
    });
    const pinHelp = document.createElement("span");
    pinHelp.id = "add-user-pin-help";
    pinHelp.className = "field-help";
    pinHelp.textContent =
      "Leave blank for NFC or app-only users. A PIN is required only for keypad door access.";
    pin.wrapper.append(pinHelp);
    const generate = document.createElement("button");
    generate.id = "generate-add-user-pin";
    generate.type = "button";
    generate.textContent = "Generate PIN";
    generate.disabled = this._addUserSubmitting;
    generate.addEventListener("click", () => {
      this._addUserForm.pin = this._generateSecurePin();
      this._addUserForm.pinMode = "generated";
      pin.input.value = this._addUserForm.pin;
      this._addUserError = undefined;
      this._syncAddUserCreateState();
      pin.input.focus();
    });
    pinRow.append(pin.wrapper, generate);
    content.append(name.wrapper, description.wrapper, notesLabel, pinRow);
  }

  _renderAddUserAccess(content) {
    this._addUserSectionHeading(
      content,
      "add-user-access-heading",
      "Door Access",
      "Choose keypad doors to program now. Doors without keypad support remain visible so you can see which access methods can be added after creating the user.",
    );
    const options = document.createElement("fieldset");
    options.className = "wizard-door-options";
    const legend = document.createElement("legend");
    legend.textContent = "PIN-capable doors";
    options.append(legend);
    const eligible = this._addUserOptions.access_points.filter(
      (door) => door.eligible !== false && door.enabled !== false,
    );
    if (eligible.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = "No PIN-capable doors are currently available.";
      options.append(empty);
    }
    for (const [index, door] of eligible.entries()) {
      const label = document.createElement("label");
      label.className = "wizard-door-option";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `add-user-door-${index}`;
      const accessPointId = this._userOptionAccessPointId(door);
      input.value = accessPointId;
      input.checked = this._addUserForm.accessPointIds.has(accessPointId);
      input.disabled = this._addUserSubmitting;
      input.addEventListener("change", () => {
        if (input.checked) this._addUserForm.accessPointIds.add(accessPointId);
        else this._addUserForm.accessPointIds.delete(accessPointId);
        this._addUserError = undefined;
        this._render();
        queueMicrotask(() => this.shadowRoot.querySelector(`#${input.id}`)?.focus());
      });
      const name = document.createElement("span");
      name.textContent = door.display_name;
      label.append(input, name);
      options.append(label);
    }
    const withoutPin = this._addUserOptions.access_points.filter(
      (door) => door.enabled !== false && door.pin_capable === false,
    );
    if (withoutPin.length > 0) {
      const otherHeading = document.createElement("h3");
      otherHeading.textContent = "Other HomePASS doors";
      const otherList = document.createElement("ul");
      otherList.className = "wizard-help";
      for (const door of withoutPin) {
        const item = document.createElement("li");
        item.textContent = door.nfc_capable === true
          ? `${door.display_name} — NFC access can be added after this user is created and enrolled.`
          : `${door.display_name} — HomePASS control is available, but user PIN access is not configured yet.`;
        otherList.append(item);
      }
      options.append(otherHeading, otherList);
    }
    const skip = document.createElement("p");
    skip.className = "wizard-help";
    skip.textContent = "No doors selected means this user will be created without access.";
    content.append(options, skip);
  }

  _renderAddUserSchedule(content) {
    this._addUserSectionHeading(
      content,
      "add-user-schedule-heading",
      "Schedule",
      "One schedule will apply to every selected door initially.",
    );
    const section = document.createElement("fieldset");
    section.id = "add-user-schedule-section";
    section.className = "wizard-schedule-options";
    section.setAttribute("aria-describedby", "add-user-schedule-error");
    const legend = document.createElement("legend");
    legend.textContent = "Access schedule";
    section.append(legend);
    const addMode = (value, labelText) => {
      const label = document.createElement("label");
      label.className = "wizard-radio-row";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "add-user-schedule-mode";
      input.value = value;
      input.checked = this._addUserForm.scheduleMode === value;
      input.disabled = this._addUserSubmitting;
      input.addEventListener("change", () => {
        this._addUserForm.scheduleMode = value;
        this._addUserError = undefined;
        this._render();
      });
      const text = document.createElement("span");
      text.textContent = labelText;
      label.append(input, text);
      section.append(label);
    };
    addMode("permanent", "Permanent access");
    const compatibleSchedules = this._compatibleUserSchedules();
    if (compatibleSchedules.some((schedule) => schedule.name !== "Permanent")) {
      addMode("existing", "Use an existing schedule");
    }
    addMode("new", "Create a new schedule");
    if (this._addUserForm.scheduleMode === "existing") {
      const label = document.createElement("label");
      label.className = "wizard-field";
      label.htmlFor = "add-user-existing-schedule";
      const title = document.createElement("span");
      title.textContent = "Schedule";
      const select = document.createElement("select");
      select.id = "add-user-existing-schedule";
      select.disabled = this._addUserSubmitting;
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose a schedule";
      select.append(placeholder);
      for (const schedule of compatibleSchedules) {
        if (schedule.name === "Permanent") continue;
        const option = document.createElement("option");
        option.value = schedule.schedule_id;
        option.textContent = schedule.name;
        select.append(option);
      }
      select.value = this._addUserForm.existingScheduleId;
      select.addEventListener("change", () => {
        this._addUserForm.existingScheduleId = select.value;
        this._addUserError = undefined;
        this._syncAddUserCreateState();
      });
      label.append(title, select);
      section.append(label);
    }
    if (this._addUserForm.scheduleMode === "new") {
      section.append(this._addUserNewScheduleFields());
    }
    const scheduleError = document.createElement("p");
    scheduleError.id = "add-user-schedule-error";
    scheduleError.className = "form-error";
    scheduleError.setAttribute("role", "alert");
    const message = this._addUserScheduleError();
    scheduleError.hidden = !message;
    scheduleError.textContent = message ?? "";
    content.append(section, scheduleError);
  }

  _addUserNewScheduleFields() {
    return this._inlineScheduleFields({
      form: this._addUserForm.newSchedule,
      prefix: "add-user",
      disabled: this._addUserSubmitting,
      changed: () => {
        this._addUserError = undefined;
        this._render();
      },
      inputChanged: () => {
        this._addUserError = undefined;
        this._syncAddUserCreateState();
      },
    });
  }

  _inlineScheduleFields({ form, prefix, disabled, changed, inputChanged }) {
    const wrapper = document.createElement("div");
    wrapper.className = "wizard-new-schedule";
    const validity = document.createElement("fieldset");
    validity.className = "wizard-option-group";
    const validityLegend = document.createElement("legend");
    validityLegend.textContent = "Validity";
    validity.append(validityLegend);
    const hours = document.createElement("fieldset");
    hours.className = "wizard-option-group";
    const hoursLegend = document.createElement("legend");
    hoursLegend.textContent = "Allowed hours";
    hours.append(hoursLegend);
    const addChoice = (container, name, value, labelText, current, callback) => {
      const label = document.createElement("label");
      label.className = "wizard-radio-row";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = name;
      input.value = value;
      input.checked = current === value;
      input.disabled = disabled;
      input.addEventListener("change", callback);
      const text = document.createElement("span");
      text.textContent = labelText;
      label.append(input, text);
      container.append(label);
    };
    addChoice(
      validity,
      `${prefix}-validity`,
      "permanent",
      "No expiration",
      form.validity,
      () => {
        form.validity = "permanent";
        changed();
      },
    );
    addChoice(
      validity,
      `${prefix}-validity`,
      "specific-dates",
      "Specific dates",
      form.validity,
      () => {
        form.validity = "specific-dates";
        changed();
      },
    );
    wrapper.append(validity);
    if (form.validity === "specific-dates") {
      const dateFields = document.createElement("div");
      dateFields.className = "wizard-date-time-grid";
      for (const [field, labelText, type] of [
        ["startsDate", "Start date", "date"],
        ["startsTime", "Start time", "time"],
        ["endsDate", "End date", "date"],
        ["endsTime", "End time", "time"],
      ]) {
        const item = this._wizardInput(`${prefix}-${field}`, labelText, form[field], { type });
        item.input.disabled = disabled;
        item.input.addEventListener("change", () => {
          form[field] = item.input.value;
          inputChanged();
        });
        dateFields.append(item.wrapper);
      }
      wrapper.append(dateFields);
    }
    addChoice(
      hours,
      `${prefix}-hours`,
      "24-hours",
      "24-hour access",
      form.accessHours,
      () => {
        form.accessHours = "24-hours";
        changed();
      },
    );
    addChoice(
      hours,
      `${prefix}-hours`,
      "specific-hours",
      "Specific weekly hours",
      form.accessHours,
      () => {
        form.accessHours = "specific-hours";
        changed();
      },
    );
    wrapper.append(hours);
    if (form.accessHours === "specific-hours") {
      const days = document.createElement("fieldset");
      const legend = document.createElement("legend");
      legend.textContent = "Days";
      days.append(legend);
      const allDays = document.createElement("button");
      allDays.type = "button";
      allDays.className = "all-days-button";
      const everyDaySelected = form.selectedDays.length === SCHEDULE_WEEKDAYS.length;
      allDays.textContent = everyDaySelected ? "Clear All" : "All Days";
      allDays.disabled = disabled;
      allDays.addEventListener("click", () => {
        this._toggleAllScheduleDays(form);
        changed();
      });
      days.append(allDays);
      for (const { value, label: labelText } of SCHEDULE_WEEKDAYS) {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.checked = form.selectedDays.includes(value);
        input.disabled = disabled;
        input.addEventListener("change", () => {
          const selected = new Set(form.selectedDays);
          if (input.checked) selected.add(value); else selected.delete(value);
          form.selectedDays = [...selected].sort((left, right) => left - right);
          inputChanged();
        });
        label.append(input, labelText);
        days.append(label);
      }
      wrapper.append(days);
      const timeFields = document.createElement("div");
      timeFields.className = "wizard-date-time-grid";
      for (const [field, labelText] of [["startTime", "Start time"], ["endTime", "End time"]]) {
        const item = this._wizardInput(`${prefix}-${field}`, labelText, form[field], {
          type: "time",
        });
        item.input.disabled = disabled;
        item.input.addEventListener("change", () => {
          form[field] = item.input.value;
          inputChanged();
        });
        timeFields.append(item.wrapper);
      }
      wrapper.append(timeFields);
      const pinNote = document.createElement("p");
      pinNote.className = "schedule-pin-note";
      pinNote.textContent =
        "The user's PIN will be disabled outside the selected access hours.";
      wrapper.append(pinNote);
    }
    return wrapper;
  }

  _dialogTemplate() {
    if (!this._editing) return this._addUserDialogTemplate();
    const dialogId = "edit-person-dialog";
    const title = "Edit User";
    return `
      <ha-dialog id="${dialogId}" open>
        <ha-dialog-header slot="header">
          <span slot="title">${title}</span>
        </ha-dialog-header>
        <div class="dialog-content">
          <ha-input id="display-name" label="Display Name" required></ha-input>
          <ha-input id="description" label="Description (optional)"
            maxlength="${MAX_USER_DESCRIPTION_LENGTH}"></ha-input>
          <ha-textarea id="notes" label="Notes" rows="3" resize="auto"></ha-textarea>
          <ha-formfield label="Enabled">
            <ha-switch id="enabled"></ha-switch>
          </ha-formfield>
          <p id="form-error" class="form-error" role="alert" hidden></p>
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="cancel-person" appearance="plain" slot="secondaryAction">
            Cancel
          </ha-button>
          <ha-button id="save-person" slot="primaryAction">
            Save
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _configureDialog() {
    if (!this._editing) {
      this._configureAddUserDialog();
      return;
    }
    const dialog = this.shadowRoot.querySelector(
      this._editing ? "#edit-person-dialog" : "#add-person-dialog",
    );
    const displayName = this.shadowRoot.querySelector("#display-name");
    const description = this.shadowRoot.querySelector("#description");
    const notes = this.shadowRoot.querySelector("#notes");
    const enabled = this.shadowRoot.querySelector("#enabled");
    const cancel = this.shadowRoot.querySelector("#cancel-person");
    const save = this.shadowRoot.querySelector("#save-person");
    const formError = this.shadowRoot.querySelector("#form-error");

    displayName.value = this._form.displayName;
    description.value = this._form.description;
    notes.value = this._form.notes;
    enabled.checked = this._form.enabled;
    displayName.disabled = this._saving;
    description.disabled = this._saving;
    notes.disabled = this._saving;
    enabled.disabled = this._saving;
    cancel.disabled = this._saving;
    save.disabled = this._saving;
    save.textContent = this._saving ? "Saving…" : "Save";

    if (this._validationError) {
      formError.hidden = false;
      formError.textContent = this._validationError;
    }

    cancel.addEventListener("click", () => this._closePersonDialog());
    save.addEventListener("click", () => void this._savePerson());
    dialog.addEventListener("closed", () => this._closePersonDialog());
    displayName.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void this._savePerson();
      }
    });
  }

  _deleteDialogTemplate() {
    return `
      <ha-dialog id="delete-person-dialog" open>
        <ha-dialog-header slot="header">
          <span slot="title">Delete user &quot;<span id="delete-person-name"></span>&quot;?</span>
        </ha-dialog-header>
        <div class="dialog-content">
          <div>
            <p id="delete-person-access-label" class="confirmation-message">
              This user currently has access to:
            </p>
            <ul id="delete-person-access-points" class="delete-person-access-points"></ul>
            <p id="delete-person-no-access" class="confirmation-message" hidden>
              This user currently has no access assigned.
            </p>
          </div>
          <p class="confirmation-message">Deleting this user will:</p>
          <ul class="delete-person-effects">
            <li>Delete this user from HomePASS.</li>
            <li>Delete all HomePASS access records associated with this user.</li>
          </ul>
          <p class="confirmation-detail"><strong>This action cannot be undone.</strong></p>
          <div id="delete-pending" class="access-update-status" role="status" hidden>
            Removing access from the device…<br />
            This can take a few seconds.
          </div>
          <p id="delete-error" class="form-error delete-person-error" role="alert" hidden></p>
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button id="cancel-delete" appearance="plain" slot="secondaryAction">
            Cancel
          </ha-button>
          <ha-button id="confirm-delete" variant="danger" slot="primaryAction">
            Delete User
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _configureDeleteDialog() {
    const dialog = this.shadowRoot.querySelector("#delete-person-dialog");
    const cancel = this.shadowRoot.querySelector("#cancel-delete");
    const confirm = this.shadowRoot.querySelector("#confirm-delete");
    this._refreshDeleteDialog();

    cancel.addEventListener("click", () => this._closeDeletePersonDialog());
    confirm.addEventListener("click", () => void this._deletePerson());
    dialog.addEventListener("closed", () => this._closeDeletePersonDialog());
  }

  _refreshDeleteDialog() {
    const name = this.shadowRoot.querySelector("#delete-person-name");
    const cancel = this.shadowRoot.querySelector("#cancel-delete");
    const confirm = this.shadowRoot.querySelector("#confirm-delete");
    const error = this.shadowRoot.querySelector("#delete-error");
    const pending = this.shadowRoot.querySelector("#delete-pending");
    const accessLabel = this.shadowRoot.querySelector("#delete-person-access-label");
    const accessPoints = this.shadowRoot.querySelector("#delete-person-access-points");
    const noAccess = this.shadowRoot.querySelector("#delete-person-no-access");
    if (!name || !cancel || !confirm || !error || !pending) {
      return;
    }

    name.textContent = this._selectedPerson?.display_name ?? "this user";
    if (accessLabel && accessPoints && noAccess) {
      accessPoints.textContent = "";
      const accessPointNames = [...new Set(
        this._accessMetadata
          .map((metadata) => metadata.access_point_display_name)
          .filter((displayName) => typeof displayName === "string" && displayName.trim()),
      )];
      const hasAccess = accessPointNames.length > 0;
      accessLabel.hidden = !hasAccess;
      accessPoints.hidden = !hasAccess;
      noAccess.hidden = hasAccess;
      for (const displayName of accessPointNames) {
        const item = document.createElement("li");
        item.textContent = displayName;
        accessPoints.append(item);
      }
    }
    cancel.disabled = this._deleting;
    confirm.disabled = this._deleting;
    confirm.textContent = this._deleting ? "Deleting…" : "Delete User";
    pending.hidden = !this._deleting;
    error.hidden = this._deleting || !this._deleteError;
    error.textContent = this._deleteError ?? "";
  }

  _giveAccessDialogTemplate() {
    return `
      <ha-dialog id="give-access-dialog" open>
        <ha-dialog-header slot="header">
          <span slot="title">Give Access</span>
        </ha-dialog-header>
        <div id="give-access-content" class="dialog-content"></div>
        <ha-dialog-footer slot="footer">
          <ha-button id="back-give-access" appearance="plain" slot="secondaryAction" hidden>
            Back
          </ha-button>
          <ha-button id="cancel-give-access" appearance="plain" slot="secondaryAction">
            Cancel
          </ha-button>
          <ha-button id="next-give-access" slot="primaryAction">Next</ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _manageAccessDialogTemplate() {
    return `
      <ha-dialog id="manage-access-dialog" open>
        <ha-dialog-header slot="header">
          <span id="manage-access-title" slot="title">Manage Access</span>
        </ha-dialog-header>
        <div id="manage-access-summary" class="dialog-content">
          <div id="manage-access-view-notice" role="status" hidden>
            <p class="success-title">PIN replaced successfully.</p>
            <p>
              The new PIN has been securely stored in HomePASS and programmed on the
              access device.
            </p>
          </div>
          <div class="detail-field">
            <span class="detail-label">User</span>
            <div id="manage-access-person" class="detail-value"></div>
          </div>
          <div class="detail-field">
            <span class="detail-label">Current access</span>
            <div id="manage-access-current" class="detail-fields"></div>
          </div>
          <div class="detail-field">
            <span class="detail-label">PIN</span>
            <div class="credential-reveal-row">
              <div id="manage-access-credential" class="detail-value"></div>
              <ha-circular-progress
                id="reveal-pin-progress"
                size="small"
                hidden
              ></ha-circular-progress>
              <button
                id="toggle-pin-visibility"
                class="credential-visibility-toggle"
                type="button"
                aria-label="Reveal PIN"
                aria-busy="false"
              >
                <ha-icon id="pin-visibility-icon" icon="mdi:eye"></ha-icon>
              </button>
            </div>
            <span id="reveal-pin-status" role="status" aria-live="polite" hidden>
              Retrieving PIN…
            </span>
            <p id="reveal-pin-error" class="form-error" role="alert" hidden></p>
          </div>
          <div class="credential-actions">
            <ha-button id="edit-access" appearance="filled">Edit Door Access</ha-button>
            <ha-button id="schedule-access" appearance="filled">Schedule</ha-button>
            <ha-button id="change-pin" appearance="filled">Change PIN</ha-button>
          </div>
        </div>
        <div id="edit-access-view" class="dialog-content" hidden>
          <div id="edit-access-content"></div>
          <div id="edit-access-status" class="access-update-status" role="status" hidden></div>
          <p id="edit-access-error" class="form-error" role="alert" hidden></p>
        </div>
        <div id="manage-access-success" class="dialog-content" role="status" hidden>
          <p id="manage-access-result-title" class="success-title">✓ Access saved.</p>
          <p id="manage-access-success-message"></p>
        </div>
        <div id="change-pin-view" class="dialog-content" hidden></div>
        <ha-dialog-footer slot="footer">
          <ha-button id="cancel-edit-access" appearance="plain" slot="secondaryAction"
            hidden disabled aria-hidden="true" tabindex="-1">
            Cancel
          </ha-button>
          <ha-button id="save-edit-access" slot="primaryAction"
            hidden disabled aria-hidden="true" tabindex="-1">Save</ha-button>
          <ha-button id="done-manage-access" slot="primaryAction"
            hidden disabled aria-hidden="true" tabindex="-1">Done</ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _configureManageAccessDialog() {
    const dialog = this.shadowRoot.querySelector("#manage-access-dialog");
    this._manageAccessDialogElement = dialog;
    const edit = this.shadowRoot.querySelector("#edit-access");
    const schedule = this.shadowRoot.querySelector("#schedule-access");
    const changePin = this.shadowRoot.querySelector("#change-pin");
    const cancelEdit = this.shadowRoot.querySelector("#cancel-edit-access");
    const saveEdit = this.shadowRoot.querySelector("#save-edit-access");
    const done = this.shadowRoot.querySelector("#done-manage-access");
    edit.addEventListener("click", () => void this._openEditAccessDialog());
    schedule?.addEventListener("click", () => {
      this._closeManageAccessDialog();
      void this._openPersonSchedule();
    });
    changePin.addEventListener("click", () => this._openChangePin());
    dialog.addEventListener("click", this._handleManageAccessDialogClick);
    cancelEdit.addEventListener("click", () => this._handleManageAccessCancel());
    saveEdit.addEventListener("click", () => this._handleManageAccessPrimary());
    done.addEventListener("click", () => this._handleManageAccessDone());
    dialog.addEventListener("closed", () => {
      // A full panel render can replace the dialog element while preserving the
      // same logical Manage Access session. Ignore the detached element's late
      // close event so it cannot invalidate a Reveal owned by the new element.
      if (this._manageAccessDialogElement !== dialog) {
        return;
      }
      this._closeManageAccessDialog();
    });
    this._updateManageAccessDialog();
  }

  _renderManageAccessSummary() {
    const notice = this.shadowRoot.querySelector("#manage-access-view-notice");
    const person = this.shadowRoot.querySelector("#manage-access-person");
    const current = this.shadowRoot.querySelector("#manage-access-current");
    const credential = this.shadowRoot.querySelector("#manage-access-credential");
    const reveal = this.shadowRoot.querySelector("#toggle-pin-visibility");
    const revealIcon = this.shadowRoot.querySelector("#pin-visibility-icon");
    const revealProgress = this.shadowRoot.querySelector("#reveal-pin-progress");
    const revealStatus = this.shadowRoot.querySelector("#reveal-pin-status");
    const revealError = this.shadowRoot.querySelector("#reveal-pin-error");
    const changePin = this.shadowRoot.querySelector("#change-pin");
    const noticeKind = this._manageAccessSession?.context.notice;
    notice.hidden = !["pin_assigned", "pin_replaced"].includes(noticeKind);
    if (!notice.hidden) {
      notice.textContent = noticeKind === "pin_assigned"
        ? "PIN saved securely. This user is ready for door assignment."
        : "PIN replaced successfully and synchronized with assigned doors.";
    }
    person.textContent = this._selectedPerson?.display_name ?? "";
    current.textContent = "";
    const credentialTarget = this._accessMetadata.find(
      (metadata) => metadata.credential_stored,
    );
    const credentialStored = this._personHasStoredCredential();
    if (
      this._manageAccessSession &&
      this._selectedPerson?.person_id &&
      this._manageAccessSession.personId !== this._selectedPerson.person_id
    ) {
      this._clearCredentialReveal("person_changed");
      this._beginManageAccessSession(
        this._selectedPerson.person_id,
        credentialTarget?.access_point_id,
      );
    }
    if (
      this._manageAccessSession &&
      this._manageAccessSession.accessPointId !== credentialTarget?.access_point_id
    ) {
      const personId = this._manageAccessSession.personId;
      this._clearCredentialReveal("access_point_changed");
      this._beginManageAccessSession(personId, credentialTarget?.access_point_id);
    }
    reveal.hidden = !credentialStored;
    const revealController = this._currentRevealController();
    revealController.mount(
      credential,
      reveal,
      revealIcon,
      revealProgress,
      revealStatus,
      credentialStored ? "••••••" : "No stored PIN credential.",
    );
    if (!this._manageAccessMetadataCurrent) {
      revealController.setBlocked(true);
      revealError.hidden = false;
      revealError.textContent = this._manageAccessRefreshError ??
        "HomePASS could not retrieve this PIN. Close and reopen Manage Access to try again.";
    } else if (this._manageAccessSession?.revealCooldownMessage) {
      revealController.setBlocked(true);
      revealError.hidden = false;
      revealError.textContent = this._manageAccessSession.revealCooldownMessage;
    }
    for (const metadata of this._accessMetadata) {
      const access = document.createElement("div");
      access.className = "detail-fields";
      const door = document.createElement("div");
      door.textContent = `✓ ${metadata.access_point_display_name}`;
      access.append(
        door,
        this._detailField("Status", this._accessHealthLabel(metadata)),
        this._detailField(
          "Last synchronized",
          new Date(metadata.updated_at).toLocaleString(),
        ),
      );
      if (metadata.driver) {
        access.append(this._detailField("Driver", this._driverLabel(metadata.driver)));
      }
      current.append(access);
    }
    const replacementCapability = this._manageAccessReplacementCapability();
    changePin.disabled = replacementCapability === "loading";
    changePin.textContent = replacementCapability === "loading"
      ? "Checking Change PIN…"
      : replacementCapability === "missing" ? "Set PIN" : "Change PIN";
    changePin.title = "";
    changePin.setAttribute(
      "aria-busy",
      String(replacementCapability === "loading"),
    );
  }

  _updateManageAccessDialog() {
    const title = this.shadowRoot.querySelector("#manage-access-title");
    const summary = this.shadowRoot.querySelector("#manage-access-summary");
    const editView = this.shadowRoot.querySelector("#edit-access-view");
    const successView = this.shadowRoot.querySelector("#manage-access-success");
    const changePinView = this.shadowRoot.querySelector("#change-pin-view");
    const content = this.shadowRoot.querySelector("#edit-access-content");
    const error = this.shadowRoot.querySelector("#edit-access-error");
    const operationStatus = this.shadowRoot.querySelector("#edit-access-status");
    const cancel = this.shadowRoot.querySelector("#cancel-edit-access");
    const save = this.shadowRoot.querySelector("#save-edit-access");
    const done = this.shadowRoot.querySelector("#done-manage-access");
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    summary.hidden = true;
    editView.hidden = true;
    successView.hidden = true;
    changePinView.hidden = true;
    this._setManageAccessActionState(cancel, false, false);
    this._setManageAccessActionState(save, false, false);
    this._setManageAccessActionState(done, false, false);

    switch (state) {
      case MANAGE_ACCESS_STATE.VIEW:
        title.textContent = "Manage Access";
        summary.hidden = false;
        this._renderManageAccessSummary();
        this._setManageAccessActionState(done, true, true);
        return;
      case MANAGE_ACCESS_STATE.EDIT_ACCESS:
      case MANAGE_ACCESS_STATE.SAVING_ACCESS:
      case MANAGE_ACCESS_STATE.VERIFYING_ACCESS:
        title.textContent = "Edit Door Access";
        editView.hidden = false;
        this._renderEditAccessView(content, error, operationStatus, cancel, save);
        return;
      case MANAGE_ACCESS_STATE.CHANGE_PIN:
      case MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN:
      case MANAGE_ACCESS_STATE.REPLACING_PIN:
        title.textContent = this._personHasStoredCredential() ? "Change PIN" : "Set PIN";
        changePinView.hidden = false;
        this._renderChangePinView(changePinView, cancel, save, done);
        return;
      case MANAGE_ACCESS_STATE.SUCCESS:
      case MANAGE_ACCESS_STATE.PARTIAL:
        title.textContent = "Access saved";
        successView.hidden = false;
        this.shadowRoot.querySelector("#manage-access-result-title").textContent =
          state === MANAGE_ACCESS_STATE.PARTIAL
            ? "Access saved. Synchronization pending."
            : "✓ Access saved.";
        this.shadowRoot.querySelector("#manage-access-success-message").textContent =
          context.message ?? "Access updated.";
        this._setManageAccessActionState(done, true, true);
        return;
      case MANAGE_ACCESS_STATE.ERROR:
        this._renderManageAccessErrorState({
          title,
          editView,
          changePinView,
          content,
          error,
          operationStatus,
          cancel,
          save,
          done,
          context,
        });
        return;
      default:
        throw new Error(`Unsupported Manage Access state: ${state}`);
    }
  }

  _renderEditAccessView(content, error, operationStatus, cancel, save) {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    content.textContent = "";
    operationStatus.hidden = true;
    operationStatus.textContent = "";
    error.hidden = true;
    error.textContent = "";
    if (this._editAccessPointsLoading) {
      content.textContent = "Loading access points…";
    } else {
      const options = document.createElement("div");
      options.className = "detail-fields";
      for (const accessPoint of this._accessPoints) {
        const accessPointId = this._userOptionAccessPointId(accessPoint);
        const pinSupported = accessPoint.capabilities?.pin === true ||
          accessPoint.pin_capable === true;
        const nfcSupported = this._nfcAccessPoints.some(
          (door) => door.id === accessPointId,
        );
        if (!pinSupported && !nfcSupported) continue;
        const door = document.createElement("fieldset");
        door.className = "manage-access-door-methods";
        const legend = document.createElement("legend");
        const allowed = document.createElement("input");
        allowed.type = "checkbox";
        allowed.checked = this._editAccessSelection.has(accessPointId) ||
          this._editNfcAccessSelection.has(accessPointId);
        allowed.disabled = state !== MANAGE_ACCESS_STATE.EDIT_ACCESS ||
          accessPoint.enabled === false;
        const doorName = document.createElement("span");
        doorName.textContent = accessPoint.enabled === false
          ? `${accessPoint.display_name} — Door disabled`
          : accessPoint.display_name;
        legend.append(allowed, doorName);
        const methods = document.createElement("div");
        methods.className = "manage-access-method-options";
        const addMethod = (labelText, selected, enabled, changed) => {
          const label = document.createElement("label");
          const input = document.createElement("input");
          input.type = "checkbox";
          input.checked = selected;
          input.disabled = state !== MANAGE_ACCESS_STATE.EDIT_ACCESS || !allowed.checked || !enabled;
          input.addEventListener("change", () => changed(input.checked));
          const text = document.createElement("span");
          text.textContent = labelText;
          label.append(input, text);
          methods.append(label);
        };
        if (pinSupported) {
          addMethod("PIN", this._editAccessSelection.has(accessPointId), true, (checked) => {
            if (checked) this._editAccessSelection.add(accessPointId);
            else this._editAccessSelection.delete(accessPointId);
            this._updateManageAccessDialog();
          });
        }
        if (nfcSupported) {
          addMethod(
            this._nfcEnrollment?.enrolled === true ? "NFC" : "NFC — enrollment pending",
            this._editNfcAccessSelection.has(accessPointId),
            true,
            (checked) => {
              if (checked) this._editNfcAccessSelection.add(accessPointId);
              else this._editNfcAccessSelection.delete(accessPointId);
              this._updateManageAccessDialog();
            },
          );
        }
        allowed.addEventListener("change", () => {
          if (!allowed.checked) {
            this._editAccessSelection.delete(accessPointId);
            this._editNfcAccessSelection.delete(accessPointId);
          } else {
            // Door permission is independent of credential readiness. Persist the
            // NFC relationship now, even before a passkey exists, and program a
            // PIN only when the User already has one. This lets an administrator
            // authorize a User first and finish credential setup later.
            if (nfcSupported) this._editNfcAccessSelection.add(accessPointId);
            if (pinSupported && this._personHasStoredCredential()) {
              this._editAccessSelection.add(accessPointId);
            }
          }
          this._updateManageAccessDialog();
        });
        door.append(legend, methods);
        options.append(door);
      }
      content.append(options);
      if (!this._personHasStoredCredential() && this._editAccessSelection.size > 0) {
        {
          const pinSection = document.createElement("div");
          pinSection.className = "manage-access-pin";
          const pin = this._wizardInput(
            "assign-access-pin",
            "PIN",
            this._editAccessPin,
            { type: "password", maximum: 10 },
          );
          pin.input.inputMode = "numeric";
          pin.input.autocomplete = "new-password";
          pin.input.pattern = "[0-9]*";
          pin.input.disabled = state !== MANAGE_ACCESS_STATE.EDIT_ACCESS;
          pin.input.addEventListener("input", () => {
            this._editAccessPin = pin.input.value;
            this._editAccessPointsError = undefined;
            const action = this.shadowRoot.querySelector("#save-edit-access");
            if (action) action.disabled = !this._editAccessAssignmentReady();
          });
          const generate = document.createElement("button");
          generate.type = "button";
          generate.className = "manage-access-generate-pin";
          generate.textContent = "Generate PIN";
          generate.disabled = state !== MANAGE_ACCESS_STATE.EDIT_ACCESS;
          generate.addEventListener("click", () => {
            this._editAccessPin = this._generateSecurePin();
            this._updateManageAccessDialog();
            queueMicrotask(() => this.shadowRoot.querySelector("#assign-access-pin")?.focus());
          });
          const help = document.createElement("p");
          help.className = "wizard-help";
          help.textContent =
            "This user does not yet have a PIN. Enter one before assigning doors.";
          pinSection.append(pin.wrapper, generate, help);
          content.append(pinSection);
        }
        const schedule = document.createElement("fieldset");
        schedule.className = "manage-access-schedule";
        const legend = document.createElement("legend");
        legend.textContent = "User schedule";
        schedule.append(legend);
        const compatibleSchedules = this._compatibleUserSchedules(this._editAccessSchedules);
        if (this._accessMetadata.length > 0) {
          const selectedScheduleId = this._editAccessScheduleMode === "existing"
            ? this._editAccessScheduleId
            : this._editAccessSchedules.find(
                (available) => available.name === "Permanent",
              )?.schedule_id;
          const selectedSchedule = this._editAccessSchedules.find(
            (available) => available.schedule_id === selectedScheduleId,
          );
          const current = document.createElement("p");
          current.className = "manage-access-current-schedule";
          current.textContent = selectedSchedule?.name ?? "Current schedule unavailable";
          schedule.append(current);
        } else {
          const modes = [["permanent", "Permanent access"]];
          if (compatibleSchedules.some((available) => available.name !== "Permanent")) {
            modes.push(["existing", "Use an existing schedule"]);
          }
          modes.push(["new", "Create a new schedule"]);
          for (const [value, labelText] of modes) {
            const label = document.createElement("label");
            const input = document.createElement("input");
            input.type = "radio";
            input.name = "assign-access-schedule";
            input.value = value;
            input.checked = this._editAccessScheduleMode === value;
            input.disabled = state !== MANAGE_ACCESS_STATE.EDIT_ACCESS;
            input.addEventListener("change", () => {
              this._editAccessScheduleMode = value;
              this._updateManageAccessDialog();
            });
            label.append(input, labelText);
            schedule.append(label);
          }
          if (this._editAccessScheduleMode === "existing") {
            const select = document.createElement("select");
            select.id = "assign-access-schedule-id";
            select.setAttribute("aria-label", "Existing schedule");
            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Choose a schedule";
            select.append(placeholder);
            for (const available of compatibleSchedules) {
              if (available.name === "Permanent") continue;
              const option = document.createElement("option");
              option.value = available.schedule_id;
              option.textContent = available.name;
              select.append(option);
            }
            select.value = this._editAccessScheduleId;
            select.disabled = state !== MANAGE_ACCESS_STATE.EDIT_ACCESS;
            select.addEventListener("change", () => {
              this._editAccessScheduleId = select.value;
              this._updateManageAccessDialog();
            });
            schedule.append(select);
          }
          if (this._editAccessScheduleMode === "new") {
            schedule.append(this._inlineScheduleFields({
              form: this._editAccessNewSchedule,
              prefix: "assign-access",
              disabled: state !== MANAGE_ACCESS_STATE.EDIT_ACCESS,
              changed: () => this._updateManageAccessDialog(),
              inputChanged: () => this._updateManageAccessDialog(),
            }));
          }
        }
        const note = document.createElement("p");
        note.className = "wizard-help";
        note.textContent = this._accessMetadata.length > 0
          ? "Existing door schedules are preserved. Use Schedule to organize assigned doors into schedule groups."
          : "The selected schedule applies to these new doors. You can organize door subsets later with Schedule.";
        schedule.append(note);
        content.append(schedule);
      }
    }
    const inlineScheduleError = this._editAccessScheduleError();
    const inlinePinError = this._editAccessPin && !/^\d{4,10}$/.test(this._editAccessPin)
      ? "Enter a PIN containing 4 to 10 digits."
      : undefined;
    if (this._editAccessPointsError || context.message || inlineScheduleError || inlinePinError) {
      error.hidden = false;
      error.textContent = context.message ?? this._editAccessPointsError ??
        inlineScheduleError ?? inlinePinError;
    }
    if (state === MANAGE_ACCESS_STATE.VERIFYING_ACCESS) {
      operationStatus.hidden = false;
      operationStatus.textContent = "Removing access…\nWaiting for lock confirmation.";
    } else if (context.status === "needs_attention") {
      operationStatus.hidden = false;
      operationStatus.textContent = "Needs Attention\nThe lock could not confirm this change.";
    } else if (context.status === "out_of_sync") {
      operationStatus.hidden = false;
      operationStatus.textContent = "Out of Sync\nThe lock still reports this access as active.";
    }
    const pending = [
      MANAGE_ACCESS_STATE.SAVING_ACCESS,
      MANAGE_ACCESS_STATE.VERIFYING_ACCESS,
    ].includes(state);
    const retryableError = state === MANAGE_ACCESS_STATE.ERROR && context.retry === true;
    const assignmentReady = this._editAccessSelection.size > 0 && !this._personHasStoredCredential()
      ? this._editAccessAssignmentReady()
      : true;
    this._setManageAccessActionState(cancel, true, !pending);
    this._setManageAccessActionState(
      save,
      state !== MANAGE_ACCESS_STATE.ERROR || retryableError,
      !pending && !this._editAccessPointsLoading &&
        (!this._editAccessPointsError || retryableError) && assignmentReady,
    );
    save.textContent = state === MANAGE_ACCESS_STATE.SAVING_ACCESS
      ? "Saving…"
      : context.errorCode === "pin_incompatible"
        ? "Change PIN"
      : context.status === "out_of_sync"
        ? "Retry removal"
      : context.status === "needs_attention"
        ? "Retry verification"
      : retryableError
        ? "Retry"
        : "Save Door Access";
  }

  _renderManageAccessErrorState(elements) {
    const { context } = elements;
    if (context.source === "edit_access") {
      elements.title.textContent = "Edit Door Access";
      elements.editView.hidden = false;
      this._renderEditAccessView(
        elements.content,
        elements.error,
        elements.operationStatus,
        elements.cancel,
        elements.save,
      );
      return;
    }
    elements.title.textContent = this._personHasStoredCredential() ? "Change PIN" : "Set PIN";
    elements.changePinView.hidden = false;
    if (context.source === "change_pin_refresh") {
      this._renderChangePinSuccess(
        elements.changePinView,
        elements.cancel,
        elements.save,
        elements.done,
        context.message,
      );
      return;
    }
    if (context.source === "capability") {
      const message = document.createElement("p");
      message.id = "change-pin-error";
      message.className = "form-error";
      message.setAttribute("role", "alert");
      message.textContent = context.message;
      elements.changePinView.textContent = "";
      elements.changePinView.append(message);
      this._setManageAccessActionState(elements.cancel, true, true);
      return;
    }
    this._renderChangePinView(
      elements.changePinView,
      elements.cancel,
      elements.save,
      elements.done,
    );
  }

  _handleManageAccessCancel() {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (
      state === MANAGE_ACCESS_STATE.EDIT_ACCESS ||
      (state === MANAGE_ACCESS_STATE.ERROR && context.source === "edit_access")
    ) {
      this._cancelEditAccess();
      return;
    }
    if (
      state === MANAGE_ACCESS_STATE.CHANGE_PIN ||
      state === MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN ||
      (state === MANAGE_ACCESS_STATE.ERROR && context.source === "capability") ||
      (state === MANAGE_ACCESS_STATE.ERROR && context.source === "change_pin")
    ) {
      this._resetChangePin();
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.VIEW);
    }
  }

  _handleManageAccessPrimary() {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (
      state === MANAGE_ACCESS_STATE.ERROR &&
      context.source === "edit_access" &&
      context.errorCode === "pin_incompatible"
    ) {
      this._resetChangePin();
      this._changePinRequirements = "nuki";
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.CHANGE_PIN);
      return;
    }
    if (
      state === MANAGE_ACCESS_STATE.EDIT_ACCESS ||
      (state === MANAGE_ACCESS_STATE.ERROR && context.source === "edit_access" && context.retry)
    ) {
      if (state === MANAGE_ACCESS_STATE.ERROR && context.newRequestOnRetry) {
        this._editAccessRequestId = this._newRevealRequestId();
      }
      void this._saveAccessSelection();
      return;
    }
    if (
      state === MANAGE_ACCESS_STATE.CHANGE_PIN ||
      (state === MANAGE_ACCESS_STATE.ERROR && context.source === "change_pin")
    ) {
      if (this._changePinValid && this._changePinChanged) {
        this._transitionManageAccessState(MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN);
      }
      return;
    }
    if (state === MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN) {
      void this._replacePin();
    }
  }

  _handleManageAccessDone() {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (state === MANAGE_ACCESS_STATE.VIEW) {
      this._closeManageAccessDialog();
      return;
    }
    if ([MANAGE_ACCESS_STATE.SUCCESS, MANAGE_ACCESS_STATE.PARTIAL].includes(state)) {
      this._resetChangePin();
      this._editAccessPointsError = undefined;
      this._editAccessPendingIds = new Set();
      this._editAccessSelection = new Set();
      this._editNfcAccessSelection = new Set();
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.VIEW);
      return;
    }
    if (state === MANAGE_ACCESS_STATE.ERROR && context.source === "change_pin_refresh") {
      this._closeManageAccessDialog();
    }
  }

  _personHasStoredCredential() {
    return this._personCredentialStored ||
      this._accessMetadata.some((metadata) => metadata.credential_stored);
  }

  _manageAccessReplacementCapability() {
    if (!this._manageAccessMetadataCurrent) {
      return "loading";
    }
    if (!this._personHasStoredCredential()) return "missing";
    const targets = this._accessMetadata.filter((metadata) => metadata.credential_stored);
    if (targets.length === 0) return "vault_only";
    let unresolved = false;
    for (const target of targets) {
      const capability = target.credential_capabilities;
      if (
        !capability ||
        capability.status === "unavailable" ||
        !["supported", "unsupported"].includes(capability.status)
      ) {
        unresolved = true;
        continue;
      }
      if (
        capability.status === "unsupported" ||
        capability.replace_pin !== true
      ) {
        return "unsupported";
      }
      if (typeof capability.exact_readback !== "boolean") {
        unresolved = true;
      }
    }
    return unresolved ? "loading" : "supported";
  }

  _openChangePin() {
    if (this._currentManageAccessState() !== MANAGE_ACCESS_STATE.VIEW) {
      return;
    }
    const capability = this._manageAccessReplacementCapability();
    if (capability === "loading") {
      return;
    }
    this._resetChangePin();
    this._editAccessRequestId = this._newRevealRequestId();
    if (capability === "unsupported") {
      this._changePinError = "This device does not support changing the PIN in HomePASS.";
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
        source: "capability",
        message: this._changePinError,
      });
      return;
    }
    this._transitionManageAccessState(MANAGE_ACCESS_STATE.CHANGE_PIN);
  }

  _renderChangePinView(content, cancel, replace, done) {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    const pending = state === MANAGE_ACCESS_STATE.REPLACING_PIN;
    const confirming = state === MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN;
    const editing = state === MANAGE_ACCESS_STATE.CHANGE_PIN ||
      (state === MANAGE_ACCESS_STATE.ERROR && context.source === "change_pin");
    content.textContent = "";
    if (confirming) {
      const heading = document.createElement("h3");
      heading.textContent = this._personHasStoredCredential() ? "Replace PIN?" : "Set PIN?";
      const body = document.createElement("p");
      body.textContent = this._personHasStoredCredential()
        ? "The existing PIN will stop working once the new PIN has been successfully updated."
        : "This PIN will be stored securely for future door assignments.";
      content.append(heading, body);
    } else if (editing || pending) {
      const body = document.createElement("p");
      body.textContent = this._changePinRequirements === "nuki"
        ? "Use six digits from 1–9. Nuki does not accept 0, or a PIN beginning with 12. HomePASS will finish assigning the selected door after the PIN is updated."
        : this._personHasStoredCredential()
        ? "The existing PIN will be replaced after the new PIN has been successfully updated."
        : "Set a PIN now so this user can be assigned door access.";
      const label = document.createElement("label");
      label.setAttribute("for", "replacement-pin");
      label.textContent = "New PIN";
      const input = document.createElement("input");
      input.id = "replacement-pin";
      input.type = "password";
      input.inputMode = "numeric";
      input.autocomplete = "new-password";
      input.value = this._changePinValue;
      input.disabled = pending;
      input.addEventListener("input", () => {
        this._changePinValue = input.value;
        void this._validateReplacementPin();
      });
      const generate = document.createElement("ha-button");
      generate.id = "generate-replacement-pin";
      generate.textContent = "Generate PIN";
      generate.disabled = pending;
      generate.addEventListener("click", () => {
        if (generate.disabled) return;
        this._changePinValue = this._generateSecurePin();
        input.value = this._changePinValue;
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
        void this._validateReplacementPin({ immediate: true });
      });
      content.append(body, label, input, generate);
      if (pending) {
        const progress = document.createElement("div");
        progress.className = "access-update-status";
        progress.setAttribute("role", "status");
        progress.textContent = this._accessMetadata.length > 0
          ? "Replacing PIN...\nProgramming new PIN ✓\nConfirming new PIN ⟳\nUpdating HomePASS ○"
          : "Saving PIN...\nUpdating secure storage ⟳";
        content.append(progress);
      }
    }
    const error = document.createElement("p");
    error.id = "change-pin-error";
    error.className = "form-error";
    error.setAttribute("role", "alert");
    const message = context.message ?? this._changePinError;
    error.hidden = !message;
    error.textContent = message ?? "";
    content.append(error);
    this._setManageAccessActionState(cancel, true, !pending);
    this._setManageAccessActionState(replace, true, !pending && (
      confirming ||
      (editing && this._changePinValid && this._changePinChanged)
    ));
    replace.textContent = pending
      ? this._personHasStoredCredential() ? "Replacing…" : "Saving…"
      : this._personHasStoredCredential() ? "Replace PIN" : "Save PIN";
    this._setManageAccessActionState(done, false, false);
  }

  _renderChangePinSuccess(content, cancel, replace, done, refreshError = undefined) {
    content.textContent = "";
    const heading = document.createElement("p");
    heading.className = "success-title";
    heading.textContent = this._personHasStoredCredential()
      ? "PIN updated successfully."
      : "PIN saved successfully.";
    const body = document.createElement("p");
    body.textContent = this._accessMetadata.length > 0
      ? "The new PIN has been securely stored in HomePASS and programmed on the access device."
      : "The new PIN has been securely stored in HomePASS.";
    content.append(heading, body);
    if (refreshError) {
      const error = document.createElement("p");
      error.id = "change-pin-error";
      error.className = "form-error";
      error.setAttribute("role", "alert");
      error.textContent = refreshError;
      content.append(error);
    }
    this._setManageAccessActionState(cancel, false, false);
    this._setManageAccessActionState(replace, false, false);
    this._setManageAccessActionState(done, true, true);
  }

  async _validateReplacementPin({ immediate = false } = {}) {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (
      state !== MANAGE_ACCESS_STATE.CHANGE_PIN &&
      !(state === MANAGE_ACCESS_STATE.ERROR && context.source === "change_pin")
    ) {
      return;
    }
    const generation = ++this._changePinValidationGeneration;
    this._clearReplacementValidationTimer();
    this._changePinValid = this._changePinRequirements === "nuki"
      ? /^[1-9]{6}$/.test(this._changePinValue) && !this._changePinValue.startsWith("12")
      : /^\d{4,10}$/.test(this._changePinValue);
    this._changePinChanged = false;
    this._changePinError = this._changePinValid
      ? undefined
      : this._changePinRequirements === "nuki"
        ? "Enter six digits using 1–9, and do not begin with 12."
        : "Enter a PIN containing 4 to 10 digits.";
    this._updateChangePinValidationControls();
    if (!this._changePinValid || !this._selectedPerson) return;
    if (!this._personHasStoredCredential()) {
      this._changePinChanged = true;
      this._changePinError = undefined;
      this._updateChangePinValidationControls();
      return;
    }
    if (!immediate) {
      this._changePinValidationTimer = window.setTimeout(() => {
        this._changePinValidationTimer = undefined;
        void this._compareReplacementPin(generation, this._changePinValue);
      }, REPLACEMENT_VALIDATION_DELAY);
      return;
    }
    await this._compareReplacementPin(generation, this._changePinValue);
  }

  async _compareReplacementPin(generation, pin) {
    const ownership = this._captureManageAccessRequest(
      "change_pin_validation",
      [MANAGE_ACCESS_STATE.CHANGE_PIN, MANAGE_ACCESS_STATE.ERROR],
    );
    if (!ownership) {
      return;
    }
    try {
      const result = await this._hass.callWS({
        type: VALIDATE_REPLACEMENT_PIN_COMMAND,
        person_id: ownership.personId,
        pin,
      });
      if (
        generation !== this._changePinValidationGeneration ||
        !this._manageAccessOwnsRequest(ownership)
      ) return;
      this._changePinChanged = result?.changed === true;
      this._changePinError = this._changePinChanged
        ? undefined
        : "Choose a PIN different from the current PIN.";
    } catch (_error) {
      if (
        generation !== this._changePinValidationGeneration ||
        !this._manageAccessOwnsRequest(ownership)
      ) return;
      this._changePinError = "Unable to validate the PIN right now.";
    }
    this._updateChangePinValidationControls();
  }

  _updateChangePinValidationControls() {
    const state = this._currentManageAccessState();
    const context = this._manageAccessSession?.context ?? {};
    if (
      state !== MANAGE_ACCESS_STATE.CHANGE_PIN &&
      !(state === MANAGE_ACCESS_STATE.ERROR && context.source === "change_pin")
    ) {
      return;
    }
    if (state === MANAGE_ACCESS_STATE.ERROR) {
      this._manageAccessSession.context = {
        ...context,
        message: this._changePinError,
      };
    }
    const replace = this.shadowRoot.querySelector("#save-edit-access");
    const error = this.shadowRoot.querySelector("#change-pin-error");
    if (replace) {
      replace.disabled = !(this._changePinValid && this._changePinChanged);
      replace.tabIndex = replace.disabled ? -1 : 0;
    }
    if (error) {
      error.hidden = !this._changePinError;
      error.textContent = this._changePinError ?? "";
    }
  }

  async _replacePin() {
    if (
      this._currentManageAccessState() !== MANAGE_ACCESS_STATE.CONFIRM_CHANGE_PIN ||
      !this._selectedPerson ||
      this._manageAccessSession?.personId !== this._selectedPerson.person_id
    ) return;
    const personId = this._selectedPerson.person_id;
    const assigningFirstPin = !this._personHasStoredCredential();
    this._changePinError = undefined;
    this._transitionManageAccessState(MANAGE_ACCESS_STATE.REPLACING_PIN);
    const ownership = this._captureManageAccessRequest(
      "change_pin_replace",
      MANAGE_ACCESS_STATE.REPLACING_PIN,
    );
    try {
      const result = assigningFirstPin
        ? await this._hass.callWS({
            type: "call_service",
            domain: DOMAIN,
            service: ASSIGN_USER_ACCESS_ACTION,
            service_data: {
              request_id: this._editAccessRequestId,
              person_id: personId,
              access_point_ids: [],
              schedule_id: this._selectedPerson.schedule_id,
              pin: this._changePinValue,
            },
            return_response: true,
          })
        : await this._hass.callWS({
            type: REPLACE_PIN_COMMAND,
            person_id: personId,
            pin: this._changePinValue,
            retry: this._changePinRetry,
          });
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      if (assigningFirstPin) {
        if (result.response?.status !== "completed") throw new Error("assignment_failed");
      } else if (result?.completed !== true) {
        throw new Error("replacement_failed");
      }
      this._changePinValue = "";
      const resumeDoorAccess = this._changePinRequirements === "nuki" &&
        this._editAccessSelection.size > 0;
      this._manageAccessMetadataCurrent = false;
      this._manageAccessRefreshError =
        "HomePASS is refreshing access details before PIN Reveal is available.";
      this._clearCredentialReveal("credential_replaced");
      this._clearRevealCooldown();
      try {
        await this._refreshAccessState(personId, ownership);
      } catch (_error) {
        if (!this._manageAccessOwnsRequest(ownership)) {
          return;
        }
        this._manageAccessRefreshError =
          "HomePASS could not refresh access details. Close and reopen Manage Access to try again.";
        this._changePinError = this._manageAccessRefreshError;
        this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
          source: "change_pin_refresh",
          message: this._changePinError,
        });
        return;
      }
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      this._refreshPersonDetailsInPlace();
      if (resumeDoorAccess) {
        this._resetChangePin();
        this._transitionManageAccessState(MANAGE_ACCESS_STATE.EDIT_ACCESS);
        queueMicrotask(() => void this._saveAccessSelection());
        return;
      }
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.VIEW, {
        notice: assigningFirstPin ? "pin_assigned" : "pin_replaced",
      });
    } catch (error) {
      if (!this._manageAccessOwnsRequest(ownership)) {
        return;
      }
      this._changePinError = this._friendlyReplacementError(error);
      const code = String(error?.code ?? error?.message ?? "").toLowerCase();
      this._changePinRetry = code.includes("pending");
      this._transitionManageAccessState(MANAGE_ACCESS_STATE.ERROR, {
        source: "change_pin",
        message: this._changePinError,
        retry: true,
      });
    }
  }

  _friendlyReplacementError(error) {
    const code = String(error?.code ?? error?.message ?? "").toLowerCase();
    if (code.includes("validation")) return "Enter a different valid PIN.";
    if (code.includes("pending")) {
      return "The saved PIN has not been replaced. Wait a few seconds and try again.";
    }
    if (code.includes("unsupported")) {
      return "This device does not support changing the PIN in HomePASS.";
    }
    if (code.includes("unavailable")) return "Unable to replace the PIN right now.";
    if (code.includes("concurrent")) {
      return "This access was changed somewhere else. Reopen it and try again.";
    }
    return "Unable to replace the PIN right now.";
  }

  _setManageAccessActionState(control, visible, enabled) {
    control.hidden = !visible;
    control.disabled = !enabled;
    control.tabIndex = visible && enabled ? 0 : -1;
    control.inert = !visible;
    control.setAttribute("aria-hidden", String(!visible));
    control.setAttribute("style", visible ? "" : "display: none;");
  }

  _createCredentialRevealController(
    credential = undefined,
    revealButton = undefined,
    revealIcon = undefined,
    revealProgress = undefined,
    revealStatus = undefined,
  ) {
    let plaintext;
    let timer;
    let generation = 0;
    let pending = false;
    let blocked = false;
    let elements;

    const updateControl = () => {
      if (!elements) {
        return;
      }
      const {
        credential: mountedCredential,
        revealButton: mountedButton,
        revealIcon: mountedIcon,
        revealProgress: mountedProgress,
        revealStatus: mountedStatus,
        maskedText,
      } = elements;
      const revealed = plaintext !== undefined;
      mountedCredential.textContent = revealed ? plaintext : maskedText;
      mountedButton.disabled = pending || blocked;
      mountedButton.setAttribute("aria-busy", String(pending));
      const owner = mountedButton.dataset?.pinOwner;
      const ownerSuffix = owner ? ` for ${owner}` : "";
      mountedButton.setAttribute(
        "aria-label",
        pending
          ? `Retrieving PIN${ownerSuffix}`
          : revealed
            ? `Hide PIN${ownerSuffix}`
            : `Reveal PIN${ownerSuffix}`,
      );
      mountedIcon.setAttribute(
        "icon",
        pending ? "mdi:loading" : revealed ? "mdi:eye-off" : "mdi:eye",
      );
      if (mountedProgress) {
        mountedProgress.hidden = !pending;
        mountedProgress.active = pending;
        mountedProgress.indeterminate = pending;
      }
      if (mountedStatus) {
        mountedStatus.hidden = !pending;
      }
    };

    const clear = () => {
      generation += 1;
      if (timer !== undefined) {
        window.clearTimeout(timer);
        timer = undefined;
      }
      plaintext = undefined;
      pending = false;
      updateControl();
    };

    const mount = (
      mountedCredential,
      mountedButton,
      mountedIcon,
      mountedProgress = undefined,
      mountedStatus = undefined,
      maskedText = "••••••",
    ) => {
      if (elements && elements.credential !== mountedCredential) {
        elements.credential.textContent = elements.maskedText;
        elements.revealButton.disabled = true;
        elements.revealButton.setAttribute("aria-busy", "false");
        elements.revealButton.setAttribute("aria-label", "Reveal PIN");
        elements.revealIcon.setAttribute("icon", "mdi:eye");
        if (elements.revealProgress) {
          elements.revealProgress.hidden = true;
          elements.revealProgress.active = false;
          elements.revealProgress.indeterminate = false;
        }
        if (elements.revealStatus) {
          elements.revealStatus.hidden = true;
        }
      }
      elements = {
        credential: mountedCredential,
        revealButton: mountedButton,
        revealIcon: mountedIcon,
        revealProgress: mountedProgress,
        revealStatus: mountedStatus,
        maskedText,
      };
      updateControl();
    };

    if (credential && revealButton && revealIcon) {
      mount(credential, revealButton, revealIcon, revealProgress, revealStatus);
    }

    return {
      mount,
      beginRequest: () => {
        generation += 1;
        pending = true;
        updateControl();
        return generation;
      },
      clear,
      finishRequest: (requestGeneration) => {
        if (generation === requestGeneration) {
          pending = false;
          updateControl();
        }
      },
      isCurrent: (requestGeneration) => generation === requestGeneration,
      isPending: () => pending,
      isBlocked: () => blocked,
      setBlocked: (value) => {
        blocked = value;
        updateControl();
      },
      isRevealed: () => plaintext !== undefined,
      show: (value, requestGeneration) => {
        if (generation !== requestGeneration || typeof value !== "string") {
          return false;
        }
        plaintext = value;
        pending = false;
        updateControl();
        timer = window.setTimeout(clear, REVEAL_TIMEOUT);
        return true;
      },
    };
  }

  _currentRevealController() {
    return this._manageAccessSession?.revealController;
  }

  _beginManageAccessSession(personId, accessPointId) {
    this._clearRevealCooldown();
    this._manageAccessSessionSequence += 1;
    this._manageAccessSession = {
      id: this._manageAccessSessionSequence,
      personId,
      accessPointId,
      state: MANAGE_ACCESS_STATE.VIEW,
      stateEntryId: 1,
      context: {},
      requestSequences: Object.create(null),
      revealController: this._createCredentialRevealController(),
      revealCooldownMessage: undefined,
    };
    return this._manageAccessSession;
  }

  _currentManageAccessSession(personId, accessPointId) {
    if (!this._manageAccessDialogOpen) {
      return undefined;
    }
    if (
      !this._manageAccessSession ||
      this._manageAccessSession.personId !== personId ||
      this._manageAccessSession.accessPointId !== accessPointId
    ) {
      const discardReason = !this._manageAccessSession
        ? "session_missing"
        : this._manageAccessSession.personId !== personId
          ? "person_changed"
          : "access_point_changed";
      this._clearCredentialReveal(discardReason);
      return this._beginManageAccessSession(personId, accessPointId);
    }
    return this._manageAccessSession;
  }

  _revealRequestDiscardReason(ownership) {
    if (!this._manageAccessDialogOpen) {
      return "dialog_closed";
    }
    if (ownership.cancelledReason) {
      return this._normalizeRevealDiscardReason(ownership.cancelledReason);
    }
    if (!this._manageAccessSession) {
      return "session_missing";
    }
    if (this._manageAccessSession.id !== ownership.sessionId) {
      return "session_changed";
    }
    if (
      this._manageAccessSession.state !== ownership.state ||
      this._manageAccessSession.stateEntryId !== ownership.stateEntryId
    ) {
      return "state_changed";
    }
    if (
      this._selectedPerson?.person_id !== ownership.personId ||
      this._manageAccessSession.personId !== ownership.personId
    ) {
      return "person_changed";
    }
    const targetAvailable = ownership.accessPointId === undefined
      ? this._personCredentialStored
      : this._accessMetadata.some(
          (record) =>
            record.access_point_id === ownership.accessPointId && record.credential_stored,
        );
    if (!targetAvailable) {
      return "target_missing";
    }
    if (this._manageAccessSession.accessPointId !== ownership.accessPointId) {
      return "access_point_changed";
    }
    if (
      this._manageAccessSession.requestSequences.reveal !== ownership.sequence ||
      this._activeRevealRequest !== ownership
    ) {
      return "request_superseded";
    }
    return undefined;
  }

  _normalizeRevealDiscardReason(reason) {
    return REVEAL_DISCARD_REASONS.has(reason) ? reason : "unknown";
  }

  _toggleCredentialReveal() {
    if (this._currentManageAccessState() !== MANAGE_ACCESS_STATE.VIEW) {
      return;
    }
    const controller = this._currentRevealController();
    if (controller?.isRevealed()) {
      this._clearCredentialReveal("eye_off_selected");
      return;
    }
    if (
      !controller ||
      controller.isPending() ||
      controller.isBlocked()
    ) {
      return;
    }
    void this._requestCredentialReveal();
  }

  _handleManageAccessDialogClick(event) {
    const eventPath = typeof event.composedPath === "function"
      ? event.composedPath()
      : [event.target];
    const toggle = eventPath.find((element) => element?.id === "toggle-pin-visibility") ??
      event.target?.closest?.("#toggle-pin-visibility");
    if (!toggle) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    this._toggleCredentialReveal();
  }

  _clearCredentialReveal(reason = "state_reset") {
    const discardReason = this._normalizeRevealDiscardReason(reason);
    if (this._activeRevealRequest) {
      this._activeRevealRequest.cancelledReason = discardReason;
    }
    if (this._activeRevealTrace) {
      this._traceCredentialReveal(
        this._activeRevealTrace.requestId,
        "frontend_context_invalidated",
        this._activeRevealTrace.startedAt,
        {
          ...this._activeRevealTrace.context,
          discard_reason: discardReason,
        },
      );
    }
    this._currentRevealController()?.clear();
  }

  _clearRevealCooldown() {
    if (this._revealCooldownTimer !== undefined) {
      window.clearTimeout(this._revealCooldownTimer);
      this._revealCooldownTimer = undefined;
    }
    if (this._manageAccessSession) {
      this._manageAccessSession.revealCooldownMessage = undefined;
    }
    this._currentRevealController()?.setBlocked(false);
    const errorElement = this.shadowRoot?.querySelector?.("#reveal-pin-error");
    if (errorElement) {
      errorElement.hidden = true;
      errorElement.textContent = "";
    }
  }

  _startRevealCooldown(error, errorElement) {
    const message = String(error?.message ?? "");
    const match = message.match(/try again in (\d+) seconds?/i);
    const retryAfter = match ? Number(match[1]) : 60;
    this._clearRevealCooldown();
    const sessionId = this._manageAccessSession?.id;
    if (this._manageAccessSession) {
      this._manageAccessSession.revealCooldownMessage = REVEAL_COOLDOWN_MESSAGE;
    }
    this._currentRevealController()?.setBlocked(true);
    errorElement.hidden = false;
    errorElement.textContent = REVEAL_COOLDOWN_MESSAGE;
    this._revealCooldownTimer = window.setTimeout(() => {
      this._revealCooldownTimer = undefined;
      if (this._manageAccessSession?.id !== sessionId) {
        return;
      }
      this._manageAccessSession.revealCooldownMessage = undefined;
      this._currentRevealController()?.setBlocked(false);
      if (this._manageAccessDialogOpen) {
        const currentError = this.shadowRoot?.querySelector?.("#reveal-pin-error");
        if (currentError?.textContent === REVEAL_COOLDOWN_MESSAGE) {
          currentError.hidden = true;
          currentError.textContent = "";
        }
      }
    }, retryAfter * 1000);
  }

  async _requestCredentialReveal() {
    if (this._currentManageAccessState() !== MANAGE_ACCESS_STATE.VIEW) {
      return;
    }
    const metadata = this._accessMetadata.find((record) => record.credential_stored);
    const errorElement = this.shadowRoot.querySelector("#reveal-pin-error");
    if (!this._selectedPerson || !this._personHasStoredCredential()) {
      return;
    }
    if (!this._manageAccessMetadataCurrent) {
      this._currentRevealController()?.setBlocked(true);
      errorElement.hidden = false;
      errorElement.textContent = this._manageAccessRefreshError ??
        "HomePASS could not retrieve this PIN. Close and reopen Manage Access to try again.";
      return;
    }
    const personId = this._selectedPerson.person_id;
    const accessPointId = metadata?.access_point_id;
    const previousSession = this._manageAccessSession;
    const session = this._currentManageAccessSession(personId, accessPointId);
    if (!session) {
      return;
    }
    if (session !== previousSession) {
      this._updateManageAccessDialog();
    }
    const controller = this._currentRevealController();
    if (!controller || controller.isPending() || controller.isBlocked()) {
      return;
    }
    const stateOwnership = this._captureManageAccessRequest(
      "reveal",
      MANAGE_ACCESS_STATE.VIEW,
    );
    if (!stateOwnership) {
      return;
    }
    const requestGeneration = controller.beginRequest();
    const ownership = {
      ...stateOwnership,
      controller,
      generation: requestGeneration,
      cancelledReason: undefined,
    };
    this._activeRevealRequest = ownership;
    const requestId = this._newRevealRequestId();
    const traceStartedAt = this._revealTraceNow();
    const traceContext = { person_id: personId };
    if (accessPointId !== undefined) traceContext.access_point_id = accessPointId;
    if (metadata?.credential_revision !== undefined) {
      traceContext.credential_revision = metadata.credential_revision;
    }
    this._activeRevealTrace = { requestId, startedAt: traceStartedAt, context: traceContext };
    errorElement.hidden = true;
    errorElement.textContent = "";
    try {
      const request = {
        type: REVEAL_PIN_COMMAND,
        person_id: personId,
        panel_asset_version: PANEL_ASSET_VERSION,
      };
      if (accessPointId !== undefined) request.access_point_id = accessPointId;
      if (requestId) {
        request.request_id = requestId;
      }
      const response = await this._callRevealWithTimeout(
        request,
        requestId,
        traceStartedAt,
        traceContext,
      );
      const discardReason = this._revealRequestDiscardReason(ownership);
      if (discardReason) {
        this._traceCredentialReveal(
          requestId,
          "frontend_response_discarded",
          traceStartedAt,
          {
            ...traceContext,
            discard_reason: discardReason,
          },
        );
        if (response && typeof response === "object") {
          response.pin = undefined;
        }
        return;
      }
      const currentController = this._currentRevealController();
      if (!currentController) {
        this._traceCredentialReveal(
          requestId,
          "frontend_response_discarded",
          traceStartedAt,
          {
            ...traceContext,
            discard_reason: "controller_detached",
          },
        );
        if (response && typeof response === "object") {
          response.pin = undefined;
        }
        return;
      }
      const displayed = currentController.show(response?.pin, ownership.generation);
      if (response && typeof response === "object") {
        response.pin = undefined;
      }
      if (!displayed) {
        throw new Error("invalid_reveal_response");
      }
    } catch (error) {
      const discardReason = this._revealRequestDiscardReason(ownership);
      if (discardReason) {
        const stillCurrentContext =
          this._manageAccessDialogOpen &&
          this._manageAccessSession?.id === ownership.sessionId &&
          this._manageAccessSession?.state === ownership.state &&
          this._manageAccessSession?.stateEntryId === ownership.stateEntryId &&
          this._selectedPerson?.person_id === ownership.personId &&
          this._manageAccessSession?.requestSequences.reveal === ownership.sequence &&
          this._activeRevealRequest === ownership;
        if (
          stillCurrentContext &&
          ![
            "dialog_closed",
            "session_changed",
            "session_missing",
            "person_changed",
            "access_point_changed",
            "target_missing",
            "request_superseded",
            "eye_off_selected",
            "state_changed",
          ].includes(discardReason)
        ) {
          const currentErrorElement = this.shadowRoot.querySelector("#reveal-pin-error") ??
            errorElement;
          currentErrorElement.hidden = false;
          currentErrorElement.textContent =
            "HomePASS could not retrieve this PIN. Please reopen Manage Access and try again.";
        }
        return;
      }
      const currentErrorElement = this.shadowRoot.querySelector("#reveal-pin-error") ??
        errorElement;
      const code = String(error?.code ?? error?.message ?? "").toLowerCase();
      if (code.includes("rate_limited")) {
        this._startRevealCooldown(error, currentErrorElement);
      } else {
        currentErrorElement.hidden = false;
        currentErrorElement.textContent = this._friendlyRevealError(error);
      }
    } finally {
      if (ownership.controller?.isCurrent(ownership.generation)) {
        ownership.controller.finishRequest(ownership.generation);
      }
      if (this._activeRevealRequest === ownership) {
        this._activeRevealRequest = undefined;
      }
      if (this._activeRevealTrace?.requestId === requestId) {
        this._activeRevealTrace = undefined;
      }
    }
  }

  _newRevealRequestId() {
    try {
      const cryptoApi = globalThis.crypto;
      if (typeof cryptoApi?.randomUUID === "function") {
        return cryptoApi.randomUUID();
      }
      if (typeof cryptoApi?.getRandomValues === "function") {
        const bytes = new Uint8Array(16);
        cryptoApi.getRandomValues(bytes);
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;
        const hex = [...bytes]
          .map((value) => value.toString(16).padStart(2, "0"))
          .join("");
        return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-` +
          `${hex.slice(16, 20)}-${hex.slice(20)}`;
      }
    } catch (_error) {
      // Request correlation must never interfere with credential retrieval.
    }
    this._revealCorrelationSequence += 1;
    const tail = String(this._revealCorrelationSequence).padStart(12, "0").slice(-12);
    return `00000000-0000-4000-8000-${tail}`;
  }

  _revealTraceNow() {
    try {
      return globalThis.performance?.now?.() ?? Date.now();
    } catch (_error) {
      return 0;
    }
  }

  _traceCredentialReveal(requestId, stage, startedAt, context = {}) {
    try {
      const diagnostic = {
        request_id: requestId,
        stage,
        elapsed_ms: Math.round((this._revealTraceNow() - startedAt) * 1000) / 1000,
        panel_asset_version: PANEL_ASSET_VERSION,
      };
      if (typeof context.person_id === "string") {
        diagnostic.person_id = context.person_id;
      }
      if (typeof context.access_point_id === "string") {
        diagnostic.access_point_id = context.access_point_id;
      }
      if (Number.isInteger(context.credential_revision)) {
        diagnostic.credential_revision = context.credential_revision;
      }
      if (typeof context.error_code === "string") {
        diagnostic.error_code = context.error_code;
      }
      if (typeof context.error_message === "string") {
        diagnostic.error_message = context.error_message;
      }
      if (typeof context.discard_reason === "string") {
        diagnostic.discard_reason = context.discard_reason;
      }
      globalThis.console?.info?.("HomePASS PIN Reveal", diagnostic);
    } catch (_error) {
      // Diagnostics are deliberately best-effort and contain no credential material.
    }
  }

  async _callRevealWithTimeout(request, requestId, startedAt, traceContext) {
    let finished = false;
    let timeout;
    this._traceCredentialReveal(
      requestId,
      "frontend_request_sent",
      startedAt,
      traceContext,
    );
    let response;
    try {
      response = this._hass.callWS(request).then(
        (result) => {
          this._traceCredentialReveal(
            requestId,
            "frontend_promise_resolved",
            startedAt,
            traceContext,
          );
          if (finished && result && typeof result === "object") {
            this._traceCredentialReveal(
              requestId,
              "frontend_late_response_discarded",
              startedAt,
              { ...traceContext, discard_reason: "request_already_settled" },
            );
            result.pin = undefined;
          }
          return result;
        },
        (error) => {
          const diagnostic = this._revealErrorDiagnostic(error);
          this._traceCredentialReveal(
            requestId,
            "frontend_promise_rejected",
            startedAt,
            { ...traceContext, ...diagnostic },
          );
          throw error;
        },
      );
    } catch (error) {
      const diagnostic = this._revealErrorDiagnostic(error);
      this._traceCredentialReveal(
        requestId,
        "frontend_promise_rejected",
        startedAt,
        { ...traceContext, ...diagnostic },
      );
      throw error;
    }
    const deadline = new Promise((_, reject) => {
      timeout = window.setTimeout(() => {
        const timeoutError = Object.assign(new Error("Reveal request timed out"), {
          code: "reveal_timeout",
        });
        this._traceCredentialReveal(
          requestId,
          "frontend_timeout_guard_fired",
          startedAt,
          { ...traceContext, ...this._revealErrorDiagnostic(timeoutError) },
        );
        reject(timeoutError);
      }, REVEAL_REQUEST_TIMEOUT);
    });
    try {
      return await Promise.race([response, deadline]);
    } finally {
      finished = true;
      window.clearTimeout(timeout);
    }
  }

  _revealErrorDiagnostic(error) {
    const rawCode = String(error?.code ?? "").toLowerCase();
    const safeCodes = new Set([
      "admin_required",
      "unauthorized",
      "rate_limited",
      "credential_unavailable",
      "vault_unavailable",
      "reveal_failed",
      "reveal_timeout",
      "invalid_format",
      "unknown_command",
      "id_reuse",
      "connection_lost",
    ]);
    const errorCode = safeCodes.has(rawCode) ? rawCode : "unknown";
    return {
      error_code: errorCode,
      error_message: this._friendlyRevealError(error),
    };
  }

  _friendlyRevealError(error, surface = "manage-access") {
    const code = String(error?.code ?? error?.message ?? "").toLowerCase();
    if (code.includes("admin_required") || code.includes("unauthorized")) {
      return "Administrator access required";
    }
    if (code.includes("rate_limited")) {
      return "PIN reveal is temporarily limited. Please wait a moment and try again.";
    }
    if (code.includes("credential_unavailable")) {
      return "Credential unavailable";
    }
    if (code.includes("vault_unavailable")) {
      return "Vault unavailable";
    }
    if (code.includes("reveal_timeout")) {
      return "PIN retrieval took too long. Please try again.";
    }
    return surface === "users-card"
      ? "HomePASS could not retrieve this PIN. Try again."
      : "HomePASS could not retrieve this PIN. Please reopen Manage Access and try again.";
  }

  _mountGiveAccessDialog() {
    if (this.shadowRoot.querySelector("#give-access-dialog")) {
      this._updateGiveAccessDialog();
      return;
    }
    const template = document.createElement("template");
    template.innerHTML = this._giveAccessDialogTemplate();
    this.shadowRoot.append(template.content.cloneNode(true));
    this._configureGiveAccessDialog();
  }

  _configureGiveAccessDialog() {
    const dialog = this.shadowRoot.querySelector("#give-access-dialog");
    const back = this.shadowRoot.querySelector("#back-give-access");
    const cancel = this.shadowRoot.querySelector("#cancel-give-access");
    const next = this.shadowRoot.querySelector("#next-give-access");

    this._updateGiveAccessDialog();
    back.addEventListener("click", () => this._backGiveAccessWizard());
    cancel.addEventListener("click", () => this._closeGiveAccessWizard());
    next.addEventListener("click", () => this._continueGiveAccessWizard());
    dialog.addEventListener("closed", () => this._closeGiveAccessWizard());
  }

  _updateGiveAccessDialog() {
    const content = this.shadowRoot.querySelector("#give-access-content");
    const back = this.shadowRoot.querySelector("#back-give-access");
    const cancel = this.shadowRoot.querySelector("#cancel-give-access");
    const next = this.shadowRoot.querySelector("#next-give-access");
    if (!content || !back || !cancel || !next) {
      return;
    }

    content.textContent = "";
    back.hidden = this._giveAccessStep !== "pin";
    back.disabled = back.hidden || this._provisioning;
    back.setAttribute("aria-hidden", String(back.hidden));
    cancel.hidden = this._giveAccessStep === "result";
    cancel.disabled = cancel.hidden || this._provisioning;
    cancel.setAttribute("aria-hidden", String(cancel.hidden));
    cancel.textContent = "Cancel";
    next.hidden = false;

    if (this._giveAccessStep === "where") {
      this._renderAccessPointStep(content, next);
    } else if (this._giveAccessStep === "pin") {
      this._renderPinStep(content, next);
    } else {
      this._renderGiveAccessResult(content, next);
    }
  }

  _renderAccessPointStep(content, next) {
    const step = document.createElement("p");
    step.className = "wizard-step";
    step.textContent = "Step 1";
    const question = document.createElement("p");
    question.className = "wizard-question";
    question.textContent = "Where would you like to give access?";
    const options = document.createElement("div");
    options.className = "access-point-options";
    const error = document.createElement("p");
    error.className = "form-error";
    error.setAttribute("role", "alert");
    content.append(step, question, options, error);

    if (this._accessPointsLoading) {
      options.textContent = "Loading access points…";
    } else if (this._accessPointsError) {
      error.textContent = this._accessPointsError;
    } else if (this._accessPoints.length === 0) {
      options.textContent = "No access points are available.";
    } else {
      const group = document.createElement("div");
      group.setAttribute("role", "radiogroup");
      group.setAttribute("aria-label", "Available access points");
      for (const accessPoint of this._accessPoints) {
        if (this._hasAccessTo(accessPoint.id)) {
          const assigned = document.createElement("div");
          assigned.className = "assigned-access-point";
          const name = document.createElement("span");
          name.textContent = `✓ ${accessPoint.display_name}`;
          const status = document.createElement("span");
          status.className = "assigned-access-point-status";
          status.textContent = "Already has access";
          assigned.append(name, status);
          group.append(assigned);
          continue;
        }
        const field = document.createElement("ha-formfield");
        field.className = "access-point-option";
        field.setAttribute("label", accessPoint.display_name);
        const option = document.createElement("input");
        option.type = "radio";
        option.name = "homepass-access-point";
        option.value = accessPoint.id;
        option.checked = accessPoint.id === this._selectedAccessPoint?.id;
        option.setAttribute("aria-label", accessPoint.display_name);
        option.addEventListener("change", () => {
          if (!option.checked) {
            return;
          }
          this._selectedAccessPoint = accessPoint;
          next.disabled = false;
        });
        field.append(option);
        group.append(field);
      }
      options.append(group);
      if (this._accessPoints.every((accessPoint) => this._hasAccessTo(accessPoint.id))) {
        error.textContent =
          "This user already has access to every available door.";
      }
    }

    next.disabled =
      this._accessPointsLoading ||
      Boolean(this._accessPointsError) ||
      !this._selectedAccessPoint;
    next.textContent = "Next";
  }

  _renderPinStep(content, next) {
    const step = document.createElement("p");
    step.className = "wizard-step";
    step.textContent = "Step 2";
    const question = document.createElement("p");
    question.className = "wizard-question";
    question.textContent = "How would you like to create the PIN?";
    const choices = document.createElement("div");
    choices.setAttribute("role", "radiogroup");
    choices.setAttribute("aria-label", "PIN creation method");
    for (const [value, label] of [
      ["generated", "Generate a PIN for me"],
      ["manual", "I'll choose my own PIN"],
    ]) {
      const field = document.createElement("ha-formfield");
      field.setAttribute("label", label);
      const option = document.createElement("input");
      option.type = "radio";
      option.name = "homepass-pin-mode";
      option.value = value;
      option.checked = this._pinMode === value;
      option.addEventListener("change", () => {
        if (!option.checked) {
          return;
        }
        this._pinMode = value;
        this._pin = value === "generated" ? this._generateSecurePin() : "";
        this._pinValidationError = undefined;
        this._provisionError = undefined;
        this._updateGiveAccessDialog();
      });
      field.append(option);
      choices.append(field);
    }
    content.append(step, question, choices);

    if (this._pinMode === "generated") {
      const pin = document.createElement("div");
      pin.className = "pin-display";
      pin.setAttribute("aria-label", "Generated PIN");
      pin.textContent = this._pin ?? "";
      content.append(pin);
    } else {
      const input = document.createElement("input");
      input.className = "pin-input";
      input.type = "text";
      input.inputMode = "numeric";
      input.autocomplete = "off";
      input.maxLength = 10;
      input.placeholder = "Enter 4 to 10 digits";
      input.setAttribute("aria-label", "PIN");
      input.value = this._pin ?? "";
      input.addEventListener("input", () => {
        this._pin = input.value;
        this._pinValidationError = this._pinIsValid()
          ? undefined
          : "Enter a PIN containing 4 to 10 digits.";
        next.disabled = !this._pinIsValid() || this._provisioning;
      });
      content.append(input);
    }

    const error = document.createElement("p");
    error.className = "form-error";
    error.setAttribute("role", "alert");
    error.textContent = this._pinValidationError ?? this._provisionError ?? "";
    content.append(error);
    if (this._provisioning) {
      const loading = document.createElement("div");
      loading.className = "provisioning-status";
      loading.setAttribute("role", "status");
      const progress = document.createElement("ha-circular-progress");
      progress.setAttribute("active", "");
      progress.setAttribute("indeterminate", "");
      const message = document.createElement("span");
      message.textContent = "Programming lock…";
      loading.append(progress, message);
      content.append(loading);
    }
    next.textContent = this._provisioning ? "Programming lock…" : "Give Access";
    next.disabled = !this._pinIsValid() || this._provisioning;
  }

  _renderGiveAccessResult(content, next) {
    const result = this._provisionResult;
    const heading = document.createElement("p");
    heading.className = "success-title";
    heading.textContent = "✅ Access Created";
    const summary = document.createElement("div");
    summary.className = "success-summary";
    for (const [label, value] of [
      ["User", result?.person_display_name],
      ["Access Point", result?.access_point_display_name],
      ["PIN", this._pin],
    ]) {
      const item = document.createElement("div");
      const itemLabel = document.createElement("p");
      itemLabel.className = "success-label";
      itemLabel.textContent = label;
      const itemValue = document.createElement("p");
      itemValue.className = "success-value";
      itemValue.textContent = value ?? "";
      item.append(itemLabel, itemValue);
      summary.append(item);
    }
    content.append(heading, summary);
    if (result?.status === "inconclusive") {
      const status = document.createElement("p");
      status.className = "confirmation-note";
      status.textContent =
        "The PIN has been sent to the lock. Some Yale locks may take a short time to confirm the update. We recommend testing the PIN before giving it to the user.";
      content.append(status);
    }
    const information = document.createElement("div");
    information.className = "success-information";
    const informationTitle = document.createElement("strong");
    informationTitle.textContent = "PIN saved";
    const informationMessage = document.createElement("p");
    informationMessage.textContent =
      "This PIN has been securely stored in HomePASS and has been sent to the lock.";
    const revealMessage = document.createElement("p");
    revealMessage.textContent =
      "You can reveal it later from this user's access details.";
    information.append(informationTitle, informationMessage, revealMessage);
    content.append(information);
    next.textContent = "Done";
    next.disabled = false;
  }

  _personCard(person) {
    const card = document.createElement("ha-card");
    card.className = "person-card";
    const open = document.createElement("button");
    open.className = "person-card-open";
    open.type = "button";
    open.setAttribute("aria-label", `View User Details for ${person.display_name}`);
    open.addEventListener("click", () => void this._openPersonDetails(person.person_id));

    const visual = document.createElement("div");
    visual.className = "person";

    const avatar = document.createElement("span");
    avatar.className = "person-avatar";
    avatar.setAttribute("aria-hidden", "true");
    const avatarIcon = document.createElement("ha-icon");
    avatarIcon.setAttribute("icon", "mdi:account");
    avatar.append(avatarIcon);

    const content = document.createElement("div");
    content.className = "person-content";
    const heading = document.createElement("div");
    heading.className = "person-heading";
    const name = document.createElement("span");
    name.className = "person-name homepass-entity-name";
    name.textContent = person.display_name;
    heading.append(name);

    if (!person.enabled) {
      const status = document.createElement("span");
      status.className = "person-status disabled";
      status.textContent = "Disabled";
      heading.append(status);
    }
    content.append(heading);

    const accessCount = Number.isInteger(person.access_count) ? person.access_count : undefined;
    if (person.description) {
      const description = document.createElement("span");
      description.className = "person-description";
      description.textContent = person.description;
      content.append(description);
    }

    const meta = document.createElement("div");
    meta.className = "person-card-meta";
    if (this._currentPage === "people") meta.append(this._personQuickPin(person));
    if (this._currentPage === "people" && this._hass?.user?.is_admin) {
      const nfcStatus = this._nfcEnrollmentStatuses.get(person.person_id);
      meta.append(this._personMetric(
        "mdi:nfc",
        nfcStatus?.enrolled === true
          ? `NFC enrolled · ${Number(nfcStatus.access_count ?? 0)} ${Number(nfcStatus.access_count ?? 0) === 1 ? "Door" : "Doors"}`
          : nfcStatus
            ? Number(nfcStatus.access_count ?? 0) > 0
              ? `NFC pending · ${Number(nfcStatus.access_count)} ${Number(nfcStatus.access_count) === 1 ? "Door" : "Doors"}`
              : "NFC not enrolled"
            : "NFC status unavailable",
      ));
    }
    meta.append(this._personMetric(
      "mdi:door",
      Number.isInteger(accessCount)
        ? `${accessCount} ${accessCount === 1 ? "Door" : "Doors"}`
        : "Door assignments unavailable",
    ));
    content.append(meta);

    const chevron = document.createElement("span");
    chevron.className = "person-chevron";
    chevron.setAttribute("aria-hidden", "true");
    const chevronIcon = document.createElement("ha-icon");
    chevronIcon.setAttribute("icon", "mdi:chevron-right");
    chevron.append(chevronIcon);

    visual.append(avatar, content, chevron);
    card.append(open, visual);
    return card;
  }

  _personQuickPin(person) {
    const row = document.createElement("div");
    row.className = "person-quick-pin";
    const label = document.createElement("span");
    label.className = "person-quick-pin-label";
    label.textContent = "PIN:";
    const value = document.createElement("span");
    value.className = "person-quick-pin-value";
    value.setAttribute("role", "status");
    value.setAttribute("aria-live", "polite");
    value.textContent = person.credential_stored === true ? "••••" : "Not set";
    row.append(label, value);
    if (person.credential_stored !== true) return row;

    const progress = document.createElement("ha-circular-progress");
    progress.className = "person-quick-pin-progress";
    progress.setAttribute("size", "small");
    progress.hidden = true;
    const status = document.createElement("span");
    status.className = "sr-only";
    status.setAttribute("role", "status");
    status.textContent = "Retrieving PIN";
    status.hidden = true;
    const toggle = document.createElement("button");
    toggle.className = "person-quick-pin-toggle";
    toggle.type = "button";
    toggle.dataset.pinOwner = person.display_name;
    toggle.setAttribute("aria-label", `Reveal PIN for ${person.display_name}`);
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", "mdi:eye");
    toggle.append(icon);
    const error = document.createElement("span");
    error.className = "person-quick-pin-error";
    error.setAttribute("role", "alert");
    error.hidden = this._quickPinErrorPersonId !== person.person_id;
    error.textContent = error.hidden ? "" : this._quickPinError ?? "";
    let controller = this._quickPinControllers.get(person.person_id);
    if (!controller) {
      controller = this._createCredentialRevealController();
      this._quickPinControllers.set(person.person_id, controller);
    }
    controller.mount(value, toggle, icon, progress, status, "••••");
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      void this._toggleQuickPinReveal(person, controller, error);
    });
    row.append(progress, toggle, status, error);
    return row;
  }

  async _toggleQuickPinReveal(person, controller, errorElement) {
    if (controller.isRevealed()) {
      controller.clear();
      if (this._activeQuickPinPersonId === person.person_id) {
        this._activeQuickPinPersonId = undefined;
      }
      return;
    }
    if (controller.isPending() || controller.isBlocked()) return;
    this._clearQuickPinErrors(errorElement);
    for (const [personId, other] of this._quickPinControllers) {
      if (personId !== person.person_id) other.clear();
    }
    const generation = ++this._quickPinRequestGeneration;
    this._activeQuickPinPersonId = person.person_id;
    const controllerGeneration = controller.beginRequest();
    const requestId = this._newRevealRequestId();
    const startedAt = this._revealTraceNow();
    const context = { person_id: person.person_id };
    if (typeof person.credential_access_point_id === "string") {
      context.access_point_id = person.credential_access_point_id;
    }
    try {
      const request = {
        type: REVEAL_PIN_COMMAND,
        person_id: person.person_id,
        panel_asset_version: PANEL_ASSET_VERSION,
        request_id: requestId,
      };
      if (context.access_point_id) request.access_point_id = context.access_point_id;
      const response = await this._callRevealWithTimeout(request, requestId, startedAt, context);
      if (
        generation !== this._quickPinRequestGeneration ||
        this._activeQuickPinPersonId !== person.person_id ||
        this._currentPage !== "people" ||
        this._detailsPersonId
      ) {
        if (response && typeof response === "object") response.pin = undefined;
        return;
      }
      const shown = controller.show(response?.pin, controllerGeneration);
      if (response && typeof response === "object") response.pin = undefined;
      if (!shown) throw new Error("invalid_reveal_response");
    } catch (error) {
      if (
        generation !== this._quickPinRequestGeneration ||
        this._activeQuickPinPersonId !== person.person_id
      ) return;
      this._quickPinErrorPersonId = person.person_id;
      this._quickPinError = this._friendlyRevealError(error, "users-card");
      errorElement.hidden = false;
      errorElement.textContent = this._quickPinError;
    } finally {
      controller.finishRequest(controllerGeneration);
    }
  }

  _clearQuickPinReveals() {
    this._quickPinRequestGeneration += 1;
    this._activeQuickPinPersonId = undefined;
    this._clearQuickPinErrors();
    for (const controller of this._quickPinControllers.values()) controller.clear();
  }

  _clearQuickPinErrors(currentError = undefined) {
    this._quickPinErrorPersonId = undefined;
    this._quickPinError = undefined;
    const errors = new Set(
      this.shadowRoot?.querySelectorAll?.(".person-quick-pin-error") ?? [],
    );
    if (currentError) errors.add(currentError);
    for (const error of errors) {
      error.hidden = true;
      error.textContent = "";
    }
  }

  _personStatus(person) {
    if (!person.enabled) return "Disabled";
    const reported = String(person.status ?? "").toLowerCase();
    if (reported === "scheduled") return "Scheduled";
    if (reported === "pending") return "Pending";
    return "Enabled";
  }

  _personSummaryLine(iconName, primary, secondary = undefined) {
    const line = document.createElement("span");
    line.className = "person-summary-line";
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", iconName);
    icon.setAttribute("aria-hidden", "true");
    const copy = document.createElement("span");
    copy.className = "person-summary-copy";
    const primaryText = document.createElement("span");
    primaryText.className = "person-summary-primary";
    primaryText.textContent = primary;
    copy.append(primaryText);
    if (secondary) {
      const secondaryText = document.createElement("span");
      secondaryText.className = "person-summary-secondary";
      secondaryText.textContent = secondary;
      copy.append(secondaryText);
    }
    line.append(icon, copy);
    return line;
  }

  _personMetric(iconName, value) {
    const metric = document.createElement("span");
    metric.className = "person-metric";
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", iconName);
    icon.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.textContent = value;
    metric.append(icon, text);
    return metric;
  }

  _formatPersonLastUsed(value) {
    if (!value) return "Never used";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Never used";
    const now = new Date();
    const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    const day = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const dayDifference = Math.round((today - day) / 86400000);
    if (dayDifference === 0) return `Today ${time}`;
    if (dayDifference === 1) return `Yesterday ${time}`;
    return `${date.toLocaleDateString()} ${time}`;
  }

  _peopleEmptyState() {
    const card = document.createElement("div");
    card.className = "state-card people-empty-state";
    const mark = document.createElement("div");
    mark.className = "homepass-mark-placeholder";
    mark.innerHTML = this._homePassBrandLockup("empty");
    const heading = document.createElement("h2");
    heading.textContent = "No users yet";
    const description = document.createElement("p");
    description.textContent =
      "Create your first user to begin managing access to your home.";
    const add = document.createElement("button");
    add.id = "empty-add-person";
    add.className = "add-person";
    add.type = "button";
    const addIcon = document.createElement("ha-icon");
    addIcon.setAttribute("icon", "mdi:plus");
    const addLabel = document.createElement("span");
    addLabel.textContent = "Add User";
    add.append(addIcon, addLabel);
    add.addEventListener("click", () => this._openAddPersonDialog());
    card.append(mark, heading, description, add);
    return card;
  }

  _detailField(label, value) {
    const field = document.createElement("div");
    field.className = "detail-field";
    const fieldLabel = document.createElement("span");
    fieldLabel.className = "detail-label";
    fieldLabel.textContent = label;
    const fieldValue = document.createElement("div");
    fieldValue.className = "detail-value";
    if (value instanceof Node) {
      fieldValue.append(value);
    } else {
      fieldValue.textContent = value;
    }
    field.append(fieldLabel, fieldValue);
    return field;
  }

  _summaryCard(title, message, icon) {
    const card = document.createElement("ha-card");
    card.className = "details-card summary-card";
    const cardIcon = document.createElement("ha-icon");
    cardIcon.setAttribute("icon", icon);
    const body = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = title;
    const description = document.createElement("p");
    description.textContent = message;
    body.append(heading, description);
    card.append(cardIcon, body);
    return card;
  }

  _personScheduleSummaryCard() {
    const card = document.createElement("ha-card");
    card.className = "details-card summary-card";
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", "mdi:calendar-clock");
    const body = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = "Schedule";
    const copy = document.createElement("div");
    copy.className = "schedule-entry-copy";
    if (this._scheduleGroups.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = this._accessMetadata.length === 0
        ? "No doors are assigned."
        : "Schedule details are unavailable.";
      copy.append(empty);
    }
    for (const group of this._scheduleGroups) {
      const schedule = group.schedule;
      const entry = document.createElement("div");
      entry.className = "schedule-group-summary";
      const title = document.createElement("p");
      title.textContent = schedule?.name === "Permanent"
        ? "Permanent access"
        : schedule?.name ?? "Schedule";
      const doors = document.createElement("p");
      const names = Array.isArray(group.access_point_names)
        ? group.access_point_names
        : (group.access_point_ids ?? []).map(
            (accessPointId) =>
              this._accessMetadata.find(
                (metadata) => metadata.access_point_id === accessPointId,
              )?.access_point_display_name ?? "Door",
          );
      doors.textContent = `${names.length} ${names.length === 1 ? "door" : "doors"} · ${
        names.join(", ")
      }`;
      const hours = document.createElement("p");
      if (!schedule || schedule.weekly_rules?.length === 0) {
        hours.textContent = "24-hour access";
      } else {
        const labels = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        const days = [
          ...new Set(schedule.weekly_rules.map((rule) => labels[Number(rule.day_of_week)])),
        ];
        const first = schedule.weekly_rules[0];
        hours.textContent =
          `${days.join(", ")} · ${first.start_time.slice(0, 5)}–${first.end_time.slice(0, 5)}`;
      }
      entry.append(title, doors, hours);
      copy.append(entry);
    }
    const edit = document.createElement("ha-button");
    edit.id = "edit-person-schedule";
    edit.className = "schedule-entry-action";
    edit.setAttribute("appearance", "plain");
    edit.textContent = "Edit Schedule";
    edit.addEventListener("click", () => this._openPersonSchedule());
    body.append(heading, copy, edit);
    card.append(icon, body);
    return card;
  }

  _hasAccessTo(accessPointId) {
    return this._accessMetadata.some(
      (metadata) => metadata.access_point_id === accessPointId,
    );
  }

  _accessHealthLabel(metadata) {
    if (
      metadata.synchronization_status === "synchronizing" ||
      metadata.synchronization_status === "pending"
    ) {
      return "Synchronizing";
    }
    if (metadata.synchronization_status === "retry_required") {
      return "Out of sync";
    }
    if (
      metadata.synchronization_status === "manual_attention_required" ||
      metadata.synchronization_status === "unknown"
    ) {
      return "Needs attention";
    }
    return "Working";
  }

  _driverLabel(driver) {
    if (driver === "zwave_js") return "Z-Wave JS";
    if (driver === "homepass_keypad") return "HomePASS keypad";
    return driver;
  }

  _credentialSummaryCard() {
    const card = document.createElement("ha-card");
    card.className = "details-card summary-card";
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", "mdi:key-variant");
    const body = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = "Credentials";
    const status = document.createElement("p");
    status.textContent = this._personHasStoredCredential()
      ? "PIN stored securely."
      : "No stored PIN credential.";
    body.append(heading, status);
    const passkeys = Array.isArray(this._nfcEnrollment?.passkeys)
      ? this._nfcEnrollment.passkeys
      : [];
    if (passkeys.length > 0) {
      const subheading = document.createElement("h3");
      subheading.textContent = "Passkey devices";
      const list = document.createElement("div");
      list.className = "nfc-passkey-list";
      for (const passkey of passkeys) {
        const item = document.createElement("div");
        item.className = "nfc-passkey-item";
        const name = document.createElement("strong");
        name.textContent = passkey.backed_up
          ? "Synced passkey"
          : passkey.device_type === "single_device"
            ? "Device-bound passkey"
            : "Passkey device";
        const details = document.createElement("span");
        const enrolledAt = passkey.created_at
          ? new Date(passkey.created_at).toLocaleDateString()
          : "date unavailable";
        details.textContent = `${passkey.backed_up ? "Backed up" : "Not backed up"} · Enrolled ${enrolledAt}`;
        item.append(name, details);
        list.append(item);
      }
      body.append(subheading, list);
    } else if (this._nfcEnrollment && this._nfcEnrollment.enrolled !== true) {
      const noPasskey = document.createElement("p");
      noPasskey.textContent = "No NFC passkey enrolled.";
      body.append(noPasskey);
    }
    card.append(icon, body);
    return card;
  }

  _stateCard(message, title) {
    const card = document.createElement("div");
    card.className = "state-card";
    if (title) {
      const heading = document.createElement("h2");
      heading.textContent = title;
      card.append(heading);
    }
    const description = document.createElement("p");
    description.textContent = message;
    card.append(description);
    return card;
  }

  _emptyForm() {
    return { displayName: "", description: "", notes: "", enabled: true };
  }
}

if (!customElements.get(SLIDE_ACTION_WEB_COMPONENT)) {
  customElements.define(
    SLIDE_ACTION_WEB_COMPONENT,
    class extends HomePassSlideAction {},
  );
}

if (!customElements.get(PANEL_WEB_COMPONENT)) {
  customElements.define(PANEL_WEB_COMPONENT, class extends HomePassPanel {});
}

