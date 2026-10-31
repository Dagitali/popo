"""
:mod:`tests.unit.config.test_u_swift_policy` module.

Validate explicit Swift policy independently of Python package metadata.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.config import ConfigurationError
from popo.config._common import read_popo
from popo.config.selection import load_plan
from popo.config.swift_policy import (
    load_swift_policy_config,
    parse_swift_policy,
    parse_version,
)
from tests.support.files import snapshot_files

# SECTION: CONSTANTS


REQUIRED_SETTINGS_MESSAGE = (
    'Swift policy requires compilers, workflows and a boolean CI preference'
)


# !SECTION


# SECTION: TESTS


class TestSwiftPolicyConfiguration:
    """Reject ambiguous versions, unsafe paths and inconsistent preferences."""

    @pytest.mark.parametrize(
        'old,new,message',
        (
            pytest.param(
                '[swift-policy]',
                '[other]',
                'swift-policy must be a TOML table',
                id='missing-table',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "snapshot"',
                'Swift policy requires stable numeric versions',
                id='unstable-tools',
            ),
            pytest.param(
                'compiler-versions = ["6.1.2", "6.2.0"]',
                'compiler-versions = []',
                REQUIRED_SETTINGS_MESSAGE,
                id='empty-compilers',
            ),
            pytest.param(
                'compiler-versions = ["6.1.2", "6.2.0"]',
                'compiler-versions = ["6.1", "6.1.0", "6.1.2"]',
                'Swift compiler versions, preference and tools minimum conflict',
                id='duplicate-compilers',
            ),
            pytest.param(
                'preferred-version = "6.1.2"',
                'preferred-version = "6.3.0"',
                'Swift compiler versions, preference and tools minimum conflict',
                id='unsupported-preference',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "7.0"',
                'Swift compiler versions, preference and tools minimum conflict',
                id='incompatible-tools',
            ),
            pytest.param(
                'workflow-globs = [".github/workflows/ci.yml"]',
                'workflow-globs = []',
                REQUIRED_SETTINGS_MESSAGE,
                id='empty-workflows',
            ),
            pytest.param(
                'workflow-globs = [".github/workflows/ci.yml"]',
                'workflow-globs = ["../ci.yml"]',
                'Swift policy paths must stay inside root',
                id='escaping-workflow',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "5.9"\nmanifest="/Package.swift"',
                'Swift policy paths must stay inside root',
                id='absolute-manifest',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "5.9"\nversion-file="../version"',
                'Swift policy paths must stay inside root',
                id='escaping-version-file',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "5.9"\nrequire-preferred-in-ci=1',
                REQUIRED_SETTINGS_MESSAGE,
                id='nonboolean-preference',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "5.9"\nworkflow-version-key="bad key"',
                'workflow-version-key must be a literal identifier',
                id='invalid-input-key',
            ),
            pytest.param(
                'tools-version = "5.9"',
                'tools-version = "5.9"\nunknown=true',
                'unknown swift-policy setting',
                id='unknown-setting',
            ),
        ),
    )
    def test_invalid_configuration(
        self,
        swift_policy_consumer: Path,
        old: str,
        new: str,
        message: str,
    ) -> None:
        """
        Reject each mutation for its intended error without changing files.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        old : str
            Original value replaced by the scenario.
        new : str
            Replacement value supplied by the scenario.
        message : str
            Complete expected diagnostic for the selected policy violation.
        """
        path = swift_policy_consumer / 'popo.toml'
        text = path.read_text(encoding='utf-8')
        assert text.count(old) == 1
        path.write_text(text.replace(old, new, 1), encoding='utf-8')
        before = snapshot_files(swift_policy_consumer)
        with pytest.raises(ConfigurationError) as raised:
            load_swift_policy_config(swift_policy_consumer)
        assert str(raised.value) == message
        assert snapshot_files(swift_policy_consumer) == before

    def test_parse_without_reading_inputs(
        self,
        swift_policy_consumer: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Parse preloaded settings without reading configuration or inputs.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        """
        root = swift_policy_consumer
        settings = read_popo(root)
        expected = load_swift_policy_config(root)
        reader = Mock(side_effect=AssertionError('unexpected file read'))
        monkeypatch.setattr(Path, 'read_text', reader)
        assert parse_swift_policy(root, settings) == expected
        reader.assert_not_called()

    @pytest.mark.parametrize('embedded', [False, True], ids=['standalone', 'pyproject'])
    def test_policy_sources(
        self,
        swift_policy_consumer: Path,
        embedded: bool,
    ) -> None:
        """
        Verify policy sources.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        embedded : bool
            Whether policy is embedded in Python project metadata.
        """
        root = swift_policy_consumer
        if embedded:
            text = (
                (root / 'popo.toml')
                .read_text()
                .replace('[swift-policy]', '[tool.popo.swift-policy]')
            )
            (root / 'popo.toml').unlink()
            (root / 'pyproject.toml').write_text(text, encoding='utf-8')
        config = load_swift_policy_config(root)
        assert config == parse_swift_policy(root, read_popo(root))
        assert config.preferred_version == '6.1.2'
        assert config.tools_version == '5.9'
        assert config.manifest == root / 'Package.swift'
        assert 'check-swift-policy' in load_plan(root).checks

    @pytest.mark.parametrize(
        'version,expected',
        [
            ('6.1', (6, 1, 0)),
            ('6.1.0', (6, 1, 0)),
            (' \t6.1\n', (6, 1, 0)),
            ('0.0', (0, 0, 0)),
            ('12.34.56', (12, 34, 56)),
            *(
                (version, None)
                for version in (
                    '6.1-SNAPSHOT',
                    '6',
                    '06.1',
                    '>=6.0',
                    '6.0.0.1',
                    '',
                    '6.١',
                    '6.1+build',
                    '6.1-rc.1',
                )
            ),
        ],
    )
    def test_version_syntax(
        self,
        version: str,
        expected: tuple[int, int, int] | None,
    ) -> None:
        """
        Normalize stable ASCII versions and reject unsupported syntax.

        Parameters
        ----------
        version : str
            Version value supplied to the parser or policy comparison.
        expected : tuple[int, int, int] | None
            Expected result for the selected parameterized scenario.
        """
        if expected is None:
            with pytest.raises(
                ValueError,
                match=r'^expected stable Swift major\.minor\[\.patch\] version$',
            ):
                parse_version(version)
        else:
            assert parse_version(version) == expected


# !SECTION
