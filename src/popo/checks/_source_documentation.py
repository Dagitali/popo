"""
:mod:`popo.checks._source_documentation` module.

Share callable evidence, source-size, documentation-width and guide checks.
"""

import re
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import (
    DeclarationFacts,
    DeclarationRecord,
    ResultSection,
    SourceFacts,
)
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


@dataclass(frozen=True, slots=True)
class DocumentationDialect:
    """
    Bind native markup readers and section mappings to shared evidence
    assembly.

    Attributes
    ----------
    read_parameter_names : collections.abc.Callable[[str], set[str]]
        Native reader for documented argument names, retaining case rules.
    read_section : collections.abc.Callable[[str, str], str]
        Native reader for stripped content of one named markup section.
    raises_section : str
        Exception label understood by the native reader: Raises or Throws.
    result_section : str or None
        Fixed result label when native markup uses one form. None preserves
        the requested conceptual section, such as Python Returns or Yields.

    Notes
    -----
    Native adapters supply implementation readers; consumer configuration does
    not supply callbacks. Markup parsing and policy selection stay separate.
    """

    read_parameter_names: Callable[[str], set[str]]
    read_section: Callable[[str, str], str]
    raises_section: str
    result_section: str | None = None

    def interpret(
        self,
        doc: str,
        return_section: ResultSection,
    ) -> CallableDocumentation:
        """
        Collect callable documentation evidence using the language's markup.

        Parameters
        ----------
        doc : str
            Native documentation text supplied by a declaration collector.
        return_section : ResultSection
            Required conceptual result section, or empty when unneeded.

        Returns
        -------
        CallableDocumentation
            Immutable names and content-bearing result/exception evidence.
            An absent result requirement never requests result evidence.

        Notes
        -----
        Reader exceptions propagate unchanged. This assembles observations;
        it does not validate prose, types, syntax or exception escape behavior.
        """
        result = (
            self.result_section if self.result_section is not None else return_section
        )
        return CallableDocumentation(
            frozenset(self.read_parameter_names(doc)),
            bool(self.read_section(doc, result)) if return_section else False,
            bool(self.read_section(doc, self.raises_section)),
        )


@dataclass(frozen=True, slots=True)
class DocumentationPresence:
    """
    Store native presence and spacing decisions for one declaration.

    Attributes
    ----------
    required : bool
        Whether this declaration's language-specific policy requires docs.
    present : bool
        Whether native documentation satisfies that language's presence rule.
        Python uses cleaned-string truthiness; Swift ignores whitespace alone.
    spacing_line : int or None
        One-based location of a candidate spacing finding, or None when
        spacing passes or is not enabled. Missing required docs take priority.

    Notes
    -----
    This record carries policy observations, not another source syntax model.
    Language adapters select rules; shared evaluation owns diagnostic order.
    """

    required: bool
    present: bool
    spacing_line: int | None = None


# !SECTION


# SECTION: TYPE ALIASES


type DocumentationInterpreter = Callable[[str, ResultSection], CallableDocumentation]


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


def declaration_findings(
    facts: DeclarationFacts,
    config: SourceCheckConfig,
    relative: str,
    presence: DocumentationPresence,
    callable_kinds: Collection[str],
    interpret: DocumentationInterpreter,
) -> list[str]:
    """
    Evaluate native presence/spacing observations before callable contracts.

    Parameters
    ----------
    facts : DeclarationFacts
        Shared declaration location and signature/documentation evidence.
    config : SourceCheckConfig
        Consumer-owned callable documentation switches.
    relative : str
        Repository-relative diagnostic filename.
    presence : DocumentationPresence
        Language-derived presence requirements and optional spacing location.
    callable_kinds : collections.abc.Collection[str]
        Language-specific kinds with callable documentation requirements.
    interpret : DocumentationInterpreter
        Native markup interpreter; syntax and attachment are already known.

    Returns
    -------
    list[str]
        Missing required documentation or a spacing finding, followed by
        callable-contract findings. Missing docs do not suppress contracts.

    Notes
    -----
    Native adapters retain whitespace, nominal/member and spacing policies.
    No source is read or parsed; interpreter exceptions propagate unchanged.
    """
    failures: list[str] = []
    if presence.required and not presence.present:
        failures.append(f'{relative}:{facts.line}: missing declaration documentation')
    elif presence.spacing_line is not None:
        failures.append(
            f'{relative}:{presence.spacing_line}: '
            'missing blank line before documentation',
        )
    failures.extend(
        callable_findings(facts, config, relative, callable_kinds, interpret),
    )
    return failures


def documentation_findings[Declaration: DeclarationRecord](
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
        Precomputed overview and declarations in native discovery order.
        Python retains breadth-first AST order; Swift retains source order.
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
