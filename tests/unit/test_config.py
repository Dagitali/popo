"""
:mod:`tests.unit.test_config` module.

Test configuration discovery for infrastructure project layouts.
"""

from pathlib import Path

import pytest

from popo.config import ConfigurationError, load_config
from tests.support.files import FileWriter

# SECTION: TESTS


class TestConfiguration:
    """Cover layout defaults, explicit overrides, and invalid project metadata."""

    @pytest.mark.parametrize(
        ('metadata', 'requirements', 'mode'),
        [
            ('infra/pyproject.toml', 'infra/requirements.txt', 'exact'),
            ('pyproject.toml', 'requirements.txt', 'exact'),
            ('pyproject.toml', 'requirements/lowest.txt', 'minimum-constraints'),
        ],
    )
    def test_detects_layout(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        metadata: str,
        requirements: str,
        mode: str,
    ) -> None:
        write_file(metadata, '[project]\nrequires-python = ">=3.13"\ndependencies = []')
        write_file(requirements, '')
        config = load_config(tmp_path)
        assert config.dependencies.metadata == tmp_path / metadata
        assert config.dependencies.requirements == tmp_path / requirements
        assert config.dependencies.mode == mode

    def test_empty_repository_defaults(
        self,
        tmp_path: Path,
    ) -> None:
        config = load_config(tmp_path)
        assert config.root == tmp_path.resolve()
        assert config.dependencies.requirements == tmp_path / 'requirements/lowest.txt'
        assert config.python_policy.requires_python == '>=3.13'

    def test_explicit_overrides(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        write_file(
            'pyproject.toml',
            '[tool.popo.dependencies]\n'
            'metadata = "custom.toml"\nrequirements = "pins.txt"\nmode = "exact"\n'
            '[tool.popo.python-policy]\npython-version = "3.14"\n'
            'ruff-config = "ruff.toml"\nworkflow-directory = "automation"',
        )
        config = load_config(tmp_path)
        assert config.dependencies.metadata == tmp_path / 'custom.toml'
        assert config.dependencies.requirements == tmp_path / 'pins.txt'
        assert config.python_policy.ruff_target_version == 'py314'
        assert config.python_policy.mypy_python_version == '3.14'
        assert config.python_policy.ruff_config == tmp_path / 'ruff.toml'
        assert config.python_policy.workflow_directory == tmp_path / 'automation'

    @pytest.mark.parametrize('metadata', ['[', '[project]\nrequires-python = 313'])
    def test_invalid_consumer_metadata_uses_policy_default(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        metadata: str,
    ) -> None:
        write_file('infra/pyproject.toml', metadata)
        write_file('infra/requirements.txt', '')
        assert load_config(tmp_path).python_policy.requires_python == '>=3.13'

    @pytest.mark.parametrize(
        ('content', 'message'),
        [
            ('[', 'invalid TOML'),
            ('tool = 1', 'tool must be a TOML table'),
            ('[tool]\npopo = []', 'tool.popo must be a TOML table'),
            (
                '[tool.popo]\ndependencies = []',
                'tool.popo.dependencies must be a TOML table',
            ),
            ('[tool.popo.dependencies]\nmode = "unknown"', 'dependency mode must be'),
            (
                '[tool.popo.dependencies]\nmetadata = ""',
                'metadata must be a non-empty string',
            ),
            (
                '[tool.popo.python-policy]\npython-version = 313',
                'python-version must be',
            ),
            ('project = []', 'project must be a TOML table'),
        ],
    )
    def test_rejects_invalid_configuration(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
        message: str,
    ) -> None:
        write_file('pyproject.toml', content)
        with pytest.raises(ConfigurationError, match=message):
            load_config(tmp_path)


# !SECTION
