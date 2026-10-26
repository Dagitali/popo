"""
:mod:`tests.unit.checks.test_u_yaml` module.

Verify shared YAML traversal order, cycle handling and deep structures.
"""

from collections.abc import Callable

import pytest
import yaml

from popo.checks._yaml import mapping_nodes, parse_mapping, read_mapping
from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture(
    name='parse_yaml',
    params=['text', 'file'],
)
def parse_yaml_fixture(
    request: pytest.FixtureRequest,
    write_file: FileWriter,
) -> Callable[[str], dict[str, object]]:
    """Select a parsing boundary with an independent input per scenario."""
    if request.param == 'text':
        return parse_mapping

    def parse(source: str) -> dict[str, object]:
        return read_mapping(write_file('ci.yml', source))

    return parse


# !SECTION


# SECTION: TESTS


class TestMappingTraversal:
    """
    Preserve deterministic traversal without recursion or alias duplication.
    """

    @pytest.mark.parametrize('container', ['mapping', 'sequence'])
    def test_deep_containers(
        self,
        container: str,
    ) -> None:
        """
        Visit mappings beyond Python's recursion limit without recursive calls.
        """
        leaf: dict[str, object] = {'uses': './action'}
        value: object = leaf
        for _ in range(2500):
            value = {'child': value} if container == 'mapping' else [value]
        nodes = list(mapping_nodes(value))
        assert nodes[-1] is leaf
        assert len(nodes) == (2501 if container == 'mapping' else 1)

    def test_order_and_shared_seen_set(self) -> None:
        """
        Keep depth-first order, shared-container deduplication and caller
        state.
        """
        first: dict[str, object] = {'name': 'first'}
        last: dict[str, object] = {'name': 'last'}
        root: dict[str, object] = {'children': [first, first, last]}
        root['cycle'] = root
        seen: set[int] = set()
        assert [id(node) for node in mapping_nodes(root, seen)] == [
            id(root),
            id(first),
            id(last),
        ]
        assert list(mapping_nodes(root, seen)) == []
        assert {id(root), id(root['children']), id(first), id(last)} <= seen


class TestYamlSnapshots:
    """Keep text and file parsing under the same safe mapping contract."""

    @pytest.mark.parametrize('source', ['on: push', 'a: &a {loop: *a}'])
    def test_mapping_inputs(
        self,
        parse_yaml: Callable[[str], dict[str, object]],
        source: str,
    ) -> None:
        """Retain workflow event keys and safely construct cyclic aliases."""
        document = parse_yaml(source)
        if source.startswith('on:'):
            assert document == {'on': 'push'}
        else:
            child = document['a']
            assert isinstance(child, dict)
            assert child['loop'] is child

    @pytest.mark.parametrize(
        'source,error',
        [
            ('', ValueError),
            ('[]', ValueError),
            ('a: 1\na: 2', ValueError),
            ('1: value', ValueError),
            ('[', yaml.YAMLError),
            ('!!python/object:builtins.object {}', yaml.YAMLError),
        ],
    )
    def test_invalid_inputs(
        self,
        parse_yaml: Callable[[str], dict[str, object]],
        source: str,
        error: type[Exception],
    ) -> None:
        """Reject unsafe or malformed inputs with both parsing interfaces."""
        with pytest.raises(error):
            parse_yaml(source)

    def test_mapping_label_is_preserved(self) -> None:
        """Label shape errors consistently without requiring a source file."""
        with pytest.raises(ValueError, match='workflow must be a mapping'):
            parse_mapping('null', label='workflow')


# !SECTION
