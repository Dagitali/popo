"""
:mod:`popo.checks.test_results` module.

Validate named native test-summary formats without revealing report contents.
"""

import json
from glob import escape
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig
from popo.config.test_results import TestResultsConfig

from ._source_inputs import discover, inspect_sources

# SECTION: CONSTANTS


COUNTS = ('totalTestCount', 'passedTests', 'failedTests', 'skippedTests')


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _report_findings(
    source: str,
    config: TestResultsConfig,
) -> list[str]:
    """
    Decode one report and dispatch its named adapter without source disclosure.

    JSON errors take precedence over an unsupported directly constructed
    adapter. Input discovery and relative diagnostic locations belong to the
    caller; no files are read or modified here.

    Parameters
    ----------
    source : str
        Decoded input text to inspect without executing it.
    config : TestResultsConfig
        Configuration supplying the input paths and validation rules.

    Returns
    -------
    list[str]
        Redacted JSON, adapter or threshold diagnostics; empty for a passing
        report.
    """
    try:
        report = json.loads(source)
    except (ValueError, RecursionError):
        return ['invalid test-result JSON']
    if config.adapter != 'xcode-summary':
        return ['unsupported test-result adapter']
    return xcode_summary(report, config.thresholds)


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: TestResultsConfig,
    root: Path | None = None,
    summary: Path | None = None,
) -> list[str]:
    """
    Inspect every selected report using the configured named adapter.

    Parameters
    ----------
    config : TestResultsConfig
        Input selection, explicit adapter and acceptance thresholds.
    root : pathlib.Path or None
        Explicit artifact directory, otherwise the consumer repository root.
    summary : pathlib.Path or None
        Explicit single report, overriding include/exclude selection. Cannot
        be combined with an artifact root. Symlink escapes remain rejected.

    Returns
    -------
    list[str]
        Redacted schema, arithmetic, acceptance, discovery and read findings.
        Files and thresholds are checked independently; empty inputs fail.
    """
    if root is not None and summary is not None:
        return ['choose either a result root or a single summary']
    inputs = config.inputs
    try:
        if summary is not None:
            boundary = summary.absolute().parent.resolve()
            inputs = SourceCheckConfig(
                boundary,
                'test-results',
                (escape(summary.name),),
                (),
                {},
            )
        else:
            boundary = (root or config.inputs.root).resolve()
    except (OSError, ValueError):
        return ['cannot resolve selected result root']
    paths, failures = discover(inputs, boundary)

    def inspect(
        path: Path,
        source: str,
    ) -> list[str]:
        """
        Label adapter findings without disclosing report contents.

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
        relative = path.relative_to(boundary).as_posix()
        return [
            f'{relative}: {finding}' for finding in _report_findings(source, config)
        ]

    return [*failures, *inspect_sources(paths, boundary, inspect)]


def xcode_summary(
    report: object,
    thresholds: dict[str, int],
) -> list[str]:
    """
    Validate the Xcode adapter's schema, arithmetic and acceptance thresholds.

    Parameters
    ----------
    report : object
        Parsed JSON root; no source or warning message is emitted.
    thresholds : dict[str, int]
        Loader-validated minimum and maximum counts.

    Returns
    -------
    list[str]
        Fixed diagnostics without report values or private warning contents.
        An absent warning field is treated as an empty list; malformed warning
        types fail.
    """
    if not isinstance(report, dict) or any(
        type(report.get(key)) is not int or report[key] < 0 for key in COUNTS
    ):
        return ['malformed native test counts']
    if report['totalTestCount'] != sum(report[key] for key in COUNTS[1:]):
        return ['native test counts disagree with total']
    warnings = report.get('runtimeWarnings', [])
    if not isinstance(warnings, list):
        return ['malformed native runtime warnings']
    observed = (
        ('minimum-tests', report['totalTestCount']),
        ('minimum-passed', report['passedTests']),
        ('maximum-failed', report['failedTests']),
        ('maximum-skipped', report['skippedTests']),
        ('maximum-warnings', len(warnings)),
    )
    return [
        f'{key} acceptance threshold not satisfied'
        for key, value in observed
        if (
            value < thresholds[key]
            if key.startswith('minimum-')
            else value > thresholds[key]
        )
    ]


# !SECTION
