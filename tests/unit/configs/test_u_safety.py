# test_u_safety.py
# Validate opt-in safety configuration without credentials or network access.
"""Exercise safety configuration boundaries and explicit opt-in behavior."""

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

    @pytest.mark.parametrize('expiry', ['"2026-13-01"', '2026-10-08'])
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
        assert config.npm_pairs == (('package.json', 'package-lock.json'),)
        assert config.exceptions[0][:5] == (
            'ci.yml',
            'workflow_run',
            'team',
            'reviewed',
            'reviewer',
        )


# !SECTION
