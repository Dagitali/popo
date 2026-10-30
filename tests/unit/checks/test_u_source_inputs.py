"""
:mod:`tests.unit.checks.test_u_source_inputs` module.

Verify source discovery, read failures and inspection without source writes.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Self
from unittest.mock import Mock, call, patch

import pytest

from popo.checks import _source_inputs, logs
from popo.config.source_checks import SourceCheckConfig, load_source_check
from tests.support.files import FileWriter, snapshot_files
from tests.support.source_checks import SourceCase

# SECTION: TESTS


class TestSourceInputDiscovery:
    """Retain matches across overlapping patterns and partial traversals."""

    @pytest.mark.parametrize('interrupted', (False, True))
    def test_overlapping_patterns_retain_partial_matches(
        self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        interrupted: bool,
    ) -> None:
        """
        Deduplicate paths without treating repeated matches as missing.

        Parameters
        ----------
        source_case : SourceCase
            Language-specific source parser, policy and fixture helpers.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        interrupted : bool
            Whether discovery fails after yielding partial results.
        """
        domain, filename, _ = source_case
        path = write_file(filename, 'PRIVATE source')
        before = snapshot_files(tmp_path)
        config = SourceCheckConfig(
            tmp_path,
            domain,
            ('first', 'second', 'missing'),
            (),
            {},
        )

        def glob(
            directory: Path,
            pattern: str,
        ) -> Iterator[Path]:
            """
            Yield a repeated match before an optional traversal failure.

            Parameters
            ----------
            directory : Path
                Directory containing the isolated operation inputs.
            pattern : str
                Glob or literal selection passed to the operation.

            Yields
            ------
            Path
                Real matching paths yielded before any injected discovery
                error.

            Raises
            ------
            OSError, ValueError
                If the configured discovery operation fails; earlier matches
                may already have been yielded.
            """
            assert directory == tmp_path
            if pattern != 'missing':
                yield path
            if interrupted and pattern == 'first':
                raise OSError('PRIVATE traversal error')

        with monkeypatch.context() as scoped:
            scoped.setattr(Path, 'glob', glob)
            paths, failures = _source_inputs.discover(config)
        assert paths == [path]
        assert failures == [
            *(['cannot discover configured source inputs'] if interrupted else []),
            'no inputs match: missing',
        ]
        assert snapshot_files(tmp_path) == before


class TestSourceInputFailures:
    """Keep discovery/read errors redacted and equivalent across languages."""

    @pytest.mark.parametrize('kind', ['decode', 'directory', 'inspect', 'glob'])
    def test_failed_inputs(
        self: Self,
        source_case: SourceCase,
        write_file: FileWriter,
        tmp_path: Path,
        kind: str,
    ) -> None:
        """
        Verify failed inputs.

        Parameters
        ----------
        source_case : SourceCase
            Language-specific source parser, policy and fixture helpers.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        kind : str
            Native syntax kind or policy variant under test.
        """
        domain, filename, validate = source_case
        write_file('popo.toml', f'[{domain}]\ninclude=["{filename}"]')
        path = tmp_path / filename
        if kind == 'directory':
            path.mkdir()
        else:
            path.write_bytes(b'\xff' if kind == 'decode' else b'value = 1')
        config = load_source_check(tmp_path, domain)
        if kind in {'inspect', 'glob'}:
            operation = 'is_file' if kind == 'inspect' else 'glob'
            with patch.object(Path, operation, side_effect=PermissionError('PRIVATE')):
                failures = validate(config)
        else:
            failures = validate(config)
        assert failures
        assert 'PRIVATE' not in '\n'.join(failures)

    def test_undecodable_logs_do_not_disclose_content(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """
        Verify undecodable logs do not disclose content.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        write_file(
            'popo.toml',
            '[logs]\ninclude=["*.log"]\npatterns={ warning="WARNING" }',
        )
        (tmp_path / 'private.log').write_bytes(b'PRIVATE\xff')
        assert logs.validate(load_source_check(tmp_path, 'logs')) == [
            'private.log: cannot read UTF-8 input',
        ]


class TestSourceInspection:
    """Keep shared reads ordered, redacted and independent of domain policy."""

    @pytest.mark.parametrize('consumed', (1, 2, 3, 4))
    def test_consumes_only_requested_findings(
        self,
        tmp_path: Path,
        consumed: int,
    ) -> None:
        """
        Defer each file read and consume inspector iterators incrementally.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated root containing two readable source inputs.
        consumed : int
            Number of findings requested before inspecting read activity.
        """
        paths = [tmp_path / name for name in ('first', 'last')]
        for path in paths:
            path.write_text(path.name, encoding='utf-8')
        before = snapshot_files(tmp_path)
        inspect = Mock(side_effect=lambda path, source: iter((source,) * 2))
        with patch.object(
            _source_inputs,
            'read_source',
            wraps=_source_inputs.read_source,
        ) as read:
            findings = _source_inputs.inspect_sources(iter(paths), tmp_path, inspect)
            read.assert_not_called()
            inspect.assert_not_called()
            expected = ['first', 'first', 'last', 'last']
            assert [next(findings) for _ in range(consumed)] == expected[:consumed]
            reached = paths[: (consumed + 1) // 2]
            assert read.call_args_list == [call(path, tmp_path) for path in reached]
            assert inspect.call_args_list == [call(path, path.name) for path in reached]
            assert list(findings) == expected[consumed:]
            assert list(findings) == []
            assert read.call_count == inspect.call_count == 2
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('during_iteration', (False, True))
    def test_inspector_failures_propagate(
        self,
        tmp_path: Path,
        during_iteration: bool,
    ) -> None:
        """
        Propagate inspector failures instead of reporting partial success.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        during_iteration : bool
            Raise while consuming findings instead of calling the inspector.
        """
        path = tmp_path / 'input'
        path.write_text('text', encoding='utf-8')
        error = RuntimeError('inspection failed')
        inspect = (
            Mock(return_value=iter(Mock(side_effect=error), None))
            if during_iteration
            else Mock(side_effect=error)
        )
        with pytest.raises(
            RuntimeError,
            match='inspection failed',
            check=lambda raised: raised is error,
        ):
            list(_source_inputs.inspect_sources((path,), tmp_path, inspect))

    @pytest.mark.parametrize('failure', ('decode', 'missing'))
    def test_reads_once_and_continues_after_input_errors(
        self,
        tmp_path: Path,
        failure: str,
    ) -> None:
        """
        Retain duplicate findings and skip inspection of unreadable inputs.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        failure : str
            Expected failure text, or None for a successful scenario.
        """
        first, bad, last = (tmp_path / name for name in ('first', 'bad', 'last'))
        first.write_text('one', encoding='utf-8')
        last.write_text('two', encoding='utf-8')
        if failure == 'decode':
            bad.write_bytes(b'PRIVATE\xff')
        paths = (first, bad, last)
        before = snapshot_files(tmp_path)
        inspect = Mock(side_effect=lambda path, source: iter((path.name,) * 2))
        with patch.object(
            _source_inputs,
            'read_source',
            wraps=_source_inputs.read_source,
        ) as read:
            findings = list(
                _source_inputs.inspect_sources(iter(paths), tmp_path, inspect),
            )
        assert findings == [
            'first',
            'first',
            'bad: cannot read UTF-8 input',
            'last',
            'last',
        ]
        assert read.call_args_list == [call(path, tmp_path) for path in paths]
        assert inspect.call_args_list == [call(first, 'one'), call(last, 'two')]
        assert snapshot_files(tmp_path) == before


# !SECTION
