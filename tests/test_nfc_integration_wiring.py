"""Regression coverage for NFC integration startup wiring."""

from __future__ import annotations

import ast
from pathlib import Path


def test_setup_wires_nfc_capability_and_command_dispatcher() -> None:
    """Pass the Door command service for both NFC protocol boundaries."""
    setup_source = (
        Path(__file__).parents[1] / "custom_components" / "homepass" / "__init__.py"
    ).read_text(encoding="utf-8")
    setup_tree = ast.parse(setup_source)
    constructor_calls = [
        node
        for node in ast.walk(setup_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "NfcAccessService"
    ]

    assert len(constructor_calls) == 1
    arguments = constructor_calls[0].args
    assert len(arguments) == 7
    assert all(
        isinstance(argument, ast.Name) and argument.id == "access_point_command_service"
        for argument in arguments[-2:]
    )
