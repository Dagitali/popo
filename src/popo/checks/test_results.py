"""
:mod:`popo.checks.test_results` module.

Validate named native test-summary formats without revealing report contents.
"""

import json
from glob import escape
from pathlib import Path

from popo.config.source_checks import SourceCheckConfig
from popo.config.test_results import TestResultsConfig

from ._source_inputs import discover, read_source

# SECTION: CONSTANTS


COUNTS = ('totalTestCount', 'passedTests', 'failedTests', 'skippedTests')


# !SECTION


# SECTION: FUNCTIONS


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
        Missing warnings mean an empty list; other malformed warning types fail.
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
    for path in paths:
        source, errors = read_source(path, boundary)
        failures.extend(errors)
        if source is None:
            continue
        relative = path.relative_to(boundary).as_posix()
        try:
            report = json.loads(source)
        except (ValueError, RecursionError):
            failures.append(f'{relative}: invalid test-result JSON')
            continue
        if config.adapter != 'xcode-summary':
            failures.append(f'{relative}: unsupported test-result adapter')
            continue
        failures.extend(
            f'{relative}: {finding}'
            for finding in xcode_summary(report, config.thresholds)
        )
    return failures


# !SECTION
