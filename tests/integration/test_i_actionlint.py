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

import shlex
import sys
from pathlib import Path

import pytest

from popo.cli import main
from tests.support.files import FileWriter

# SECTION: TESTS


class TestActionlintCommandLine:
    """
    Cover actionlint command line.

    Exercise compatibility, source validation and validator exit behavior.
    """

    @pytest.mark.parametrize('status', [0, 17])
    def test_actionlint_compatibility(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        status: int,
        capsys: pytest.CaptureFixture[str],
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
        """
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
            'print(p.resolve()); print("stderr", file=sys.stderr); '
            f'sys.exit({status})'
        )
        command = shlex.join([sys.executable, '-c', code])
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
        assert str(workflow) in streams.out
        assert streams.err == 'stderr\n'
        assert workflow.read_text() == original

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
    ) -> None:
        """
        Reject unsafe source before launching even a nonexistent executable.

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
        """
        write_file('.github/workflows/probe.yml', source)
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
        assert expected in capsys.readouterr().out


# !SECTION
