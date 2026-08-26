"""NFC and device-passkey access for HomePASS.

The package intentionally has no eager imports. This keeps the cryptographic
codec independently testable and avoids creating cycles during HomePASS setup.
"""
