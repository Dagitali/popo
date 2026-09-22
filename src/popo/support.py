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
    """Return sorted YAML automation files below *directory*."""

    if not directory.is_dir():
        return []
    return sorted((*directory.rglob('*.yml'), *directory.rglob('*.yaml')))


def normalize_release(
    release: str,
    /,
) -> str:
    """Return a semantic release without an optional leading ``v``."""

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
    """Print check results and return a conventional process status."""

    if failures:
        for failure in failures:
            print(f'FAIL: {failure}')
        return 1
    print(f'PASS: {success}')
    return 0


# !SECTION