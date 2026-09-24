"""
:mod:`tests.support.files` module.

Types shared by temporary repository fixtures.
"""

from collections.abc import Callable
from pathlib import Path

# SECTION: TYPE ALIASES


type FileWriter = Callable[[str, str], Path]


# !SECTION
