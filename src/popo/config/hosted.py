"""Load explicit hosted audit policy without contacting GitHub.

Maintainer Notes
----------------
Keep expectations consumer-owned and reject ambiguous exception records.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from ._common import ConfigurationError, read_popo, require_table

# SECTION: DATA CLASSES


@dataclass(frozen=True)
class RepositoryPolicy:
    """Hold validated expectations for one GitHub repository."""

    name: str
    settings: dict[str, bool]
    labels: tuple[str, ...]
    codeowners: bool
    branches: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ExceptionPolicy:
    """Hold a scoped, approved, expiring deviation from an expectation."""

    repository: str
    check: str
    owner: str
    reason: str
    approved_by: str
    approval: str
    expires: date


@dataclass(frozen=True)
class HostedConfig:
    """Group repository expectations and explicit exception records."""

    repositories: tuple[RepositoryPolicy, ...]
    exceptions: tuple[ExceptionPolicy, ...]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _strings(
    value: object,
    name: str,
) -> tuple[str, ...]:
    """Require unique, nonempty string values in a configuration array."""
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ConfigurationError(f'{name} must be an array of nonempty strings')
    result = tuple(str(item) for item in value)
    if len(set(result)) != len(result):
        raise ConfigurationError(f'{name} contains duplicates')
    return result


# !SECTION


# SECTION: FUNCTIONS


def expected_checks(
    policy: RepositoryPolicy,
) -> set[str]:
    """
    Return stable identifiers eligible for scoped exceptions.

    Parameters
    ----------
    policy : RepositoryPolicy
        Validated repository expectations.

    Returns
    -------
    set[str]
        Exact setting, label, CODEOWNERS, and branch-check identifiers.
    """
    return {
        *policy.settings,
        *(f'label:{label}' for label in policy.labels),
        *(['codeowners'] if policy.codeowners else []),
        *(f'branch:{branch}:protected' for branch in policy.branches),
        *(
            f'branch:{branch}:check:{check}'
            for branch, checks in policy.branches.items()
            for check in checks
        ),
    }


def load_hosted_config(
    root: Path,
) -> HostedConfig:
    """Load the explicitly configured GitHub audit inventory.

    Parameters
    ----------
    root : pathlib.Path
        Repository containing ``[tool.popo.hosted]`` in pyproject.toml.

    Returns
    -------
    HostedConfig
        Validated expectations and exceptions; no network access occurs.

    Raises
    ------
    ConfigurationError
        If policy is absent, malformed, duplicated, or contains unknown keys.
    OSError, UnicodeError
        If configuration cannot be read or decoded.
    """
    table = require_table(read_popo(root).get('hosted'), name='tool.popo.hosted')
    if set(table) - {'repositories', 'exceptions'}:
        raise ConfigurationError('unknown hosted configuration key')
    repositories: list[RepositoryPolicy] = []
    entries = table.get('repositories')
    if not isinstance(entries, list) or not entries:
        raise ConfigurationError('hosted.repositories must be a nonempty array')
    for entry in entries:
        row = require_table(entry, name='hosted repository')
        if set(row) - {'name', 'settings', 'labels', 'codeowners', 'branches'}:
            raise ConfigurationError('unknown hosted repository key')
        name = row.get('name')
        if not isinstance(name, str) or not re.fullmatch(
            r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',
            name,
        ):
            raise ConfigurationError('repository name must be owner/repository')
        settings = require_table(row.get('settings', {}), name='settings')
        if set(settings) - {
            'private-vulnerability-reporting',
            'secret-scanning',
            'secret-scanning-push-protection',
        } or any(type(value) is not bool for value in settings.values()):
            raise ConfigurationError(
                'settings must contain supported boolean expectations',
            )
        codeowners = row.get('codeowners', False)
        if type(codeowners) is not bool:
            raise ConfigurationError('codeowners must be boolean')
        branches = require_table(row.get('branches', {}), name='branches')
        if any(not branch.strip() for branch in branches):
            raise ConfigurationError('branch names cannot be empty')
        repositories.append(
            RepositoryPolicy(
                name,
                {key: bool(value) for key, value in settings.items()},
                _strings(row.get('labels', []), 'labels'),
                codeowners,
                {
                    branch: _strings(checks, f'branches.{branch}')
                    for branch, checks in branches.items()
                },
            ),
        )
    if len({repo.name.lower() for repo in repositories}) != len(repositories):
        raise ConfigurationError('duplicate repository policy')
    if any(not expected_checks(repo) for repo in repositories):
        raise ConfigurationError('each repository needs at least one expectation')
    exceptions: list[ExceptionPolicy] = []
    entries = table.get('exceptions', [])
    if not isinstance(entries, list):
        raise ConfigurationError('hosted.exceptions must be an array')
    for entry in entries:
        row = require_table(entry, name='hosted exception')
        keys = {
            'repository',
            'check',
            'owner',
            'reason',
            'approved-by',
            'approval',
            'expires',
        }
        if set(row) != keys or any(
            not isinstance(value, str) or not value.strip() for value in row.values()
        ):
            raise ConfigurationError('exceptions require all documented string fields')
        values = {key: str(value) for key, value in row.items()}
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', values['expires']):
                raise ValueError('noncanonical date')
            expires = date.fromisoformat(values['expires'])
        except ValueError as error:
            raise ConfigurationError('exception expires must be an ISO date') from error
        repo = next(
            (item for item in repositories if item.name == values['repository']),
            None,
        )
        checks = set() if repo is None else expected_checks(repo)
        if values['check'] not in checks:
            raise ConfigurationError(
                'exception must target a configured repository/check',
            )
        try:
            approval = urlsplit(values['approval'])
        except ValueError as error:
            raise ConfigurationError('invalid exception approval URL') from error
        if (
            approval.scheme != 'https'
            or not approval.hostname
            or approval.username
            or approval.password
        ):
            raise ConfigurationError('exception approval must be an HTTPS evidence URL')
        exceptions.append(
            ExceptionPolicy(
                values['repository'],
                values['check'],
                values['owner'],
                values['reason'],
                values['approved-by'],
                values['approval'],
                expires,
            ),
        )
    if len({(item.repository, item.check) for item in exceptions}) != len(exceptions):
        raise ConfigurationError('duplicate exception scope')
    return HostedConfig(tuple(repositories), tuple(exceptions))


# !SECTION
