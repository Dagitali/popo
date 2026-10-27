"""
:mod:`popo.config.python_boundaries` module.

Load consumer-owned Python architectural layer policy.
"""

from pathlib import Path

from .source_boundaries import BoundaryConfig, load_boundaries_config

# SECTION: FUNCTIONS


def load_python_boundaries_config(
    root: Path,
) -> BoundaryConfig:
    """
    Load validated Python layers without inspecting consumer source.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository containing standalone or embedded policy.

    Returns
    -------
    BoundaryConfig
        Confined selections and validated layer references in policy order.

    Raises
    ------
    ConfigurationError
        Settings, identifiers, selections or layer references are invalid.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    return load_boundaries_config(root, 'python-boundaries')


# !SECTION
