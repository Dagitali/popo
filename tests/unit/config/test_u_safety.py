# test_u_safety.py
# Validate opt-in safety configuration without credentials or network access.
"""
:mod:`tests.unit.config.test_u_safety` module.

Exercise safety configuration boundaries and explicit opt-in behavior.
"""

from datetime import date
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config._common import parse_iso_date
from popo.config.safety import load_safety_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestCanonicalDates:
    """Keep shared date syntax strict without imposing expiry policy."""

    @pytest.mark.parametrize(
        'text,expected',
        (
            ('2024-02-29', date(2024, 2, 29)),
            ('2000-02-29', date(2000, 2, 29)),
            ('2026-10-28', date(2026, 10, 28)),
            ('1900-02-29', None),
            ('2026-02-29', None),
            ('20240229', None),
            ('2024-W09-4', None),
            (' 2024-02-29', None),
            ('2024-2-29', None),
            ('2024-02-29T00:00:00', None),
        ),
    )
    def test_calendar_and_canonical_format(
        self,
        text: str,
        expected: date | None,
    ) -> None:
        """
        Accept valid leap dates and reject alternate or impossible dates.

        Parameters
        ----------
        text : str
            Text or subprocess text-mode flag supplied to the operation.
        expected : date | None
            Expected result for the selected parameterized scenario.
        """
        if expected is None:
            with pytest.raises(ValueError):
                parse_iso_date(text)
        else:
            assert parse_iso_date(text) == expected


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
        config = load_safety_config(tmp_path)
        assert not config.configured
        assert config.workflows == config.npm_pairs == ()

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
        with pytest.raises(ConfigurationError, match='duplicate'):
            load_safety_config(tmp_path)

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
        with pytest.raises(ConfigurationError, match=f'^{message}$'):
            load_safety_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'content,message',
        [
            ('unknown = true', 'unknown'),
            ('workflow-globs = "x"', 'arrays'),
            ('workflow-globs = ["../x"]', 'inside'),
            ('workflow-globs = ["/x"]', 'inside'),
            ('npm-pairs = [{manifest = "x"}]', 'manifest and lockfile'),
            ('exceptions = [{}]', 'exact scope'),
            ('npm-pairs = [{manifest = "", lockfile = "x"}]', 'inside'),
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
        with pytest.raises(ConfigurationError, match=message):
            load_safety_config(tmp_path)

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
        config = load_safety_config(tmp_path)
        assert config.configured
        assert config.exceptions[0].expires == date(2026, 10, 8)
        assert config.exceptions[0].approver == 'reviewer'
        assert config.npm_pairs == (('package.json', 'package-lock.json'),)
        assert config.exceptions[0][:5] == (
            'ci.yml',
            'workflow_run',
            'team',
            'reviewed',
            'reviewer',
        )


# !SECTION
