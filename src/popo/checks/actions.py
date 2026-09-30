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


def is_pinned(
    reference: str,
) -> bool:
    """Return whether a reference satisfies the shared pin policy.

    Parameters
    ----------
    reference : str
        Uses value, without YAML quoting or comments.

    Returns
    -------
    bool
        True for a full hexadecimal commit or an exempt local/container reference.
        This syntax check does not verify remote existence or container immutability.
    """
    if reference.startswith(('./', 'docker://')):
        return True
    action, separator, revision = reference.rpartition('@')
    return bool(separator and action and FULL_COMMIT_PATTERN.fullmatch(revision))


def validate(
    automation_directory: Path,
) -> list[str]:
    """
    Return pinning failures for remote references in recognized uses lines.

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

    Raises
    ------
    OSError
        If a discovered YAML path cannot be read.
    UnicodeError
        If YAML text cannot be decoded as UTF-8.

    Notes
    -----
    Scan YAML files recursively using a line-based pattern, not a YAML parser.
    Require a nonempty action name and a 40-character hexadecimal revision;
    do not verify action existence, commit authenticity, or complete reference
    syntax. References beginning with ``./`` or ``docker://`` are exempt,
    so success does not establish container-image immutability. No network
    requests are made.
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
            if not is_pinned(reference):
                failures.append(
                    f'{path}:{line_number}: remote action must use a full '
                    f'40-character commit SHA: {reference}',
                )
    return failures


# !SECTION
