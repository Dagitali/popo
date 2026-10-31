"""
:mod:`tests.unit.config.test_u_automation` module.

Test validation of consumer automation configuration.
"""

import json
from collections.abc import Callable
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


@pytest.fixture(
    name='write_policy',
    params=('popo.toml', 'pyproject.toml'),
    ids=('standalone', 'pyproject'),
)
def write_policy_fixture(
    request: pytest.FixtureRequest,
    write_file: FileWriter,
) -> Callable[[str], Path]:
    """
    Write automation settings to each supported consumer policy source.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Standalone or embedded policy filename selected by pytest.
    write_file : FileWriter
        UTF-8 writer rooted in the isolated consumer directory.

    Returns
    -------
    collections.abc.Callable[[str], pathlib.Path]
        Writer accepting table contents and returning the policy path.
    """
    filename = str(request.param)
    header = 'automation' if filename == 'popo.toml' else 'tool.popo.automation'

    def write_policy(
        settings: str,
    ) -> Path:
        """
        Write one automation table with the selected source's header.

        Parameters
        ----------
        settings : str
            TOML entries belonging to the automation table.

        Returns
        -------
        pathlib.Path
            Created consumer policy file.
        """
        return write_file(filename, f'[{header}]\n{settings}')

    return write_policy


# !SECTION


# SECTION: TESTS


class TestAutomationConfiguration:
    """Validate consumer automation configuration settings."""

    def test_explicit_empty_arrays_override_defaults(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        automation_key: str,
    ) -> None:
        """
        Retain explicit empty arrays without replacing unrelated defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root containing the selected policy source.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        automation_key : str
            Explicit array setting whose empty value must be retained.
        """
        write_policy(f'{automation_key}=[]')
        before = snapshot_files(tmp_path)
        expected = replace(
            AutomationConfig(tmp_path),
            configured=True,
            **{automation_key.replace('-', '_'): ()},
        )
        assert load_automation_config(tmp_path) == expected
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'key',
        ('workflow-globs', 'action-globs', 'template-globs', 'yaml-globs'),
    )
    @pytest.mark.parametrize('absolute', (False, True), ids=('traversal', 'absolute'))
    def test_globs_stay_inside_repository(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        key: str,
        absolute: bool,
    ) -> None:
        """
        Reject traversal and native absolute paths for every discovery glob.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root used to form a native absolute path.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        key : str
            Discovery glob setting receiving an unsafe path.
        absolute : bool
            Whether to test an absolute path instead of parent traversal.
        """
        pattern = str(tmp_path / 'ci.yml') if absolute else '../ci.yml'
        write_policy(f'{key}={json.dumps([pattern])}')
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_automation_config(tmp_path)
        assert str(raised.value) == f'{key} must stay inside the repository'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        ('setting', 'message'),
        [
            ('unknown = []', 'unknown tool.popo.automation setting'),
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
        write_policy: Callable[[str], Path],
        setting: str,
        message: str,
    ) -> None:
        """
        Reject unsupported keys, repository aliases, and placeholder refs.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        setting : str
            Automation TOML setting selected to exercise invalid configuration.
        message : str
            Diagnostic identifying the invalid setting.
        """
        write_policy(setting)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_automation_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'value',
        (
            pytest.param('false', id='boolean'),
            pytest.param('0', id='integer'),
            pytest.param('""', id='empty-string'),
            pytest.param('"x"', id='nonempty-string'),
            pytest.param('{}', id='table'),
            pytest.param('[1]', id='nonstring-element'),
            pytest.param('[""]', id='empty-element'),
            pytest.param('[" "]', id='blank-element'),
        ),
    )
    def test_malformed_explicit_values_never_use_defaults(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        automation_key: str,
        value: str,
    ) -> None:
        """
        Reject malformed explicit arrays and values instead of using defaults.

        Falsey non-array settings must not silently select model defaults.
        Invalid array elements fail consistently for every supported key.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root containing one malformed explicit setting.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        automation_key : str
            Array setting receiving an invalid explicit value.
        value : str
            Valid TOML scalar, mapping or array with an invalid setting shape.
        """
        write_policy(f'{automation_key}={value}')
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
        write_policy: Callable[[str], Path],
    ) -> None:
        """
        Inherit model defaults without changing the explicit empty policy.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root containing an explicitly empty automation table.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        """
        write_policy('')
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
        write_policy: Callable[[str], Path],
        separator: str,
        trailing: bool,
    ) -> None:
        """
        Reject embedded and trailing whitespace in exact ref tokens.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        separator : str
            Separator spelling used by the scenario.
        trailing : bool
            Whether the input includes a trailing separator.
        """
        token = 'RELEASE' + separator + ('' if trailing else 'SHA')
        write_policy(
            'template-placeholder-refs=' + json.dumps([token]),
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_automation_config(tmp_path)
        assert str(raised.value) == 'template placeholders must be exact ref tokens'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('token', ['RELEASE_SHA', 'vNext-1.0', '_template_'])
    def test_placeholder_retains_literal_token(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        token: str,
    ) -> None:
        """
        Keep valid placeholder spelling unchanged across policy sources.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        token : str
            Literal token inserted into the scenario input.
        """
        write_policy(
            'template-placeholder-refs=' + json.dumps([token]),
        )
        before = snapshot_files(tmp_path)
        assert load_automation_config(tmp_path).template_placeholder_refs == (token,)
        assert snapshot_files(tmp_path) == before

    def test_repeated_patterns_remain_supported(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
    ) -> None:
        """
        Preserve automation's intentional duplicate-array compatibility.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_policy : collections.abc.Callable[[str], pathlib.Path]
            Writer for the selected standalone or embedded automation table.
        """
        write_policy(
            'workflow-globs=["ci.yml", "ci.yml"]',
        )
        before = snapshot_files(tmp_path)
        assert load_automation_config(tmp_path).workflow_globs == ('ci.yml', 'ci.yml')
        assert snapshot_files(tmp_path) == before


# !SECTION
