"""
:mod:`popo.checks._python_documentation` module.

Interpret NumPy documentation separately from Python syntax.
"""

import re

from popo.config.source_checks import SourceCheckConfig

from ._python_declarations import CALLABLE_KINDS, Declaration
from ._source_declarations import SourceFacts
from ._source_documentation import (
    CallableDocumentation,
    callable_findings,
)
from ._source_documentation import (
    documentation_findings as collect_documentation_findings,
)

# SECTION: CONSTANTS


PARAMETER_PATTERN = re.compile(r'(?m)^(\*{0,2}\w+(?:,\s*\*{0,2}\w+)*)[ \t]*:')
SECTION_END_PATTERN = re.compile(r'(?m)^[A-Za-z][A-Za-z ]*\n-+\s*\n')
SECTION_PATTERNS = {
    name: re.compile(rf'(?m)^{name}\s*\n-+\s*\n')
    for name in ('Parameters', 'Returns', 'Yields', 'Raises')
}


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _declaration_findings(
    declaration: Declaration,
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """
    Check one declaration's documentation policy and callable contract.

    Parameters
    ----------
    declaration : Declaration
        Shared documentation/signature facts and Python-only observations.
    config : SourceCheckConfig
        Declaration-presence and callable-contract switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Declaration-presence and callable-contract findings in that order.

    Notes
    -----
    Declaration presence applies to Python classes and functions alike.
    Callable evidence uses NumPy sections; syntax requirements were collected
    independently, including receiver exclusion and explicit body requirements.
    """
    failures: list[str] = []
    facts = declaration.facts
    doc = facts.documentation
    if config.settings['declaration-docs'] and not doc:
        failures.append(
            f'{relative}:{facts.line}: missing declaration documentation',
        )
    failures.extend(
        callable_findings(facts, config, relative, CALLABLE_KINDS, _documentation),
    )
    return failures


def _documentation(
    doc: str,
    return_section: str,
) -> CallableDocumentation:
    """
    Collect callable documentation evidence using the language's markup.

    Parameters
    ----------
    doc : str
        Cleaned NumPy docstring supplied by the declaration collector.
    return_section : str
        Required conceptual section: Returns, Yields, or empty when unneeded.

    Returns
    -------
    CallableDocumentation
        Documented parameter names and content-bearing result/exception
        sections. An absent requirement does not request result evidence.

    Notes
    -----
    Grouped and variadic names come from Parameters; the declaration selects
    Returns or Yields, and Raises supplies exception evidence. Section content
    is inspected without validating prose, types or exception escape behavior.
    """
    return CallableDocumentation(
        frozenset(_parameters(doc)),
        bool(_section(doc, return_section)) if return_section else False,
        bool(_section(doc, 'Raises')),
    )


def _parameters(
    doc: str,
) -> set[str]:
    """
    Extract documented parameter names using the language's notation.

    Parameters
    ----------
    doc : str
        Cleaned NumPy docstring containing an optional Parameters section.

    Returns
    -------
    set[str]
        Case-sensitive grouped and variadic names, without leading stars.
        Missing sections yield an empty set; descriptions and types are not
        validated. Names are compared with receiver-excluded syntax facts.
    """
    return {
        name.strip().lstrip('*')
        for names in PARAMETER_PATTERN.findall(_section(doc, 'Parameters'))
        for name in names.split(',')
    }


def _section(
    doc: str,
    name: str,
) -> str:
    """
    Extract content from one recognized documentation section.

    Parameters
    ----------
    doc : str
        Cleaned NumPy docstring; section headings are case-sensitive.
    name : str
        Supported section name from SECTION_PATTERNS.

    Returns
    -------
    str
        Stripped content through the next underlined section heading, or an
        empty string for a missing section. Unrelated sections end the span.

    Raises
    ------
    KeyError
        If name is not a supported section name.
    """
    match = SECTION_PATTERNS[name].search(doc)
    if match is None:
        return ''
    remainder = doc[match.end() :]
    end = SECTION_END_PATTERN.search(remainder)
    return remainder[: end.start() if end else len(remainder)].strip()


# !SECTION


# SECTION: FUNCTIONS


def documentation_findings(
    source: SourceFacts[Declaration],
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """
    Check overview/declaration presence and NumPy callable sections.

    Parameters
    ----------
    source : SourceFacts[Declaration]
        Precomputed Python facts; this interpreter does not traverse the AST.
    config : SourceCheckConfig
        Consumer-owned documentation switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Missing documentation and incomplete parameter/return/raise sections.

    Notes
    -----
    Signature names exclude an initial self or cls receiver. Return and yield
    requirements and explicit raises come from the declaration collector.
    Explicit raises include locally caught ones; exception escape analysis,
    indirect exceptions, prose quality and type descriptions are not validated.
    """
    return collect_documentation_findings(
        source,
        config,
        relative,
        _declaration_findings,
    )


# !SECTION
