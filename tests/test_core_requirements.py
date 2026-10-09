"""Regression coverage for Core-owned dependency conflicts."""

from unittest import TestCase

from scripts.check_core_requirements import core_owned_requirements


class CoreRequirementsTest(TestCase):
    """Prevent the October 2026 dependency outage and equivalent future mistakes."""

    def test_rejects_previous_cryptography_pin(self) -> None:
        self.assertEqual(
            core_owned_requirements(["cryptography==48.0.1"], ["cryptography==50.0.1"]),
            {"cryptography"},
        )

    def test_rejects_duplicate_even_when_versions_currently_match(self) -> None:
        self.assertEqual(
            core_owned_requirements(["cryptography==50.0.1"], ["cryptography==50.0.1"]),
            {"cryptography"},
        )

    def test_normalizes_distribution_names(self) -> None:
        self.assertEqual(
            core_owned_requirements(["Some_Package>=1"], ["some-package==2"]),
            {"some-package"},
        )

    def test_allows_integration_specific_dependencies(self) -> None:
        self.assertEqual(core_owned_requirements(["qrcode==8.2"], ["cryptography==50.0.1"]), set())

    def test_ignores_inactive_extra_requirements(self) -> None:
        self.assertEqual(
            core_owned_requirements(["qrcode==8.2"], ['qrcode==8.2; extra == "optional"']),
            set(),
        )
