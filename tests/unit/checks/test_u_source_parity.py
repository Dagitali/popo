"""
:mod:`tests.unit.checks.test_u_source_parity` module.

Verify shared source-policy contracts and language-specific documentation.
"""

import ast
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Self
from unittest.mock import Mock, call, patch

import pytest

from popo.checks import (
    _python_declarations,
    _python_syntax,
    _source_inputs,
    _swift_declarations,
    _swift_syntax,
    logs,
    python_source,
    swift_source,
)
from popo.checks._source_declarations import (
    CallableRequirements,
    ParameterSpan,
    ResultSection,
    parameter_lines,
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

    @pytest.mark.parametrize('case', ['none', 'returns', 'raises'])
    def test_callable_documentation_requirements(
        self: Self,
        source_case: SourceCase,
        case: str,
    ) -> None:
        """
        Share requirement vocabulary while retaining each analysis source.
        """
        domain, _, _ = source_case
        if domain == 'python-source':
            annotation, body = {
                'none': ('None', 'pass'),
                'returns': ('int', 'return 1'),
                'raises': ('None', 'raise ValueError()'),
            }[case]
            syntax = ast.parse(f'def f() -> {annotation}: {body}').body[0]
            assert isinstance(syntax, ast.FunctionDef)
            requirements = _python_declarations._requirements(
                syntax,
                _python_declarations._signature(syntax),
            )
        else:
            tail = {
                'none': '',
                'returns': ' -> Int',
                'raises': ' rethrows -> Void',
            }[case]
            requirements = _swift_declarations._requirements('func', tail)
        assert requirements == CallableRequirements(
            'Returns' if case == 'returns' else '',
            case == 'raises',
        )

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
        assert facts.result_section == 'Returns'
        assert facts.exception_required
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
        assert callable_.result_section == 'Returns'
        assert not callable_.exception_required

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

    @pytest.mark.parametrize(
        'python_text,swift_text,python_overview,swift_overview',
        [
            pytest.param('', '', False, False, id='empty'),
            pytest.param(
                '"""Overview."""\nvalue = 1',
                '/// Overview.\nlet value = 1',
                True,
                True,
                id='leading',
            ),
            pytest.param(
                'value = 1\n"""Late documentation."""',
                'let value = 1\n/// Late documentation.',
                False,
                False,
                id='after-code',
            ),
            pytest.param(
                'value = """Literal text."""',
                'let value = "/// Literal text."',
                False,
                False,
                id='literal-decoy',
            ),
            pytest.param(
                'class C:\n    """Declaration documentation."""',
                '/// Declaration documentation.\nstruct C {}',
                False,
                True,
                id='declaration-documentation',
            ),
        ],
    )
    def test_file_overview_conventions(
        self: Self,
        source_case: SourceCase,
        python_text: str,
        swift_text: str,
        python_overview: bool,
        swift_overview: bool,
    ) -> None:
        """Preserve each language's leading file-documentation convention."""
        domain, _, _ = source_case
        if domain == 'python-source':
            parsed = _python_declarations.parse(python_text)
            assert parsed.has_overview is python_overview
        else:
            parsed = _swift_declarations.parse(swift_text)
            assert parsed.has_overview is swift_overview

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
            assert inner.result_section == 'Yields'
            assert inner.exception_required
        else:
            parsed = _swift_declarations.parse(
                'func outer() {\n'
                '    func inner(value: Int) throws -> Int { value }\n}\n',
            )
            assert len(parsed.declarations) == 1
        outer = parsed.declarations[0].facts
        assert outer.parameter_names == ()
        assert outer.result_section == ''
        assert not outer.exception_required

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

    @pytest.mark.parametrize('multiline', [False, True])
    def test_signature_observation_names_and_layout(
        self: Self,
        source_case: SourceCase,
        multiline: bool,
    ) -> None:
        """
        Keep signature record roles aligned across native and lexical input.
        """
        domain, _, _ = source_case
        if domain == 'python-source':
            parameters = '\n    value: int,\n' if multiline else 'value: int'
            source = f'def f({parameters}) -> int: return value'
            syntax = ast.parse(source).body[0]
            assert isinstance(syntax, ast.FunctionDef)
            signature = _python_declarations._signature(syntax)
            assert signature.annotated
            assert signature.returns
        else:
            parameters = '\n    value: Int\n' if multiline else 'value: Int'
            source = f'func f({parameters}) -> Int {{ value }}'
            code, _ = _swift_declarations.lexical_view(source)
            signature = _swift_declarations._signature(code, len('func'))
            assert signature.tail.strip() == '-> Int'
            assert code[signature.end] == '{'
        assert signature.parameter_names == ('value',)
        assert signature.parameter_lines is multiline

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
        assert facts.result_section == ('' if kind == 'nominal' else 'Returns')
        assert not facts.exception_required


class TestSourceInputDiscovery:
    """Retain matches across overlapping patterns and partial traversals."""

    @pytest.mark.parametrize('interrupted', (False, True))
    def test_overlapping_patterns_retain_partial_matches(
        self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        interrupted: bool,
    ) -> None:
        """Deduplicate paths without treating repeated matches as missing."""
        domain, filename, _ = source_case
        path = write_file(filename, 'PRIVATE source')
        before = snapshot_files(tmp_path)
        config = SourceCheckConfig(
            tmp_path,
            domain,
            ('first', 'second', 'missing'),
            (),
            {},
        )

        def glob(
            directory: Path,
            pattern: str,
        ) -> Iterator[Path]:
            """Yield a repeated match before an optional traversal failure."""
            assert directory == tmp_path
            if pattern != 'missing':
                yield path
            if interrupted and pattern == 'first':
                raise OSError('PRIVATE traversal error')

        with monkeypatch.context() as scoped:
            scoped.setattr(Path, 'glob', glob)
            paths, failures = _source_inputs.discover(config)
        assert paths == [path]
        assert failures == [
            *(['cannot discover configured source inputs'] if interrupted else []),
            'no inputs match: missing',
        ]
        assert snapshot_files(tmp_path) == before


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

    def test_diagnostic_order_across_selected_files(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """Report discovery and guide failures before sorted file findings."""
        domain, filename, validate = source_case
        suffix = Path(filename).suffix
        first, last = f'a{suffix}', f'z{suffix}'
        write_file(
            'popo.toml',
            f'[{domain}]\ninclude=["*{suffix}", "missing{suffix}"]\n'
            'file-overviews=true\nsource-guide="Guide.md"',
        )
        write_file(last, 'value = 1')
        write_file(first, '').write_bytes(b'\xff')
        before = snapshot_files(tmp_path)
        assert validate(load_source_check(tmp_path, domain)) == [
            f'no inputs match: missing{suffix}',
            'Guide.md: cannot read UTF-8 input',
            f'{first}: cannot read UTF-8 input',
            f'{last}: missing file overview',
        ]
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


class TestParsedSourceEvaluation:
    """Keep shared evaluation order independent of native parser behavior."""

    def test_limits_documentation_and_conventions_keep_order(
        self,
        source_case: SourceCase,
        tmp_path: Path,
    ) -> None:
        """Report limits before documentation and signature-layout findings."""
        domain, filename, validate = source_case
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude=["{filename}"]\nmax-file-lines=1\n'
            'file-overviews=true\ndeclaration-docs=true\nparameter-lines=true\n'
            + ('member-docs=true\n' if domain == 'swift-source' else ''),
            encoding='utf-8',
        )
        (tmp_path / filename).write_text(
            'def f(value: int):\n    pass'
            if domain == 'python-source'
            else 'func f(value: Int) {\n}',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        findings = validate(load_source_check(tmp_path, domain))
        assert findings[0] == f'{filename}: file exceeds configured line limit'
        assert 'overview' in findings[1]
        assert findings[2] == f'{filename}:1: missing declaration documentation'
        assert findings[3] == f'{filename}:1: parameters require separate lines'
        assert len(findings) == 4
        assert snapshot_files(tmp_path) == before


class TestNativeSyntaxContracts:
    """
    Preserve comparable locations and purposeful parser-failure semantics.
    """

    def test_native_failure_and_recovery_remain_distinct(
        self,
        source_case: SourceCase,
    ) -> None:
        """
        Reject invalid Python but retain explicit unsupported Swift facts.
        """
        domain, _, _ = source_case
        if domain == 'python-source':
            with pytest.raises(SyntaxError):
                _python_declarations.parse('def broken(')
        else:
            parsed = _swift_declarations.parse('func broken(')
            assert len(parsed.declarations) == 1
            assert parsed.declarations[0].facts.parameter_names is None

    @pytest.mark.parametrize(
        'parser',
        (_python_syntax.parse, _swift_syntax.parse),
        ids=('python', 'swift'),
    )
    def test_native_parsers_reject_unencodable_text(
        self,
        parser: Callable[[str], object],
    ) -> None:
        """
        Expose the same UTF-8 encoding contract for direct parser callers.
        """
        with pytest.raises(UnicodeEncodeError):
            parser('\ud800')

    def test_unicode_declaration_locations(
        self,
        source_case: SourceCase,
    ) -> None:
        """
        Use physical declaration lines regardless of UTF-8 identifier width.
        """
        domain, _, _ = source_case
        parsed = (
            _python_declarations.parse('"""Overview 😀."""\nclass Ω:\n    pass')
            if domain == 'python-source'
            else _swift_declarations.parse('/// Overview 😀.\nstruct Ω {}')
        )
        assert parsed.has_overview
        assert parsed.documentation_lines == (1,)
        assert len(parsed.declarations) == 1
        assert parsed.declarations[0].facts.line == 2
        assert parsed.declarations[0].facts.kind == (
            'class' if domain == 'python-source' else 'struct'
        )


class TestCallableRequirementNormalization:
    """
    Select shared vocabulary after each language collects native evidence.
    """

    @pytest.mark.parametrize('exceptions', (False, True))
    @pytest.mark.parametrize(
        'returns,yields,section',
        (
            (False, False, ''),
            (True, False, 'Returns'),
            (False, True, 'Yields'),
            (True, True, 'Yields'),
        ),
    )
    def test_result_priority_and_independent_exception_requirements(
        self,
        returns: bool,
        yields: bool,
        exceptions: bool,
        section: ResultSection,
    ) -> None:
        """Keep generator priority and preserve the native exception flag."""
        result = CallableRequirements.from_observations(
            returns=returns,
            yields=yields,
            exceptions=exceptions,
        )
        assert result == CallableRequirements(section, exceptions)
        assert result.result_section == section
        assert result.exception_required is exceptions


class TestParameterLayout:
    """
    Evaluate comparable spans while preserving native parameter discovery.
    """

    @pytest.mark.parametrize(
        'spans,expected',
        (
            ((), True),
            (((2, 2),), True),
            (((3, 3), (2, 2)), True),
            (((1, 1),), False),
            (((0, 0),), False),
            (((2, 3),), False),
            (((2, None),), False),
            (((2, 2), (2, 2)), False),
        ),
    )
    def test_distinct_single_line_spans_follow_the_declaration(
        self,
        spans: tuple[tuple[int, int | None], ...],
        expected: bool,
    ) -> None:
        """
        Accept unordered iterators and reject each physical-layout failure.
        """
        assert (
            parameter_lines(
                1,
                (ParameterSpan(start, end) for start, end in spans),
            )
            is expected
        )


class TestSourceInspection:
    """Keep shared reads ordered, redacted and independent of domain policy."""

    def test_inspector_failures_propagate(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Propagate inspector failures instead of reporting partial success.
        """
        path = tmp_path / 'input'
        path.write_text('text', encoding='utf-8')
        error = RuntimeError('inspection failed')
        inspect = Mock(side_effect=error)
        with pytest.raises(
            RuntimeError,
            match='inspection failed',
            check=lambda raised: raised is error,
        ):
            _source_inputs.inspect_sources((path,), tmp_path, inspect)

    @pytest.mark.parametrize('failure', ('decode', 'missing'))
    def test_reads_once_and_continues_after_input_errors(
        self,
        tmp_path: Path,
        failure: str,
    ) -> None:
        """
        Retain duplicate findings and skip inspection of unreadable inputs.
        """
        first, bad, last = (tmp_path / name for name in ('first', 'bad', 'last'))
        first.write_text('one', encoding='utf-8')
        last.write_text('two', encoding='utf-8')
        if failure == 'decode':
            bad.write_bytes(b'PRIVATE\xff')
        paths = (first, bad, last)
        before = snapshot_files(tmp_path)
        inspect = Mock(side_effect=lambda path, source: iter((path.name,) * 2))
        with patch.object(
            _source_inputs,
            'read_source',
            wraps=_source_inputs.read_source,
        ) as read:
            findings = _source_inputs.inspect_sources(iter(paths), tmp_path, inspect)
        assert findings == [
            'first',
            'first',
            'bad: cannot read UTF-8 input',
            'last',
            'last',
        ]
        assert read.call_args_list == [call(path, tmp_path) for path in paths]
        assert inspect.call_args_list == [call(first, 'one'), call(last, 'two')]
        assert snapshot_files(tmp_path) == before


# !SECTION
