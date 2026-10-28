"""
:mod:`popo.checks._source_validation` module.

Run shared source discovery, guide checks and read-only file inspection.
"""

from collections.abc import Callable
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import DeclarationFacts, DeclarationRecord, SourceFacts
from ._source_documentation import guide_findings, limits
from ._source_inputs import discover, read_source

# SECTION: TYPE ALIASES


type ParsedSourceInspector[Declaration: DeclarationRecord] = Callable[
    [SourceFacts[Declaration], SourceCheckConfig, str],
    list[str],
]
type SourceInspector = Callable[[SourceCheckConfig, Path, str], list[str]]


# !SECTION


# SECTION: FUNCTIONS


def parsed_source_findings[Declaration: DeclarationRecord](
    parsed: SourceFacts[Declaration],
    config: SourceCheckConfig,
    path: Path,
    lines: list[str],
    documentation: ParsedSourceInspector[Declaration],
    conventions: ParsedSourceInspector[Declaration],
) -> list[str]:
    """
    Evaluate parsed source limits, documentation and conventions in order.

    Parameters
    ----------
    parsed : SourceFacts[Declaration]
        Native front-end observations; no syntax is parsed again here.
    config : SourceCheckConfig
        Consumer-owned limits and rule switches.
    path : pathlib.Path
        Source path lexically inside config.root, used for diagnostics.
    lines : list[str]
        Physical lines of the original decoded source for limit checks.
    documentation, conventions : ParsedSourceInspector[Declaration]
        Language-specific inspectors receiving parsed facts, config and the
        relative filename. Their native declaration types remain intact.

    Returns
    -------
    list[str]
        Limit findings, then documentation findings, then convention findings.
        Inspector order and messages are preserved without deduplication.

    Raises
    ------
    KeyError
        Required limit or rule settings are absent from direct configuration.
    ValueError
        The source path is outside config.root or a numeric limit is invalid.

    Notes
    -----
    Call only after successful front-end collection. Parse failures remain the
    caller's responsibility. Inspectors own redaction; their exceptions are
    not intercepted. No files are read and no consumer code is executed.
    """
    relative = path.relative_to(config.root).as_posix()
    return [
        *limits(config, path, lines, parsed.documentation_lines),
        *documentation(parsed, config, relative),
        *conventions(parsed, config, relative),
    ]


def signature_findings(
    facts: DeclarationFacts,
    config: SourceCheckConfig,
    relative: str,
    *,
    report_unsupported: bool = False,
) -> list[str]:
    """
    Report native signature support before common parameter-layout findings.

    Parameters
    ----------
    facts : DeclarationFacts
        Precomputed parameter names and native layout decision.
    config : SourceCheckConfig
        Consumer-owned parameter-lines switch.
    relative : str
        Repository-relative filename for location-only diagnostics.
    report_unsupported : bool, optional
        Report None parameter names as unsupported instead of evaluating
        layout. The caller determines whether support checking is enabled
        and which native declaration kinds are applicable.

    Returns
    -------
    list[str]
        One unsupported-signature or enabled parameter-layout finding, or an
        empty list. An unsupported finding takes precedence over layout.

    Raises
    ------
    KeyError
        The parameter-lines setting is absent when layout is evaluated.

    Notes
    -----
    Python's native AST collector supplies supported signatures. Swift enables
    support reporting only when a callable contract/layout switch is active.
    Annotation, ordering, receiver and signature parsing rules remain native.
    No source is read, parsed or executed here.
    """
    location = f'{relative}:{facts.line}'
    if report_unsupported and facts.parameter_names is None:
        return [f'{location}: unsupported callable signature']
    if config.settings['parameter-lines'] and not facts.parameter_lines:
        return [f'{location}: parameters require separate lines']
    return []


def validate_sources(
    config: SourceCheckConfig,
    source_findings: SourceInspector,
) -> list[str]:
    """
    Collect discovery, guide, read and language-specific findings in order.

    Parameters
    ----------
    config : SourceCheckConfig
        Consumer-owned source selection, guide and convention settings.
    source_findings : SourceInspector
        Language-specific inspector receiving config, path and UTF-8 text.
        Called once per readable selected file, in sorted path order.

    Returns
    -------
    list[str]
        Discovery and guide findings followed by each file's read or inspection
        findings. Discovery/read errors are redacted by the input helpers;
        exceptions from the language-specific inspector are not intercepted.

    Notes
    -----
    This runner does not parse source or impose language-specific conventions.
    Inspectors must preserve read-only checking and location-only diagnostics.
    """
    paths, failures = discover(config)
    failures.extend(guide_findings(config, paths))
    for path in paths:
        source, errors = read_source(path, config.root)
        failures.extend(errors)
        if source is not None:
            failures.extend(source_findings(config, path, source))
    return failures


# !SECTION
