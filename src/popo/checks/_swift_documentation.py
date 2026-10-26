"""
:mod:`popo.checks._swift_documentation` module.

Interpret DocC documentation separately from Swift syntax.
"""

import re

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import SourceFacts
from ._source_documentation import contract_findings
from ._swift_declarations import CALLABLE_KINDS, NOMINAL_KINDS, Declaration

# SECTION: CONSTANTS


FIELD_PATTERNS = {
    name: re.compile(
        rf'(?ims)^[ \t]*-[ \t]*{name}:[ \t]*(.*?)'
        r'(?=^[ \t]*-[ \t]*(?:Parameters?|Returns|Throws)\b|\Z)',
    )
    for name in ('Parameters', 'Returns', 'Throws')
}
PARAMETER_PATTERN = re.compile(r'(?m)^[ \t]*-[ \t]*`?(\w+)`?:')
SINGULAR_PARAMETER_PATTERN = re.compile(r'(?im)^[ \t]*-[ \t]*Parameter[ \t]+`?(\w+)`?:')


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _parameters(
    doc: str,
) -> set[str]:
    """Read singular Parameter entries and nested Parameters list entries."""
    names = set(SINGULAR_PARAMETER_PATTERN.findall(doc))
    names.update(PARAMETER_PATTERN.findall(_section(doc, 'Parameters')))
    return names


def _section(
    doc: str,
    name: str,
) -> str:
    """Read a DocC list field through the next recognized contract field."""
    match = FIELD_PATTERNS[name].search(doc)
    return match[1].strip() if match else ''


# SECTION: FUNCTIONS


def documentation_findings(
    source: SourceFacts[Declaration],
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """
    Check overview/declaration presence, spacing and DocC contract fields.

    Parameters
    ----------
    source : SourceFacts[Declaration]
        Precomputed lexical facts; signatures are not reinterpreted here.
    config : SourceCheckConfig
        Consumer-owned documentation switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Missing documentation, spacing and callable contract findings.

    Notes
    -----
    Internal argument names use Parameter entries or Parameters lists. Returns
    and Throws fields must have content when required by declaration facts.
    Triple-slash comments are the supported notation; full DocC validation and
    the frontend's unsupported Swift grammar remain separate responsibilities.
    """
    failures = (
        [f'{relative}: missing file overview']
        if config.settings['file-overviews'] and not source.has_overview
        else []
    )
    for declaration in source.declarations:
        facts = declaration.facts
        doc = facts.documentation
        required = (
            config.settings['declaration-docs']
            if facts.kind in NOMINAL_KINDS
            else config.settings['member-docs']
        )
        if required and not doc.strip():
            failures.append(
                f'{relative}:{facts.line}: missing declaration documentation',
            )
        elif (
            doc and config.settings['declaration-spacing'] and not declaration.separated
        ):
            failures.append(
                f'{relative}:{declaration.documentation_start}: '
                'missing blank line before documentation',
            )
        if facts.kind in CALLABLE_KINDS:
            failures.extend(
                contract_findings(
                    facts,
                    config,
                    relative,
                    _parameters(doc),
                    bool(_section(doc, 'Returns')),
                    bool(_section(doc, 'Throws')),
                ),
            )
    return failures


# !SECTION
