"""
:mod:`popo.config.python_policy` module.

Python-policy settings and defaults derived from dependency metadata.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from ._common import ConfigurationError, read_popo, read_string, require_table
from .dependencies import DependencyConfig, parse_dependencies

# SECTION: DATA CLASSES


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
    workflow_parser : {'text', 'scoped'}
        Legacy text resolution by default, or strict scoped YAML observations.
        Scoped mode requires selected version inputs in each workflow file.

    Notes
    -----
    Both the independent loader and :func:`~popo.config.load_config` base
    relative configured paths on the repository root. Direct construction does
    not read files or validate settings or version syntax.
    """

    metadata: Path
    requires_python: str
    python_version: str
    python_version_file: Path
    ruff_config: Path
    ruff_target_version: str
    mypy_python_version: str
    workflow_directory: Path
    workflow_parser: Literal['text', 'scoped'] = 'text'


# !SECTION


# SECTION: FUNCTIONS


def load_python_policy_config(
    root: Path,
) -> PythonPolicyConfig:
    """
    Load Python policy through its own entry point with legacy defaults.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root with standalone or embedded configuration.

    Returns
    -------
    PythonPolicyConfig
        The same settings/defaults as the aggregate project loader. Dependency
        layout still supplies Python metadata defaults for compatibility.

    Raises
    ------
    ConfigurationError
        Invalid selected configuration, dependency defaults or Python policy.
    OSError, UnicodeError
        Configuration/default metadata cannot be read or decoded.
    ValueError
        Selected dependency metadata cannot be expressed relative to root.
    """
    root = root.resolve()
    settings = read_popo(root)
    return parse_python_policy(root, settings, parse_dependencies(root, settings))


def parse_python_policy(
    root: Path,
    popo: dict[str, object],
    dependencies: DependencyConfig,
) -> PythonPolicyConfig:
    """
    Derive Python defaults from selected metadata, then apply overrides.

    Parameters
    ----------
    root : pathlib.Path
        Repository root used to resolve configured relative paths.
    popo : dict[str, object]
        Parsed Popo settings from the selected policy source.
    dependencies : DependencyConfig
        Selected metadata supplying default Python requirements and paths.

    Returns
    -------
    PythonPolicyConfig
        Python-policy settings with explicit overrides applied.

    Raises
    ------
    ConfigurationError
        If project or policy tables, or configured strings, are invalid.
    OSError, UnicodeError
        If existing dependency metadata cannot be read or decoded as UTF-8.
    ValueError
        Selected dependency metadata cannot be expressed relative to root.

    Notes
    -----
    Invalid TOML in dependency metadata is caught and uses default
    requirements.
    """
    metadata_document: dict[str, object] = {}
    if dependencies.metadata.is_file():
        try:
            metadata_document = tomllib.loads(
                dependencies.metadata.read_text(encoding='utf-8'),
            )
        except tomllib.TOMLDecodeError:
            pass
    project = require_table(metadata_document.get('project', {}), name='project')
    default_requires = project.get('requires-python', '>=3.13')
    if not isinstance(default_requires, str):
        default_requires = '>=3.13'

    python_table = require_table(
        popo.get('python-policy', {}),
        name='tool.popo.python-policy',
    )
    python_version = read_string(python_table, 'python-version', default='3.13')
    workflow_parser = read_string(python_table, 'workflow-parser', default='text')
    if workflow_parser not in {'text', 'scoped'}:
        raise ConfigurationError('workflow-parser must be text or scoped')
    return PythonPolicyConfig(
        metadata=root
        / read_string(
            python_table,
            'metadata',
            default=str(dependencies.metadata.relative_to(root)),
        ),
        requires_python=read_string(
            python_table,
            'requires-python',
            default=default_requires,
        ),
        python_version=python_version,
        python_version_file=root
        / read_string(python_table, 'python-version-file', default='.python-version'),
        ruff_config=root
        / read_string(
            python_table,
            'ruff-config',
            default=str(dependencies.metadata.relative_to(root)),
        ),
        ruff_target_version=read_string(
            python_table,
            'ruff-target-version',
            default=f'py{python_version.replace('.', '')}',
        ),
        mypy_python_version=read_string(
            python_table,
            'mypy-python-version',
            default=python_version,
        ),
        workflow_directory=root
        / read_string(
            python_table,
            'workflow-directory',
            default='.github/workflows',
        ),
        workflow_parser=cast(Literal['text', 'scoped'], workflow_parser),
    )


# !SECTION
