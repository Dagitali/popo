"""
:mod:`popo.config.project` module.

Aggregate dependency and Python-policy configuration for a repository.
"""

from dataclasses import dataclass
from pathlib import Path

from ._common import read_popo
from .dependencies import DependencyConfig, parse_dependencies
from .python_policy import PythonPolicyConfig, parse_python_policy

# SECTION: DATA CLASSES


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
    popo = read_popo(root)
    dependencies = parse_dependencies(root, popo)
    python_policy = parse_python_policy(root, popo, dependencies)
    return ProjectConfig(root, dependencies, python_policy)


# !SECTION
