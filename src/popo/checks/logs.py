"""
:mod:`popo.checks.logs` module.

Reject configured literal diagnostics without disclosing matched log lines.
"""

from pathlib import Path

from popo.config._common import require_table
from popo.config.source_checks import SourceCheckConfig

from ._source_inputs import discover, read_source

# SECTION: FUNCTIONS


def validate(
    config: SourceCheckConfig,
    root: Path | None = None,
) -> list[str]:
    """
    Inspect explicit logs and return only locations and configured rule IDs.

    Parameters
    ----------
    config : SourceCheckConfig
        Input globs and named, nonblank, single-line literal patterns.
    root : pathlib.Path or None
        Explicit artifact boundary, otherwise the consumer repository.

    Returns
    -------
    list[str]
        Redacted findings. Missing inputs and unreadable or non-UTF-8 logs
        fail rather than establishing success without evidence. Root resolution
        errors also become redacted diagnostics. Findings retain sorted file,
        line and configured pattern order; each rule reports once per line,
        even when its literal occurs repeatedly.
    """
    try:
        boundary = (root or config.root).resolve()
    except (OSError, ValueError):
        return ['cannot resolve selected input root']
    paths, failures = discover(config, boundary)
    patterns = tuple(
        (name, str(pattern))
        for name, pattern in require_table(
            config.settings['patterns'],
            name='logs.patterns',
        ).items()
    )
    for path in paths:
        source, errors = read_source(path, boundary)
        failures.extend(errors)
        if source is None:
            continue
        relative = path.relative_to(boundary)
        failures.extend(
            f'{relative}:{number}: {name}'
            for number, line in enumerate(source.splitlines(), start=1)
            for name, pattern in patterns
            if pattern in line
        )
    return failures


# !SECTION
