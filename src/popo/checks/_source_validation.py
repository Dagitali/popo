"""
:mod:`popo.checks._source_validation` module.

Run shared source discovery, guide checks and read-only file inspection.
"""

from collections.abc import Callable
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._source_documentation import guide_findings
from ._source_inputs import discover, read_source

# SECTION: TYPE ALIASES


type SourceInspector = Callable[[SourceCheckConfig, Path, str], list[str]]


# !SECTION


# SECTION: FUNCTIONS


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
