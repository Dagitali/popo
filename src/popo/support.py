"""
:mod:`popo.support` module.

Shared support for popo commands.
"""

import re
from collections.abc import Sequence
from pathlib import Path

# SECTION: CONSTANTS


RELEASE_PATTERN = re.compile(
    r'^v?(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$',
)


# !SECTION


# SECTION: FUNCTIONS


def automation_paths(
    directory: Path,
    /,
) -> list[Path]:
    """
    Return sorted YAML automation files below *directory*.

    Parameters
    ----------
    directory : pathlib.Path
        Directory tree containing workflow or action files.

    Returns
    -------
    list[pathlib.Path]
        Recursively sorted ``.yml`` and ``.yaml`` paths, or an empty list
        when the input is not a directory.

    Notes
    -----
    Discover matching paths without reading or parsing YAML, checking that
    matches are regular files, or restricting them to recognized workflows.
    Hidden and generated directories are not explicitly excluded. Glob case
    sensitivity follows the host filesystem's rules.
    """

    if not directory.is_dir():
        return []
    return sorted((*directory.rglob('*.yml'), *directory.rglob('*.yaml')))


def normalize_release(
    release: str,
    /,
) -> str:
    """
    Return a semantic release without an optional leading ``v``.

    Parameters
    ----------
    release : str
        Three-component release version with an optional leading ``v``.

    Returns
    -------
    str
        Version in ``MAJOR.MINOR.PATCH`` form.

    Raises
    ------
    ValueError
        If the input is not a three-component release version. Leading
        zeroes, prerelease suffixes, and build metadata are not accepted.
    """

    if match := RELEASE_PATTERN.fullmatch(release):
        return match.group('version')
    raise ValueError(
        'release version must use vMAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH: '
        f'{release!r}',
    )


def report(
    failures: Sequence[str],
    /,
    *,
    success: str,
) -> int:
    """
    Print check results and return a conventional process status.

    Parameters
    ----------
    failures : collections.abc.Sequence[str]
        Validation failures to print to standard output with ``FAIL:`` prefixes.
    success : str
        Message to print with a ``PASS:`` prefix when there are no failures.

    Returns
    -------
    int
        One when failures exist; otherwise, zero.
    """

    if failures:
        for failure in failures:
            print(f'FAIL: {failure}')
        return 1
    print(f'PASS: {success}')
    return 0


# !SECTION
