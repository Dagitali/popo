"""
:mod:`tests.unit.checks.test_u_apple_metadata` module.

Exercise OpenStep parsing and strict, value-private Apple policy loading.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.checks._openstep import parse_project
from popo.checks.apple_metadata import _same
from popo.config import ConfigurationError
from popo.config.apple_metadata import load_apple_metadata_config
from tests.support.apple_metadata import POLICY

# SECTION: TESTS


class TestAppleMetadata:
    """Keep generic parsing and configuration matrices in the dependency."""

    @pytest.mark.parametrize(
        'before,after',
        (
            ('kind = "plist"', 'kind = "json"'),
            ('id = "privacy"', 'id = "invalid id"'),
            ('id = "identity"', 'id = "privacy"'),
            ('path = "Info.plist"', 'path = "../Info.plist"'),
            ('path = "Info.plist"', 'path = "/Info.plist"'),
            ('path = "Info.plist"', 'path = "./Info.plist"'),
            ('path = "Info.plist"', 'path = ""'),
            ('path = "Info.plist"', 'path = 1'),
            ('absent = ["PrivateKey"]', 'unknown = true'),
            ('absent = ["PrivateKey"]', 'absent = [1]'),
            ('absent = ["PrivateKey"]', 'absent = ["a", "a"]'),
            ('absent = ["PrivateKey"]', 'absent = ["ITSAppUsesNonExemptEncryption"]'),
            ('absent = ["PrivateKey"]', 'target = "not-allowed"'),
            ('target = "Example"', 'scope = "invalid"'),
            ('target = "Example"', 'scope = "project"\ntarget = "Example"'),
            ('target = "Example"', 'target = 1'),
            ('target = "Example"', 'target = ""'),
            ('configurations = ["Debug", "Release"]', 'configurations = []'),
            ('PRODUCT_BUNDLE_IDENTIFIER = "com.example.app"', 'S = false'),
            ('ITSAppUsesNonExemptEncryption = false', 'Value = inf'),
            ('ITSAppUsesNonExemptEncryption = false', 'Value = 2026-11-03'),
        ),
    )
    def test_invalid_policy_is_rejected(
        self: Self,
        tmp_path: Path,
        before: str,
        after: str,
    ) -> None:
        """
        Reject unsafe selectors, contradictory keys and unsupported values.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable policy root.
        before, after : str
            Literal mutation isolating one invalid policy field.
        """
        (tmp_path / 'pyproject.toml').write_text(POLICY.replace(before, after))
        with pytest.raises(ConfigurationError):
            load_apple_metadata_config(tmp_path)

    @pytest.mark.parametrize(
        'source',
        (
            '',
            '{',
            '{ a = 1; a = 2; }',
            '{ () = 1; }',
            '{ {} = 1; }',
            '{} {}',
            '{} /* unfinished',
            '{ a = "unfinished; }',
            '{} "',
            '{ a 1; }',
        ),
    )
    def test_malformed_openstep_fails(
        self: Self,
        source: str,
    ) -> None:
        """
        Reject truncated, duplicate, invalid-key and trailing project tokens.

        Parameters
        ----------
        source : str
            Malformed OpenStep subset input.
        """
        with pytest.raises(ValueError):
            parse_project(source)

    def test_openstep_comments_arrays_and_quoted_strings(self: Self) -> None:
        """Preserve explicit project scalars and skip comments correctly."""
        assert parse_project('{ a = (one); }') == {'a': ['one']}
        assert parse_project('// c\n{ a = (one, "two words",); /* c */ b = {}; }') == {
            'a': ['one', 'two words'],
            'b': {},
        }

    @pytest.mark.parametrize(
        'actual,expected,equal',
        (
            (False, 0, False),
            ([True], [1], False),
            ({'v': False}, {'v': 0}, False),
            ([], [1], False),
            ({'a': 1}, {'b': 1}, False),
            (1.5, 1.5, True),
        ),
    )
    def test_typed_comparison(
        self: Self,
        actual: object,
        expected: object,
        equal: bool,
    ) -> None:
        """
        Distinguish Boolean, numeric and nested collection expectations.

        Parameters
        ----------
        actual, expected : object
            Native values and configured comparison values.
        equal : bool
            Exact recursive comparison result.
        """
        assert _same(actual, expected) is equal


# !SECTION
