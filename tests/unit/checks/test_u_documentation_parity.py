"""
:mod:`tests.unit.checks.test_u_documentation_parity` module.

Compare callable documentation evidence without merging markup conventions.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.checks import _python_documentation, _swift_documentation
from popo.checks._source_declarations import DeclarationFacts
from popo.checks._source_documentation import CallableDocumentation, contract_findings
from popo.config.source_checks import SourceCheckConfig

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


# !SECTION
