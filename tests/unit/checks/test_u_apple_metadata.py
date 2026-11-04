"""
:mod:`tests.unit.checks.test_u_apple_metadata` module.

Exercise OpenStep parsing and strict typed Apple metadata comparisons.
"""

from typing import Self

import pytest

from popo.checks._openstep import parse_project
from popo.checks.apple_metadata import _same

# SECTION: TESTS


class TestAppleMetadata:
    """Inspect OpenStep syntax and typed metadata comparisons without tools."""

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
