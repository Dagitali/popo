"""
:mod:`tests.unit.checks.test_u_documentation_parity` module.

Compare callable documentation evidence without merging markup conventions.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.checks import (
    _python_declarations,
    _python_documentation,
    _swift_declarations,
    _swift_documentation,
)
from popo.checks._source_declarations import DeclarationFacts, ResultSection
from popo.checks._source_documentation import (
    CallableDocumentation,
    DocumentationDialect,
    DocumentationInterpreter,
    DocumentationPresence,
    callable_findings,
    contract_findings,
)
from popo.config.source_checks import DOMAINS, SourceCheckConfig

# SECTION: TYPE ALIASES


type DocumentationCase = tuple[str, DocumentationInterpreter]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(name='documentation_case', params=['numpy', 'docc'])
def documentation_case_fixture(
    request: pytest.FixtureRequest,
) -> DocumentationCase:
    """Select an independent markup interpreter with a common evidence type."""
    style = str(request.param)
    interpret = (
        _python_documentation._documentation
        if style == 'numpy'
        else _swift_documentation._documentation
    )
    return style, interpret


# !SECTION


# SECTION: TESTS


class TestCallableDocumentation:
    """Keep comparable evidence separate from declaration requirements."""

    @pytest.mark.parametrize('present', [False, True])
    def test_contract_diagnostics(
        self,
        documentation_case: DocumentationCase,
        tmp_path: Path,
        present: bool,
    ) -> None:
        """Compare parsed evidence with the same explicit callable contract."""
        style, interpret = documentation_case
        doc = {
            'numpy': 'Parameters\n----------\nvalue : int\n    Input.\n\n'
            'Returns\n-------\nint\n    Result.\n\n'
            'Raises\n------\nValueError\n    Invalid input.\n',
            'docc': '- Parameter value: Input.\n- Returns: Result.\n'
            '- Throws: Invalid input.\n',
        }[style]
        facts = DeclarationFacts(7, 'function', '', ('value',), 'Returns', True)
        config = SourceCheckConfig(
            tmp_path,
            'python-source' if style == 'numpy' else 'swift-source',
            (),
            (),
            {'parameter-docs': True, 'return-docs': True, 'raises-docs': True},
        )
        findings = contract_findings(
            facts,
            config,
            'sample',
            interpret(doc if present else '', 'Returns'),
        )
        assert findings == (
            []
            if present
            else [
                'sample:7: parameter documentation incomplete',
                'sample:7: return documentation missing',
                'sample:7: raises documentation missing',
            ]
        )

    def test_empty_sections_have_no_evidence(
        self,
        documentation_case: DocumentationCase,
    ) -> None:
        """Require field content independently of heading or label presence."""
        style, interpret = documentation_case
        doc = {
            'numpy': 'Parameters\n----------\n\nReturns\n-------\n\nRaises\n------\n',
            'docc': '- Parameters:\n- Returns:\n- Throws:\n',
        }[style]
        assert interpret(doc, 'Returns') == CallableDocumentation()

    def test_grouped_parameter_notation(
        self,
        documentation_case: DocumentationCase,
    ) -> None:
        """
        Normalize grouped NumPy names and nested DocC entries equivalently.
        """
        style, interpret = documentation_case
        doc = {
            'numpy': 'Parameters\n----------\nvalue, options : int\n    Inputs.\n',
            'docc': '- Parameters:\n  - value: Input.\n  - options: Options.\n',
        }[style]
        assert interpret(doc, '') == CallableDocumentation(
            frozenset({'value', 'options'}),
        )

    def test_parameter_name_case_is_preserved(
        self,
        documentation_case: DocumentationCase,
    ) -> None:
        """Keep parameter spelling separate from markup-label case rules."""
        style, interpret = documentation_case
        doc = {
            'numpy': 'Parameters\n----------\nValue : int\n    Input.\n',
            'docc': '- Parameter Value: Input.\n',
        }[style]
        assert interpret(doc, '').parameter_names == frozenset({'Value'})

    @pytest.mark.parametrize(
        'required,complete',
        [
            ((), True),
            (('value',), True),
            (('value', 'value'), True),
            (('Value',), False),
            (('value', 'missing'), False),
        ],
    )
    def test_parameter_name_coverage(
        self,
        documentation_case: DocumentationCase,
        tmp_path: Path,
        required: tuple[str, ...],
        complete: bool,
    ) -> None:
        """Ignore repeated/extra names while requiring exact-case coverage."""
        style, interpret = documentation_case
        doc = {
            'numpy': 'Parameters\n----------\nvalue, value, extra : int\n    Inputs.\n',
            'docc': '- Parameter value: Input.\n- Parameters:\n'
            '  - value: Repeated input.\n  - extra: Extra input.\n',
        }[style]
        evidence = interpret(doc, '')
        assert evidence.parameter_names == frozenset({'value', 'extra'})
        domain = 'python-source' if style == 'numpy' else 'swift-source'
        config = SourceCheckConfig(
            tmp_path,
            domain,
            (),
            (),
            dict(DOMAINS[domain]) | {'parameter-docs': True},
        )
        assert contract_findings(
            DeclarationFacts(7, 'function', doc, required),
            config,
            'sample',
            evidence,
        ) == ([] if complete else ['sample:7: parameter documentation incomplete'])

    def test_section_label_case_remains_language_specific(
        self,
        documentation_case: DocumentationCase,
    ) -> None:
        """Preserve case-sensitive NumPy headings and case-insensitive DocC."""
        style, interpret = documentation_case
        doc = {
            'numpy': 'returns\n-------\nint\n    Result.\n',
            'docc': '- rEtUrNs: Result.\n',
        }[style]
        assert interpret(doc, 'Returns').result_documented is (style == 'docc')

    def test_variadic_and_singular_parameter_notation(
        self,
        documentation_case: DocumentationCase,
    ) -> None:
        """Preserve NumPy stars and DocC singular/backticked name support."""
        style, interpret = documentation_case
        doc = {
            'numpy': 'Parameters\n----------\n*args : int\n    Inputs.\n'
            '**kwargs : int\n    Named inputs.\n',
            'docc': '- Parameter `args`: Inputs.\n- Parameter kwargs: Named inputs.',
        }[style]
        assert interpret(doc, '') == CallableDocumentation(
            frozenset({'args', 'kwargs'}),
        )


class TestDeclarationDocumentation:
    """
    Preserve language-specific presence switches at the declaration boundary.
    """

    @pytest.mark.parametrize('nominal', [False, True])
    @pytest.mark.parametrize('required', [False, True])
    @pytest.mark.parametrize('documented', [False, True])
    def test_presence_policy_uses_the_correct_switch(
        self,
        documentation_case: DocumentationCase,
        tmp_path: Path,
        nominal: bool,
        required: bool,
        documented: bool,
    ) -> None:
        """Keep nominal/member policies independent with exact diagnostics."""
        style, _ = documentation_case
        domain = 'python-source' if style == 'numpy' else 'swift-source'
        settings = {
            key: False if type(value) is bool else value
            for key, value in DOMAINS[domain].items()
        }
        doc = 'Details.' if documented else ''
        if style == 'numpy':
            settings['declaration-docs'] = required
            facts = DeclarationFacts(5, 'class' if nominal else 'function', doc, ())
            declaration = _python_declarations.Declaration(facts)
            presence = _python_documentation._presence
            check = _python_documentation._declaration_findings
        else:
            settings['declaration-docs'] = required if nominal else not required
            settings['member-docs'] = not required if nominal else required
            facts = DeclarationFacts(5, 'struct' if nominal else 'func', doc, ())
            declaration = _swift_declarations.Declaration(facts, 1, True)
            presence = _swift_documentation._presence
            check = _swift_documentation._declaration_findings
        config = SourceCheckConfig(tmp_path, domain, (), (), settings)
        assert presence(declaration, config) == DocumentationPresence(
            required=required,
            present=documented,
        )
        assert check(declaration, config, 'sample') == (
            ['sample:5: missing declaration documentation']
            if required and not documented
            else []
        )


class TestNumPyDocumentation:
    """Retain the distinction between value returns and generator yields."""

    @pytest.mark.parametrize('section', ['Returns', 'Yields'])
    @pytest.mark.parametrize('required', ['Returns', 'Yields'])
    def test_result_section_selection(
        self,
        section: str,
        required: ResultSection,
    ) -> None:
        """Require the section selected by the declaration's own facts."""
        doc = f'{section}\n-------\nint\n    Result.\n'
        evidence = _python_documentation._documentation(doc, required)
        assert evidence.result_documented is (section == required)

    @pytest.mark.parametrize(
        'doc,expected',
        [
            ('Returns\n-------\nint\n    Result.', 'int\n    Result.'),
            (
                'Overview.\n\nReturns\n-------\n\nint\n    Result.\n\n'
                'Notes\n-----\nPrivate notes.',
                'int\n    Result.',
            ),
            ('Returns\n-------\n\nNotes\n-----\nPrivate notes.', ''),
            ('Returns\n-------\nFirst.\nReturns\n-------\nSecond.', 'First.'),
        ],
    )
    def test_section_boundaries_use_original_offsets(
        self,
        doc: str,
        expected: str,
    ) -> None:
        """Stop at any underlined heading and preserve first-section content."""
        assert _python_documentation._section(doc, 'Returns') == expected


class TestDocumentationRunner:
    """Keep overview diagnostics before declarations across both languages."""

    @pytest.mark.parametrize('language', ('python', 'swift'))
    def test_overview_precedes_declarations(
        self,
        tmp_path: Path,
        language: str,
    ) -> None:
        """Preserve source order and redact names and bodies in diagnostics."""
        domain = f'{language}-source'
        config = SourceCheckConfig(
            tmp_path,
            domain,
            ('*',),
            (),
            dict(DOMAINS[domain])
            | {
                'file-overviews': True,
                'declaration-docs': True,
            },
        )
        parser = _python_declarations if language == 'python' else _swift_declarations
        interpreter = (
            _python_documentation if language == 'python' else _swift_documentation
        )
        text = (
            'class PrivateFirst: pass\nclass PrivateSecond: pass'
            if language == 'python'
            else 'struct PrivateFirst {}\nstruct PrivateSecond {}'
        )
        findings = interpreter.documentation_findings(
            parser.parse(text),
            config,
            'source',
        )
        assert len(findings) == 3
        assert findings[0].startswith('source:')
        assert 'overview' in findings[0]
        assert findings[1].startswith('source:1:')
        assert findings[2].startswith('source:2:')
        assert 'Private' not in '\n'.join(findings)


class TestDisabledCallableContracts:
    """Keep shared dispatch independent of a consumer's selected rules."""

    @pytest.mark.parametrize('language', ('python', 'swift'))
    def test_disabled_rules_do_not_require_sections(
        self,
        tmp_path: Path,
        language: str,
    ) -> None:
        """
        Leave absent callable markup valid when all relevant rules are off.
        """
        domain = f'{language}-source'
        settings = dict(DOMAINS[domain]) | {
            'file-overviews': False,
            'declaration-docs': False,
        }
        config = SourceCheckConfig(tmp_path, domain, ('*',), (), settings)
        parser = _python_declarations if language == 'python' else _swift_declarations
        interpreter = (
            _python_documentation if language == 'python' else _swift_documentation
        )
        source = (
            'def f(value: int) -> int:\n    raise ValueError()'
            if language == 'python'
            else 'func f(value: Int) throws -> Int { throw Failure() }'
        )
        assert (
            interpreter.documentation_findings(
                parser.parse(source),
                config,
                'source',
            )
            == []
        )

    @pytest.mark.parametrize(
        'kind,names,enabled',
        [('class', (), True), ('function', None, True), ('function', (), False)],
    )
    def test_inapplicable_contracts_skip_markup(
        self,
        tmp_path: Path,
        kind: str,
        names: tuple[str, ...] | None,
        enabled: bool,
    ) -> None:
        """Avoid evidence readers when no callable contract can be checked."""
        interpret = Mock(side_effect=AssertionError('unexpected markup read'))
        config = SourceCheckConfig(
            tmp_path,
            'python-source',
            (),
            (),
            dict(DOMAINS['python-source'])
            | dict.fromkeys(('parameter-docs', 'return-docs', 'raises-docs'), enabled),
        )
        assert (
            callable_findings(
                DeclarationFacts(1, kind, 'Unparsed documentation.', names),
                config,
                'sample',
                ('function',),
                interpret,
            )
            == []
        )
        interpret.assert_not_called()
        if names is None:
            assert (
                contract_findings(
                    DeclarationFacts(1, kind, '', None),
                    config,
                    'sample',
                    CallableDocumentation(),
                )
                == []
            )


class TestDeclarationDocumentationOrder:
    """Share reporting order while preserving native whitespace and spacing."""

    @pytest.mark.parametrize('doc', ('', '   ', 'PRIVATE overview.'))
    def test_presence_spacing_and_contract_precedence(
        self,
        documentation_case: DocumentationCase,
        tmp_path: Path,
        doc: str,
    ) -> None:
        """
        Retain missing/spacing precedence and still check callable contracts.
        """
        style, _ = documentation_case
        domain = 'python-source' if style == 'numpy' else 'swift-source'
        settings = dict(DOMAINS[domain]) | {
            'declaration-docs': True,
            'return-docs': True,
        }
        kind = 'function' if style == 'numpy' else 'func'
        facts = DeclarationFacts(7, kind, doc, (), 'Returns')
        if style == 'numpy':
            declaration = _python_declarations.Declaration(facts)
            findings = _python_documentation._declaration_findings(
                declaration,
                SourceCheckConfig(tmp_path, domain, (), (), settings),
                'source',
            )
            expected = [] if doc else ['source:7: missing declaration documentation']
        else:
            settings |= {'member-docs': True, 'declaration-spacing': True}
            declaration = _swift_declarations.Declaration(facts, 6, False)
            findings = _swift_documentation._declaration_findings(
                declaration,
                SourceCheckConfig(tmp_path, domain, (), (), settings),
                'source',
            )
            expected = [
                'source:7: missing declaration documentation'
                if not doc.strip()
                else 'source:6: missing blank line before documentation',
            ]
        assert findings == [*expected, 'source:7: return documentation missing']
        assert 'PRIVATE' not in '\n'.join(findings)


class TestDocumentationDialectMapping:
    """Map shared result requirements through each native markup dialect."""

    @pytest.mark.parametrize('required', ('', 'Returns', 'Yields'))
    def test_result_section_mapping_preserves_native_semantics(
        self,
        documentation_case: DocumentationCase,
        required: ResultSection,
    ) -> None:
        """
        Keep NumPy result selection and DocC's fixed Returns field distinct.
        """
        style, interpret = documentation_case
        doc = (
            'Yields\n------\nint\n    Values.\n'
            if style == 'numpy'
            else '- Returns: A value.'
        )
        evidence = interpret(doc, required)
        assert evidence.parameter_names == frozenset()
        assert not evidence.exception_documented
        assert evidence.result_documented == (
            required == 'Yields' if style == 'numpy' else bool(required)
        )


class TestDocumentationReaderContract:
    """Accept native name iterables without imposing mutable collections."""

    def test_single_pass_names_retain_case_and_are_frozen(
        self,
    ) -> None:
        """Consume one-shot evidence once and skip unrequested result reads."""
        names = iter(('value', 'value', 'Value'))
        read_names = Mock(return_value=names)
        read_section = Mock(return_value='')
        dialect = DocumentationDialect(read_names, read_section, 'Throws')
        assert dialect.interpret('Native text.', '') == CallableDocumentation(
            frozenset({'value', 'Value'}),
        )
        read_names.assert_called_once_with('Native text.')
        read_section.assert_called_once_with('Native text.', 'Throws')
        assert list(names) == []


# !SECTION
