"""
:mod:`tests.unit.config.test_u_automation` module.

Test validation of consumer automation configuration.
"""

import json
from pathlib import Path

import pytest

from popo.config import ConfigurationError, load_automation_config
from tests.support.files import FileWriter

# SECTION: TESTS


@pytest.mark.parametrize(
    ('filename', 'prefix'),
    [
        pytest.param('popo.toml', '[automation]\n', id='standalone'),
        pytest.param('pyproject.toml', '[tool.popo.automation]\n', id='pyproject'),
    ],
)
class TestAutomationConfiguration:
    """Validate consumer automation configuration settings."""

    @pytest.mark.parametrize(
        ('setting', 'message'),
        [
            ('unknown = []', 'unknown tool.popo.automation setting'),
            ('workflow-globs = "x"', 'workflow-globs must be an array'),
            ('action-globs = [1]', 'action-globs must be an array'),
            ('yaml-globs = ["../x"]', 'yaml-globs must stay inside'),
            ('template-globs = ["/absolute"]', 'template-globs must stay inside'),
            (
                'local-repositories = ["owner"]',
                'local-repositories must contain owner/repo',
            ),
            (
                'template-placeholder-refs = ["a/b"]',
                'template placeholders must be exact ref tokens',
            ),
        ],
    )
    def test_invalid_configuration(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
        setting: str,
        message: str,
    ) -> None:
        """
        Verify automation loading rejects unsupported keys, types, and unsafe
        patterns.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        setting : str
            Automation TOML setting selected to exercise invalid configuration.
        filename : str
            Standalone or Python metadata policy filename.
        prefix : str
            Table header appropriate to the selected policy source.
        message : str
            Diagnostic identifying the invalid setting.
        """
        write_file(filename, prefix + setting)
        with pytest.raises(ConfigurationError, match=message):
            load_automation_config(tmp_path)

    @pytest.mark.parametrize('separator', [' ', '\t', '\r', '\n', '\u00a0', '\u2028'])
    @pytest.mark.parametrize('trailing', [False, True])
    def test_placeholder_rejects_all_whitespace(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
        separator: str,
        trailing: bool,
    ) -> None:
        """Reject embedded and trailing whitespace in exact ref tokens."""
        token = 'RELEASE' + separator + ('' if trailing else 'SHA')
        write_file(
            filename,
            prefix + 'template-placeholder-refs=' + json.dumps([token]),
        )
        with pytest.raises(ConfigurationError, match='exact ref tokens'):
            load_automation_config(tmp_path)

    @pytest.mark.parametrize('token', ['RELEASE_SHA', 'vNext-1.0', '_template_'])
    def test_placeholder_retains_literal_token(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
        token: str,
    ) -> None:
        """Keep valid placeholder spelling unchanged across policy sources."""
        write_file(
            filename,
            prefix + 'template-placeholder-refs=' + json.dumps([token]),
        )
        assert load_automation_config(tmp_path).template_placeholder_refs == (token,)

    def test_repeated_patterns_remain_supported(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
    ) -> None:
        """Preserve automation's intentional duplicate-array compatibility."""
        write_file(
            filename,
            prefix + 'workflow-globs=["ci.yml", "ci.yml"]',
        )
        assert load_automation_config(tmp_path).workflow_globs == ('ci.yml', 'ci.yml')


# !SECTION
