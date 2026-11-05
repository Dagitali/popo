"""
:mod:`tests.integration.test_i_apple_release` module.

Exercise isolated release reports and value-redacted public command failures.
"""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Self
from unittest.mock import Mock

import pytest

from popo.cli import main
from tests.support.apple_release import POLICY, PROJECT
from tests.support.files import snapshot_files

# SECTION: CONSTANTS


FAILURE = 'error: apple-release-identity: invalid configuration or release metadata\n'


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(name='release_root')
def release_root_fixture(
    tmp_path: Path,
) -> Path:
    """
    Write literal consumer policy and native release input.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Disposable consumer root.

    Returns
    -------
    pathlib.Path
        Independent release configuration and project.
    """
    (tmp_path / 'pyproject.toml').write_text(POLICY, encoding='utf-8')
    project = tmp_path / 'Example.xcodeproj/project.pbxproj'
    project.parent.mkdir()
    project.write_text(PROJECT, encoding='utf-8')
    return tmp_path


# !SECTION


# SECTION: TESTS


class TestAppleReleaseCLI:
    """Require complete reports without native tools, Git state or mutation."""

    @pytest.mark.parametrize('format_', ('text', 'json'))
    @pytest.mark.parametrize(
        'case',
        (
            'missing',
            'utf8',
            'malformed',
            'schema',
            'policy',
            'tag',
        ),
    )
    def test_failure_is_private_and_leaves_stdout_empty(
        self: Self,
        release_root: Path,
        capsys: pytest.CaptureFixture[str],
        case: str,
        format_: str,
    ) -> None:
        """
        Reject incomplete evidence without partial reports or native values.

        Parameters
        ----------
        release_root : pathlib.Path
            Fresh disposable release input.
        capsys : pytest.CaptureFixture[str]
            Captured public command output.
        case : str
            Input, configuration or explicit tag failure.
        format_ : str
            Requested report format, neither of which permits partial output.
        """
        project = release_root / 'Example.xcodeproj/project.pbxproj'
        arguments = [
            'apple-release-identity',
            '--root',
            str(release_root),
            '--format',
            format_,
        ]
        if case == 'missing':
            project.unlink()
        elif case == 'utf8':
            project.write_bytes(b'\xffPRIVATE')
        elif case == 'malformed':
            project.write_text('{ PRIVATE', encoding='utf-8')
        elif case == 'schema':
            project.write_text('PRIVATE', encoding='utf-8')
        elif case == 'policy':
            (release_root / 'pyproject.toml').write_text(
                'PRIVATE malformed',
                encoding='utf-8',
            )
        else:
            arguments += ['--tag', 'PRIVATE wrong tag']
        before = snapshot_files(release_root)
        assert main(arguments) == 1
        output = capsys.readouterr()
        assert output.out == ''
        assert output.err == FAILURE
        assert snapshot_files(release_root) == before

    @pytest.mark.parametrize('format_', ('text', 'json'))
    @pytest.mark.parametrize('tag', (None, 'v1.2.0'))
    def test_report_exposes_only_selected_identity(
        self: Self,
        release_root: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        format_: str,
        tag: str | None,
    ) -> None:
        """
        Report explicit fields independently of tools and environment tags.

        Parameters
        ----------
        release_root : pathlib.Path
            Disposable native project and policy.
        capsys : pytest.CaptureFixture[str]
            Captured report and diagnostics.
        monkeypatch : pytest.MonkeyPatch
            Prevent tool execution and supply an irrelevant environment tag.
        format_ : str
            Human-readable or independent versioned JSON report.
        tag : str or None
            Optional matching caller tag.
        """
        project = release_root / 'Example.xcodeproj/project.pbxproj'
        project.write_text(
            PROJECT.replace(
                'PRODUCT_BUNDLE_IDENTIFIER =',
                'PRIVATE_SETTING =',
            ),
            encoding='utf-8',
        )
        monkeypatch.setenv('GITHUB_REF_NAME', 'PRIVATE wrong tag')
        runner = Mock(side_effect=AssertionError('Unexpected tool'))
        monkeypatch.setattr(subprocess, 'Popen', runner)
        before = snapshot_files(release_root)
        arguments = [
            'apple-release-identity',
            '--root',
            str(release_root),
            '--format',
            format_,
        ]
        if tag is not None:
            arguments += ['--tag', tag]
        assert main(arguments) == 0
        output = capsys.readouterr()
        assert output.err == ''
        assert 'PRIVATE' not in output.out
        if format_ == 'json':
            assert json.loads(output.out) == {
                'schema_version': 1,
                'version': '1.2.0',
                'build': 7,
            }
        else:
            assert output.out == 'Release identity: 1.2.0 / build 7\n'
        runner.assert_not_called()
        assert snapshot_files(release_root) == before

    def test_reporting_cannot_be_selected_as_a_native_check(
        self: Self,
        release_root: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Keep field reports outside shared native check-result aggregation.

        Parameters
        ----------
        release_root : pathlib.Path
            Consumer whose explicit check list incorrectly names reporting.
        capsys : pytest.CaptureFixture[str]
            Captured sanitized check-selection findings.
        """
        (release_root / 'pyproject.toml').write_text(
            '[tool.popo]\nchecks=["apple-release-identity"]\n' + POLICY,
            encoding='utf-8',
        )
        before = snapshot_files(release_root)
        assert main(['check-all', '--root', str(release_root)]) == 1
        output = capsys.readouterr()
        assert output.out == (
            'FAIL: configuration: unknown offline checks: apple-release-identity\n'
        )
        assert output.err == ''
        assert snapshot_files(release_root) == before

    def test_symlink_cannot_escape_consumer_root(
        self: Self,
        release_root: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Reject a selected external file without inspecting its metadata.

        Parameters
        ----------
        release_root : pathlib.Path
            Consumer containing a selected project symlink.
        tmp_path : pathlib.Path
            Disposable root used to derive an external sibling input.
        capsys : pytest.CaptureFixture[str]
            Captured redacted diagnostics.
        symlink : collections.abc.Callable[[pathlib.Path, pathlib.Path], None]
            Platform-aware creator preserving unexpected fixture failures.
        """
        project = release_root / 'Example.xcodeproj/project.pbxproj'
        outside = tmp_path.parent / (tmp_path.name + '-PRIVATE-project')
        outside.write_text(PROJECT, encoding='utf-8')
        project.unlink()
        try:
            symlink(project, outside)
            before = snapshot_files(release_root)
            outside_before = outside.read_bytes()
            assert main(['apple-release-identity', '--root', str(release_root)]) == 1
            output = capsys.readouterr()
            assert output.out == ''
            assert output.err == FAILURE
            assert snapshot_files(release_root) == before
            assert outside.read_bytes() == outside_before
        finally:
            outside.unlink()


# !SECTION
