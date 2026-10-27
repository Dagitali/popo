"""
:mod:`popo.config.swift_boundaries` module.

Load consumer-owned Swift architectural layer policy.
"""

from pathlib import Path

from .source_boundaries import BoundaryConfig, load_boundaries_config

# SECTION: FUNCTIONS


def load_swift_boundaries_config(
    root: Path,
) -> BoundaryConfig:
    """
    Load validated Swift layers without inspecting consumer source.

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
    return load_boundaries_config(root, 'swift-boundaries')


# !SECTION
