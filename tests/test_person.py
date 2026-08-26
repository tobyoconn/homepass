"""Tests for the person model."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from custom_components.homepass.models import Person


def test_person_normalizes_name_and_round_trips() -> None:
    person = Person(display_name="  Alex  ", notes="Owner")
    restored = Person.from_dict(person.to_dict())
    assert person.display_name == "Alex"
    assert restored == person


def test_person_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Person(display_name="   ")
