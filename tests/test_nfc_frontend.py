"""Public NFC page presentation safeguards."""

from pathlib import Path

_FRONTEND = Path(__file__).parents[1] / "custom_components" / "homepass" / "nfc" / "frontend"


def test_frontend_adapts_passkey_presentation_by_platform() -> None:
    """Apple, Android, and unknown clients receive appropriate presentation."""
    source = (_FRONTEND / "nfc-access.js").read_text(encoding="utf-8")

    assert "userAgentData?.platform" in source
    assert 'kind: "apple"' in source
    assert 'kind: "android"' in source
    assert 'kind: "generic"' in source
    assert "Face ID or Touch ID" in source
    assert "fingerprint, face, or screen lock" in source


def test_frontend_expires_unlock_page_and_aborts_active_passkey_prompt() -> None:
    """A stale page becomes non-interactive and cannot finish its passkey flow."""
    source = (_FRONTEND / "nfc-access.js").read_text(encoding="utf-8")

    assert "window.setTimeout(expire" in source
    assert "credentialController.abort()" in source
    assert "This page has expired" in source
    assert "Tap the NFC tag again to operate the door" in source
    assert "button.hidden = true" in source
    assert "[hidden]" in (_FRONTEND / "nfc-access.css").read_text(encoding="utf-8")


def test_success_pages_explain_that_they_can_be_closed() -> None:
    """Enrollment and unlock share one platform-neutral completion note."""
    source = (_FRONTEND / "nfc-access.js").read_text(encoding="utf-8")
    preview = (_FRONTEND / "unlock-preview.html").read_text(encoding="utf-8")

    assert "completionNote.hidden = false" in source
    assert "You can safely close this page or navigate away." in preview


def test_door_access_pages_identify_authorized_user_requirement() -> None:
    """Unlock pages direct unenrolled visitors to the property owner."""
    notice = (
        "HomePASS door access is for enrolled, authorized users only. "
        "If you are not enrolled, contact the property owner for entry."
    )
    preview = (_FRONTEND / "unlock-preview.html").read_text(encoding="utf-8")
    views = (_FRONTEND.parent / "views.py").read_text(encoding="utf-8")

    assert notice in preview
    assert "HomePASS door access is for enrolled" in views
    assert 'if mode != "enroll"' in views


def test_roller_door_page_uses_server_selected_open_or_close_action() -> None:
    """The short-lived NFC page presents the operation bound by the backend."""
    source = (_FRONTEND / "nfc-access.js").read_text(encoding="utf-8")

    assert '["open", "close", "unlock"].includes(config.action)' in source
    assert "Click here to ${doorAction} the door" in source
    assert 'result.action === "close"' in source
    assert 'result.action === "open"' in source
