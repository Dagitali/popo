"""
:mod:`tests.unit.config.test_u_automation` module.

Test validation of consumer automation configuration.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from popo.config import AutomationConfig, ConfigurationError, load_automation_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(
    name='automation_key',
    params=(
        'workflow-globs',
        'action-globs',
        'template-globs',
        'yaml-globs',
        'local-repositories',
        'template-placeholder-refs',
    ),
)
def automation_key_fixture(
    request: pytest.FixtureRequest,
) -> str:
    """
    Select an automation array setting for independent validation scenarios.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Setting name selected from the supported automation array fields.

    Returns
    -------
    str
        Consumer-facing key shared by default and malformed-value scenarios.
    """
    return str(request.param)


# !SECTION


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

    def test_explicit_empty_arrays_override_defaults(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
        automation_key: str,
    ) -> None:
        """
        Retain explicit empty arrays without replacing unrelated defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root containing the selected policy source.
        write_file : FileWriter
            Writer creating isolated consumer configuration.
        filename : str
            Standalone or Python project metadata filename.
        prefix : str
            Automation table header for the selected source.
        automation_key : str
            Explicit array setting whose empty value must be retained.
        """
        write_file(filename, prefix + f'{automation_key}=[]')
        before = snapshot_files(tmp_path)
        expected = replace(
            AutomationConfig(tmp_path),
            configured=True,
            **{automation_key.replace('-', '_'): ()},
        )
        assert load_automation_config(tmp_path) == expected
        assert snapshot_files(tmp_path) == before

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
        Verify invalid configuration.

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

    @pytest.mark.parametrize('value', ('false', '0', '""', '{}'))
    def test_malformed_explicit_values_never_use_defaults(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
        automation_key: str,
        value: str,
    ) -> None:
        """
        Reject falsey non-array values instead of silently using defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root containing one malformed explicit setting.
        write_file : FileWriter
            Writer creating the selected standalone or embedded policy.
        filename : str
            Consumer policy filename supplied by the class parameters.
        prefix : str
            Table header appropriate to the selected configuration source.
        automation_key : str
            Array setting whose explicit type is invalid.
        value : str
            Valid TOML scalar or mapping with an invalid setting type.
        """
        write_file(filename, prefix + f'{automation_key}={value}')
        before = snapshot_files(tmp_path)
        with pytest.raises(
            ConfigurationError,
            match=f'^{automation_key} must be an array of nonempty strings$',
        ):
            load_automation_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    def test_omitted_arrays_preserve_model_defaults(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        prefix: str,
    ) -> None:
        """
        Inherit the declared model defaults without creating consumer inputs.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root containing an explicitly empty automation table.
        write_file : FileWriter
            Writer creating only the selected consumer configuration.
        filename : str
            Standalone or project metadata policy filename.
        prefix : str
            Empty automation table header for the selected policy source.
        """
        write_file(filename, prefix)
        before = snapshot_files(tmp_path)
        assert load_automation_config(tmp_path) == AutomationConfig(
            tmp_path,
            configured=True,
        )
        assert snapshot_files(tmp_path) == before

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
        """
        Reject embedded and trailing whitespace in exact ref tokens.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        filename : str
            Input filename used in the scenario.
        prefix : str
            Prefix inserted into the source or configuration input.
        separator : str
            Separator spelling used by the scenario.
        trailing : bool
            Whether the input includes a trailing separator.
        """
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
        """
        Keep valid placeholder spelling unchanged across policy sources.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        filename : str
            Input filename used in the scenario.
        prefix : str
            Prefix inserted into the source or configuration input.
        token : str
            Literal token inserted into the scenario input.
        """
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
        """
        Preserve automation's intentional duplicate-array compatibility.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        filename : str
            Input filename used in the scenario.
        prefix : str
            Prefix inserted into the source or configuration input.
        """
        write_file(
            filename,
            prefix + 'workflow-globs=["ci.yml", "ci.yml"]',
        )
        assert load_automation_config(tmp_path).workflow_globs == ('ci.yml', 'ci.yml')


# !SECTION
