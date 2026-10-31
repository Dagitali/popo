"""
:mod:`tests.unit.config.test_u_project` module.

Test project configuration discovery and shared loader contracts.
"""

from collections.abc import Callable
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
from popo.config.dependencies import parse_dependencies
from tests.support.files import FileWriter, snapshot_files

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
        'metadata,requirements,mode,uninspected',
        [
            (
                'pyproject.toml',
                'requirements/lowest.txt',
                'minimum-constraints',
                ('requirements.txt', 'infra/pyproject.toml', 'infra/requirements.txt'),
            ),
            (
                'pyproject.toml',
                'requirements.txt',
                'exact',
                ('infra/pyproject.toml', 'infra/requirements.txt'),
            ),
            (
                'infra/pyproject.toml',
                'infra/requirements.txt',
                'exact',
                ('requirements/lowest.txt', 'requirements.txt'),
            ),
        ],
        ids=('minimum-first', 'root-exact-before-infra', 'missing-root-metadata'),
    )
    def test_dependency_discovery_skips_unneeded_probes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        write_file: FileWriter,
        metadata: str,
        requirements: str,
        mode: DependencyMode,
        uninspected: tuple[str, ...],
    ) -> None:
        """
        Stop after a complete layout and skip companions of missing metadata.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing one complete dependency layout.
        monkeypatch : pytest.MonkeyPatch
            Restore the filesystem probe after the scenario.
        write_file : FileWriter
            Writer creating the selected metadata and requirements inputs.
        metadata : str
            Repository-relative metadata path of the selected layout.
        requirements : str
            Repository-relative requirements path of the selected layout.
        mode : DependencyMode
            Comparison mode established by that layout.
        uninspected : tuple[str, ...]
            Unneeded paths whose inspection would raise a private error.
        """
        write_file(metadata, 'intentionally not parsed during discovery')
        write_file(requirements, 'intentionally not parsed during discovery')
        before = snapshot_files(tmp_path)
        original = Path.is_file
        blocked = {tmp_path / name for name in uninspected}

        def is_file(
            path: Path,
        ) -> bool:
            """
            Reject unneeded probes while retaining real file-existence checks.

            Parameters
            ----------
            path : pathlib.Path
                Candidate path inspected by dependency discovery.

            Returns
            -------
            bool
                Original filesystem observation for a permitted path.

            Raises
            ------
            PermissionError
                If discovery inspects a path excluded by the scenario.
            """
            if path in blocked:
                raise PermissionError('PRIVATE UNNEEDED INPUT')
            return original(path)

        with monkeypatch.context() as patch:
            patch.setattr(Path, 'is_file', is_file)
            config = parse_dependencies(tmp_path, {})
        assert config == DependencyConfig(
            tmp_path / metadata,
            tmp_path / requirements,
            mode,
        )
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        ('metadata', 'requirements', 'mode', 'shadowed'),
        [
            ('infra/pyproject.toml', 'infra/requirements.txt', 'exact', ()),
            ('pyproject.toml', 'requirements.txt', 'exact', ()),
            ('pyproject.toml', 'requirements/lowest.txt', 'minimum-constraints', ()),
            (
                'pyproject.toml',
                'requirements.txt',
                'exact',
                ('infra/pyproject.toml', 'infra/requirements.txt'),
            ),
            (
                'pyproject.toml',
                'requirements/lowest.txt',
                'minimum-constraints',
                ('requirements.txt',),
            ),
            (
                'pyproject.toml',
                'requirements/lowest.txt',
                'minimum-constraints',
                ('infra/pyproject.toml', 'infra/requirements.txt'),
            ),
            (
                'pyproject.toml',
                'requirements/lowest.txt',
                'minimum-constraints',
                ('requirements.txt', 'infra/pyproject.toml', 'infra/requirements.txt'),
            ),
            (
                'infra/pyproject.toml',
                'infra/requirements.txt',
                'exact',
                ('pyproject.toml',),
            ),
        ],
    )
    def test_detects_layout(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        metadata: str,
        requirements: str,
        mode: str,
        shadowed: tuple[str, ...],
    ) -> None:
        """
        Verify discovered dependency files, precedence and comparison mode.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        metadata : str
            Expected repository-relative metadata file discovered for the
            layout.
        requirements : str
            Expected repository-relative requirements file discovered for the
            layout.
        mode : str
            Dependency comparison policy selected for the scenario.
        shadowed : tuple[str, ...]
            Lower-priority or incomplete candidate files that must not win.
        """
        write_file(metadata, '[project]\nrequires-python = ">=3.13"\ndependencies = []')
        write_file(requirements, '')
        for name in shadowed:
            write_file(
                name,
                '[project]\nrequires-python=">=3.14"\ndependencies=[]'
                if name.endswith('.toml')
                else '',
            )
        before = snapshot_files(tmp_path)
        config = load_config(tmp_path)
        assert config.dependencies.metadata == tmp_path / metadata
        assert config.dependencies.requirements == tmp_path / requirements
        assert config.dependencies.mode == mode
        assert config.python_policy.requires_python == '>=3.13'
        assert snapshot_files(tmp_path) == before

    def test_empty_repository_defaults(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify an empty repository receives resolved portable policy defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
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
        Verify explicit overrides.

        Verify consumer settings override discovered paths and derived Python
        defaults.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
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
            Temporary directory for isolated test inputs.
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
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        metadata : str
            Metadata text selected for the parsing or validation scenario.
        """
        write_file('infra/pyproject.toml', metadata)
        write_file('infra/requirements.txt', '')
        assert load_config(tmp_path).python_policy.requires_python == '>=3.13'

    @pytest.mark.parametrize(
        ('loader', 'content', 'message'),
        [
            *(
                pytest.param(loader, content, message, id=f'{domain}-{case}')
                for domain, loader in (
                    ('project', load_config),
                    ('automation', load_automation_config),
                )
                for case, content, message in (
                    ('invalid-toml', '[', 'invalid TOML'),
                    ('invalid-tool', 'tool = 1', 'tool must be a TOML table'),
                    (
                        'invalid-popo',
                        '[tool]\npopo = []',
                        'tool.popo must be a TOML table',
                    ),
                )
            ),
            *(
                pytest.param(load_config, content, message, id=case)
                for case, content, message in (
                    (
                        'dependency-table',
                        '[tool.popo]\ndependencies = []',
                        'tool.popo.dependencies must be a TOML table',
                    ),
                    (
                        'dependency-mode',
                        '[tool.popo.dependencies]\nmode = "unknown"',
                        'dependency mode must be',
                    ),
                    (
                        'empty-metadata',
                        '[tool.popo.dependencies]\nmetadata = ""',
                        'metadata must be a non-empty string',
                    ),
                    (
                        'python-version',
                        '[tool.popo.python-policy]\npython-version = 313',
                        'python-version must be',
                    ),
                    ('project-table', 'project = []', 'project must be a TOML table'),
                )
            ),
        ],
    )
    def test_loaders_reject_invalid_configuration(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        loader: Callable[[Path], ProjectConfig | AutomationConfig],
        content: str,
        message: str,
    ) -> None:
        """
        Reject shared root errors and project-specific policy errors.

        Both loaders reject malformed root settings. Dependency and Python
        policy failures apply only to the project loader; automation loading
        intentionally ignores those domains.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        loader : collections.abc.Callable
            Project or automation loader under test.
        content : str
            Invalid project configuration supplied to the loader.
        message : str
            Regular expression matching the expected configuration error.
        """
        write_file('pyproject.toml', content)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            loader(tmp_path)
        assert snapshot_files(tmp_path) == before

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
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
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

    def test_python_defaults_follow_dependency_metadata(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify python defaults follow dependency metadata.

        Verify default Python requirements and Ruff paths follow dependency
        metadata.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
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
