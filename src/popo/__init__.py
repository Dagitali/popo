"""
:mod:`popo` package.

Public package for popo.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('popo')
except PackageNotFoundError:
    __version__ = '0.1.0'

# SECTION: PACKAGE API / EXPORTS


__all__ = ['__version__']


# !SECTION
