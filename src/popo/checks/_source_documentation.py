"""
:mod:`popo.checks._source_documentation` module.

Share source-size, documentation-width and guide checks across languages.
"""

import re
from collections.abc import Iterable
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._source_declarations import DeclarationFacts
from ._source_inputs import read_source

# SECTION: FUNCTIONS


def contract_findings(
    facts: DeclarationFacts,
    config: SourceCheckConfig,
    relative: str,
    parameters: set[str],
    returns: bool,
    raises: bool,
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
    parameters : set[str]
        Names found in the language's documentation parameter notation.
    returns, raises : bool
        Whether the required return and exception sections have content.

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
            not set(facts.parameter_names) <= parameters,
            'parameter documentation incomplete',
        ),
        (
            'return-docs',
            bool(facts.return_section) and not returns,
            'return documentation missing',
        ),
        ('raises-docs', facts.raises and not raises, 'raises documentation missing'),
    )
    return [
        f'{location}: {message}'
        for key, failed, message in rules
        if config.settings[key] and failed
    ]


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


# !SECTION
