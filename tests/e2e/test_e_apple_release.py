"""
:mod:`tests.e2e.test_e_apple_release` module.

Verify release-identity reporting in isolated wheel and sdist installations.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from tests.support.apple_release import POLICY, PROJECT
from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: TESTS


class TestInstalledAppleRelease:
    """Exercise both public entry points without checkout imports or Xcode."""

    @pytest.mark.parametrize('module', (False, True), ids=('console', 'module'))
    @pytest.mark.parametrize('format_', ('text', 'json'))
    def test_installed_identity_and_tag_failure(
        self: Self,
        installation: Installation,
        tmp_path: Path,
        module: bool,
        format_: str,
    ) -> None:
        """
        Emit complete release fields and reject mismatched tags privately.

        Parameters
        ----------
        installation : Installation
            Fresh package installation outside the source checkout.
        tmp_path : pathlib.Path
            Disposable native release inputs.
        module : bool
            Use the module rather than console entry point.
        format_ : str
            Human-readable or independent JSON field report.
        """
        (tmp_path / 'pyproject.toml').write_text(POLICY, encoding='utf-8')
        project = tmp_path / 'Example.xcodeproj/project.pbxproj'
        project.parent.mkdir()
        project.write_text(PROJECT, encoding='utf-8')
        arguments = (
            'apple-release-identity',
            '--root',
            str(tmp_path),
            '--format',
            format_,
        )
        before = snapshot_files(tmp_path)
        result = installation.run(*arguments, '--tag', 'v1.2.0', module=module)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ''
        if format_ == 'json':
            assert json.loads(result.stdout) == {
                'schema_version': 1,
                'version': '1.2.0',
                'build': 7,
            }
        else:
            assert result.stdout == 'Release identity: 1.2.0 / build 7\n'
        assert snapshot_files(tmp_path) == before
        result = installation.run(*arguments, '--tag', 'PRIVATE', module=module)
        assert result.returncode == 1
        assert result.stdout == ''
        assert result.stderr == (
            'error: apple-release-identity: invalid configuration or release metadata\n'
        )
        assert snapshot_files(tmp_path) == before


# !SECTION
