"""
:mod:`tests.unit.checks.test_u_openstep` module.

Verify the supported OpenStep grammar independently of Apple metadata policy.
"""

from typing import Self

import pytest

from popo.checks._openstep import ProjectValue, parse_project

# SECTION: TESTS


class TestOpenStepSyntax:
    """Test grammar acceptance and rejection apart from project selection."""

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
            pytest.param('}', id='unmatched-brace'),
            pytest.param(')', id='unmatched-parenthesis'),
            pytest.param('=', id='unquoted-equals'),
            pytest.param(';', id='unquoted-semicolon'),
            pytest.param(',', id='unquoted-comma'),
            pytest.param('(,)', id='comma-array-value'),
            pytest.param('(=)', id='equals-array-value'),
            pytest.param('{ ; = value; }', id='delimiter-key'),
            pytest.param('{ key = =; }', id='delimiter-value'),
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

    @pytest.mark.parametrize(
        ('source', 'expected'),
        (
            pytest.param('{ a = (one); }', {'a': ['one']}, id='single-array-item'),
            pytest.param(
                '// c\n{ a = (one, "two words",); /* c */ b = {}; }',
                {'a': ['one', 'two words'], 'b': {}},
                id='comments-arrays-and-quoted-strings',
            ),
            *(
                pytest.param(source, expected, id=f'{shape}-{label}')
                for label, symbol in (
                    ('open-brace', '{'),
                    ('close-brace', '}'),
                    ('open-parenthesis', '('),
                    ('close-parenthesis', ')'),
                    ('equals', '='),
                    ('semicolon', ';'),
                    ('comma', ','),
                )
                for shape, source, expected in (
                    ('scalar', f'"{symbol}"', symbol),
                    ('array', f'("{symbol}")', [symbol]),
                    ('mapping', f'{{ "{symbol}" = "{symbol}"; }}', {symbol: symbol}),
                )
            ),
        ),
    )
    def test_supported_project_values(
        self,
        source: str,
        expected: ProjectValue,
    ) -> None:
        """
        Preserve explicit scalars, arrays, mappings and quoted punctuation.

        Skip comments correctly while retaining quoted strings. Structural
        delimiters remain valid inside quoted scalar values and dictionary
        keys; each grammar form receives an independent test case.

        Parameters
        ----------
        source : str
            Supported OpenStep subset input with comments or quoted delimiters.
        expected : ProjectValue
            Exact native scalar, list or mapping expected from the input.
        """
        assert parse_project(source) == expected


# !SECTION
