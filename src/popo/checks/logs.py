"""
:mod:`popo.checks.logs` module.

Reject configured literal diagnostics without disclosing matched log lines.
"""

from pathlib import Path

from popo.config._common import require_table
from popo.config.source_checks import SourceCheckConfig

from ._source_inputs import discover, inspect_sources

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

    def inspect(
        path: Path,
        source: str,
    ) -> list[str]:
        """
        Match decoded lines without disclosing their contents.

        Parameters
        ----------
        path : Path
            Input path inspected by the operation.
        source : str
            Decoded input text to inspect without executing it.

        Returns
        -------
        list[str]
            Location-prefixed redacted findings for the decoded input.
        """
        relative = path.relative_to(boundary)
        return [
            f'{relative}:{number}: {name}'
            for number, line in enumerate(source.splitlines(), start=1)
            for name, pattern in patterns
            if pattern in line
        ]

    return [*failures, *inspect_sources(paths, boundary, inspect)]


# !SECTION
