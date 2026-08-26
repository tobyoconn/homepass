"""Tests for secret-safe Nuki Bluetooth pairing diagnostics."""

import pytest
from pyNukiBT import NukiConst, NukiErrorException

from custom_components.homepass.providers.nuki_bluetooth import (
    NukiBluetoothPairer,
    NukiBluetoothPairingError,
)


@pytest.mark.parametrize(
    ("error_code", "translation_key"),
    [
        (
            NukiConst.ErrorCode.P_ERROR_NOT_PAIRING,
            "nuki_pairing_not_enabled",
        ),
        (NukiConst.ErrorCode.K_ERROR_BAD_PIN, "nuki_pairing_bad_pin"),
        (
            NukiConst.ErrorCode.P_ERROR_MAX_USER,
            "nuki_pairing_authorization_full",
        ),
        (
            NukiConst.ErrorCode.P_ERROR_BAD_AUTHENTICATOR,
            "nuki_pairing_protocol_failed",
        ),
    ],
)
def test_pairing_error_maps_nuki_protocol_failures(
    error_code,
    translation_key: str,
) -> None:
    """Nuki protocol errors produce actionable, secret-free UI keys."""
    upstream = NukiErrorException(
        error_code,
        NukiConst.NukiCommand.AUTHORIZATION_DATA,
    )

    result = NukiBluetoothPairer._pairing_error(upstream, stage="authorize")

    assert isinstance(result, NukiBluetoothPairingError)
    assert result.translation_key == translation_key
    assert result.stage == "authorize"


def test_pairing_error_maps_timeout() -> None:
    """A response timeout is distinct from discovery and connection failures."""
    result = NukiBluetoothPairer._pairing_error(
        TimeoutError(),
        stage="authorize",
    )

    assert result.translation_key == "nuki_pairing_timeout"


def test_pairing_error_maps_connection_failure() -> None:
    """Unknown connection exceptions never leak their message to the UI."""
    result = NukiBluetoothPairer._pairing_error(
        RuntimeError("sensitive upstream detail"),
        stage="connect",
    )

    assert result.translation_key == "nuki_pairing_connection_failed"
    assert "sensitive" not in str(result)
