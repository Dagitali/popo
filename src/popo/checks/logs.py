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
        Input globs and named literal diagnostic patterns.
    root : pathlib.Path or None
        Explicit artifact boundary, otherwise the consumer repository.

    Returns
    -------
    list[str]
        Redacted findings. Missing inputs and unreadable or non-UTF-8 logs
        fail rather than establishing success without evidence. Root resolution
        errors also become redacted diagnostics.
    """
    try:
        boundary = (root or config.root).resolve()
    except (OSError, ValueError):
        return ['cannot resolve selected input root']
    paths, failures = discover(config, boundary)
    patterns = require_table(config.settings['patterns'], name='logs.patterns')
    for path in paths:
        source, errors = read_source(path, boundary)
        failures.extend(errors)
        if source is None:
            continue
        for number, line in enumerate(source.splitlines(), start=1):
            for name, pattern in patterns.items():
                if str(pattern) in line:
                    failures.append(f'{path.relative_to(boundary)}:{number}: {name}')
    return failures


# !SECTION
