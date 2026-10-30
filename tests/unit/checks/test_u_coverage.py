"""
:mod:`tests.unit.checks.test_u_coverage` module.

Protect coverage selection, counts, duplicate handling and output privacy.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from popo.coverage import document, markdown, read_summary, summarize
from tests.support.coverage import export_report

# SECTION: FIXTURES


@pytest.fixture(
    name='adapter',
    params=('llvm', 'xccov'),
)
def adapter_fixture(
    request: pytest.FixtureRequest,
) -> str:
    """
    Exercise each coverage export independently.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Selected coverage adapter.

    Returns
    -------
    str
        Adapter selected for this fixture instance.
    """
    return str(request.param)


# !SECTION


# SECTION: TESTS


class TestCoverage:
    """Exercise pure normalization without input/output or native processes."""

    @pytest.mark.parametrize(
        'covered,total',
        [
            (True, 2),
            (0, False),
            (1.0, 2),
            ('1', 2),
            (-1, 2),
            (3, 2),
            (0, -1),
            (None, 2),
            (0, None),
        ],
    )
    def test_counts_reject_invalid_values(
        self: Self,
        adapter: str,
        covered: object,
        total: object,
    ) -> None:
        """
        Reject malformed measurements with redacted diagnostics.

        Parameters
        ----------
        adapter : str
            Export adapter exercised by the fixture.
        covered : object
            Invalid or boundary covered count.
        total : object
            Invalid or boundary executable total.
        """
        report = export_report(adapter, [('App/File.swift', 1, 2)])
        groups = report['data' if adapter == 'llvm' else 'targets']
        assert isinstance(groups, list)
        file = groups[0]['files'][0]
        if adapter == 'llvm':
            file['summary']['lines'] = {'covered': covered, 'count': total}
        else:
            file.update(coveredLines=covered, executableLines=total)
        with pytest.raises(ValueError, match='coverage count'):
            summarize(report, adapter, ('**/App/**/*.swift',))

    @pytest.mark.parametrize('reverse', (False, True))
    def test_duplicate_contracts_are_adapter_specific(
        self: Self,
        adapter: str,
        reverse: bool,
    ) -> None:
        """
        Add LLVM blocks and select best Xcode file coverage in either order.

        Parameters
        ----------
        adapter : str
            Export adapter exercised by the fixture.
        reverse : bool
            Whether to reverse the target/block discovery order.
        """
        rows = [('App/File.swift', 10, 100), ('App/File.swift', 40, 100)]
        summary = summarize(
            export_report(adapter, rows[::-1] if reverse else rows),
            adapter,
            ('**/App/**/*.swift',),
        )
        assert summary.files == 1
        metric = dict(summary.metrics)['lines']
        assert (metric.covered, metric.total) == (
            (50, 200) if adapter == 'llvm' else (40, 100)
        )

    def test_inconsistent_xcode_denominators_fail(
        self: Self,
    ) -> None:
        """
        Reject ambiguous duplicate totals instead of silently choosing one.
        """
        report = export_report(
            'xccov',
            [('App/File.swift', 1, 2), ('App/File.swift', 2, 3)],
        )
        with pytest.raises(ValueError, match='inconsistent duplicate'):
            summarize(report, 'xccov', ('**/App/**/*.swift',))

    @pytest.mark.parametrize(
        'report',
        [
            None,
            [],
            {1: 'PRIVATE'},
            {'data': {}},
            {'data': [None]},
            {'data': [{'files': {}}]},
            {'data': [{'files': [None]}]},
            {'data': [{'files': [{'filename': None}]}]},
            {'data': [{'files': [{'filename': 'bad\x00name'}]}]},
            {'data': [{'files': [{'filename': 'App/X.swift'}]}]},
        ],
    )
    def test_malformed_structure_fails_without_contents(
        self: Self,
        report: object,
    ) -> None:
        """
        Fail closed on malformed export structure.

        Parameters
        ----------
        report : object
            Malformed decoded JSON or direct-call object.
        """
        with pytest.raises(ValueError) as failure:
            summarize(report, 'llvm', ('**/App/**/*.swift',))
        assert 'PRIVATE' not in str(failure.value)

    def test_missing_selection_is_unavailable(
        self: Self,
        adapter: str,
    ) -> None:
        """
        Keep absent selected sources distinct from measured zero coverage.

        Parameters
        ----------
        adapter : str
            Export adapter exercised by the fixture.
        """
        with pytest.raises(ValueError, match='measurement unavailable'):
            summarize(export_report(adapter, []), adapter, ('**/*.swift',))

    @pytest.mark.parametrize('source', ['{PRIVATE malformed', '[]'])
    def test_read_errors_do_not_expose_source(
        self: Self,
        tmp_path: Path,
        source: str,
    ) -> None:
        """
        Preserve redaction across decoding and root-structure failures.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable input directory.
        source : str
            Invalid or structurally malformed report text.
        """
        path = tmp_path / 'report.json'
        path.write_text(source, encoding='utf-8')
        with pytest.raises(ValueError) as failure:
            read_summary(path, 'llvm', ('**/*.swift',))
        assert 'PRIVATE' not in str(failure.value)

    def test_selection_exclusion_and_private_outputs(
        self: Self,
        adapter: str,
    ) -> None:
        """
        Exclude generated/test records before reading their metrics.

        Parameters
        ----------
        adapter : str
            Export adapter exercised by the fixture.
        """
        rows = [
            ('PRIVATE/App/Domain/A.swift', 1, 4),
            ('PRIVATE/App/Domain/Nested/B.swift', 2, 6),
            ('PRIVATE/DerivedSources/App/Domain/C.swift', 100, 100),
            ('PRIVATE/App/Tests/D.swift', 100, 100),
            ('PRIVATE/App/Domain/notes.txt', 100, 100),
        ]
        report = export_report(adapter, rows)
        groups = report['data' if adapter == 'llvm' else 'targets']
        assert isinstance(groups, list)
        for group, (path, _, _) in zip(groups[2:], rows[2:], strict=True):
            group['files'] = [{'filename' if adapter == 'llvm' else 'path': path}]
        summary = summarize(
            report,
            adapter,
            ('**/App/Domain/**/*.swift',),
            ('**/DerivedSources/**',),
        )
        assert summary.files == 2
        data = document(summary)
        assert data['metrics'] == {
            name: {'covered': 3, 'total': 10, 'percent': 30.0}
            for name in (
                ('lines', 'functions', 'regions') if adapter == 'llvm' else ('lines',)
            )
        }
        assert '| lines | 3 | 10 | 30.0% |' in markdown(summary)
        assert 'PRIVATE' not in markdown(summary) + json.dumps(data)

    @pytest.mark.parametrize(
        'adapter,include,exclude,zero',
        [
            ('bad', ('*',), (), None),
            ('llvm', (), (), None),
            ('llvm', ('',), (), None),
            ('llvm', ('*',), ('',), None),
            ('llvm', ('*',), (), 'bad'),
        ],
    )
    def test_unsupported_options_fail(
        self: Self,
        adapter: str,
        include: tuple[str, ...],
        exclude: tuple[str, ...],
        zero: str | None,
    ) -> None:
        """
        Reject options that cannot establish an explicit measurement scope.

        Parameters
        ----------
        adapter : str
            Adapter name supplied by a direct caller.
        include : tuple[str, ...]
            Explicit inclusion patterns, potentially invalid.
        exclude : tuple[str, ...]
            Explicit exclusion patterns, potentially invalid.
        zero : str or None
            Zero-denominator option to validate.
        """
        with pytest.raises(ValueError):
            summarize({}, adapter, include, exclude, zero)

    @pytest.mark.parametrize('zero', (None, 'allow', 'reject'))
    def test_zero_totals_are_explicit(
        self: Self,
        adapter: str,
        zero: str | None,
    ) -> None:
        """
        Preserve adapter defaults and distinguish empty from zero-percent data.

        Parameters
        ----------
        adapter : str
            Export adapter exercised by the fixture.
        zero : str or None
            Explicit override or adapter-default zero-total policy.
        """
        report = export_report(adapter, [('App/Empty.swift', 0, 0)])
        rejects = zero == 'reject' or (zero is None and adapter == 'xccov')
        if rejects:
            with pytest.raises(ValueError, match='no executable'):
                summarize(report, adapter, ('**/*.swift',), zero_total=zero)
        else:
            summary = summarize(report, adapter, ('**/*.swift',), zero_total=zero)
            assert '| lines | 0 | 0 | 0.0% |' in markdown(summary)
        measured = summarize(
            export_report(adapter, [('App/Empty.swift', 0, 5)]),
            adapter,
            ('**/*.swift',),
            zero_total=zero,
        )
        assert '| lines | 0 | 5 | 0.0% |' in markdown(measured)


# !SECTION
