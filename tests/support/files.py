"""
:mod:`tests.support.files` module.

Types and byte snapshots shared by temporary repository fixtures.
"""

from collections.abc import Callable
from pathlib import Path

# SECTION: TYPE ALIASES


type FileWriter = Callable[[str, str], Path]


# !SECTION


# SECTION: FUNCTIONS


def snapshot_files(
    root: Path,
) -> dict[Path, bytes]:
    """
    Read consumer fixture bytes for before/after comparisons.

    Parameters
    ----------
    root : pathlib.Path
        Trusted temporary consumer directory; inspect files recursively.

    Returns
    -------
    dict[pathlib.Path, bytes]
        Repository-relative file paths and their exact bytes. Each invocation
        rereads the files so additions, removals and content changes are
        visible.
        Empty directories and other filesystem metadata are not captured.

    Raises
    ------
    OSError
        If an existing file cannot be read.
    """
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob('*')
        if path.is_file()
    }


# !SECTION
