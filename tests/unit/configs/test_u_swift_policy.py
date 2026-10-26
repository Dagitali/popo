"""Validate explicit Swift policy independently of Python package metadata."""

from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.selection import load_plan
from popo.config.swift_policy import load_swift_policy_config, parse_version

# SECTION: TESTS


class TestSwiftPolicyConfiguration:
    """Reject ambiguous versions, unsafe paths and inconsistent preferences."""

    @pytest.mark.parametrize('embedded', [False, True], ids=['standalone', 'pyproject'])
    def test_policy_sources(
        self,
        swift_policy_consumer: Path,
        embedded: bool,
    ) -> None:
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
        assert config.preferred_version == '6.1.2'
        assert config.tools_version == '5.9'
        assert config.manifest == root / 'Package.swift'
        assert 'check-swift-policy' in load_plan(root).checks

    @pytest.mark.parametrize(
        'old,new',
        [
            ('[swift-policy]', '[other]'),
            ('tools-version = "5.9"', 'tools-version = "snapshot"'),
            ('compiler-versions = ["6.1.2", "6.2.0"]', 'compiler-versions = []'),
            (
                'compiler-versions = ["6.1.2", "6.2.0"]',
                'compiler-versions = ["6.1", "6.1.0"]',
            ),
            ('preferred-version = "6.1.2"', 'preferred-version = "6.3.0"'),
            ('tools-version = "5.9"', 'tools-version = "7.0"'),
            ('workflow-globs = [".github/workflows/ci.yml"]', 'workflow-globs = []'),
            (
                'workflow-globs = [".github/workflows/ci.yml"]',
                'workflow-globs = ["../ci.yml"]',
            ),
            (
                'tools-version = "5.9"',
                'tools-version = "5.9"\nmanifest="/Package.swift"',
            ),
            (
                'tools-version = "5.9"',
                'tools-version = "5.9"\nversion-file="../version"',
            ),
            (
                'tools-version = "5.9"',
                'tools-version = "5.9"\nrequire-preferred-in-ci=1',
            ),
            (
                'tools-version = "5.9"',
                'tools-version = "5.9"\nworkflow-version-key="bad key"',
            ),
            ('tools-version = "5.9"', 'tools-version = "5.9"\nunknown=true'),
        ],
    )
    def test_invalid_configuration(
        self,
        swift_policy_consumer: Path,
        old: str,
        new: str,
    ) -> None:
        path = swift_policy_consumer / 'popo.toml'
        text = path.read_text()
        assert old in text
        path.write_text(text.replace(old, new), encoding='utf-8')
        with pytest.raises(ConfigurationError):
            load_swift_policy_config(swift_policy_consumer)

    @pytest.mark.parametrize(
        'version',
        ['6.1-SNAPSHOT', '6', '06.1', '>=6.0', '6.0.0.1', ''],
    )
    def test_version_syntax(self, version: str) -> None:
        with pytest.raises(ValueError):
            parse_version(version)

    def test_omitted_patch_means_zero(self) -> None:
        assert parse_version('6.1') == parse_version('6.1.0') == (6, 1, 0)


# !SECTION
