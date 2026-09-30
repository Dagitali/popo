"""
:mod:`popo.config.dependencies` module.

Dependency settings, layout detection, and configuration parsing.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from ._common import ConfigurationError, read_string, require_table

# SECTION: TYPE ALIASES


DependencyMode = Literal['minimum-constraints', 'exact']


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


# !SECTION


# SECTION: FUNCTIONS


def parse_dependencies(root: Path, popo: dict[str, object]) -> DependencyConfig:
    """
    Apply dependency overrides to detected repository defaults.

    Parameters
    ----------
    root : pathlib.Path
        Repository root used for layout detection and relative paths.
    popo : dict[str, object]
        Parsed tool.popo settings.

    Returns
    -------
    DependencyConfig
        Detected dependency inputs with explicit overrides applied.

    Raises
    ------
    ConfigurationError
        If the dependency table, strings, or comparison mode are invalid.
    """
    detected = _detect_dependencies(root)
    dependency_table = require_table(
        popo.get('dependencies', {}),
        name='tool.popo.dependencies',
    )
    mode_text = read_string(dependency_table, 'mode', default=detected.mode)
    if mode_text not in {'minimum-constraints', 'exact'}:
        raise ConfigurationError(
            'dependency mode must be minimum-constraints or exact',
        )
    return DependencyConfig(
        metadata=root
        / read_string(
            dependency_table,
            'metadata',
            default=str(detected.metadata.relative_to(root)),
        ),
        requirements=root
        / read_string(
            dependency_table,
            'requirements',
            default=str(detected.requirements.relative_to(root)),
        ),
        mode=cast(DependencyMode, mode_text),
    )


# !SECTION
