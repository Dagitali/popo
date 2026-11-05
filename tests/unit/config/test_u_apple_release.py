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

# SECTION: TESTS


class TestAppleReleaseConfiguration:
    """Keep consumer selectors explicit and independently configurable."""

    @pytest.mark.parametrize(
        'change',
        (
            'missing',
            'unknown',
            'path',
            'target',
            'empty',
            'duplicate',
            'config-type',
            'prefix',
            'product',
        ),
    )
    def test_invalid_configuration_fails_before_input_reads(
        self: Self,
        tmp_path: Path,
        change: str,
    ) -> None:
        """
        Reject malformed selection, path and tag convention settings.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Policy root with no project files.
        change : str
            Independent policy mutation.
        """
        text = {
            'missing': '',
            'unknown': POLICY + 'unknown=true\n',
            'path': POLICY.replace('Example.xcodeproj/project.pbxproj', '../PRIVATE'),
            'target': POLICY.replace('target = "Example"', 'target = ""'),
            'empty': POLICY.replace('["Debug", "Release"]', '[]'),
            'duplicate': POLICY.replace('["Debug", "Release"]', '["Debug", "Debug"]'),
            'config-type': POLICY.replace('["Debug", "Release"]', 'true'),
            'prefix': POLICY + 'tag-prefix=" PRIVATE "\n',
            'product': POLICY + 'product-type=false\n',
        }[change]
        (tmp_path / 'pyproject.toml').write_text(text)
        with pytest.raises(ConfigurationError):
            load_apple_release_config(tmp_path)

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
        )
        config = load_apple_release_config(tmp_path)
        assert config.configurations == ('Debug', 'Release')
        assert config.tag_prefix == ''
        assert config.product_type == 'com.apple.product-type.application'


# !SECTION
