"""
:mod:`tests.unit.checks.test_u_python_syntax` module.

Verify native Python parsing, physical documentation spans and redaction.
"""

import ast

import pytest

from popo.checks import _python_syntax

# SECTION: TESTS


class TestPythonSyntax:
    """Preserve native AST behavior without importing consumer source."""

    @pytest.mark.parametrize('reverse', (False, True))
    def test_documentation_spans_are_sorted_unique_and_physical(
        self,
        reverse: bool,
    ) -> None:
        """
        Count delimiters and empty docs without counting ordinary literals.
        """
        tree = _python_syntax.parse(
            '"""Overview 😀.\nMore details.\n"""\n'
            'class Ω:\n    """"""\n'
            '    async def f(self):\n        """Details."""\n'
            '        value = "not documentation"\n',
        )
        owners = [
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            )
        ]
        assert _python_syntax.documentation_lines(
            reversed(owners * 2) if reverse else owners * 2,
        ) == (1, 2, 3, 5, 7)

    def test_source_is_not_executed_or_imported(
        self,
    ) -> None:
        """Retain executable syntax as nodes without evaluating any of it."""
        tree = _python_syntax.parse('raise RuntimeError("must not execute")')
        assert isinstance(tree, ast.Module)
        assert isinstance(tree.body[0], ast.Raise)
        assert _python_syntax.documentation_lines((tree,)) == ()

    def test_syntax_diagnostic_excludes_private_source(
        self,
    ) -> None:
        """Expose only the caller's filename and native syntax-error line."""
        with pytest.raises(SyntaxError) as raised:
            _python_syntax.parse('PRIVATE(')
        assert _python_syntax.syntax_findings(raised.value, 'source.py') == [
            'source.py:1: invalid Python source',
        ]


class TestPythonSyntaxTraversal:
    """Keep the common traversal name faithful to native Python semantics."""

    @pytest.mark.parametrize(
        'source',
        (
            'class A:\n    def f(self):\n        return 1\nx = 2',
            'value = f"{(lambda: 1)()}"',
        ),
    )
    def test_nodes_preserve_native_identity_and_breadth_first_order(
        self,
        source: str,
    ) -> None:
        """
        Expose existing AST objects without wrappers or traversal changes.
        """
        tree = _python_syntax.parse(source)
        expected = list(ast.walk(tree))
        actual = list(_python_syntax.nodes(tree))
        assert len(actual) == len(expected)
        assert all(left is right for left, right in zip(actual, expected, strict=True))
        assert actual[0] is tree


# !SECTION
