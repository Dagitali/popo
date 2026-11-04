"""
:mod:`tests.integration.test_i_apple_metadata` module.

Exercise public Apple checks, profile dispatch and private read-only findings.
"""

import json
import plistlib
from pathlib import Path
from typing import Self
from unittest.mock import patch

import pytest

from popo.cli import main
from tests.support.apple_metadata import INFO, POLICY, PROJECT
from tests.support.files import snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='apple_project')
def apple_project_fixture(
    tmp_path: Path,
) -> Path:
    """
    Create independent native inputs and consumer-owned policy.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Disposable consumer directory.

    Returns
    -------
    pathlib.Path
        Populated repository requiring no Xcode installation.
    """
    (tmp_path / 'pyproject.toml').write_text(POLICY)
    (tmp_path / 'Info.plist').write_bytes(plistlib.dumps(INFO))
    project = tmp_path / 'Example.xcodeproj/project.pbxproj'
    project.parent.mkdir()
    project.write_text(PROJECT)
    return tmp_path


# !SECTION


# SECTION: TESTS


class TestAppleMetadataCLI:
    """Validate native contracts without inspecting source or invoking tools."""

    @pytest.mark.parametrize('binary', (False, True))
    @pytest.mark.parametrize('command', ('check-apple-metadata', 'check-all'))
    def test_explicit_metadata_passes_without_mutation_or_native_tools(
        self: Self,
        apple_project: Path,
        capsys: pytest.CaptureFixture[str],
        binary: bool,
        command: str,
    ) -> None:
        """
        Accept XML/binary metadata through direct and aggregate dispatch.

        Parameters
        ----------
        apple_project : pathlib.Path
            Disposable native metadata and policy.
        capsys : pytest.CaptureFixture[str]
            Captured public command streams.
        binary : bool
            Select binary rather than XML property-list encoding.
        command : str
            Direct or configured aggregate invocation.
        """
        (apple_project / 'Info.plist').write_bytes(
            plistlib.dumps(
                INFO,
                fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML,
            ),
        )
        before = snapshot_files(apple_project)
        with patch('subprocess.run', side_effect=AssertionError('no tools')):
            assert (
                main([command, '--root', str(apple_project), '--format', 'json']) == 0
            )
        report = json.loads(capsys.readouterr().out)
        assert report['checks'][0]['check'] == 'check-apple-metadata'
        assert snapshot_files(apple_project) == before

    @pytest.mark.parametrize(
        'case',
        (
            'missing',
            'malformed',
            'not-mapping',
            'bool-as-int',
            'absent',
            'project-schema',
            'target',
            'configuration',
            'reference',
            'settings-type',
            'setting',
            'consistent',
            'missing-consistent',
            'root-project',
            'configuration-list',
            'reference-type',
            'xml',
        ),
    )
    def test_failed_metadata_is_redacted_and_other_rules_continue(
        self: Self,
        apple_project: Path,
        capsys: pytest.CaptureFixture[str],
        case: str,
    ) -> None:
        """
        Fail closed on unavailable, malformed and policy-violating inputs.

        Parameters
        ----------
        apple_project : pathlib.Path
            Disposable consumer root.
        capsys : pytest.CaptureFixture[str]
            Captured command diagnostics.
        case : str
            Independent native metadata failure.
        """
        info = apple_project / 'Info.plist'
        project = apple_project / 'Example.xcodeproj/project.pbxproj'
        if case == 'missing':
            info.unlink()
        elif case == 'malformed':
            info.write_bytes(b'PRIVATE malformed')
        elif case == 'xml':
            info.write_bytes(b'<?xml version="1.0"?><plist><dict>PRIVATE')
        elif case == 'not-mapping':
            info.write_bytes(plistlib.dumps(['PRIVATE']))
        elif case == 'bool-as-int':
            info.write_bytes(
                plistlib.dumps(INFO | {'ITSAppUsesNonExemptEncryption': 0}),
            )
        elif case == 'absent':
            info.write_bytes(plistlib.dumps(INFO | {'PrivateKey': 'PRIVATE'}))
        else:
            before, after = {
                'root-project': ('isa = PBXProject', 'isa = PRIVATE'),
                'configuration-list': ('isa = XCConfigurationList', 'isa = PRIVATE'),
                'reference-type': (
                    'buildConfigurations = (D, R,)',
                    'buildConfigurations = PRIVATE',
                ),
                'project-schema': ('objects =', 'PRIVATE ='),
                'target': ('name = Example', 'name = PRIVATE'),
                'configuration': ('name = Debug', 'name = PRIVATE'),
                'reference': (
                    'buildConfigurationList = L',
                    'buildConfigurationList = PRIVATE',
                ),
                'settings-type': ('buildSettings = {', 'PRIVATE = {'),
                'setting': ('com.example.app', 'PRIVATE'),
                'consistent': (
                    'MARKETING_VERSION = 1.2.0',
                    'MARKETING_VERSION = PRIVATE',
                ),
                'missing-consistent': ('MARKETING_VERSION', 'PRIVATE'),
            }[case]
            project.write_text(PROJECT.replace(before, after, 1))
        assert main(['check-apple-metadata', '--root', str(apple_project)]) == 1
        output = capsys.readouterr()
        assert 'PRIVATE' not in output.out + output.err
        assert 'metadata missing, invalid or violates policy' in output.out
        # A second independent failure must still be reported.
        project.write_text('PRIVATE')
        info.write_bytes(b'PRIVATE')
        assert main(['check-apple-metadata', '--root', str(apple_project)]) == 1
        assert (
            capsys.readouterr().out.count(
                'metadata missing, invalid or violates policy',
            )
            == 3
        )

    def test_symlink_cannot_escape_root(
        self: Self,
        apple_project: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Reject external symlink inputs without reporting their targets.

        Parameters
        ----------
        apple_project : pathlib.Path
            Consumer containing a selected symlink.
        tmp_path : pathlib.Path
            Disposable root used to derive an outside sibling file.
        capsys : pytest.CaptureFixture[str]
            Captured command diagnostics.
        """
        outside = tmp_path.parent / (tmp_path.name + '-PRIVATE.plist')
        outside.write_bytes(plistlib.dumps(INFO))
        info = apple_project / 'Info.plist'
        info.unlink()
        try:
            info.symlink_to(outside)
        except OSError:
            outside.unlink()
            pytest.skip('symlinks unavailable on this host')
        try:
            assert main(['check-apple-metadata', '--root', str(apple_project)]) == 1
            assert 'PRIVATE' not in capsys.readouterr().out
        finally:
            outside.unlink()


# !SECTION
