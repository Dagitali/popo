"""
:mod:`tests.integration.test_i_cli` module.

Test command-line success and failure reporting.
"""

import runpy
from pathlib import Path

import pytest

from popo import __version__
from popo.cli import main
from tests.support.files import FileWriter

# SECTION: TESTS


class TestCommandLine:
    """
    Exercise public command dispatch, diagnostics, and process exit contracts.

    Notes
    -----
    Call the public dispatcher in process with temporary consumer inputs.
    Capture output and parser exits; monkeypatch restores entry-point arguments
    and working-directory changes after each scenario.
    """

    def test_all_includes_opted_in_contracts(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Verify aggregate dispatch includes explicitly configured automation
        checks.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        capsys : pytest.CaptureFixture[str]
            Capture in-process CLI output and errors.
        """
        write_file(
            'pyproject.toml',
            '[tool.popo.automation]\nworkflow-globs = ["absent.yml"]',
        )
        assert main(['check-all', '--root', str(tmp_path)]) == 1
        assert 'no automation files match: absent.yml' in capsys.readouterr().out

    @pytest.mark.parametrize(
        ('arguments', 'path', 'content', 'status', 'message'),
        [
            (['check-docs'], 'README.md', '# Project\n', 0, 'PASS:'),
            (
                ['check-automation-contracts'],
                '.github/workflows/ci.yml',
                'on: {workflow_call: null}',
                0,
                'PASS:',
            ),
            (
                ['check-automation-contracts', '--pins-only'],
                '.github/workflows/ci.yml',
                'uses: upstream/action@main',
                1,
                'FAIL:',
            ),
            (
                ['check-automation-contracts'],
                'pyproject.toml',
                '[tool.popo.automation]\nunknown = true',
                1,
                'configuration:',
            ),
            (
                ['check-github-actions-pins'],
                '.github/ci.yml',
                f'uses: @{'a' * 40}\n',
                1,
                'FAIL:',
            ),
            (['check-docs'], 'README.md', '[missing]: absent.md\n', 1, 'FAIL:'),
            (['check-docs'], 'README.md', '# Project\n[self]: #project\n', 0, 'PASS:'),
            (
                ['check-release-changelog', 'v1.0.0'],
                'CHANGELOG.md',
                '# Changelog',
                1,
                'FAIL:',
            ),
            (
                ['check-release-changelog', 'v1.0.0', '--changelog', 'custom.md'],
                'custom.md',
                '## [1.0.0] - 2026-09-20',
                0,
                'PASS:',
            ),
            (
                ['check-github-actions-pins'],
                '.github/ci.yml',
                f'uses: owner/action@{'a' * 40}',
                0,
                'PASS:',
            ),
            (
                ['check-github-actions-pins', '--automation-directory', 'automation'],
                'automation/ci.yml',
                'uses: owner/action@main',
                1,
                'FAIL:',
            ),
            (
                ['check-dependency-boundaries'],
                'pyproject.toml',
                '[',
                1,
                'configuration:',
            ),
            (['check-python-policy'], 'pyproject.toml', '[project]', 1, 'FAIL:'),
            (['check-all'], 'README.md', '# Empty repository', 1, 'FAIL:'),
        ],
    )
    def test_commands(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        arguments: list[str],
        path: str,
        content: str,
        status: int,
        message: str,
    ) -> None:
        """
        Verify CLI dispatch returns the expected status and standard-output
        diagnostic.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        monkeypatch : pytest.MonkeyPatch
            Restore environment, attributes, and working directory.
        capsys : pytest.CaptureFixture[str]
            Capture in-process CLI output and errors.
        arguments : list[str]
            CLI argument sequence for the parameterized dispatch or parser
            scenario.
        path : str
            Repository-relative path whose contents are prepared for the
            scenario.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        status : int
            Expected process or CLI exit status.
        message : str
            Expected diagnostic substring; an empty string selects a successful
            case.
        """
        write_file(path, content)
        monkeypatch.chdir(tmp_path)
        assert main([*arguments, '--root', str(tmp_path)]) == status
        captured = capsys.readouterr()
        assert message in captured.out
        assert not captured.err

    @pytest.mark.parametrize('constraint', ['demo==1', 'demo==1 # minimum'])
    def test_dependency_command(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        constraint: str,
    ) -> None:
        """
        Verify CLI dependency checks accept minimum pins with optional
        comments.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        capsys : pytest.CaptureFixture[str]
            Capture in-process CLI output and errors.
        constraint : str
            Minimum dependency pin, optionally followed by an inline
            annotation.
        """
        write_file('pyproject.toml', '[project]\ndependencies = ["demo>=1,<2"]')
        write_file('requirements/lowest.txt', constraint)
        assert main(['check-dependency-boundaries', '--root', str(tmp_path)]) == 0
        assert 'PASS:' in capsys.readouterr().out

    def test_module_entry_point(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Verify module execution reports the installed version and exits
        successfully.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Restore environment, attributes, and working directory.
        capsys : pytest.CaptureFixture[str]
            Capture in-process CLI output and errors.
        """
        monkeypatch.setattr('sys.argv', ['popo', '--version'])
        with pytest.raises(SystemExit, check=lambda error: error.code == 0):
            runpy.run_module('popo', run_name='__main__')
        assert __version__ in capsys.readouterr().out

    @pytest.mark.parametrize(
        ('arguments', 'status', 'message'),
        [
            (['--version'], 0, __version__),
            (['--help'], 0, 'check-all'),
            ([], 2, 'required'),
            (['unknown'], 2, 'invalid choice'),
        ],
    )
    def test_parser_exits(
        self,
        arguments: list[str],
        status: int,
        message: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Verify informational and invalid arguments use their documented exit
        channels.

        Parameters
        ----------
        arguments : list[str]
            CLI argument sequence for the parameterized dispatch or parser
            scenario.
        status : int
            Expected process or CLI exit status.
        message : str
            Expected diagnostic substring; an empty string selects a successful
            case.
        capsys : pytest.CaptureFixture[str]
            Capture in-process CLI output and errors.
        """
        with pytest.raises(SystemExit, check=lambda error: error.code == status):
            main(arguments)
        captured = capsys.readouterr()
        assert message in (captured.out if status == 0 else captured.err)


# !SECTION
