"""
:mod:`popo.checks._source_documentation` module.

Share callable evidence, source-size, documentation-width and guide checks.
"""

import re
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import DeclarationFacts, SourceFacts
from ._source_inputs import read_source

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class CallableDocumentation:
    """
    Store parsed parameter, result and exception documentation evidence.

    Attributes
    ----------
    parameter_names : frozenset[str]
        Documented names normalized by the language's markup interpreter;
        spelling remains case-sensitive. This does not validate descriptions.
    return_documented : bool
        Whether notation for the required return/yield section has content.
        This observation is interpreted alongside declaration requirements.
    raises_documented : bool
        Whether the language's exception section/field has content.

    Notes
    -----
    NumPy sections and DocC fields remain separate syntaxes. This immutable
    record contains their comparable observations, not signature requirements,
    source locations, prose-quality judgments or inferred exception behavior.
    """

    parameter_names: frozenset[str] = frozenset()
    return_documented: bool = False
    raises_documented: bool = False


# !SECTION


# SECTION: TYPE ALIASES


type DocumentationInterpreter = Callable[[str, str], CallableDocumentation]


# !SECTION


# SECTION: FUNCTIONS


def callable_findings(
    facts: DeclarationFacts,
    config: SourceCheckConfig,
    relative: str,
    callable_kinds: Collection[str],
    interpret: DocumentationInterpreter,
) -> list[str]:
    """
    Interpret callable markup and compare it with signature requirements.

    Parameters
    ----------
    facts : DeclarationFacts
        Precomputed declaration requirements, including its language kind.
    config : SourceCheckConfig
        Consumer-owned callable documentation switches.
    relative : str
        Repository-relative diagnostic filename.
    callable_kinds : collections.abc.Collection[str]
        Language-specific kinds whose callable contracts should be checked.
    interpret : DocumentationInterpreter
        Convert documentation and required result section to shared evidence.

    Returns
    -------
    list[str]
        Contract findings in rule order, or empty for noncallable declarations.

    Notes
    -----
    Presence and spacing rules remain the caller's responsibility. Interpreter
    exceptions propagate; no syntax parsing or consumer execution occurs.
    """
    if facts.kind not in callable_kinds:
        return []
    return contract_findings(
        facts,
        config,
        relative,
        interpret(facts.documentation, facts.return_section),
    )


def contract_findings(
    facts: DeclarationFacts,
    config: SourceCheckConfig,
    relative: str,
    documentation: CallableDocumentation,
) -> list[str]:
    """
    Compare shared requirements with language-specific documentation facts.

    Parameters
    ----------
    facts : DeclarationFacts
        Syntax-derived callable requirements. Unsupported signatures have None
        parameter names and are diagnosed by the language convention checker.
    config : SourceCheckConfig
        Explicit parameter, return and exception documentation switches.
    relative : str
        Repository-relative filename used only to label findings.
    documentation : CallableDocumentation
        Parsed names and content-bearing result/exception notation from the
        language's markup interpreter; requirements remain in facts.

    Returns
    -------
    list[str]
        Consistent rule descriptions without names, prose or source excerpts.
    """
    if facts.parameter_names is None:
        return []
    location = f'{relative}:{facts.line}'
    rules = (
        (
            'parameter-docs',
            not set(facts.parameter_names) <= documentation.parameter_names,
            'parameter documentation incomplete',
        ),
        (
            'return-docs',
            bool(facts.return_section) and not documentation.return_documented,
            'return documentation missing',
        ),
        (
            'raises-docs',
            facts.raises and not documentation.raises_documented,
            'raises documentation missing',
        ),
    )
    return [
        f'{location}: {message}'
        for key, failed, message in rules
        if config.settings[key] and failed
    ]


def documentation_findings[Declaration](
    source: SourceFacts[Declaration],
    config: SourceCheckConfig,
    relative: str,
    declaration_findings: Callable[[Declaration, SourceCheckConfig, str], list[str]],
) -> list[str]:
    """
    Collect overview findings before language-specific declaration findings.

    Parameters
    ----------
    source : SourceFacts[Declaration]
        Precomputed overview and declarations in source order.
    config : SourceCheckConfig
        Consumer-owned documentation settings passed to each inspector.
    relative : str
        Repository-relative diagnostic filename; no file is read here.
    declaration_findings : callable
        Language-specific inspector called once per declaration, in order.
        Retains responsibility for markup, spacing and contract semantics.

    Returns
    -------
    list[str]
        Overview findings followed by each declaration's findings, preserving
        inspector order without deduplication or source-text disclosure.

    Notes
    -----
    No syntax parsing, source reads or consumer execution occurs here.
    Inspector exceptions propagate; inspectors own diagnostic redaction.
    """
    failures = overview_findings(source.has_overview, config, relative)
    for declaration in source.declarations:
        failures.extend(declaration_findings(declaration, config, relative))
    return failures


def guide_findings(
    config: SourceCheckConfig,
    paths: list[Path],
) -> list[str]:
    """
    Require exact backticked source paths in an optional confined guide.

    Parameters
    ----------
    config : SourceCheckConfig
        Source-guide path and consumer root.
    paths : list[pathlib.Path]
        Selected source files whose relative paths must occur in the guide.

    Returns
    -------
    list[str]
        Missing entries or redacted path/read errors; empty when disabled.

    Notes
    -----
    Read the guide without executing or changing it. Guide entries are exact
    inline backtick spans; this is not a complete Markdown parser. Resolution,
    file and decode errors become diagnostics rather than propagating.
    """
    name = str(config.settings['source-guide'])
    if not name:
        return []
    path = config.root / name
    try:
        if not path.resolve().is_relative_to(config.root):
            return ['source-guide escapes repository root']
    except (OSError, ValueError):
        return ['cannot resolve source-guide inside repository root']
    guide, failures = read_source(path, config.root)
    if guide is None:
        return failures
    entries = set(re.findall(r'`([^`\n]+)`', guide))
    return [
        f'{path.relative_to(config.root).as_posix()}: missing source-guide entry'
        for path in paths
        if path.relative_to(config.root).as_posix() not in entries
    ]


def limits(
    config: SourceCheckConfig,
    path: Path,
    lines: list[str],
    documentation: Iterable[int],
) -> list[str]:
    """
    Check physical file lines and one-based documentation line widths.

    Parameters
    ----------
    config : SourceCheckConfig
        Validated file/documentation limits and repository boundary.
    path : pathlib.Path
        Confined source path, used only to label findings.
    lines : list[str]
        Source lines without newline terminators.
    documentation : collections.abc.Iterable[int]
        One-based documentation line numbers; duplicates are ignored.

    Returns
    -------
    list[str]
        Relative locations and rule descriptions without source excerpts.
    """
    relative = path.relative_to(config.root).as_posix()
    width = int(str(config.settings['documentation-width']))
    failures = (
        [f'{relative}: file exceeds configured line limit']
        if len(lines) > int(str(config.settings['max-file-lines']))
        else []
    )
    failures.extend(
        f'{relative}:{number}: documentation line too long'
        for number in sorted(set(documentation))
        if len(lines[number - 1]) > width
    )
    return failures


def overview_findings(
    has_overview: bool,
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """
    Check the shared file-overview policy using language-specific facts.

    Parameters
    ----------
    has_overview : bool
        Overview observation from the language's declaration collector.
    config : SourceCheckConfig
        Consumer-owned file-overviews switch; no source is parsed here.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        One missing-overview finding when required and absent, otherwise empty.
        Python module-docstring and Swift leading-comment rules remain owned
        by their respective collectors.
    """
    return (
        [f'{relative}: missing file overview']
        if config.settings['file-overviews'] and not has_overview
        else []
    )


# !SECTION
