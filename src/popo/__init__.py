"""
:mod:`popo` package.

Public package for Popo's read-only repository-policy CLI.

The package root intentionally exports only :data:`popo.__version__`; command
dispatch and check implementations live in their respective submodules. Version
lookup uses installed distribution metadata. When that metadata is unavailable,
the literal ``0.1.0`` fallback supports source-tree imports; it is not evidence
of a release tag or a substitute for the Git-derived version used when building
distributions.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('popo')
except PackageNotFoundError:
    __version__ = '0.1.0'

# SECTION: EXPORTS / PACKAGE API


__all__ = ['__version__']


# !SECTION
