"""
:mod:`tests.unit.checks.test_u_source_parity` module.

Verify shared source-policy contracts and language-specific documentation.
"""

import ast
from collections.abc import Callable
from pathlib import Path
from typing import Self
from unittest.mock import patch

import pytest

from popo.checks import (
    _python_declarations,
    _swift_declarations,
    logs,
    python_source,
    swift_source,
)
from popo.config import ConfigurationError
from popo.config.source_checks import SourceCheckConfig, load_source_check
from tests.support.files import FileWriter, snapshot_files

# SECTION: TYPE ALIASES


type SourceCase = tuple[str, str, Callable[[SourceCheckConfig], list[str]]]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(
    name='source_case',
    params=['python', 'swift'],
)
def source_case_fixture(
    request: pytest.FixtureRequest,
) -> SourceCase:
    """Select independent language cases sharing discovery and limit rules."""
    return (
        ('python-source', 'sample.py', python_source.validate)
        if request.param == 'python'
        else ('swift-source', 'sample.swift', swift_source.validate)
    )


# !SECTION


# SECTION: TESTS


class TestSourceConventions:
    """
    Keep common option names, diagnostics and collector contracts aligned.
    """

    def test_collectors_extract_shared_facts_without_execution(
        self: Self,
        source_case: SourceCase,
    ) -> None:
        domain, _, _ = source_case
        parsed = (
            _python_declarations.parse(
                '"""Overview."""\nraise RuntimeError("must not execute")\n'
                'def f(value: int) -> int:\n'
                ' """Return an item."""\n raise ValueError()',
            )
            if domain == 'python-source'
            else _swift_declarations.parse(
                '/// Overview.\nimport Foundation\n\n/// Return an item.\n'
                'func f(value: Int) throws -> Int { value }',
            )
        )
        assert parsed.has_overview
        assert parsed.documentation_lines
        assert len(parsed.declarations) == 1
        facts = parsed.declarations[0].facts
        assert facts.parameter_names == ('value',)
        assert facts.return_section == 'Returns'
        assert facts.raises
        assert facts.documentation.strip() == 'Return an item.'

    def test_collectors_keep_nominal_and_callable_facts(
        self: Self,
        source_case: SourceCase,
    ) -> None:
        """
        Retain documentation, locations and language-specific observations.
        """
        domain, _, _ = source_case
        if domain == 'python-source':
            parsed = _python_declarations.parse(
                '"""Overview."""\n'
                'class Container:\n'
                '    """Container documentation."""\n'
                '    def method(\n'
                '        self,\n'
                '        value: int,\n'
                '    ) -> int:\n'
                '        """Callable documentation."""\n'
                '        return value\n',
            )
            assert parsed.declarations[0].instance_methods == ('method',)
            assert not parsed.declarations[1].annotated
            assert parsed.documentation_lines == (1, 3, 8)
            expected_locations = (2, 4)
        else:
            parsed = _swift_declarations.parse(
                '/// Overview.\nimport Foundation\n\n'
                '/// Container documentation.\n@MainActor\nstruct Container {\n\n'
                '    /// Callable documentation.\n'
                '    @MainActor\n'
                '    func method(\n'
                '        value: Int\n'
                '    ) -> Int { value }\n}\n',
            )
            assert parsed.declarations[0].documentation_start == 4
            assert parsed.declarations[1].documentation_start == 8
            assert all(item.separated for item in parsed.declarations)
            assert parsed.documentation_lines == (1, 4, 8)
            expected_locations = (6, 10)
        assert parsed.has_overview
        nominal, callable_ = (item.facts for item in parsed.declarations)
        assert (nominal.line, callable_.line) == expected_locations
        assert nominal.documentation.strip() == 'Container documentation.'
        assert nominal.parameter_names == ()
        assert callable_.documentation.strip() == 'Callable documentation.'
        assert callable_.parameter_names == ('value',)
        assert callable_.parameter_lines
        assert callable_.return_section == 'Returns'
        assert not callable_.raises

    def test_common_diagnostics(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        domain, filename, validate = source_case
        write_file(
            'popo.toml',
            f'[{domain}]\ninclude=["{filename}"]\n'
            'documentation-width=10\nmax-file-lines=1\nfile-overviews=false',
        )
        source = (
            '"""Long documentation."""\nx=1'
            if domain == 'python-source'
            else '/// Long documentation.\nlet x=1'
        )
        write_file(filename, source)
        assert validate(load_source_check(tmp_path, domain)) == [
            f'{filename}: file exceeds configured line limit',
            f'{filename}:1: documentation line too long',
        ]

    def test_nested_callable_discovery_remains_language_specific(
        self: Self,
        source_case: SourceCase,
    ) -> None:
        """Keep AST nesting and lexical callable-body exclusion distinct."""
        domain, _, _ = source_case
        if domain == 'python-source':
            parsed = _python_declarations.parse(
                'def outer() -> None:\n'
                '    def inner(value: int, *args: int, option: int, **kwargs: int):\n'
                '        yield value\n'
                '        raise ValueError()\n',
            )
            assert len(parsed.declarations) == 2
            inner = parsed.declarations[1].facts
            assert inner.parameter_names == ('value', 'option', 'args', 'kwargs')
            assert inner.return_section == 'Yields'
            assert inner.raises
        else:
            parsed = _swift_declarations.parse(
                'func outer() {\n'
                '    func inner(value: Int) throws -> Int { value }\n}\n',
            )
            assert len(parsed.declarations) == 1
        outer = parsed.declarations[0].facts
        assert outer.parameter_names == ()
        assert outer.return_section == ''
        assert not outer.raises

    @pytest.mark.parametrize('setting', ['docstring-width=79', 'max-module-lines=1000'])
    def test_prerelease_option_names_are_rejected(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        setting: str,
    ) -> None:
        domain, filename, _ = source_case
        write_file('popo.toml', f'[{domain}]\ninclude=["{filename}"]\n{setting}')
        with pytest.raises(ConfigurationError, match='unknown settings'):
            load_source_check(tmp_path, domain)

    @pytest.mark.parametrize('kind', ['nominal', 'callable'])
    def test_single_declaration_conversion(
        self: Self,
        source_case: SourceCase,
        kind: str,
    ) -> None:
        """
        Convert a single nominal or callable independently of aggregation.
        """
        domain, _, _ = source_case
        if domain == 'python-source':
            source = (
                'class C:\n    """Details."""\n'
                if kind == 'nominal'
                else 'def f(value: int) -> int:\n    """Details."""\n    return value\n'
            )
            syntax = ast.parse(source).body[0]
            assert isinstance(syntax, (ast.ClassDef, ast.FunctionDef))
            declaration = _python_declarations._declaration(syntax)
            assert declaration.annotated
        else:
            source = '/// Details.\n' + (
                'struct C {}'
                if kind == 'nominal'
                else 'func f(value: Int) -> Int { value }'
            )
            code, documentation = _swift_declarations.lexical_view(source)
            syntax = next(_swift_declarations._declaration_syntax(code))
            declaration = _swift_declarations._declaration(
                syntax,
                source.splitlines(),
                documentation,
            )
            assert declaration.documentation_start == 1
            assert declaration.separated
        facts = declaration.facts
        assert facts.documentation.strip() == 'Details.'
        assert facts.parameter_names == (() if kind == 'nominal' else ('value',))
        assert facts.return_section == ('' if kind == 'nominal' else 'Returns')
        assert not facts.raises


class TestSourceInputFailures:
    """Keep discovery/read errors redacted and equivalent across languages."""

    @pytest.mark.parametrize('kind', ['decode', 'directory', 'inspect', 'glob'])
    def test_failed_inputs(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        kind: str,
    ) -> None:
        domain, filename, validate = source_case
        write_file('popo.toml', f'[{domain}]\ninclude=["{filename}"]')
        path = tmp_path / filename
        if kind == 'directory':
            path.mkdir()
        else:
            path.write_bytes(b'\xff' if kind == 'decode' else b'value = 1')
        config = load_source_check(tmp_path, domain)
        if kind in {'inspect', 'glob'}:
            operation = 'is_file' if kind == 'inspect' else 'glob'
            with patch.object(Path, operation, side_effect=PermissionError('PRIVATE')):
                failures = validate(config)
        else:
            failures = validate(config)
        assert failures
        assert 'PRIVATE' not in '\n'.join(failures)

    def test_undecodable_logs_do_not_disclose_content(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        write_file(
            'popo.toml',
            '[logs]\ninclude=["*.log"]\npatterns={ warning="WARNING" }',
        )
        (tmp_path / 'private.log').write_bytes(b'PRIVATE\xff')
        assert logs.validate(load_source_check(tmp_path, 'logs')) == [
            'private.log: cannot read UTF-8 input',
        ]


class TestSourceParity:
    """Require common behavior without executing either language's source."""

    @pytest.mark.parametrize('setting', ['max-file-lines = 1', 'file-overviews = true'])
    def test_common_limits(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        setting: str,
    ) -> None:
        domain, filename, validate = source_case
        write_file('popo.toml', f'[{domain}]\ninclude=["{filename}"]\n{setting}')
        write_file(filename, 'value = 1\nvalue = 2')
        before = snapshot_files(tmp_path)
        findings = validate(load_source_check(tmp_path, domain))
        assert any(
            ('file exceeds' if 'max-' in setting else 'missing file overview') in f
            for f in findings
        )
        assert snapshot_files(tmp_path) == before

    def test_documentation_width_and_guide(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        domain, filename, validate = source_case
        write_file(
            'popo.toml',
            f'[{domain}]\ninclude=["{filename}"]\ndocumentation-width=10\nsource-guide="Guide.md"',
        )
        source = (
            '"""Long overview."""'
            if domain == 'python-source'
            else '/// Long overview.\nlet x = 1'
        )
        write_file(filename, source)
        guide = write_file('Guide.md', f'`other/{filename}`')
        findings = validate(load_source_check(tmp_path, domain))
        assert any('line too long' in f for f in findings)
        assert any('missing source-guide entry' in f for f in findings)
        guide.write_text(f'`{filename}`', encoding='utf-8')
        assert not any(
            'source-guide' in f for f in validate(load_source_check(tmp_path, domain))
        )

    @pytest.mark.parametrize('kind', ['absent', 'decode', 'escape', 'resolve'])
    def test_guide_failures_are_diagnostics(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        symlink: Callable[[Path, Path], None],
        kind: str,
    ) -> None:
        domain, filename, validate = source_case
        write_file(
            'popo.toml',
            f'[{domain}]\ninclude=["{filename}"]\nsource-guide="Guide.md"',
        )
        write_file(
            filename,
            '"""Overview."""'
            if domain == 'python-source'
            else '/// Overview.\nlet x = 1',
        )
        guide = tmp_path / 'Guide.md'
        if kind == 'decode':
            guide.write_bytes(b'\xff')
        elif kind == 'escape':
            symlink(guide, tmp_path.parent / 'external-guide')
        if kind == 'resolve':
            config = load_source_check(tmp_path, domain)
            with patch.object(Path, 'resolve', side_effect=ValueError('PRIVATE PATH')):
                findings = validate(config)
        else:
            findings = validate(load_source_check(tmp_path, domain))
        assert findings
        assert 'PRIVATE' not in '\n'.join(findings)

    @pytest.mark.parametrize(
        'setting',
        [
            'source-guide="../Guide.md"',
            'source-guide="/Guide.md"',
            'parameter-docs=1',
            'return-docs="true"',
            'raises-docs=[]',
        ],
    )
    def test_invalid_shared_options(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        setting: str,
    ) -> None:
        domain, filename, _ = source_case
        write_file('popo.toml', f'[{domain}]\ninclude=["{filename}"]\n{setting}')
        with pytest.raises(ConfigurationError):
            load_source_check(tmp_path, domain)


# !SECTION
