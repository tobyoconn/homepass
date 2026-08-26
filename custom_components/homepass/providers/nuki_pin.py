"""Shared validation rules for Nuki keypad PINs."""

from __future__ import annotations

NUKI_PIN_REQUIREMENTS = (
    "Nuki keypad PINs must contain six digits from 1 through 9 and not start with 12"
)


def validate_nuki_keypad_pin(pin: str) -> None:
    """Reject a PIN that cannot be stored by a Nuki keypad."""
    if (
        not isinstance(pin, str)
        or len(pin) != 6
        or any(character not in "123456789" for character in pin)
        or pin.startswith("12")
    ):
        raise ValueError(NUKI_PIN_REQUIREMENTS)


__all__ = ["NUKI_PIN_REQUIREMENTS", "validate_nuki_keypad_pin"]
