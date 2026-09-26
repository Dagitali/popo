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
    """
    Store immutable dependency-boundary inputs without validating their contents.

    Attributes
    ----------
    metadata : pathlib.Path
        Project metadata containing the runtime dependency declarations.
    requirements : pathlib.Path
        Requirements or minimum-version constraints to compare with metadata.
    mode : {'minimum-constraints', 'exact'}
        Compare lower bounds with fixture pins, or normalized declarations.

    Notes
    -----
    ``load_config`` bases relative configured paths on the repository root.
    Direct construction performs no path resolution or runtime validation.
    """

    metadata: Path
    requirements: Path
    mode: DependencyMode


@dataclass(frozen=True, slots=True)
class PythonPolicyConfig:
    """
    Store immutable expected Python policy and its declaration locations.

    Attributes
    ----------
    metadata : pathlib.Path
        TOML file containing project.requires-python and mypy settings.
    requires_python : str
        Expected specifier text; also bounds runtime and workflow versions.
    python_version : str
        Exact expected content of the version file after stripping whitespace.
    python_version_file : pathlib.Path
        File declaring the preferred local interpreter version.
    ruff_config : pathlib.Path
        Metadata file with tool.ruff settings, or a separate Ruff TOML file
        with top-level settings.
    ruff_target_version : str
        Exact expected Ruff target, such as ``py313``.
    mypy_python_version : str
        Exact expected mypy Python-version setting.
    workflow_directory : pathlib.Path
        Directory searched recursively for YAML version declarations.

    Notes
    -----
    ``load_config`` bases relative configured paths on the repository root.
    Construction does not read files or validate versions and policy syntax.
    """

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
    """
    Group immutable consumer configuration for the policy validators.

    Attributes
    ----------
    root : pathlib.Path
        Consumer repository root, resolved to an absolute path by load_config.
    dependencies : DependencyConfig
        Dependency inputs and comparison mode.
    python_policy : PythonPolicyConfig
        Expected interpreter policy and associated input paths.

    Notes
    -----
    Direct construction does not resolve paths or validate the nested settings.
    """

    root: Path
    dependencies: DependencyConfig
    python_policy: PythonPolicyConfig


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _detect_dependencies(
    root: Path,
) -> DependencyConfig:
    """
    Select dependency inputs using the first existing metadata/requirements pair.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root against which candidate paths are joined.

    Returns
    -------
    DependencyConfig
        Prefer root pyproject.toml with requirements/lowest.txt in minimum mode,
        then root pyproject.toml with requirements.txt in exact mode, then the
        corresponding pyproject.toml and requirements.txt pair under infra/.
        If none exists, return the first layout without creating its files.

    Notes
    -----
    Detection checks file existence only, not contents or policy validity.
    """
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


def _string(
    table: dict[str, object],
    key: str,
    *,
    default: str,
) -> str:
    """
    Read a nonempty string, using the default only when the key is absent.

    Parameters
    ----------
    table : dict[str, object]
        Configuration table to inspect without mutation.
    key : str
        Setting name, also used in failure diagnostics.
    default : str
        Value to validate and return if the key is absent.

    Returns
    -------
    str
        Nonempty setting or default, without stripping whitespace.

    Raises
    ------
    ConfigurationError
        If the selected value is not a string or is empty.
    """
    value = table.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f'{key} must be a non-empty string')
    return value


def _table(
    value: object,
    *,
    name: str,
) -> dict[str, object]:
    """
    Require a configuration table without copying or validating its entries.

    Parameters
    ----------
    value : object
        Candidate TOML table.
    name : str
        Table name used to label failure diagnostics.

    Returns
    -------
    dict[str, object]
        The original dictionary, with its type narrowed for callers.

    Raises
    ------
    ConfigurationError
        If value is not a dictionary.
    """
    if not isinstance(value, dict):
        raise ConfigurationError(f'{name} must be a TOML table')
    return cast(dict[str, object], value)


# !SECTION


# SECTION: FUNCTIONS


def load_config(root: Path) -> ProjectConfig:
    """
    Load configuration for *root*, applying portable layout defaults.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository containing optional ``[tool.popo]`` configuration
        in ``pyproject.toml``. Relative configured paths are based on this root.

    Returns
    -------
    ProjectConfig
        Dependency and Python-policy settings with explicit overrides applied
        to detected layout defaults. Loading does not create missing inputs.

    Raises
    ------
    ConfigurationError
        If root metadata contains invalid TOML, a required table or string has
        an invalid type or value, or the dependency comparison mode is unsupported.
    OSError
        If an existing metadata file cannot be read.
    UnicodeError
        If metadata cannot be decoded as UTF-8.

    Notes
    -----
    Unknown configuration keys are ignored. Individual validators check the
    referenced files; successful loading alone does not establish policy validity.

    Missing root metadata behaves as empty configuration. Dependency-layout
    detection supplies defaults before explicit overrides are applied. The
    default requires-python text comes from the selected dependency metadata,
    falling back to ``>=3.13`` when absent or not a string. Invalid TOML in
    separately selected dependency metadata also falls back at this stage;
    invalid root TOML raises ConfigurationError instead.

    Preferred Python defaults to ``3.13``; mypy defaults to that preference
    and Ruff to ``py`` plus its digits. Version-file and workflow paths default
    to .python-version and .github/workflows under root. Python-policy metadata
    and Ruff configuration default to the selected dependency metadata.
    Overriding only Python-policy metadata does not rederive requires-python
    or the Ruff configuration path from that alternate file.
    """

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
