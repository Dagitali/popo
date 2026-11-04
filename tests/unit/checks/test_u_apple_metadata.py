"""
:mod:`tests.unit.checks.test_u_apple_metadata` module.

Exercise OpenStep parsing and strict typed Apple metadata comparisons.
"""

import json
from copy import deepcopy
from typing import Self

import pytest

from popo.checks._openstep import parse_project
from popo.checks.apple_metadata import _same, _settings
from popo.config.apple_metadata import AppleRule

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

    def test_openstep_comments_arrays_and_quoted_strings(self: Self) -> None:
        """Preserve explicit project scalars and skip comments correctly."""
        assert parse_project('{ a = (one); }') == {'a': ['one']}
        assert parse_project('// c\n{ a = (one, "two words",); /* c */ b = {}; }') == {
            'a': ['one', 'two words'],
            'b': {},
        }

    @pytest.mark.parametrize('symbol', tuple('{}()=;,'))
    def test_quoted_delimiters_remain_strings(
        self,
        symbol: str,
    ) -> None:
        """
        Preserve quoted punctuation as scalar values and dictionary keys.

        Parameters
        ----------
        symbol : str
            Structural delimiter that is valid only inside a quoted string.
        """
        quoted = json.dumps(symbol)
        assert parse_project(quoted) == symbol
        assert parse_project(f'({quoted})') == [symbol]
        assert parse_project(f'{{ {quoted} = {quoted}; }}') == {symbol: symbol}

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


class TestProjectConfigurationSelection:
    """Keep native configuration lookup ordered and ambiguity-aware."""

    @pytest.mark.parametrize(
        ('names', 'selected', 'expected'),
        (
            pytest.param(
                ('Debug', 'Release'),
                ('Release', 'Debug'),
                (1, 0),
                id='order',
            ),
            pytest.param(('Debug', 'Debug'), ('Debug',), None, id='selected-duplicate'),
            pytest.param(
                ('Debug', 'Release', 'Release'),
                ('Debug',),
                (0,),
                id='unselected-duplicate',
            ),
            pytest.param(('Debug', []), ('Debug',), (0,), id='unselected-list-name'),
            pytest.param(('Debug', {}), ('Debug',), (0,), id='unselected-mapping-name'),
            pytest.param(('Debug',), ('Release',), None, id='missing-selection'),
        ),
    )
    def test_native_configuration_selection(
        self,
        names: tuple[object, ...],
        selected: tuple[str, ...],
        expected: tuple[int, ...] | None,
    ) -> None:
        """
        Preserve selection order and native identities when indexing names.

        Parameters
        ----------
        names : tuple[object, ...]
            Literal configuration names, including malformed unselected names.
        selected : tuple[str, ...]
            Requested names in consumer-defined result order.
        expected : tuple[int, ...] | None
            Expected source-object indices, or None for missing/ambiguous names.
        """
        configs = {
            str(index): {
                'isa': 'XCBuildConfiguration',
                'name': name,
                'buildSettings': {'index': index},
            }
            for index, name in enumerate(names)
        }
        project = {
            'rootObject': 'project',
            'objects': configs
            | {
                'project': {'isa': 'PBXProject', 'buildConfigurationList': 'list'},
                'list': {
                    'isa': 'XCConfigurationList',
                    'buildConfigurations': list(configs),
                },
            },
        }
        rule = AppleRule('selection', 'project', 'xcode', {}, (), '', selected, ())
        before = deepcopy(project)
        if expected is None:
            with pytest.raises(
                ValueError,
                match='^expected one named build configuration$',
            ):
                _settings(project, rule)
        else:
            actual = _settings(project, rule)
            assert actual == [{'index': index} for index in expected]
            assert all(
                item is configs[str(index)]['buildSettings']
                for item, index in zip(actual, expected, strict=True)
            )
        assert project == before


# !SECTION
