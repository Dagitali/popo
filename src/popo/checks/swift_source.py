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
        Observations from parse; no signatures are rescanned here.
    config : SourceCheckConfig
        Callable documentation and parameter-layout switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Unsupported recognized signatures or parameter-layout violations.
        Python annotation and method-order rules are not imposed on Swift.
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
        Consumer-owned limits, documentation and convention settings.
    path : pathlib.Path
        Selected readable file inside the configured repository root.
    source : str
        UTF-8 source text to inspect without executing consumer code.

    Returns
    -------
    list[str]
        File-limit, documentation and convention findings in that order.
        Parsing uses the bounded Swift lexical subset, not compiler validation.
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
    Return source-convention findings without executing inspected modules.

    Parameters
    ----------
    config : SourceCheckConfig
        Swift source paths and opt-in convention settings.

    Returns
    -------
    list[str]
        Location and rule diagnostics, never source or exception contents.

    Notes
    -----
    Mask nested comments and ordinary, multiline and raw strings before
    recognizing line-leading declarations. Triple-slash comments attach across
    attribute-only lines. Nominal declarations retain their original policy;
    member documentation and callable contract rules are separately opt-in.
    Named function, init and subscript signatures use balanced parentheses.
    Documentation names use internal parameters and DocC list fields. This
    lexical subset does not validate Swift syntax, operator signatures, regex
    literals, macros or conditional compilation. Enabled callable checks fail
    unsupported recognized signatures explicitly. Compiler and DocC validation
    remain separate responsibilities; no consumer code or tools are executed.
    """
    return validate_sources(config, _source_findings)


# !SECTION
