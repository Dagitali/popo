"""
:mod:`popo.checks.swift_source` module.

Inspect Swift source conventions through bounded lexical declaration checks.
"""

from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import SourceFacts
from ._source_documentation import limits
from ._source_validation import validate_sources
from ._swift_declarations import CALLABLE_KINDS, Declaration, parse
from ._swift_documentation import documentation_findings

# SECTION: PROTECTED FUNCTIONS


def _convention_findings(
    source: SourceFacts[Declaration],
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """
    Check supported callable signatures and opted-in parameter layout.

    Parameters
    ----------
    source : SourceFacts[Declaration]
        Collected declaration facts; no source is parsed again here.
    config : SourceCheckConfig
        Callable documentation and parameter-layout switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Unsupported recognized signatures or parameter-layout violations.
        Findings follow declaration order; empty when enabled rules pass.

    Notes
    -----
    Inspect recognized callables only. Unsupported parameter signatures produce
    a finding when any of parameter-docs, return-docs, raises-docs or
    parameter-lines is enabled. Such a finding takes precedence over parameter
    layout.
    With all four switches disabled this function returns no findings. Python
    annotation and method-order rules are not imposed on Swift.
    """
    if not any(
        config.settings[key]
        for key in (
            'parameter-docs',
            'return-docs',
            'raises-docs',
            'parameter-lines',
        )
    ):
        return []
    failures: list[str] = []
    for declaration in source.declarations:
        facts = declaration.facts
        if facts.kind not in CALLABLE_KINDS:
            continue
        location = f'{relative}:{facts.line}'
        if facts.parameter_names is None:
            failures.append(f'{location}: unsupported callable signature')
        elif config.settings['parameter-lines'] and not facts.parameter_lines:
            failures.append(f'{location}: parameters require separate lines')
    return failures


def _source_findings(
    config: SourceCheckConfig,
    path: Path,
    source: str,
) -> list[str]:
    """
    Collect Swift size, documentation and convention findings for one file.

    Parameters
    ----------
    config : SourceCheckConfig
        Validated consumer-owned limits and documentation/convention settings.
    path : pathlib.Path
        Path used for diagnostics; must be lexically inside config.root.
        This function inspects the supplied text without reading the file.
    source : str
        Decoded source text to inspect without executing consumer code.

    Returns
    -------
    list[str]
        Physical file-length and documentation-width findings, followed by
        documentation and convention findings; empty when all checks pass.
        Parsing uses the bounded Swift lexical subset, not compiler validation.

    Raises
    ------
    ValueError
        The supplied path is not lexically inside config.root.
    """
    failures: list[str] = []
    relative = path.relative_to(config.root).as_posix()
    lines = source.splitlines()
    parsed = parse(source)
    failures.extend(limits(config, path, lines, parsed.documentation_lines))
    failures.extend(documentation_findings(parsed, config, relative))
    failures.extend(_convention_findings(parsed, config, relative))
    return failures


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: SourceCheckConfig,
) -> list[str]:
    """
    Return configured source-check findings without executing consumer code.

    Parameters
    ----------
    config : popo.config.source_checks.SourceCheckConfig
        Consumer policy loaded for the ``swift-source`` domain with
        load_source_check: resolved root, include/exclude patterns, optional
        source guide, size limits and documentation/convention settings.
        This function does not load or revalidate configuration.

    Returns
    -------
    list[str]
        Discovery and guide findings, followed by read or source-rule findings
        for each sorted selected path. Diagnostics include relative locations
        where available, without source excerpts or exception contents. Missing
        or unreadable inputs become findings; unreadable files are skipped
        while remaining selected files are checked. An empty list means the
        selected inputs satisfy the implemented checks, not full language or
        documentation-tool validation.

    Raises
    ------
    KeyError
        Required rule settings are absent when direct configuration
        construction bypasses load_source_check.
    ValueError
        Numeric limits cannot be converted to integers, or selected paths
        cannot be expressed relative to config.root, when direct construction
        bypasses the loader's setting and resolved-root contracts.

    Notes
    -----
    Inspect sorted, deduplicated files selected by include/exclude patterns.
    Check the optional source guide before reading selected files as UTF-8.
    Physical line limits apply to each readable file; width limits apply only
    to recognized documentation lines. Discovery, confinement, guide and
    read/decode failures are returned as redacted findings, not raw exceptions.

    Mask nested comments and ordinary, multiline and raw strings before
    recognizing line-leading declarations. Triple-slash comments attach across
    attribute-only lines. Nominal documentation follows the consumer's
    declaration-docs setting; member documentation and callable contract rules
    are separately opt-in.

    Named function, init and subscript signatures use balanced parentheses.
    Documentation names use internal parameters and DocC list fields. This
    lexical subset does not validate Swift syntax, operator signatures, regex
    literals, macros or conditional compilation. Enabled callable checks fail
    unsupported recognized signatures explicitly. Compiler and DocC validation
    remain separate responsibilities; no consumer code or tools are executed.
    """
    return validate_sources(config, _source_findings)


# !SECTION
