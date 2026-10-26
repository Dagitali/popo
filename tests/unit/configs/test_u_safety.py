# test_u_safety.py
# Validate opt-in safety configuration without credentials or network access.
"""
:mod:`tests.unit.configs.test_u_safety` module.

Exercise safety configuration boundaries and explicit opt-in behavior.
"""

from datetime import date
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.safety import load_safety_config
from tests.support.files import FileWriter

# SECTION: TESTS


class TestSafetyConfiguration:
    """Reject malformed policy rather than silently weakening validation."""

    def test_absent_policy(
        self,
        tmp_path: Path,
    ) -> None:
        """Leave aggregate checks unchanged without consumer opt-in."""
        config = load_safety_config(tmp_path)
        assert not config.configured
        assert config.workflows == config.npm_pairs == ()

    def test_duplicate_exception_scope(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Reject ambiguous approvals for the same workflow and event."""
        entry = (
            '[[tool.popo.safety.exceptions]]\nworkflow="ci.yml"\n'
            'trigger="workflow_run"\nowner="team"\nreason="review"\n'
            'approved-by="owner"\nexpires="2026-10-08"\n'
        )
        write_file('pyproject.toml', entry * 2)
        with pytest.raises(ConfigurationError, match='duplicate'):
            load_safety_config(tmp_path)

    @pytest.mark.parametrize(
        'expiry',
        ['"2026-13-01"', '2026-10-08', '"20261008"', '"2026-W41-4"'],
    )
    def test_exception_date(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        expiry: str,
    ) -> None:
        """Require a quoted, valid date for reviewed exceptions."""
        write_file(
            'pyproject.toml',
            '[tool.popo.safety]\n[[tool.popo.safety.exceptions]]\n'
            'workflow="ci.yml"\ntrigger="workflow_run"\nowner="team"\n'
            f'reason="reviewed"\napproved-by="reviewer"\nexpires={expiry}',
        )
        with pytest.raises(ConfigurationError):
            load_safety_config(tmp_path)

    @pytest.mark.parametrize(
        ('workflow', 'trigger'),
        [('*.yml', 'workflow_run'), ('ci.yml', 'push')],
    )
    def test_exception_scope(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        workflow: str,
        trigger: str,
    ) -> None:
        """Require an exact workflow path and a privileged trigger."""
        write_file(
            'pyproject.toml',
            (
                '[[tool.popo.safety.exceptions]]\n'
                f'workflow="{workflow}"\ntrigger="{trigger}"\n'
                'owner="team"\nreason="review"\napproved-by="owner"\nexpires="2026-10-08"'
            ),
        )
        with pytest.raises(ConfigurationError):
            load_safety_config(tmp_path)

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
        """Fail explicitly for unsupported or unsafe configuration."""
        write_file('pyproject.toml', '[tool.popo.safety]\n' + content)
        with pytest.raises(ConfigurationError, match=message):
            load_safety_config(tmp_path)

    def test_valid_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Load exact reviewed scopes and configured manifest pairs."""
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
