"""
:mod:`popo.checks._source_inputs` module.

Discover configured inputs without following paths outside the selected root.
"""

from collections.abc import Callable, Iterable
from fnmatch import fnmatchcase
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

# SECTION: FUNCTIONS


def discover(
    config: SourceCheckConfig,
    root: Path | None = None,
) -> tuple[list[Path], list[str]]:
    """
    Select unique sorted files and report missing or escaping inputs.

    Parameters
    ----------
    config : SourceCheckConfig
        Validated include and exclude patterns.
    root : pathlib.Path or None
        Explicit artifact root; defaults to the configured repository root.

    Returns
    -------
    tuple[list[pathlib.Path], list[str]]
        Confined files and diagnostics containing no source contents. Root
        resolution, discovery and per-file inspection errors become redacted
        diagnostics rather than propagating.
    """
    try:
        boundary = (root or config.root).resolve()
    except (OSError, ValueError):
        return [], ['cannot resolve selected input root']
    paths: set[Path] = set()
    failures = []
    for pattern in config.include:
        matches = []
        try:
            for path in boundary.glob(pattern):
                relative = path.relative_to(boundary).as_posix()
                if any(fnmatchcase(relative, rule) for rule in config.exclude):
                    continue
                try:
                    if not path.resolve().is_relative_to(boundary):
                        failures.append(f'{relative}: input escapes selected root')
                    elif path.is_file():
                        matches.append(path)
                except (OSError, ValueError):
                    failures.append(f'{relative}: cannot inspect selected input')
        except (OSError, ValueError):
            failures.append('cannot discover configured source inputs')
        if not matches:
            failures.append(f'no inputs match: {pattern}')
        paths.update(matches)
    return sorted(paths), failures


def inspect_sources(
    paths: Iterable[Path],
    root: Path,
    inspect: Callable[[Path, str], Iterable[str]],
) -> list[str]:
    """
    Read selected inputs and collect redacted errors or inspection findings.

    Parameters
    ----------
    paths : collections.abc.Iterable[pathlib.Path]
        Caller-selected confined paths, consumed once in supplied order.
        The caller owns discovery, sorting and deduplication.
    root : pathlib.Path
        Boundary used for relative read-error diagnostics.
    inspect : collections.abc.Callable[[pathlib.Path, str], Iterable[str]]
        Read-only inspector receiving each readable path and decoded text.
        Its findings retain their order and wording, including duplicates.

    Returns
    -------
    list[str]
        Read/decode findings or inspector findings for each input, in order.
        Unreadable inputs are skipped while remaining inputs are inspected.

    Notes
    -----
    Read each supplied input once as UTF-8 without executing consumer code.
    Inspectors own domain policy and diagnostic redaction. Inspector and
    iteration exceptions propagate unchanged; no result is reported as success
    after a swallowed inspection failure. No files are modified.
    """
    failures: list[str] = []
    for path in paths:
        source, errors = read_source(path, root)
        failures.extend(errors)
        if source is not None:
            failures.extend(inspect(path, source))
    return failures


def read_source(
    path: Path,
    root: Path,
) -> tuple[str | None, list[str]]:
    """
    Read UTF-8 input while redacting filesystem and decode exception details.

    Parameters
    ----------
    path : pathlib.Path
        Selected confined input.
    root : pathlib.Path
        Boundary used for relative diagnostics.

    Returns
    -------
    tuple[str or None, list[str]]
        Source text, or a location-only readable-input diagnostic.
    """
    try:
        return path.read_text(encoding='utf-8'), []
    except (OSError, UnicodeError):
        return None, [f'{path.relative_to(root)}: cannot read UTF-8 input']


# !SECTION
