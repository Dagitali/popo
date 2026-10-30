"""
:mod:`popo.coverage` module.

Normalize exported LLVM and Xcode coverage without reading source files.
"""

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class Metric:
    """
    Retain one nonnegative coverage count without imposing a percentage gate.

    Attributes
    ----------
    covered : int
        Covered units; never greater than total.
    total : int
        Executable units; zero is permitted by an explicit reporting policy.
    """

    covered: int
    total: int


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    """
    Retain aggregate metrics independently of filenames and report contents.

    Attributes
    ----------
    adapter : str
        Export format: llvm or xccov.
    files : int
        Number of distinct selected source paths.
    metrics : tuple[tuple[str, Metric], ...]
        Ordered metric names and counts. LLVM has lines/functions/regions;
        Xcode exports lines. No source contents or paths are retained.
    """

    adapter: str
    files: int
    metrics: tuple[tuple[str, Metric], ...]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _mapping(
    value: object,
) -> dict[str, object]:
    """
    Require a JSON object without echoing its private contents.

    Parameters
    ----------
    value : object
        Decoded JSON value at an adapter-defined object position.

    Returns
    -------
    dict[str, object]
        Object narrowed for field inspection.

    Raises
    ------
    ValueError
        The selected JSON position is not an object with string keys.
    """
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError('invalid coverage object')
    return cast('dict[str, object]', value)


def _metric(
    covered: object,
    total: object,
) -> Metric:
    """
    Validate integer counts, rejecting booleans and impossible measurements.

    Parameters
    ----------
    covered : object
        Covered count supplied by the selected adapter.
    total : object
        Executable count supplied by the selected adapter.

    Returns
    -------
    Metric
        Validated counts, including an optional zero denominator.

    Raises
    ------
    ValueError
        A count is noninteger, negative or exceeds the executable total.
    """
    if type(covered) is not int or type(total) is not int:
        raise ValueError('coverage counts must be integers')
    if not 0 <= covered <= total:
        raise ValueError('invalid coverage count arithmetic')
    return Metric(covered, total)


def _sequence(
    value: object,
) -> list[object]:
    """
    Require an array without inspecting or disclosing unrelated fields.

    Parameters
    ----------
    value : object
        Decoded value at an adapter-defined array position.

    Returns
    -------
    list[object]
        Array narrowed for record traversal.

    Raises
    ------
    ValueError
        The value is not a JSON array.
    """
    if not isinstance(value, list):
        raise ValueError('invalid coverage array')
    return cast('list[object]', value)


# !SECTION


# SECTION: FUNCTIONS


def document(
    summary: CoverageSummary,
) -> dict[str, object]:
    """
    Render a versioned aggregate document without listing source filenames.

    Parameters
    ----------
    summary : CoverageSummary
        Validated measurement to serialize.

    Returns
    -------
    dict[str, object]
        JSON-compatible metrics with percentages rounded to one decimal.
    """
    return {
        'schema_version': 1,
        'adapter': summary.adapter,
        'files': summary.files,
        'metrics': {
            name: {
                'covered': metric.covered,
                'total': metric.total,
                'percent': round(100 * metric.covered / metric.total, 1)
                if metric.total
                else 0.0,
            }
            for name, metric in summary.metrics
        },
    }


def markdown(
    summary: CoverageSummary,
) -> str:
    """
    Render aggregate coverage as a portable Markdown table.

    Parameters
    ----------
    summary : CoverageSummary
        Validated measurement to render without source paths or contents.

    Returns
    -------
    str
        Table with one-decimal percentages and a final newline. Measurement
        limits and application-specific explanatory text belong to callers.
    """
    rows = [
        '# Coverage',
        '',
        '| Metric | Covered | Total | Percent |',
        '| --- | ---: | ---: | ---: |',
    ]
    for name, metric in summary.metrics:
        percent = 100 * metric.covered / metric.total if metric.total else 0.0
        rows.append(f'| {name} | {metric.covered} | {metric.total} | {percent:.1f}% |')
    return '\n'.join(rows) + '\n'


def read_summary(
    source: Path,
    adapter: str,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
    zero_total: str | None = None,
) -> CoverageSummary:
    """
    Decode an explicitly selected report without executing native tools.

    Parameters
    ----------
    source : pathlib.Path
        Exported JSON report; relative paths use the working directory.
    adapter : str
        Explicit llvm or xccov adapter.
    include : tuple[str, ...]
        Required production-file selections owned by the caller.
    exclude : tuple[str, ...], optional
        Selections excluded from the measurement.
    zero_total : str or None, optional
        Zero-denominator policy passed to summarize.

    Returns
    -------
    CoverageSummary
        Validated aggregate counts.

    Raises
    ------
    ValueError
        JSON decoding or coverage validation fails; input text is not echoed.
    OSError, UnicodeError
        Reading or decoding the report fails; CLI diagnostics are redacted.
    """
    try:
        report: object = json.loads(source.read_text(encoding='utf-8'))
    except (ValueError, RecursionError):
        raise ValueError('invalid coverage JSON') from None
    return summarize(report, adapter, include, exclude, zero_total)


def summarize(
    report: object,
    adapter: str,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
    zero_total: str | None = None,
) -> CoverageSummary:
    """
    Select explicit source paths and normalize one exported coverage report.

    POSIX glob matching is lexical and case-sensitive; no source is opened.
    Exclusions override inclusions. LLVM block/file records are additive.
    Xcode duplicates select the greatest covered-line count for a path and
    require consistent executable totals. Unselected metrics are not read.

    Parameters
    ----------
    report : object
        Decoded LLVM export or Xcode xccov report.
    adapter : str
        llvm for line/function/region metrics or xccov for line metrics.
    include : tuple[str, ...]
        Required nonempty POSIX full-path glob selections.
    exclude : tuple[str, ...], optional
        Additional full-path globs excluded from aggregation.
    zero_total : str or None, optional
        allow or reject zero executable totals. None allows LLVM zero totals
        and rejects Xcode zero totals, preserving their reporting contracts.

    Returns
    -------
    CoverageSummary
        Counts and distinct selected-path count, without raw filenames.

    Raises
    ------
    ValueError
        Selection, adapter, JSON structure, counts, duplicate denominators or
        zero-total policy is invalid, or no source files are selected.
    """
    if adapter not in {'llvm', 'xccov'} or zero_total not in {None, 'allow', 'reject'}:
        raise ValueError('invalid coverage adapter or zero-total policy')
    if not include or any(not pattern for pattern in (*include, *exclude)):
        raise ValueError('coverage selection requires nonempty patterns')
    data = _mapping(report)
    groups = _sequence(data.get('data' if adapter == 'llvm' else 'targets'))
    metrics = ('lines', 'functions', 'regions') if adapter == 'llvm' else ('lines',)
    entries: list[tuple[str, tuple[Metric, ...]]] = []
    for group in groups:
        files = _sequence(
            _mapping(group).get('files', [] if adapter == 'xccov' else None),
        )
        for value in files:
            item = _mapping(value)
            path = item.get('filename' if adapter == 'llvm' else 'path')
            if not isinstance(path, str) or not path or '\x00' in path:
                raise ValueError('invalid coverage filename')
            source = PurePosixPath(path)
            if not any(source.full_match(p, case_sensitive=True) for p in include):
                continue
            if any(source.full_match(p, case_sensitive=True) for p in exclude):
                continue
            if adapter == 'llvm':
                fields = _mapping(item.get('summary'))
                counts = tuple(
                    _metric(
                        _mapping(fields.get(m)).get('covered'),
                        _mapping(fields.get(m)).get('count'),
                    )
                    for m in metrics
                )
            else:
                counts = (
                    _metric(item.get('coveredLines'), item.get('executableLines')),
                )
            entries.append((path, counts))
    if not entries:
        raise ValueError('no selected coverage files; measurement unavailable')
    if adapter == 'xccov':
        unique: dict[str, tuple[Metric, ...]] = {}
        for path, counts in entries:
            previous = unique.get(path)
            if previous is not None and previous[0].total != counts[0].total:
                raise ValueError('inconsistent duplicate coverage totals')
            if previous is None or counts[0].covered > previous[0].covered:
                unique[path] = counts
        entries = list(unique.items())
    totals = tuple(
        (
            name,
            Metric(
                sum(c[i].covered for _, c in entries),
                sum(c[i].total for _, c in entries),
            ),
        )
        for i, name in enumerate(metrics)
    )
    if zero_total == 'reject' or (zero_total is None and adapter == 'xccov'):
        if any(metric.total == 0 for _, metric in totals):
            raise ValueError('no executable coverage units; measurement unavailable')
    return CoverageSummary(adapter, len({path for path, _ in entries}), totals)


# !SECTION
