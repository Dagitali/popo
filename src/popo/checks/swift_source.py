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
    Validate selected Swift source files without executing consumer code.

    Parameters
    ----------
    config : popo.config.source_checks.SourceCheckConfig
        Policy for ``swift-source``, normally obtained from
        :func:`~popo.config.source_checks.load_source_check`. Requires a
        resolved repository root, include/exclude glob patterns and domain
        settings.
        Configuration is neither loaded nor revalidated here.

    Returns
    -------
    list[str]
        Discovery and guide findings first, then read or source-rule findings
        for each selected file in sorted path order. An empty list means no
        findings from the configured checks. Diagnostics use relative paths
        and line numbers where applicable, without source excerpts or raw
        exception messages. Unreadable files are reported and skipped while
        remaining files are checked.

    Raises
    ------
    KeyError
        config.settings lacks an option required by this checker.
    ValueError
        A numeric limit cannot be converted to an integer, or a selected path
        cannot be expressed relative to config.root. These indicate a
        configuration that does not satisfy the loader's contracts.

    Notes
    -----
    Inspect sorted, deduplicated files selected by include/exclude patterns.
    Require exact backticked source paths in the optional source guide before
    reading selected files as UTF-8. Physical line limits apply to readable
    files; width limits apply only to recognized documentation lines. Missing
    glob matches, unsafe paths and input read/decode failures become redacted
    findings rather than raw filesystem or decoding exceptions.

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
