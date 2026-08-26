"""NFC administrator presentation safeguards."""

from pathlib import Path

_SOURCE = (
    Path(__file__).parents[1] / "custom_components" / "homepass" / "frontend" / "homepass-panel.js"
).read_text(encoding="utf-8")


def test_versioned_components_use_fresh_custom_element_constructors() -> None:
    """Panel reloads do not reuse constructors already held by the registry."""
    assert "class extends HomepassNfcProvisioner {}" in _SOURCE
    assert "class extends HomePassSlideAction {}" in _SOURCE
    assert "class extends HomePassPanel {}" in _SOURCE
    assert (
        "customElements.define(NFC_PROVISIONER_WEB_COMPONENT, HomepassNfcProvisioner)"
        not in _SOURCE
    )
    assert "customElements.define(SLIDE_ACTION_WEB_COMPONENT, HomePassSlideAction)" not in _SOURCE
    assert "customElements.define(PANEL_WEB_COMPONENT, HomePassPanel)" not in _SOURCE


def test_user_nfc_enrollment_preselects_pin_doors() -> None:
    assert 'const UPDATE_NFC_ACCESS_ACTION = "update_nfc_access"' in _SOURCE
    assert "_initializeNfcAccessSelectionFromPinAccess" in _SOURCE
    assert "already has PIN access are pre-selected" in _SOURCE
    assert 'legend.textContent = "Choose NFC doors"' in _SOURCE
    assert "access_point_ids: [...this._nfcAccessSelection]" in _SOURCE


def test_user_door_list_consolidates_pin_and_nfc_access() -> None:
    assert "_appendPersonDoorAccessMethods" in _SOURCE
    assert 'pin.textContent = "PIN"' in _SOURCE
    assert 'nfc.textContent = nfcEnrolled ? "NFC" : "NFC — enrollment pending";' in _SOURCE
    assert "Edit Door Access" in _SOURCE
    assert "_accessSummaryCard" not in _SOURCE


def test_person_details_guide_nuki_app_fingerprint_enrollment() -> None:
    """The app explains the Nuki-only scan step and biometric-data boundary."""
    assert 'const GET_NUKI_FINGERPRINT_STATUS_ACTION = "get_nuki_fingerprint_status"' in _SOURCE
    assert 'heading.textContent = "Nuki fingerprint"' in _SOURCE
    assert "Open this lock in the Nuki app and choose Keypad." in _SOURCE
    assert "Open this user's PIN entry, choose Add fingerprint" in _SOURCE
    assert 'complete.textContent = "I finished in Nuki"' in _SOURCE
    assert "never biometric data" in _SOURCE
    assert 'fingerprintMethod.textContent = fingerprint.status === "confirmed"' in _SOURCE


def test_settings_offer_explicit_read_only_nuki_storage_check() -> None:
    """Administrators can inspect Nuki storage without reopening provider setup."""
    assert 'const GET_NUKI_STORAGE_STATUS_ACTION = "get_nuki_storage_status"' in _SOURCE
    assert "Check PIN & fingerprint status" in _SOURCE
    assert "HomePASS-managed and" in _SOURCE
    assert "does not provide a complete list of fingerprints" in _SOURCE
    assert "NUKI_STORAGE_REQUEST_TIMEOUT" in _SOURCE
    assert "This normally takes 10–50 seconds" in _SOURCE
    assert "Review existing Nuki PINs" in _SOURCE


def test_credential_card_lists_sanitized_passkey_devices() -> None:
    assert "Passkey devices" in _SOURCE
    assert "Synced passkey" in _SOURCE
    assert "Device-bound passkey" in _SOURCE
    assert "Not backed up" in _SOURCE


def test_people_page_loads_nfc_summaries_in_one_request() -> None:
    assert 'const LIST_NFC_ENROLLMENT_STATUSES_ACTION = "list_nfc_enrollment_statuses"' in _SOURCE
    assert "service: LIST_NFC_ENROLLMENT_STATUSES_ACTION" in _SOURCE


def test_people_counts_refresh_when_returning_from_user_details() -> None:
    """A completed asynchronous removal must not leave stale Door counts on cards."""
    close_details = _SOURCE[_SOURCE.index("  _closePersonDetails() {") :]
    close_details = close_details[: close_details.index("  async _loadPersonPolicy")]
    assert 'if (this._currentPage === "people") void this._loadPeople();' in close_details
    assert "void this._loadPeople();" in close_details

    open_people = _SOURCE[_SOURCE.index("  _openPeoplePage() {") :]
    open_people = open_people[: open_people.index("  _openActivityPage() {")]
    assert "void this._loadPeople();" in open_people

    open_dashboard = _SOURCE[_SOURCE.index("  _openDashboardPage() {") :]
    open_dashboard = open_dashboard[
        : open_dashboard.index("  async _loadDashboardPropertySettings")
    ]
    assert "void this._loadPeople();" in open_dashboard


def test_people_page_skips_nfc_summary_call_when_nfc_is_disabled() -> None:
    """The stable empty Users page must not fail merely because NFC is unconfigured."""
    assert "nfcEnrollmentServiceAvailable" in _SOURCE
    assert "this._hass?.services?.[DOMAIN]?.[LIST_NFC_ENROLLMENT_STATUSES_ACTION]" in _SOURCE
    assert "this._nfcEnrollmentStatuses = new Map();" in _SOURCE


def test_door_page_starts_nfc_setup_before_guiding_provider_configuration() -> None:
    """The NFC action contains a focused prerequisite instead of unrelated options."""
    assert "nfcTagServiceAvailable" in _SOURCE
    assert '<button id="open-door-nfc-setup"' in _SOURCE
    assert "One-time Nabu Casa setup required" in _SOURCE
    assert "NFC setup required" in _SOURCE
    assert "HomePASS needs the secure Nabu Casa HTTPS address" in _SOURCE
    assert 'const CONFIGURE_NFC_ACTION = "configure_nfc"' in _SOURCE
    assert 'id="door-nfc-public-origin"' in _SOURCE
    assert 'id="save-door-nfc-configuration"' in _SOURCE


def test_user_can_enroll_for_nfc_before_any_door_is_available() -> None:
    """Passkey enrollment is independent from physical tag and Door provisioning."""
    assert "Door selection is optional." in _SOURCE
    assert "You can still enroll this user now and assign Doors later." in _SOURCE
    assert "this._nfcAccessSelection.size > 0" in _SOURCE
    assert "!await this._saveNfcAccess({ reload: false, render: false })" in _SOURCE
    assert (
        'primary.textContent = enrolled ? "Revoke NFC enrollment" : "Create NFC enrollment"'
        in _SOURCE
    )


def test_user_enrollment_starts_focused_nfc_setup_when_unconfigured() -> None:
    """Create enrollment explains and resolves the NFC prerequisite in place."""
    assert "_nfcEnrollmentServicesAvailable" in _SOURCE
    assert "this._nfcEnrollmentSetupOpen = true" in _SOURCE
    assert 'input.id = "user-nfc-public-origin"' in _SOURCE
    assert "before it can create an NFC enrollment link" in _SOURCE
    assert "service: CONFIGURE_NFC_ACTION" in _SOURCE
    assert "await this._createNfcEnrollment();" in _SOURCE


def test_generated_pin_is_compatible_with_nuki_and_yale() -> None:
    """Generated PINs use the strict intersection of configured provider rules."""
    assert "const range = 9 ** 6;" in _SOURCE
    assert "pin = String((value % 9) + 1) + pin;" in _SOURCE
    assert '!pin.startsWith("12")' in _SOURCE


def test_incompatible_saved_pin_guides_change_and_resumes_assignment() -> None:
    """Nuki assignment failures lead to a valid replacement instead of blind retries."""
    assert 'response.reason === "pin_incompatible"' in _SOURCE
    assert '{errorCode: "pin_incompatible"}' in _SOURCE
    assert '? "Change PIN"' in _SOURCE
    assert 'this._changePinRequirements = "nuki"' in _SOURCE
    assert "HomePASS will finish assigning the selected door" in _SOURCE
    assert "queueMicrotask(() => void this._saveAccessSelection())" in _SOURCE
    assert "accessPoint.capabilities?.pin === true" in _SOURCE
    assert "accessPoint.pin_capable === true" in _SOURCE


def test_door_management_lists_disables_reinstates_and_deletes_individual_tags() -> None:
    assert 'const LIST_NFC_TAGS_ACTION = "list_nfc_tags"' in _SOURCE
    assert 'const REVOKE_NFC_TAG_ACTION = "revoke_nfc_tag"' in _SOURCE
    assert 'const REINSTATE_NFC_TAG_ACTION = "reinstate_nfc_tag"' in _SOURCE
    assert 'const DELETE_NFC_TAG_ACTION = "delete_nfc_tag"' in _SOURCE
    assert "Registered NFC tags" in _SOURCE
    assert "data-revoke-nfc-tag" in _SOURCE
    assert "data-reinstate-nfc-tag" in _SOURCE
    assert "data-delete-nfc-tag" in _SOURCE
    assert "Temporarily disable" in _SOURCE
    assert "Delete permanently" in _SOURCE
    assert 'const PREPARE_NFC_TAG_PROTECTION_ACTION = "prepare_nfc_tag_protection"' in _SOURCE
    assert 'const CONFIRM_NFC_TAG_PROTECTION_ACTION = "confirm_nfc_tag_protection"' in _SOURCE
    assert "Protect rewriting" in _SOURCE
    assert "Rewrite protected" in _SOURCE
    assert "Protection prepared; not yet verified" in _SOURCE
    assert "Download protection file again" in _SOURCE
    assert "Protection ready to be recorded" not in _SOURCE
    assert "Record tag as protected" in _SOURCE
    assert "This button does not write to the tag again" in _SOURCE


def test_door_tag_protection_uses_ready_to_write_gototags_file() -> None:
    assert "buildGoToTagsNtag424OperationBlob" in _SOURCE
    assert "homepass-protect-${uidHex.toLowerCase()}.gototags" in _SOURCE
    assert "Double-click the downloaded <strong>.gototags</strong> file" in _SOURCE
    assert "Protection CSV downloaded" not in _SOURCE


def test_door_dialog_batches_background_loading_and_action_refreshes() -> None:
    assert "void Promise.all([" in _SOURCE
    assert "this._loadDoorStatus(door.id, {render: false})" in _SOURCE
    assert "this._loadDoorPolicy(door.id, {render: false})" in _SOURCE
    assert "this._loadDoorNfcTags(door.id, {render: false})" in _SOURCE
    assert (
        "async _loadDoorNfcTags(accessPointId = this._selectedDoorId, {render = true} = {})"
        in _SOURCE
    )


def test_existing_manual_door_can_change_its_status_sensor() -> None:
    """Door management exposes a non-destructive contact-sensor editor."""
    assert "Add door sensor" in _SOURCE
    assert "Change door sensor" in _SOURCE
    assert 'id="edit-door-status-entity"' in _SOURCE
    assert "status_entity_id: this._doorSensorEntityId" in _SOURCE
    assert "Reverse open and closed status" in _SOURCE


def test_user_door_names_open_door_management() -> None:
    assert "_openDoorFromPerson" in _SOURCE
    assert "person-door-link" in _SOURCE
    assert "Open ${person.display_name} Door management" in _SOURCE


def test_manage_access_models_door_permission_and_credential_methods() -> None:
    assert "Edit Door Access" in _SOURCE
    assert "manage-access-door-methods" in _SOURCE
    assert "manage-access-method-options" in _SOURCE
    assert "this._editNfcAccessSelection" in _SOURCE
    assert "Save Door Access" in _SOURCE


def test_manage_access_can_save_door_permission_before_credentials() -> None:
    """Door authorization is not blocked by passkey enrollment or PIN creation."""
    assert '"NFC — enrollment pending"' in _SOURCE
    assert "if (nfcSupported) this._editNfcAccessSelection.add(accessPointId);" in _SOURCE
    assert "if (pinSupported && this._personHasStoredCredential())" in _SOURCE
    assert "if (this._nfcEnrollment?.enrolled !== true) return true;" not in _SOURCE
    assert 'explanation: "Door permission saved · NFC enrollment pending"' in _SOURCE
    assert 'nfc.textContent = nfcEnrolled ? "NFC" : "NFC — enrollment pending";' in _SOURCE
