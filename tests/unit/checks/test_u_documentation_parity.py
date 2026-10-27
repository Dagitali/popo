"""
:mod:`tests.unit.checks.test_u_documentation_parity` module.

Compare callable documentation evidence without merging markup conventions.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.checks import (
    _python_declarations,
    _python_documentation,
    _swift_declarations,
    _swift_documentation,
)
from popo.checks._source_declarations import DeclarationFacts
from popo.checks._source_documentation import CallableDocumentation, contract_findings
from popo.config.source_checks import DOMAINS, SourceCheckConfig

# SECTION: TYPE ALIASES


type DocumentationCase = tuple[str, Callable[[str, str], CallableDocumentation]]


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
        assert interpret(doc, 'Returns').return_documented is (style == 'docc')

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
            check = _python_documentation._declaration_findings
        else:
            settings['declaration-docs'] = required if nominal else not required
            settings['member-docs'] = not required if nominal else required
            facts = DeclarationFacts(5, 'struct' if nominal else 'func', doc, ())
            declaration = _swift_declarations.Declaration(facts, 1, True)
            check = _swift_documentation._declaration_findings
        config = SourceCheckConfig(tmp_path, domain, (), (), settings)
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
        required: str,
    ) -> None:
        """Require the section selected by the declaration's own facts."""
        doc = f'{section}\n-------\nint\n    Result.\n'
        evidence = _python_documentation._documentation(doc, required)
        assert evidence.return_documented is (section == required)


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


# !SECTION
