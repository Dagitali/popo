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

        Parameters
        ----------
        reverse : bool
            Whether conflicting CLI arguments appear in reversed order.
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

    @pytest.mark.parametrize(
        'source,kind',
        [
            pytest.param(
                'raise RuntimeError("must not execute")',
                ast.Raise,
                id='raise',
            ),
            pytest.param('import unavailable_fixture_module', ast.Import, id='import'),
            pytest.param('value = unavailable_fixture_call()', ast.Assign, id='call'),
            pytest.param(
                'def f(value=unavailable_fixture_default()): pass',
                ast.FunctionDef,
                id='default-expression',
            ),
        ],
    )
    def test_source_is_not_executed_or_imported(
        self,
        source: str,
        kind: type[ast.AST],
    ) -> None:
        """
        Retain executable syntax as nodes without evaluating any of it.

        Parameters
        ----------
        source : str
            Decoded input text to inspect without executing it.
        kind : type[ast.AST]
            Native syntax kind or policy variant under test.
        """
        tree = _python_syntax.parse(source)
        assert isinstance(tree, ast.Module)
        assert isinstance(tree.body[0], kind)
        assert _python_syntax.documentation_lines((tree,)) == ()

    @pytest.mark.parametrize(
        'prefix,line',
        [
            pytest.param('', 1, id='first-line'),
            pytest.param('\n\n', 3, id='blank-lines'),
            pytest.param('value = "é😀"\n', 2, id='unicode'),
            pytest.param('# PRIVATE comment\r\n\r\n', 3, id='crlf'),
        ],
    )
    def test_syntax_diagnostic_excludes_private_source(
        self,
        prefix: str,
        line: int,
    ) -> None:
        """
        Expose only the caller's filename and native syntax-error line.

        Parameters
        ----------
        prefix : str
            Prefix inserted into the source or configuration input.
        line : int
            Physical source line used in the expected observation.
        """
        with pytest.raises(SyntaxError) as raised:
            _python_syntax.parse(prefix + 'PRIVATE(')
        assert _python_syntax.syntax_findings(raised.value, 'source.py') == [
            f'source.py:{line}: invalid Python source',
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

        Parameters
        ----------
        source : str
            Decoded input text to inspect without executing it.
        """
        tree = _python_syntax.parse(source)
        expected = list(ast.walk(tree))
        actual = list(_python_syntax.nodes(tree))
        assert len(actual) == len(expected)
        assert all(left is right for left, right in zip(actual, expected, strict=True))
        assert actual[0] is tree


# !SECTION
