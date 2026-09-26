"""
:mod:`popo.checks.actions` module.

Validate immutable GitHub Actions references.
"""

import re
from pathlib import Path

from popo.support import automation_paths

# SECTION: CONSTANTS


FULL_COMMIT_PATTERN = re.compile(r'^[0-9a-fA-F]{40}$')
USES_PATTERN = re.compile(
    r'^\s*(?:-\s*)?uses:\s*["\']?([^\s"\']+)["\']?\s*(?:#.*)?$',
)


# !SECTION


# SECTION: FUNCTIONS


def validate(
    automation_directory: Path,
) -> list[str]:
    """
    Return every mutable or malformed remote action reference.

    Parameters
    ----------
    automation_directory : pathlib.Path
        Directory tree containing GitHub Actions workflow and action YAML.

    Returns
    -------
    list[str]
        Human-readable failures; empty when every checked remote reference has
        a non-empty action name and a full commit SHA. Local and container
        references are exempt from this check.
    """

    if not automation_directory.is_dir():
        return [f'automation directory does not exist: {automation_directory}']
    failures: list[str] = []
    for path in automation_paths(automation_directory):
        for line_number, line in enumerate(
            path.read_text(encoding='utf-8').splitlines(),
            start=1,
        ):
            match = USES_PATTERN.match(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith(('./', 'docker://')):
                continue
            action, separator, revision = reference.rpartition('@')
            if (
                not separator
                or not action
                or FULL_COMMIT_PATTERN.fullmatch(revision) is None
            ):
                failures.append(
                    f'{path}:{line_number}: remote action must use a full '
                    f'40-character commit SHA: {reference}',
                )
    return failures


# !SECTION
