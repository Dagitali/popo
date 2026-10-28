"""
:mod:`popo.checks._swift_documentation` module.

Interpret DocC documentation separately from Swift syntax.
"""

import re

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import ResultSection, SourceFacts
from ._source_documentation import (
    CallableDocumentation,
    DocumentationDialect,
    DocumentationPresence,
    declaration_findings,
)
from ._source_documentation import (
    documentation_findings as collect_documentation_findings,
)
from ._swift_declarations import CALLABLE_KINDS, NOMINAL_KINDS, Declaration

# SECTION: CONSTANTS (1 of 2)


PARAMETER_PATTERN = re.compile(r'(?m)^[ \t]*-[ \t]*`?(\w+)`?:')
SECTION_PATTERNS = {
    name: re.compile(
        rf'(?ims)^[ \t]*-[ \t]*{name}:[ \t]*(.*?)'
        r'(?=^[ \t]*-[ \t]*(?:Parameters?|Returns|Throws)\b|\Z)',
    )
    for name in ('Parameters', 'Returns', 'Throws')
}
SINGULAR_PARAMETER_PATTERN = re.compile(r'(?im)^[ \t]*-[ \t]*Parameter[ \t]+`?(\w+)`?:')


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
        Shared facts and Swift documentation attachment/spacing observations.
    config : SourceCheckConfig
        Nominal/member presence, spacing and callable-contract switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Presence/spacing and callable-contract findings in reporting order.

    Notes
    -----
    Nominals use declaration-docs; other recognized members use member-docs.
    A missing required doc takes precedence over a spacing finding. Callable
    evidence uses DocC fields. Syntax and attachment facts are consumed
    without reconstructing signatures or compiling Swift. Shared evaluation
    owns finding order after these native policy observations are derived.
    """
    return declaration_findings(
        declaration.facts,
        config,
        relative,
        _presence(declaration, config),
        CALLABLE_KINDS,
        _documentation,
    )


def _documentation(
    doc: str,
    result_section: ResultSection,
) -> CallableDocumentation:
    """
    Collect callable documentation evidence using the language's markup.

    Parameters
    ----------
    doc : str
        Attached DocC triple-slash text supplied by the declaration collector.
    result_section : ResultSection
        Returns when a result is required, or empty when unneeded. Swift's
        collector does not request Python's Yields convention.

    Returns
    -------
    CallableDocumentation
        Documented parameter names and content-bearing result/exception
        fields. An absent requirement does not request result evidence.

    Notes
    -----
    Singular Parameter entries and nested Parameters lists name internal
    arguments. Returns and Throws fields supply result and exception evidence.
    This is bounded DocC notation, not compiler or full DocC validation.
    """
    return DIALECT.interpret(doc, result_section)


def _parameter_names(
    doc: str,
) -> set[str]:
    """
    Extract documented parameter names using the language's notation.

    Parameters
    ----------
    doc : str
        Attached DocC text containing singular or grouped parameter entries.

    Returns
    -------
    set[str]
        Case-sensitive internal names from singular Parameter entries and
        nested Parameters lists, with optional backticks removed. Field names
        are case-insensitive; descriptions and types are not validated.
    """
    names = set(SINGULAR_PARAMETER_PATTERN.findall(doc))
    names.update(PARAMETER_PATTERN.findall(_section(doc, 'Parameters')))
    return names


def _presence(
    declaration: Declaration,
    config: SourceCheckConfig,
) -> DocumentationPresence:
    """
    Derive native documentation presence and spacing observations.

    Parameters
    ----------
    declaration : Declaration
        Shared declaration facts and language-specific observations.
    config : SourceCheckConfig
        Consumer-owned declaration-presence and spacing switches.

    Returns
    -------
    DocumentationPresence
        Presence requirement, native presence decision and optional spacing
        location. Shared evaluation owns diagnostic order and wording.

    Notes
    -----
    Swift applies declaration-docs to nominals and member-docs to other
    recognized members. Whitespace alone is absent. Spacing is considered only
    when documentation is optional or present, preserving native precedence.
    No markup contracts are interpreted and no source is read or parsed.
    """
    facts = declaration.facts
    doc = facts.documentation
    required = bool(
        config.settings['declaration-docs']
        if facts.kind in NOMINAL_KINDS
        else config.settings['member-docs'],
    )
    present = bool(doc.strip())
    spacing_line = (
        declaration.documentation_start
        if (not required or present)
        and doc
        and config.settings['declaration-spacing']
        and not declaration.separated
        else None
    )
    return DocumentationPresence(required, present, spacing_line)


def _section(
    doc: str,
    name: str,
) -> str:
    """
    Extract content from one recognized documentation section.

    Parameters
    ----------
    doc : str
        Attached DocC text; recognized list-field labels are case-insensitive.
    name : str
        Supported field name from SECTION_PATTERNS.

    Returns
    -------
    str
        Stripped content through the next recognized contract field, or an
        empty string for a missing field. This is bounded list-field parsing.

    Raises
    ------
    KeyError
        If name is not a supported field name.
    """
    match = SECTION_PATTERNS[name].search(doc)
    return match[1].strip() if match else ''


# !SECTION


# SECTION: CONSTANTS (2 of 2)


# Bind after native readers are defined; evidence assembly does not parse code.
DIALECT = DocumentationDialect(
    read_parameter_names=_parameter_names,
    read_section=_section,
    exception_section='Throws',
    result_section='Returns',
)


# !SECTION


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
        Precomputed native facts; no syntax is parsed or traversed here.
    config : SourceCheckConfig
        Consumer-owned documentation switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Missing documentation and incomplete parameter/result/exception
        contracts, in native declaration order. Enabled spacing findings
        precede callable contracts for each declaration; result/exception
        evidence comes from DocC Returns/Throws fields.

    Notes
    -----
    Internal argument names use Parameter entries or Parameters lists. Returns
    and Throws fields must have content when required by declaration facts.
    Triple-slash comments are the supported notation; full DocC validation and
    the front end's unsupported Swift grammar remain separate responsibilities.
    """
    return collect_documentation_findings(
        source,
        config,
        relative,
        _declaration_findings,
    )


# !SECTION
