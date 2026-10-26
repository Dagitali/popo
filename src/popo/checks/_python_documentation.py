"""
:mod:`popo.checks._python_documentation` module.

Interpret NumPy documentation separately from Python syntax.
"""

import re

from popo.config.source_checks import SourceCheckConfig

from ._python_declarations import CALLABLE_KINDS, Declaration
from ._source_declarations import SourceFacts
from ._source_documentation import contract_findings

# SECTION: CONSTANTS


PARAMETER_PATTERN = re.compile(r'(?m)^(\*{0,2}\w+(?:,\s*\*{0,2}\w+)*)[ \t]*:')
SECTION_END_PATTERN = re.compile(r'(?m)^[A-Za-z][A-Za-z ]*\n-+\s*\n')
SECTION_PATTERNS = {
    name: re.compile(rf'(?m)^{name}\s*\n-+\s*\n')
    for name in ('Parameters', 'Returns', 'Yields', 'Raises')
}


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _section(
    doc: str,
    name: str,
) -> str:
    """Extract a NumPy section through the next underlined section heading."""
    match = SECTION_PATTERNS[name].search(doc)
    if match is None:
        return ''
    remainder = doc[match.end() :]
    end = SECTION_END_PATTERN.search(remainder)
    return remainder[: end.start() if end else len(remainder)].strip()


def _parameters(
    doc: str,
) -> set[str]:
    """Read grouped and variadic names from the NumPy Parameters section."""
    return {
        name.strip().lstrip('*')
        for names in PARAMETER_PATTERN.findall(_section(doc, 'Parameters'))
        for name in names.split(',')
    }


# !SECTION


# SECTION: FUNCTIONS


def documentation_findings(
    source: SourceFacts[Declaration],
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """Check overview/declaration presence and NumPy callable sections.

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
    failures = (
        [f'{relative}: missing file overview']
        if config.settings['file-overviews'] and not source.has_overview
        else []
    )
    for declaration in source.declarations:
        facts = declaration.facts
        doc = facts.documentation
        if config.settings['declaration-docs'] and not doc:
            failures.append(
                f'{relative}:{facts.line}: missing declaration documentation',
            )
        if facts.kind in CALLABLE_KINDS:
            failures.extend(
                contract_findings(
                    facts,
                    config,
                    relative,
                    _parameters(doc),
                    bool(_section(doc, facts.return_section))
                    if facts.return_section
                    else False,
                    bool(_section(doc, 'Raises')),
                ),
            )
    return failures


# !SECTION
