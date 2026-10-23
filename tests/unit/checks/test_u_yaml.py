"""
:mod:`tests.unit.checks.test_u_yaml` module.

Verify shared YAML traversal order, cycle handling and deep structures.
"""

import pytest

from popo.checks._yaml import mapping_nodes

# SECTION: TESTS


class TestMappingTraversal:
    """
    Preserve deterministic traversal without recursion or alias duplication.
    """

    @pytest.mark.parametrize('container', ['mapping', 'sequence'])
    def test_deep_containers(self, container: str) -> None:
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


# !SECTION
