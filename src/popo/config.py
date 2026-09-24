"""
:mod:`popo.config` module.

Load popo configuration from project metadata.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

# SECTION: TYPE ALIASES


DependencyMode = Literal['minimum-constraints', 'exact']


# !SECTION


# SECTION: EXCEPTIONS


class ConfigurationError(ValueError):
    """Raised when popo configuration is invalid."""


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class DependencyConfig:
    """Dependency-boundary input paths and comparison mode."""

    metadata: Path
    requirements: Path
    mode: DependencyMode


@dataclass(frozen=True, slots=True)
class PythonPolicyConfig:
    """Expected Python policy and the files that declare it."""

    metadata: Path
    requires_python: str
    python_version: str
    python_version_file: Path
    ruff_config: Path
    ruff_target_version: str
    mypy_python_version: str
    workflow_directory: Path


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Complete popo configuration."""

    root: Path
    dependencies: DependencyConfig
    python_policy: PythonPolicyConfig


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _detect_dependencies(root: Path) -> DependencyConfig:
    candidates: tuple[tuple[str, str, DependencyMode], ...] = (
        ('pyproject.toml', 'requirements/lowest.txt', 'minimum-constraints'),
        ('pyproject.toml', 'requirements.txt', 'exact'),
        ('infra/pyproject.toml', 'infra/requirements.txt', 'exact'),
    )
    for metadata, requirements, mode in candidates:
        if (root / metadata).is_file() and (root / requirements).is_file():
            return DependencyConfig(root / metadata, root / requirements, mode)
    return DependencyConfig(
        root / 'pyproject.toml',
        root / 'requirements/lowest.txt',
        'minimum-constraints',
    )


def _string(table: dict[str, object], key: str, *, default: str) -> str:
    value = table.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f'{key} must be a non-empty string')
    return value


def _table(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigurationError(f'{name} must be a TOML table')
    return cast(dict[str, object], value)


# !SECTION


# SECTION: FUNCTIONS


def load_config(root: Path) -> ProjectConfig:
    """Load configuration for *root*, applying portable layout defaults."""

    root = root.resolve()
    root_metadata = root / 'pyproject.toml'
    document: dict[str, object] = {}
    if root_metadata.is_file():
        try:
            document = tomllib.loads(root_metadata.read_text(encoding='utf-8'))
        except tomllib.TOMLDecodeError as error:
            raise ConfigurationError(
                f'{root_metadata}: invalid TOML: {error}',
            ) from error

    tool = _table(document.get('tool', {}), name='tool')
    popo = _table(tool.get('popo', {}), name='tool.popo')

    detected = _detect_dependencies(root)
    dependency_table = _table(
        popo.get('dependencies', {}),
        name='tool.popo.dependencies',
    )
    mode_text = _string(dependency_table, 'mode', default=detected.mode)
    if mode_text not in {'minimum-constraints', 'exact'}:
        raise ConfigurationError(
            'dependency mode must be minimum-constraints or exact',
        )
    dependencies = DependencyConfig(
        metadata=root
        / _string(
            dependency_table,
            'metadata',
            default=str(detected.metadata.relative_to(root)),
        ),
        requirements=root
        / _string(
            dependency_table,
            'requirements',
            default=str(detected.requirements.relative_to(root)),
        ),
        mode=cast(DependencyMode, mode_text),
    )

    metadata_document: dict[str, object] = {}
    if dependencies.metadata.is_file():
        try:
            metadata_document = tomllib.loads(
                dependencies.metadata.read_text(encoding='utf-8'),
            )
        except tomllib.TOMLDecodeError:
            pass
    project = _table(metadata_document.get('project', {}), name='project')
    default_requires = project.get('requires-python', '>=3.13')
    if not isinstance(default_requires, str):
        default_requires = '>=3.13'

    python_table = _table(
        popo.get('python-policy', {}),
        name='tool.popo.python-policy',
    )
    python_version = _string(python_table, 'python-version', default='3.13')
    python_policy = PythonPolicyConfig(
        metadata=root
        / _string(
            python_table,
            'metadata',
            default=str(dependencies.metadata.relative_to(root)),
        ),
        requires_python=_string(
            python_table,
            'requires-python',
            default=default_requires,
        ),
        python_version=python_version,
        python_version_file=root
        / _string(python_table, 'python-version-file', default='.python-version'),
        ruff_config=root
        / _string(
            python_table,
            'ruff-config',
            default=str(dependencies.metadata.relative_to(root)),
        ),
        ruff_target_version=_string(
            python_table,
            'ruff-target-version',
            default=f'py{python_version.replace('.', '')}',
        ),
        mypy_python_version=_string(
            python_table,
            'mypy-python-version',
            default=python_version,
        ),
        workflow_directory=root
        / _string(
            python_table,
            'workflow-directory',
            default='.github/workflows',
        ),
    )
    return ProjectConfig(root, dependencies, python_policy)


# !SECTION
