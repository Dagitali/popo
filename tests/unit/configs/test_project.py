"""
:mod:`tests.unit.configs.test_project` module.

Test project configuration discovery and shared loader contracts.
"""

from pathlib import Path

import pytest

from popo.config import (
    AutomationConfig,
    ConfigurationError,
    DependencyConfig,
    DependencyMode,
    ProjectConfig,
    PythonPolicyConfig,
    load_automation_config,
    load_config,
)
from tests.support.files import FileWriter

# SECTION: TESTS


class TestConfiguration:
    """
    Cover layout defaults, explicit overrides, and invalid project metadata.

    Notes
    -----
    Load configuration from temporary repositories to exercise layout
    discovery, overrides, defaults, facade exports, and domain-specific error
    handling. No consumer policy files are created outside the test fixtures.
    """

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
        """
        Verify discovered dependency files and their comparison mode.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        metadata : str
            Expected repository-relative metadata file discovered for the
            layout.
        requirements : str
            Expected repository-relative requirements file discovered for the
            layout.
        mode : str
            Dependency comparison policy selected for the scenario.
        """
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
        """
        Verify an empty repository receives resolved portable policy defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        """
        config = load_config(tmp_path)
        assert config.root == tmp_path.resolve()
        assert config.dependencies.requirements == tmp_path / 'requirements/lowest.txt'
        assert config.python_policy.requires_python == '>=3.13'

    def test_explicit_overrides(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify consumer settings override discovered paths and derived Python
        defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        """
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

    def test_exported_models(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify configuration facade exports preserve the expected model types.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        """
        config = load_config(tmp_path)
        mode: DependencyMode = 'minimum-constraints'
        assert isinstance(config, ProjectConfig)
        assert isinstance(config.dependencies, DependencyConfig)
        assert isinstance(config.python_policy, PythonPolicyConfig)
        assert config.dependencies.mode == mode
        assert isinstance(load_automation_config(tmp_path), AutomationConfig)

    @pytest.mark.parametrize('metadata', ['[', '[project]\nrequires-python = 313'])
    def test_invalid_consumer_metadata_uses_policy_default(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        metadata: str,
    ) -> None:
        """
        Verify invalid selected metadata falls back to Python-policy defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        metadata : str
            Metadata text selected for the parsing or validation scenario.
        """
        write_file('infra/pyproject.toml', metadata)
        write_file('infra/requirements.txt', '')
        assert load_config(tmp_path).python_policy.requires_python == '>=3.13'

    @pytest.mark.parametrize(
        ('content', 'message'),
        [
            ('[', 'invalid TOML'),
            ('tool = 1', 'tool must be a TOML table'),
            ('[tool]\npopo = []', 'tool.popo must be a TOML table'),
        ],
    )
    def test_loaders_share_root_validation(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
        message: str,
    ) -> None:
        """
        Verify project and automation loaders reject malformed root settings alike.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        message : str
            Expected diagnostic substring; an empty string selects a successful
            case.
        """
        write_file('pyproject.toml', content)
        for loader in (load_config, load_automation_config):
            with pytest.raises(ConfigurationError, match=message):
                loader(tmp_path)

    def test_loaders_validate_only_their_domains(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify loader validation and unknown-key handling stay domain-specific.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        """
        write_file(
            'pyproject.toml',
            '[tool.popo.dependencies]\nmode = "invalid"\n'
            '[tool.popo.python-policy]\npython-version = 313\n'
            '[tool.popo.automation]\n',
        )
        assert load_automation_config(tmp_path).configured
        with pytest.raises(ConfigurationError, match='dependency mode'):
            load_config(tmp_path)
        write_file(
            'pyproject.toml',
            '[tool.popo.dependencies]\nunknown = true\n'
            '[tool.popo.python-policy]\nunknown = true\n'
            '[tool.popo.automation]\nunknown = true\n',
        )
        assert load_config(tmp_path).python_policy.python_version == '3.13'
        with pytest.raises(ConfigurationError, match='unknown tool.popo.automation'):
            load_automation_config(tmp_path)

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
        """
        Verify project loading reports the expected invalid-configuration error.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        message : str
            Expected diagnostic substring; an empty string selects a successful
            case.
        """
        write_file('pyproject.toml', content)
        with pytest.raises(ConfigurationError, match=message):
            load_config(tmp_path)

    def test_python_defaults_follow_dependency_metadata(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify default Python requirements and Ruff paths follow dependency
        metadata.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        """
        write_file(
            'pyproject.toml',
            '[tool.popo.dependencies]\nmetadata = "dependencies.toml"\n'
            '[tool.popo.python-policy]\nmetadata = "python.toml"\n',
        )
        write_file('dependencies.toml', '[project]\nrequires-python = ">=3.14"')
        write_file('python.toml', '[project]\nrequires-python = ">=3.13"')
        config = load_config(tmp_path)
        assert config.python_policy.metadata == tmp_path / 'python.toml'
        assert config.python_policy.ruff_config == tmp_path / 'dependencies.toml'
        assert config.python_policy.requires_python == '>=3.14'


# !SECTION
