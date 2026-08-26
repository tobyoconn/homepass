"""Administrator NFC tag provisioning presentation safeguards."""

from pathlib import Path


_SOURCE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "homepass"
    / "frontend"
    / "homepass-nfc-provisioner.js"
).read_text(encoding="utf-8")


def test_gototags_csv_uses_the_verified_ntag424_profile() -> None:
    """The encoder download must reproduce the known-good HomePASS tag profile."""
    assert '"ndef.records.0.type": "WEBSITE"' in _SOURCE
    assert '"chip.ntag424.files.ccFileAccessRights.writeCondition": "APP_KEY_0"' in _SOURCE
    assert '"chip.ntag424.files.ccFileAccessRights.readWriteCondition": "APP_KEY_0"' in _SOURCE
    assert '"chip.ntag424.files.ndefFileAccessRights.writeCondition": "APP_KEY_0"' in _SOURCE
    assert '"chip.ntag424.files.ndefFileAccessRights.readWriteCondition": "APP_KEY_0"' in _SOURCE
    assert '"chip.ntag424.files.ndefFileAccessRights.changeCondition": "APP_KEY_0"' in _SOURCE
    assert '"chip.ntag424.sdmSettings.accessRights.fileRead": "APP_KEY_1"' in _SOURCE
    assert '"chip.ntag424.sdmSettings.accessRights.metaRead": "APP_KEY_2"' in _SOURCE
    assert '"chip.ntag424.sdmSettings.options.encryptFileData": "FALSE"' in _SOURCE
    assert '"chip.ntag424.sdmSettings.options.readCounter": "TRUE"' in _SOURCE
    assert '"chip.ntag424.sdmSettings.options.uidMirroring": "TRUE"' in _SOURCE


def test_gototags_csv_maps_homepass_keys_and_computes_url_offsets() -> None:
    """HomePASS secrets and URL-dependent offsets are not copied into wrong fields."""
    assert '"chip.ntag424.newKeys.key1": result.file_read_key' in _SOURCE
    assert '"chip.ntag424.newKeys.key2": result.meta_read_key' in _SOURCE
    assert "new TextEncoder().encode(template.slice(urlPrefix.length, urlIndex)).length" in _SOURCE
    assert "return {piccData, macInput: mac, mac}" in _SOURCE


def test_gototags_workflow_opens_ready_to_write_without_manual_setup() -> None:
    """The normal path skips operation creation and CSV import."""
    for text in (
        "Download GoToTags file",
        "Double-click the <strong>.gototags</strong> file",
        "GoToTags Desktop opens automatically",
        "click <strong>Start encoding</strong>",
        "Once the encoding session has started",
        "green <strong>VERIFIED</strong>",
        "zero errors",
        "If GoToTags reports an error",
        "some keys may already have changed",
    ):
        assert text in _SOURCE


def test_gototags_operation_is_private_ready_and_self_contained() -> None:
    assert 'operationType: "VARIABLE_ENCODE_NFC_TAGS"' in _SOURCE
    assert 'chipType: "NTAG424"' in _SOURCE
    assert 'status: "READY"' in _SOURCE
    assert "verify: true" in _SOURCE
    assert "integrations: []" in _SOURCE
    assert "lock: booleanValue(values.lock)" in _SOURCE
    assert 'lock: permanentlyLock ? "TRUE" : "FALSE"' in _SOURCE
    assert 'storedZip("file.gototags"' in _SOURCE
    assert 'link.download = `homepass-${door || "door"}-${this._uid}.gototags`' in _SOURCE
    for private_field in ('"account":', '"client":', '"reader":', '"hardwareUid":', '"ipAddress":'):
        assert private_field not in _SOURCE


def test_new_tags_offer_recoverable_or_permanent_rewrite_protection() -> None:
    assert "Leave it re-writable with the HomePASS administrator key (recommended)" in _SOURCE
    assert "Lock it as permanently written" in _SOURCE
    assert "This gives the strongest protection against alteration, but it is irreversible" in _SOURCE
    assert '"chip.ntag424.newKeys.key0": result.admin_key' in _SOURCE
    assert '"chip.ntag424.currentKeys.key0": result.current_admin_key || factoryKey' in _SOURCE
    assert "currentFileKey = existingTag ? result.file_read_key : factoryKey" in _SOURCE
    assert "currentMetaKey = existingTag ? result.meta_read_key : factoryKey" in _SOURCE
    assert "CONFIRM_NFC_TAG_PROTECTION_ACTION" in _SOURCE


def test_gototags_workflow_keeps_tags_recoverable_and_uid_specific() -> None:
    """The UI warns administrators against the two most damaging setup mistakes."""
    assert "place only tag UID" in _SOURCE
    assert "A permanently locked tag cannot be repaired or re-encoded" in _SOURCE
    assert "some keys may already have changed" in _SOURCE


def test_protection_confirmation_explains_what_homepass_records() -> None:
    assert "Record completed tag setup" in _SOURCE
    assert "This button does not write to the tag again" in _SOURCE
    assert "Tag setup recorded" in _SOURCE


def test_setup_explains_supported_hardware_and_manual_alternative() -> None:
    for text in (
        "Only genuine NTAG424 DNA tags are supported by HomePASS",
        'href="https://gototags.com/software"',
        "ACS ACR1552U USB-C NFC Reader IV",
        "Other NTAG424-compatible writers and software can also be used",
        "Enter the tag's 14-digit UID below",
        "Set up tag manually",
        "Manual NTAG424 DNA settings",
        "CC file access rights",
        "NDEF file access rights",
        "Proprietary file access rights",
        "Secure Dynamic Messaging",
    ):
        assert text in _SOURCE
