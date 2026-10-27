"""
:mod:`popo.config.hosted` module.

Load explicit hosted audit policy without contacting GitHub.

Maintainer Notes
----------------
Keep expectations consumer-owned and reject ambiguous exception records.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from ._common import ConfigurationError, read_popo, read_strings, require_table

# SECTION: DATA CLASSES


@dataclass(frozen=True)
class ExceptionPolicy:
    """
    Hold a scoped approval attestation for an expiring deviation.

    Attributes
    ----------
    repository, check : str
        Exact repository and expected-check identifiers covered by approval.
    owner, reason : str
        Responsible maintainer and explanation of the deviation.
    approved_by, approval : str
        Approver and HTTPS evidence URL; authenticity requires human review.
    expires : datetime.date
        Inclusive expiry date, compared against the UTC calendar date.

    Notes
    -----
    Direct construction does not validate or authenticate the attestation.
    """

    repository: str
    check: str
    owner: str
    reason: str
    approved_by: str
    approval: str
    expires: date


@dataclass(frozen=True)
class RepositoryPolicy:
    """
    Hold explicit expectations for one GitHub repository.

    Attributes
    ----------
    name : str
        Owner/repository name on github.com.
    settings : dict[str, bool]
        Configured security-setting names and desired enabled states.
    labels : tuple[str, ...]
        Exact labels whose existence is required.
    codeowners : bool
        Whether to require CODEOWNERS and inspect hosted validation errors.
    branches : dict[str, tuple[str, ...]]
        Branch names mapped to required check contexts. Empty tuples require
        branch protection without naming required contexts.

    Notes
    -----
    Direct construction performs no validation. Freezing prevents attribute
    rebinding but does not make nested dictionaries immutable.
    """

    name: str
    settings: dict[str, bool]
    labels: tuple[str, ...]
    codeowners: bool
    branches: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class HostedConfig:
    """
    Group repository expectations and explicit exception records.

    Attributes
    ----------
    repositories : tuple[RepositoryPolicy, ...]
        Explicit audit inventory in declaration order.
    exceptions : tuple[ExceptionPolicy, ...]
        Scoped attestations applied only to confirmed missing expectations.

    Notes
    -----
    Construction does not validate policy or contact GitHub.
    """

    repositories: tuple[RepositoryPolicy, ...]
    exceptions: tuple[ExceptionPolicy, ...]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _exception_policy(
    entry: object,
    repository_checks: dict[str, set[str]],
) -> ExceptionPolicy:
    """
    Parse an approval scoped to a configured repository and expected check.

    Parameters
    ----------
    entry : object
        Consumer exception table with all documented string fields.
    repository_checks : dict[str, set[str]]
        Exact repository names mapped to their eligible expectation IDs.

    Returns
    -------
    ExceptionPolicy
        Scoped approval with a canonical expiry and HTTPS evidence URL.

    Raises
    ------
    ConfigurationError
        Fields, expiry, scope or evidence URL are invalid. Evidence is parsed
        locally; its existence and authenticity are not verified.
    """
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
    checks = repository_checks.get(values['repository'], set())
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
    return ExceptionPolicy(
        values['repository'],
        values['check'],
        values['owner'],
        values['reason'],
        values['approved-by'],
        values['approval'],
        expires,
    )


def _repository_policy(
    entry: object,
) -> RepositoryPolicy:
    """
    Parse one repository's consumer-owned expectations without hosted reads.

    Parameters
    ----------
    entry : object
        Repository table containing its name and supported expectations.

    Returns
    -------
    RepositoryPolicy
        Typed settings, labels, CODEOWNERS selection and branch expectations.
        Cross-repository duplicates and empty policies are checked separately.

    Raises
    ------
    ConfigurationError
        Keys, repository name, setting types, labels or branches are invalid.
    """
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
    return RepositoryPolicy(
        name,
        {key: bool(value) for key, value in settings.items()},
        read_strings(row.get('labels', []), 'labels'),
        codeowners,
        {
            branch: read_strings(checks, f'branches.{branch}')
            for branch, checks in branches.items()
        },
    )


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
        Repository containing ``[hosted]`` in standalone ``popo.toml`` or
        ``[tool.popo.hosted]`` in ``pyproject.toml``.

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
    entries = table.get('repositories')
    if not isinstance(entries, list) or not entries:
        raise ConfigurationError('hosted.repositories must be a nonempty array')
    repositories = [_repository_policy(entry) for entry in entries]
    if len({repo.name.lower() for repo in repositories}) != len(repositories):
        raise ConfigurationError('duplicate repository policy')
    repository_checks = {repo.name: expected_checks(repo) for repo in repositories}
    if not all(repository_checks.values()):
        raise ConfigurationError('each repository needs at least one expectation')
    entries = table.get('exceptions', [])
    if not isinstance(entries, list):
        raise ConfigurationError('hosted.exceptions must be an array')
    exceptions = [_exception_policy(entry, repository_checks) for entry in entries]
    if len({(item.repository, item.check) for item in exceptions}) != len(exceptions):
        raise ConfigurationError('duplicate exception scope')
    return HostedConfig(tuple(repositories), tuple(exceptions))


# !SECTION
