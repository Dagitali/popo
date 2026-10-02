"""
:mod:`tests.unit.conftest` module.

Fixtures used by multiple unit test modules.
"""

import errno
from collections.abc import Callable
from pathlib import Path

import pytest

# SECTION: FIXTURES


@pytest.fixture(name='symlink')
def symlink_fixture() -> Callable[[Path, Path], None]:
    """
    Provide a symlink creator that skips unsupported platform operations.

    Returns
    -------
    collections.abc.Callable[[pathlib.Path, pathlib.Path], None]
        Create the first path as a link to the second, preserving directory
        targets on Windows. Parent directories must already exist.

    Notes
    -----
    The callable skips only unavailable symlink operations and permission
    restrictions. Other :exc:`OSError` failures propagate rather than masking
    broken fixture setup. The fixture itself does not create links.
    """

    def create(
        link: Path,
        target: Path,
    ) -> None:
        """
        Link fixture paths or skip when platform capabilities prevent it.

        Parameters
        ----------
        link : pathlib.Path
            New symlink location with an existing parent directory.
        target : pathlib.Path
            Existing file or directory to reference.

        Raises
        ------
        OSError
            If creation fails for reasons other than platform restrictions.
        """
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except NotImplementedError:
            pytest.skip('Symlinks are unavailable on this platform')
        except OSError as error:
            if error.errno not in {
                errno.EPERM,
                errno.EACCES,
                errno.ENOSYS,
                errno.ENOTSUP,
            }:
                raise
            pytest.skip(f'Symlinks are unavailable: {error}')

    return create


# !SECTION
