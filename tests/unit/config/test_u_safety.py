# test_u_safety.py
# Validate opt-in safety configuration without credentials or network access.
"""
:mod:`tests.unit.config.test_u_safety` module.

Exercise safety configuration boundaries and explicit opt-in behavior.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.safety import SafetyConfig, SafetyException, load_safety_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestSafetyConfiguration:
    """Reject malformed policy rather than silently weakening validation."""

    def test_absent_policy(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Leave aggregate checks unchanged without consumer opt-in.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        assert load_safety_config(tmp_path) == SafetyConfig(tmp_path.resolve())
        assert snapshot_files(tmp_path) == {}

    def test_duplicate_exception_scope(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Reject ambiguous approvals for the same workflow and event.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        """
        entry = (
            '[[tool.popo.safety.exceptions]]\nworkflow="ci.yml"\n'
            'trigger="workflow_run"\nowner="team"\nreason="review"\n'
            'approved-by="owner"\nexpires="2026-10-08"\n'
        )
        write_file('pyproject.toml', entry * 2)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_safety_config(tmp_path)
        assert str(raised.value) == 'duplicate safety exception scope'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('field', ('workflow-globs', 'npm-pairs', 'exceptions'))
    @pytest.mark.parametrize(
        'value',
        (
            pytest.param('false', id='boolean'),
            pytest.param('0', id='integer'),
            pytest.param('""', id='empty-string'),
            pytest.param('"x"', id='nonempty-string'),
            pytest.param('{}', id='table'),
        ),
    )
    def test_invalid_array_settings(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        field: str,
        value: str,
    ) -> None:
        """
        Reject nonarrays for every safety setting, including falsey values.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing the malformed policy.
        write_file : FileWriter
            UTF-8 writer creating the consumer policy.
        field : str
            Array setting receiving a scalar or mapping.
        value : str
            TOML spelling of a value that must not become an empty default.
        """
        write_file('pyproject.toml', f'[tool.popo.safety]\n{field}={value}')
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_safety_config(tmp_path)
        assert str(raised.value) == 'safety settings must be arrays'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'field,value,message',
        [
            *(
                ('expires', expiry, 'exception expires must be a quoted ISO date')
                for expiry in ('"2026-13-01"', '"20261008"', '"2026-W41-4"')
            ),
            ('expires', '2026-10-08', 'exception details must be nonempty strings'),
            ('workflow', '"*.yml"', 'exception workflow must be an exact path'),
            ('trigger', '"push"', 'exception trigger must be privileged'),
        ],
    )
    def test_invalid_exception_fields(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        field: str,
        value: str,
        message: str,
    ) -> None:
        """
        Require a quoted valid date, exact workflow and privileged trigger.

        Reviewed exceptions retain explicit scope and approval details; an
        invalid field must fail for its intended reason without file changes.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        field : str
            Configuration or report field selected for mutation.
        value : str
            Unvalidated value supplied to the operation.
        message : str
            Expected error message or scenario diagnostic.
        """
        fields = {
            'workflow': '"ci.yml"',
            'trigger': '"workflow_run"',
            'owner': '"team"',
            'reason': '"reviewed"',
            'approved-by': '"reviewer"',
            'expires': '"2026-10-08"',
        } | {field: value}
        write_file(
            'pyproject.toml',
            '[[tool.popo.safety.exceptions]]\n'
            + '\n'.join(f'{key}={entry}' for key, entry in fields.items()),
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_safety_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'content,message',
        [
            ('unknown = true', 'unknown tool.popo.safety setting'),
            (
                'npm-pairs = [{manifest = "x"}]',
                'npm-pairs requires manifest and lockfile',
            ),
            ('exceptions = [{}]', 'safety exception requires exact scope and approval'),
        ],
    )
    def test_invalid_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
        message: str,
    ) -> None:
        """
        Fail explicitly for unsupported or unsafe configuration.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        content : str
            Text written to the scenario input.
        message : str
            Expected error message or scenario diagnostic.
        """
        write_file('pyproject.toml', '[tool.popo.safety]\n' + content)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_safety_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'setting',
        (
            pytest.param('workflow-globs=[PATH]', id='workflow'),
            pytest.param(
                'npm-pairs=[{manifest=PATH,lockfile="package-lock.json"}]',
                id='manifest',
            ),
            pytest.param(
                'npm-pairs=[{manifest="package.json",lockfile=PATH}]',
                id='lockfile',
            ),
        ),
    )
    @pytest.mark.parametrize(
        'path',
        (None, '../ci.yml', ''),
        ids=('absolute', 'traversal', 'empty'),
    )
    def test_paths_stay_inside_repository(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        setting: str,
        path: str | None,
    ) -> None:
        """
        Reject absolute, traversing and empty workflow or npm pair paths.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Consumer root used to construct a platform-native absolute path.
        write_file : FileWriter
            UTF-8 writer creating the consumer policy.
        setting : str
            TOML template with one unsafe path marker and valid companions.
        path : str | None
            Invalid relative path, or None to construct a native absolute path.
        """
        pattern = str(tmp_path / 'ci.yml') if path is None else path
        settings = setting.replace('PATH', json.dumps(pattern))
        write_file('pyproject.toml', '[tool.popo.safety]\n' + settings)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_safety_config(tmp_path)
        assert str(raised.value) == 'safety paths must stay inside the repository'
        assert snapshot_files(tmp_path) == before

    def test_valid_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Load exact reviewed scopes and configured manifest pairs.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        """
        write_file(
            'pyproject.toml',
            '[tool.popo.safety]\nworkflow-globs=["ci.yml"]\n'
            'npm-pairs=[{manifest="package.json",lockfile="package-lock.json"}]\n'
            '[[tool.popo.safety.exceptions]]\nworkflow="ci.yml"\n'
            'trigger="workflow_run"\nowner="team"\nreason="reviewed"\n'
            'approved-by="reviewer"\nexpires="2026-10-08"',
        )
        before = snapshot_files(tmp_path)
        assert load_safety_config(tmp_path) == SafetyConfig(
            root=tmp_path.resolve(),
            workflows=('ci.yml',),
            exceptions=(
                SafetyException(
                    workflow='ci.yml',
                    trigger='workflow_run',
                    owner='team',
                    reason='reviewed',
                    approver='reviewer',
                    expires=date(2026, 10, 8),
                ),
            ),
            npm_pairs=(('package.json', 'package-lock.json'),),
            configured=True,
        )
        assert snapshot_files(tmp_path) == before


# !SECTION
