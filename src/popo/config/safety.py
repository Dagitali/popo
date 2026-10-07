# safety.py
# Read-only consumer safety policy; never execute workflow or package commands.
"""Load opt-in workflow and npm manifest consistency policy."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

from ._common import ConfigurationError, read_popo, require_table

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class SafetyConfig:
    """Store validated consumer safety policy.

    Attributes
    ----------
    root : pathlib.Path
        Resolved repository boundary.
    workflows : tuple[str, ...]
        Relative workflow discovery patterns.
    exceptions : tuple[tuple[str, str, str, str, str, date], ...]
        Exact workflow, trigger, owner, reason, approver, and expiry records.
    npm_pairs : tuple[tuple[str, str], ...]
        Manifest and lockfile pairs, including copied source manifests.
    configured : bool
        Whether the consumer opted into aggregate validation.
    """

    root: Path
    workflows: tuple[str, ...] = ()
    exceptions: tuple[tuple[str, str, str, str, str, date], ...] = ()
    npm_pairs: tuple[tuple[str, str], ...] = ()
    configured: bool = False


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _path(value: object) -> str:
    """Require a nonempty repository-relative policy path."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or Path(value).is_absolute()
        or '..' in Path(value).parts
    ):
        raise ConfigurationError('safety paths must stay inside the repository')
    return value


# !SECTION


# SECTION: FUNCTIONS


def load_safety_config(root: Path) -> SafetyConfig:
    """
    Load safety settings without commands or network access.

    Parameters
    ----------
    root : pathlib.Path
        Consumer containing optional ``tool.popo.safety`` metadata.

    Returns
    -------
    SafetyConfig
        Validated settings; no discovery when the table is absent.

    Raises
    ------
    ConfigurationError
        Unknown keys, unsafe paths, malformed pairs, or invalid exceptions.
    """
    root = root.resolve()
    popo = read_popo(root)
    table = require_table(popo.get('safety', {}), name='tool.popo.safety')
    if set(table) - {'workflow-globs', 'exceptions', 'npm-pairs'}:
        raise ConfigurationError('unknown tool.popo.safety setting')
    arrays: dict[str, list[object]] = {}
    for key in ('workflow-globs', 'exceptions', 'npm-pairs'):
        value = table.get(key, [])
        if not isinstance(value, list):
            raise ConfigurationError('safety settings must be arrays')
        arrays[key] = cast(list[object], value)
    workflows = tuple(_path(item) for item in arrays['workflow-globs'])
    pairs: list[tuple[str, str]] = []
    for item in arrays['npm-pairs']:
        pair = require_table(item, name='npm-pairs entry')
        if set(pair) != {'manifest', 'lockfile'}:
            raise ConfigurationError('npm-pairs requires manifest and lockfile')
        pairs.append((_path(pair['manifest']), _path(pair['lockfile'])))
    exceptions: list[tuple[str, str, str, str, str, date]] = []
    for item in arrays['exceptions']:
        entry = require_table(item, name='safety exception')
        if set(entry) != {
            'workflow',
            'trigger',
            'owner',
            'reason',
            'approved-by',
            'expires',
        }:
            raise ConfigurationError(
                'safety exception requires exact scope and approval',
            )
        workflow = _path(entry['workflow'])
        if any(character in workflow for character in '*?['):
            raise ConfigurationError('exception workflow must be an exact path')
        trigger = entry['trigger']
        if trigger not in ('pull_request_target', 'workflow_run'):
            raise ConfigurationError('exception trigger must be privileged')
        details = [entry[key] for key in ('owner', 'reason', 'approved-by', 'expires')]
        if not all(isinstance(value, str) and value.strip() for value in details):
            raise ConfigurationError('exception details must be nonempty strings')
        owner, reason, approver, expiry = map(str, details)
        try:
            expires = date.fromisoformat(expiry)
        except ValueError as error:
            raise ConfigurationError(
                'exception expires must be a quoted ISO date',
            ) from error
        exceptions.append((workflow, str(trigger), owner, reason, approver, expires))
    scopes = [(entry[0], entry[1]) for entry in exceptions]
    if len(scopes) != len(set(scopes)):
        raise ConfigurationError('duplicate safety exception scope')
    return SafetyConfig(
        root,
        workflows,
        tuple(exceptions),
        tuple(pairs),
        'safety' in popo,
    )


# !SECTION
