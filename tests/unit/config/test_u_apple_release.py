"""
:mod:`tests.unit.config.test_u_apple_release` module.

Reject unsafe or ambiguous release policy before native inputs are read.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.config import ConfigurationError
from popo.config.apple_release import load_apple_release_config
from tests.support.apple_release import POLICY
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestAppleReleaseConfiguration:
    """Keep consumer selectors explicit and independently configurable."""

    @pytest.mark.parametrize(
        'before,after,message',
        (
            pytest.param(
                POLICY,
                '',
                'apple-release must be a TOML table',
                id='missing',
            ),
            pytest.param(
                '',
                'unknown=true\n',
                'apple-release: unknown setting',
                id='unknown',
            ),
            pytest.param(
                'Example.xcodeproj/project.pbxproj',
                '../PRIVATE',
                'apple-release.project: requires a confined literal path',
                id='path',
            ),
            pytest.param(
                'target = "Example"',
                'target = ""',
                'target must be a non-empty string',
                id='target',
            ),
            pytest.param(
                '["Debug", "Release"]',
                '[]',
                'apple-release: requires configurations',
                id='empty',
            ),
            pytest.param(
                '["Debug", "Release"]',
                '["Debug", "Debug"]',
                'apple-release.configurations contains duplicates',
                id='duplicate',
            ),
            pytest.param(
                '["Debug", "Release"]',
                'true',
                'apple-release.configurations must be an array of nonempty strings',
                id='config-type',
            ),
            pytest.param(
                '',
                'tag-prefix=" PRIVATE "\n',
                'apple-release: invalid tag-prefix',
                id='prefix',
            ),
            pytest.param(
                '',
                'product-type=false\n',
                'product-type must be a non-empty string',
                id='product',
            ),
        ),
    )
    def test_invalid_configuration_fails_before_input_reads(
        self: Self,
        tmp_path: Path,
        before: str,
        after: str,
        message: str,
    ) -> None:
        """
        Reject malformed selection, path and tag convention settings.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Policy root with no project files.
        before : str
            Unique policy fragment to replace; empty appends a setting.
        after : str
            Independent invalid replacement or appended setting.
        message : str
            Exact diagnostic identifying the intended failure.
        """
        if before:
            assert POLICY.count(before) == 1
            text = POLICY.replace(before, after, 1)
        else:
            text = POLICY + after
        (tmp_path / 'pyproject.toml').write_text(text, encoding='utf-8')
        snapshot = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_apple_release_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == snapshot

    def test_standalone_policy_uses_its_own_root_table(
        self: Self,
        tmp_path: Path,
    ) -> None:
        """
        Accept standard standalone configuration and an empty tag prefix.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer policy root independent of Python project metadata.
        """
        (tmp_path / 'popo.toml').write_text(
            POLICY.replace('tool.popo.', '') + 'tag-prefix=""\n',
            encoding='utf-8',
        )
        snapshot = snapshot_files(tmp_path)
        config = load_apple_release_config(tmp_path)
        assert config.configurations == ('Debug', 'Release')
        assert config.tag_prefix == ''
        assert config.product_type == 'com.apple.product-type.application'
        assert snapshot_files(tmp_path) == snapshot


# !SECTION
