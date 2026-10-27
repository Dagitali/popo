"""
:mod:`tests.unit.checks.test_u_python_source` module.

Exercise Python source policy and language-specific findings.
"""

import ast
from pathlib import Path
from textwrap import dedent
from typing import Self

import pytest

from popo.checks import _python_declarations, python_source
from popo.config import ConfigurationError
from popo.config.source_checks import load_source_check
from tests.support.files import FileWriter

# SECTION: TESTS


class TestPythonDocumentation:
    """Match NumPy sections to each callable's own AST contract."""

    def test_complete_contracts_and_nested_scope(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        write_file(
            'popo.toml',
            '[python-source]\ninclude=["*.py"]\nparameter-docs=true\nreturn-docs=true\nraises-docs=true',
        )
        write_file(
            'sample.py',
            dedent('''\
            class C:
                def method(self, a, /, *args, b=None, **kwargs) -> int:
                    """Return an item.

                    Parameters
                    ----------
                    a, b : int
                        Inputs.
                    *args : int
                        Extra inputs.
                    **kwargs : int
                        Named inputs.

                    Returns
                    -------
                    int
                        Result.

                    Raises
                    ------
                    ValueError
                        Invalid input.
                    """
                    raise ValueError()

            def outer():
                def inner():
                    """Yield an item.

                    Yields
                    ------
                    int
                        Item.
                    """
                    yield 1
                class Nested:
                    pass
                supplier = lambda: (yield 1)
                return None
            '''),
        )
        assert (
            python_source.validate(load_source_check(tmp_path, 'python-source')) == []
        )

    @pytest.mark.parametrize(
        ('source', 'option', 'expected'),
        [
            ('class C: pass', 'declaration-docs', 'missing declaration'),
            ('def f(value): pass', 'parameter-docs', 'parameter documentation'),
            ('def f() -> int: return 1', 'return-docs', 'return documentation'),
            ('def f(): yield 1', 'return-docs', 'return documentation'),
            ('def f(): raise ValueError()', 'raises-docs', 'raises documentation'),
            (
                'def f():\n try: pass\n except Exception: raise',
                'raises-docs',
                'raises documentation',
            ),
        ],
    )
    def test_missing_contracts(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
        source: str,
        option: str,
        expected: str,
    ) -> None:
        write_file('popo.toml', f'[python-source]\ninclude=["*.py"]\n{option}=true')
        write_file('sample.py', source)
        findings = python_source.validate(load_source_check(tmp_path, 'python-source'))
        assert len(findings) == 1
        assert expected in findings[0]

    @pytest.mark.parametrize(
        'annotation',
        ['None', 'NoReturn', 'Never', 'typing.NoReturn', 'typing.Never'],
    )
    @pytest.mark.parametrize('quoted', [False, True])
    @pytest.mark.parametrize('body', ['pass', 'return 1'])
    def test_nonvalue_return_annotations(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
        annotation: str,
        quoted: bool,
        body: str,
    ) -> None:
        """
        Treat forward references equally while retaining explicit returns.
        """
        write_file(
            'popo.toml',
            '[python-source]\ninclude=["*.py"]\nreturn-docs=true',
        )
        result_type = repr(annotation) if quoted else annotation
        write_file('sample.py', f'def f() -> {result_type}: {body}')
        findings = python_source.validate(load_source_check(tmp_path, 'python-source'))
        assert findings == (
            ['sample.py:1: return documentation missing'] if body == 'return 1' else []
        )

    @pytest.mark.parametrize(
        'body,return_section,raises',
        [
            ('return 1', 'Returns', False),
            ('yield 1', 'Yields', False),
            ('raise ValueError()', '', True),
        ],
    )
    def test_signature_facts_exclude_body_requirements(
        self: Self,
        body: str,
        return_section: str,
        raises: bool,
    ) -> None:
        """
        Keep native signature annotations separate from explicit body facts.
        """
        source = f'def f(value: int) -> None:\n    {body}\n'
        syntax = ast.parse(source).body[0]
        assert isinstance(syntax, ast.FunctionDef)
        signature = _python_declarations._signature(syntax)
        assert signature.parameter_names == ('value',)
        assert signature.annotated
        assert not signature.returns
        facts = _python_declarations._declaration(syntax).facts
        assert facts.return_section == return_section
        assert facts.raises is raises


class TestPythonSource:
    """Use fresh synthetic policies; never inspect host financial inputs."""

    def test_annotated_multiline_signatures_and_self_exception(
        self: Self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[python-source]\ninclude = ["*.py"]\nannotations = true\n'
            'parameter-lines = true\nalphabetical-methods = true',
        )
        (tmp_path / 'sample.py').write_text(
            'from typing import Self\nclass C:\n'
            ' def a(self: Self) -> None: pass\n'
            ' async def b(\n  self: Self,\n  x: int = 1,\n'
            '  /,\n  *args: int,\n  y: int = 2,\n  **kwargs: int,\n'
            ' ) -> None: pass\n',
        )
        assert (
            python_source.validate(load_source_check(tmp_path, 'python-source')) == []
        )

    @pytest.mark.parametrize('kind', ('missing', 'escaped', 'excluded', 'undecodable'))
    def test_inputs_fail_closed(
        self: Self,
        tmp_path: Path,
        kind: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[python-source]\ninclude = ["*.py"]\nexclude = ["ignored.py"]',
        )
        if kind == 'escaped':
            (tmp_path / 'sample.py').symlink_to(tmp_path.parent / 'outside.py')
        elif kind == 'excluded':
            (tmp_path / 'ignored.py').write_text('x = 1')
        elif kind == 'undecodable':
            (tmp_path / 'sample.py').write_bytes(b'\xff')
        assert python_source.validate(load_source_check(tmp_path, 'python-source'))

    @pytest.mark.parametrize(
        'settings',
        (
            'include = []',
            'include = ["../outside.py"]',
            'include = ["/outside.py"]',
            'include = ["*.py"]\nannotations = 1',
            'include = ["*.py"]\nmax-file-lines = 0',
            'include = ["*.py"]\nunknown = true',
        ),
    )
    def test_invalid_configuration(
        self: Self,
        tmp_path: Path,
        settings: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text('[python-source]\n' + settings)
        with pytest.raises(ConfigurationError):
            load_source_check(tmp_path, 'python-source')

    def test_missing_policy_is_explicit(
        self: Self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(ConfigurationError):
            load_source_check(tmp_path, 'python-source')

    def test_parameter_syntax_retains_native_nodes_and_grouping(
        self: Self,
    ) -> None:
        """
        Keep native parameter locations and the documented grouping order.
        """
        syntax = ast.parse(
            'def f(value: int, /, *args: int, option: int = 0, '
            '**kwargs: int) -> None: pass',
        ).body[0]
        assert isinstance(syntax, ast.FunctionDef)
        parameters = _python_declarations._parameters(syntax)
        assert tuple(parameter.arg for parameter in parameters) == (
            'value',
            'option',
            'args',
            'kwargs',
        )
        assert parameters[0] is syntax.args.posonlyargs[0]
        assert all(isinstance(parameter, ast.arg) for parameter in parameters)
        assert all(parameter.lineno == 1 for parameter in parameters)

    @pytest.mark.parametrize(
        'source,option,diagnostic',
        (
            ('def f(x): pass', 'annotations = true', 'missing signature'),
            ('def f(x: int) -> None: pass', 'parameter-lines = true', 'separate lines'),
            (
                'class C:\n def z(self): pass\n def a(self): pass',
                'alphabetical-methods = true',
                'not alphabetical',
            ),
            (
                '"""Long documentation"""',
                'documentation-width = 10',
                'documentation line',
            ),
            ('x = 1\ny = 2', 'max-file-lines = 1', 'file exceeds'),
            ('def broken(', '', 'invalid Python'),
            ('async def f(x): pass', 'annotations = true', 'missing signature'),
            (
                'def f(\n x: int = (\n  1\n ),\n) -> None: pass',
                'parameter-lines = true',
                'separate lines',
            ),
        ),
    )
    def test_python_rules(
        self: Self,
        tmp_path: Path,
        source: str,
        option: str,
        diagnostic: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[python-source]\ninclude = ["*.py"]\n' + option,
        )
        (tmp_path / 'sample.py').write_text(source)
        findings = python_source.validate(load_source_check(tmp_path, 'python-source'))
        assert any(diagnostic in finding for finding in findings)
        assert all(source not in finding for finding in findings)


# !SECTION
