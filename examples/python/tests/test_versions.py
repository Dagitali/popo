"""Exercise the Python consumer independently of its repository guardrails."""

from unittest import TestCase

from packaging.version import InvalidVersion

from guardrail_example import normalized_version


class TestVersions(TestCase):
    """Check canonical versions and malformed application input."""

    def test_normalized_version(self) -> None:
        """Normalize an alternate release-candidate spelling."""
        self.assertEqual(normalized_version('1.0RC1'), '1.0rc1')

    def test_invalid_version(self) -> None:
        """Reject text that cannot represent a package version."""
        with self.assertRaises(InvalidVersion):
            normalized_version('not-a-version')
