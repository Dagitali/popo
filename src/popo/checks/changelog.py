"""
:mod:`popo.checks.changelog` module.

Validate release changelog entries.
"""

import re
from datetime import date
from pathlib import Path

from popo.support import normalize_release

# SECTION: FUNCTIONS


def validate(
    changelog: Path,
    release: str,
) -> list[str]:
    """Return failures for a missing or invalid dated release heading."""

    try:
        version = normalize_release(release)
    except ValueError as error:
        return [str(error)]
    if not changelog.is_file():
        return [f'changelog does not exist: {changelog}']
    pattern = re.compile(
        rf'^## \[{re.escape(version)}\] - (?P<date>\d{{4}}-\d{{2}}-\d{{2}})$',
        re.MULTILINE,
    )
    heading = pattern.search(changelog.read_text(encoding='utf-8'))
    if heading is None:
        return [f'{changelog.name} has no dated section for {version}']
    try:
        date.fromisoformat(heading.group('date'))
    except ValueError:
        return [
            f'{changelog.name} has an invalid date for {version}: '
            f'{heading.group('date')}',
        ]
    return []


# !SECTION
