"""
:mod:`tests.integration.test_i_coverage` module.

Exercise public coverage reporting, read-only operation and redacted failures.
"""

import json
import subprocess
from pathlib import Path
from typing import Self
from unittest.mock import Mock

import pytest

from popo.cli import main
from tests.support.coverage import export_report
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestCoverageCLI:
    """Keep generation outside check profiles and native-tool execution."""

    @pytest.mark.parametrize(
        'case',
        ('missing', 'json', 'utf8', 'schema', 'unavailable'),
    )
    def test_failure_keeps_stdout_empty_and_contents_private(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        case: str,
    ) -> None:
        """
        Report input failures without exposing paths, source text or errors.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Directory containing disposable report inputs.
        capsys : pytest.CaptureFixture[str]
            Captured public command streams.
        case : str
            Missing input, decoding, schema or unavailable-measurement failure.
        """
        source = tmp_path / 'PRIVATE[1].json'
        if case != 'missing':
            source.write_bytes(
                {
                    'json': b'{PRIVATE',
                    'utf8': b'\xffPRIVATE',
                    'schema': b'{"data":"PRIVATE"}',
                    'unavailable': b'{"data":[]}',
                }[case],
            )
        before = snapshot_files(tmp_path)
        assert (
            main(
                [
                    'coverage-summary',
                    str(source),
                    '--adapter',
                    'llvm',
                    '--include',
                    '**/*.swift',
                ],
            )
            == 1
        )
        output = capsys.readouterr()
        assert output.out == ''
        assert 'error: coverage-summary:' in output.err
        assert 'PRIVATE' not in output.err
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'arguments',
        [
            [],
            ['input.json'],
            ['input.json', '--adapter', 'bad', '--include', '*'],
            ['input.json', '--adapter', 'llvm'],
            ['input.json', '--adapter', 'llvm', '--include', '*', '--format', 'bad'],
        ],
    )
    def test_invalid_usage_never_reads_inputs(
        self: Self,
        monkeypatch: pytest.MonkeyPatch,
        arguments: list[str],
    ) -> None:
        """
        Reject unsupported CLI options before opening a report.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Restores the input-read guard after the scenario.
        arguments : list[str]
            Incomplete or invalid generation arguments.
        """
        reader = Mock(side_effect=AssertionError('Unexpected report read'))
        monkeypatch.setattr(Path, 'read_text', reader)
        with pytest.raises(SystemExit) as failure:
            main(['coverage-summary', *arguments])
        assert failure.value.code == 2
        reader.assert_not_called()

    @pytest.mark.parametrize('adapter', ('llvm', 'xccov'))
    @pytest.mark.parametrize('format_', (None, 'markdown', 'json'))
    def test_success_is_read_only_and_runs_no_native_tools(
        self: Self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        adapter: str,
        format_: str | None,
    ) -> None:
        """
        Emit only complete selected measurements in every supported format.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Directory containing a literal report filename with glob
            characters.
        monkeypatch : pytest.MonkeyPatch
            Restores the native-process guard after the scenario.
        capsys : pytest.CaptureFixture[str]
            Captured public command streams.
        adapter : str
            Explicit export adapter selected by the caller.
        format_ : str or None
            Explicit Markdown/JSON or default Markdown output.
        """
        source = tmp_path / 'report[1].json'
        source.write_text(
            json.dumps(
                export_report(
                    adapter,
                    [
                        ('PRIVATE/App/File.swift', 3, 4),
                        ('PRIVATE/Tests/Test.swift', 100, 100),
                    ],
                ),
            ),
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        runner = Mock(side_effect=AssertionError('Unexpected native tool'))
        monkeypatch.setattr(subprocess, 'Popen', runner)
        arguments = [
            'coverage-summary',
            str(source),
            '--adapter',
            adapter,
            '--include',
            '**/App/**/*.swift',
            '--exclude',
            '**/Tests/**',
        ]
        if format_:
            arguments += ['--format', format_]
        assert main(arguments) == 0
        output = capsys.readouterr()
        assert output.err == ''
        assert 'PRIVATE' not in output.out
        if format_ == 'json':
            data = json.loads(output.out)
            assert data['schema_version'] == 1
            assert data['files'] == 1
            assert data['metrics']['lines'] == {
                'covered': 3,
                'total': 4,
                'percent': 75.0,
            }
        else:
            assert '| lines | 3 | 4 | 75.0% |' in output.out
        runner.assert_not_called()
        assert snapshot_files(tmp_path) == before


# !SECTION
