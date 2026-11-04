"""
:mod:`tests.e2e.test_e_apple_metadata` module.

Exercise installed Apple metadata checks outside the source checkout.
"""

import json
import plistlib
from pathlib import Path
from typing import Self

import pytest

from tests.support.apple_metadata import INFO, POLICY, PROJECT
from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: TESTS


class TestInstalledAppleMetadata:
    """Require equivalent public behavior in console and module entry points."""

    @pytest.mark.parametrize('module', (False, True), ids=('console', 'module'))
    def test_installed_metadata_contract(
        self: Self,
        installation: Installation,
        tmp_path: Path,
        module: bool,
    ) -> None:
        """
        Validate native metadata and reject changes with redacted findings.

        Parameters
        ----------
        installation : Installation
            Wheel or sdist installed in an isolated environment.
        tmp_path : pathlib.Path
            Independent consumer repository.
        module : bool
            Use the installed module rather than console entry point.
        """
        (tmp_path / 'pyproject.toml').write_text(POLICY)
        (tmp_path / 'Info.plist').write_bytes(plistlib.dumps(INFO))
        project = tmp_path / 'Example.xcodeproj/project.pbxproj'
        project.parent.mkdir()
        project.write_text(PROJECT)
        before = snapshot_files(tmp_path)
        arguments = (
            'check-apple-metadata',
            '--root',
            str(tmp_path),
            '--format',
            'json',
        )
        result = installation.run(*arguments, module=module)
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(result.stdout)['checks'][0]['check'] == 'check-apple-metadata'
        assert snapshot_files(tmp_path) == before
        (tmp_path / 'Info.plist').write_bytes(
            plistlib.dumps(INFO | {'PrivateKey': 'PRIVATE'}),
        )
        before = snapshot_files(tmp_path)
        result = installation.run(*arguments, module=module)
        assert result.returncode == 1
        assert 'PRIVATE' not in result.stdout + result.stderr
        assert snapshot_files(tmp_path) == before


# !SECTION
