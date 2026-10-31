# tests/integration/test_i_actionlint.py
# popo
#
# Responsibilities
# - Exercise actionlint compatibility dispatch and unchanged tool failures.
#
# Maintainer Notes
# - Use a deterministic fake linter; no installations or network requests.

"""
:mod:`tests.integration.test_i_actionlint` module.

Public CLI integration for actionlint's disposable compatibility view.
"""

import errno
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.cli import main
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestActionlintCommandLine:
    """
    Cover actionlint command line.

    Exercise compatibility, source validation and validator exit behavior.
    """

    @pytest.mark.parametrize(
        'aliased_temp',
        (False, True),
        ids=('real-temp', 'aliased-temp'),
    )
    @pytest.mark.parametrize('status', [0, 17])
    def test_actionlint_compatibility(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        status: int,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        aliased_temp: bool,
    ) -> None:
        """
        Preserve both streams, validator status, and source self references.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        status : int
            Expected CLI exit status or hosted response state.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        monkeypatch : pytest.MonkeyPatch
            Restore the temporary-directory base after the scenario.
        aliased_temp : bool
            Whether temporary views use a symlinked base directory.
        """
        if aliased_temp:
            real = tmp_path.parent / f'{tmp_path.name}-temp'
            real.mkdir()
            alias = tmp_path.parent / f'{tmp_path.name}-alias'
            try:
                alias.symlink_to(real, target_is_directory=True)
            except OSError as error:
                if error.errno not in {
                    errno.EACCES,
                    errno.EPERM,
                    errno.ENOSYS,
                    errno.ENOTSUP,
                }:
                    raise
                pytest.skip(f'Directory symlinks unavailable: {error}')
            monkeypatch.setattr(tempfile, 'tempdir', str(alias))
        write_file(
            'actions/test/action.yml',
            'name: Test\ndescription: Test\nruns: {using: node24}',
        )
        original = 'jobs: {probe: {steps: [{uses: "$/actions/test"}]}}\n'
        workflow = write_file('.github/workflows/probe.yml', original)
        code = (
            'import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
            'text=p.read_text(); assert "$/" not in text; '
            'assert pathlib.Path("actions/test/action.yml").is_file(); '
            'print(p.resolve()); print(f"stderr: {p.resolve()}", file=sys.stderr); '
            f'sys.exit({status})'
        )
        command = shlex.join([sys.executable, '-c', code])
        before = snapshot_files(tmp_path)
        assert (
            main(
                [
                    'check-actionlint',
                    '--root',
                    str(tmp_path),
                    '--actionlint',
                    command,
                    str(workflow),
                ],
            )
            == status
        )
        streams = capsys.readouterr()
        assert streams.out == f'{workflow}\n'
        assert streams.err == f'stderr: {workflow}\n'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'source,expected',
        [
            ('uses: "$/actions/test@main"', 'invalid self-repository'),
            ('uses: "$/actions/missing"', 'missing local'),
            ('uses: "$/../outside"', 'invalid self-repository'),
            ('uses: one\nuses: two', 'duplicate YAML key'),
        ],
    )
    def test_actionlint_rejects_invalid_source(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        source: str,
        expected: str,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Reject unsafe source before attempting any validator process launch.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        source : str
            Decoded input text to inspect without executing it.
        expected : str
            Expected result for the selected parameterized scenario.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        monkeypatch : pytest.MonkeyPatch
            Restore the process-launch guard after each independent scenario.
        """
        write_file('.github/workflows/probe.yml', source)
        before = snapshot_files(tmp_path)
        runner = Mock(side_effect=AssertionError('invalid source must not launch'))
        monkeypatch.setattr(subprocess, 'run', runner)
        assert (
            main(
                [
                    'check-actionlint',
                    '--root',
                    str(tmp_path),
                    '--actionlint',
                    'nonexistent-actionlint',
                ],
            )
            == 1
        )
        streams = capsys.readouterr()
        assert expected in streams.out
        assert streams.err == ''
        runner.assert_not_called()
        assert snapshot_files(tmp_path) == before


# !SECTION
