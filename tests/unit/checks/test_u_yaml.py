"""
:mod:`tests.unit.checks.test_u_yaml` module.

Verify safe YAML parsing, traversal order, cycles and deep structures.
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
    """
    Select a parsing boundary with an independent input per scenario.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest request carrying the selected fixture parameter.
    write_file : FileWriter
        Fixture writing UTF-8 files beneath the temporary consumer root.

    Returns
    -------
    Callable[[str], dict[str, object]]
        Callable writing and parsing YAML within the temporary consumer.
    """
    if request.param == 'text':
        return parse_mapping

    def parse(
        source: str,
    ) -> dict[str, object]:
        """
        Write YAML to a temporary input and return its parsed mapping.

        Parameters
        ----------
        source : str
            Decoded input text to inspect without executing it.

        Returns
        -------
        dict[str, object]
            Parsed YAML mapping from the written scenario input.
        """
        return read_mapping(write_file('ci.yml', source))

    return parse


# !SECTION


# SECTION: TESTS


class TestMappingTraversal:
    """
    Cover mapping traversal.

    Preserve deterministic traversal without recursion or alias duplication.
    """

    @pytest.mark.parametrize('container', ['mapping', 'sequence'])
    def test_deep_containers(
        self,
        container: str,
    ) -> None:
        """
        Visit mappings beyond Python's recursion limit without recursive calls.

        Parameters
        ----------
        container : str
            Container syntax used to surround the scenario input.
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
        Verify order and shared seen set.

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

    @pytest.mark.parametrize('container', ('mapping', 'sequence'))
    def test_partial_consumption_tracks_only_reached_containers(
        self,
        container: str,
    ) -> None:
        """
        Retain native identities and caller state while traversal is paused.

        Parameters
        ----------
        container : str
            Whether siblings belong to a mapping or sequence.
        """
        first: dict[str, object] = {'name': 'first'}
        last: dict[str, object] = {'name': 'last'}
        root: dict[str, object] | list[object] = (
            {'first': first, 'last': last} if container == 'mapping' else [first, last]
        )
        seen: set[int] = set()
        traversal = mapping_nodes(root, seen)
        if container == 'mapping':
            assert next(traversal) is root
        assert next(traversal) is first
        assert seen == {id(root), id(first)}
        assert next(traversal) is last
        assert list(traversal) == []
        assert seen == {id(root), id(first), id(last)}
        assert root == (
            {'first': first, 'last': last} if container == 'mapping' else [first, last]
        )

    @pytest.mark.parametrize('container', ('mapping', 'sequence'))
    def test_previsited_shared_containers_skip_their_descendants(
        self,
        container: str,
    ) -> None:
        """
        Skip caller-visited aliases without suppressing independent siblings.

        Parameters
        ----------
        container : str
            Container variant shared between two parent paths.
        """
        hidden: dict[str, object] = {'name': 'hidden'}
        shared: dict[str, object] | list[object] = (
            {'child': hidden} if container == 'mapping' else [hidden]
        )
        visible: dict[str, object] = {'name': 'visible'}
        root: dict[str, object] = {
            'first': shared,
            'second': [shared, visible],
        }
        root['cycle'] = root
        seen = {id(shared)}
        assert [id(node) for node in mapping_nodes(root, seen)] == [
            id(root),
            id(visible),
        ]
        assert id(hidden) not in seen
        assert {id(root), id(shared), id(root['second']), id(visible)} == seen

    @pytest.mark.parametrize('value', (None, False, 0, '', 'PRIVATE', (), set()))
    def test_scalars_do_not_change_caller_state(
        self,
        value: object,
    ) -> None:
        """
        Ignore values outside the mapping/list traversal contract.

        Parameters
        ----------
        value : object
            Scalar or unsupported container that supplies no mapping nodes.
        """
        seen = {123}
        assert list(mapping_nodes(value, seen)) == []
        assert seen == {123}


class TestYamlSnapshots:
    """Keep text and file parsing under the same safe mapping contract."""

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
        """
        Reject unsafe or malformed inputs with both parsing interfaces.

        Parameters
        ----------
        parse_yaml : Callable[[str], dict[str, object]]
            Fixture parser writing YAML to an isolated consumer input.
        source : str
            Decoded input text to inspect without executing it.
        error : type[Exception]
            Error value or exception class injected by the scenario.
        """
        with pytest.raises(error):
            parse_yaml(source)

    @pytest.mark.parametrize('source', ['on: push', 'a: &a {loop: *a}'])
    def test_mapping_inputs(
        self,
        parse_yaml: Callable[[str], dict[str, object]],
        source: str,
    ) -> None:
        """
        Retain workflow event keys and safely construct cyclic aliases.

        Parameters
        ----------
        parse_yaml : Callable[[str], dict[str, object]]
            Fixture parser writing YAML to an isolated consumer input.
        source : str
            Decoded input text to inspect without executing it.
        """
        document = parse_yaml(source)
        if source.startswith('on:'):
            assert document == {'on': 'push'}
        else:
            child = document['a']
            assert isinstance(child, dict)
            assert child['loop'] is child

    def test_mapping_label_is_preserved(self) -> None:
        """Label shape errors consistently without requiring a source file."""
        with pytest.raises(ValueError, match='workflow must be a mapping'):
            parse_mapping('null', label='workflow')


# !SECTION
