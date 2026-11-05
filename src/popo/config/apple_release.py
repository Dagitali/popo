"""
:mod:`popo.config.apple_release` module.

Load consumer-owned Apple release selectors without choosing a release version.
"""

from dataclasses import dataclass
from pathlib import Path

from ._common import (
    ConfigurationError,
    read_literal_path,
    read_popo,
    read_string,
    read_strings,
    require_table,
)

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class AppleReleaseConfig:
    """
    Store one exact native target release selection.

    Attributes
    ----------
    project : str
        Literal root-confined POSIX project filename.
    target : str
        Exact native target name.
    configurations : tuple[str, ...]
        Required complete configuration-name set in selection order.
    product_type : str
        Required native product type; defaults to application in the loader.
    tag_prefix : str
        Literal prefix for an explicitly supplied release tag.
    """

    project: str
    target: str
    configurations: tuple[str, ...]
    product_type: str
    tag_prefix: str


# !SECTION


# SECTION: FUNCTIONS


def load_apple_release_config(
    root: Path,
) -> AppleReleaseConfig:
    """
    Load strict release policy without reading native project metadata.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository containing standalone or embedded policy.

    Returns
    -------
    AppleReleaseConfig
        Exact selectors and tag convention; no version/build duplication.

    Raises
    ------
    ConfigurationError
        Required fields are missing, empty, unsafe or unsupported.
    OSError, UnicodeError
        The consumer policy cannot be read or decoded.
    """
    table = require_table(read_popo(root).get('apple-release'), name='apple-release')
    if table.keys() - {
        'project',
        'target',
        'configurations',
        'product-type',
        'tag-prefix',
    }:
        raise ConfigurationError('apple-release: unknown setting')
    project = read_literal_path(table.get('project'), 'apple-release.project')
    target = read_string(table, 'target', default='')
    configurations = read_strings(
        table.get('configurations'),
        'apple-release.configurations',
    )
    if not configurations:
        raise ConfigurationError('apple-release: requires configurations')
    product_type = read_string(
        table,
        'product-type',
        default='com.apple.product-type.application',
    )
    prefix = table.get('tag-prefix', 'v')
    if not isinstance(prefix, str) or any(
        char.isspace() or ord(char) < 32 for char in prefix
    ):
        raise ConfigurationError('apple-release: invalid tag-prefix')
    return AppleReleaseConfig(project, target, configurations, product_type, prefix)


# !SECTION
