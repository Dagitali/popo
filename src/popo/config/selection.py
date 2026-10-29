"""
:mod:`popo.config.selection` module.

Select offline repository checks without assuming a consumer language.
"""

from dataclasses import dataclass
from pathlib import Path

from ._common import (
    ConfigurationError,
    configuration_path,
    read_popo,
    read_strings,
    require_table,
)

# SECTION: CONSTANTS


BASELINE = (
    'check-docs',
    'check-github-actions-pins',
    'check-dependency-boundaries',
    'check-python-policy',
)
OPTIONAL = {
    'test-results': 'check-test-results',
    'python-boundaries': 'check-python-boundaries',
    'swift-boundaries': 'check-swift-boundaries',
    'python-source': 'check-python-source',
    'swift-policy': 'check-swift-policy',
    'swift-source': 'check-swift-source',
    'logs': 'check-logs',
    'automation': 'check-automation-contracts',
    'safety': 'check-repository-safety',
    'files': 'check-required-files',
    'headers': 'check-file-headers',
    'guardrails': 'check-guardrail-parity',
}
CHECKS = (*BASELINE, *OPTIONAL.values())


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class CheckPlan:
    """
    Describe selected checks and their configuration provenance.

    Attributes
    ----------
    source : pathlib.Path
        Authoritative consumer configuration path, even when absent.
    checks : tuple[str, ...]
        Unique offline check commands, in execution order.
    reason : str
        Source of selection: legacy defaults, explicit checks or named profile.

    Notes
    -----
    These guarantees describe plans returned by :func:`load_plan`. Direct
    construction does not validate the source path or check selection.
    """

    source: Path
    checks: tuple[str, ...]
    reason: str


# !SECTION


# SECTION: FUNCTIONS


def load_plan(
    root: Path,
    profile: str | None = None,
) -> CheckPlan:
    """
    Resolve a nonempty check selection without running validators.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root containing optional Popo configuration.
    profile : str or None, optional
        Explicit profile name; never inferred from the consumer's language.

    Returns
    -------
    CheckPlan
        Ordered checks and their provenance. Without explicit selection, retain
        baseline checks plus configured opt-in domains.

    Raises
    ------
    ConfigurationError
        Malformed, empty, duplicate or unknown selections, or missing profile.
    OSError, UnicodeError
        Unreadable consumer configuration.
    """
    root = root.resolve()
    settings = read_popo(root)
    return parse_plan(root, settings, profile)


def parse_plan(
    root: Path,
    settings: dict[str, object],
    profile: str | None = None,
) -> CheckPlan:
    """
    Select checks from an already-read consumer configuration snapshot.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository root; resolved before recording provenance.
    settings : dict[str, object]
        Standalone or embedded Popo table, inspected without mutation.
    profile : str or None, optional
        Explicit profile; otherwise use configured checks or legacy defaults.

    Returns
    -------
    CheckPlan
        Validated checks in configuration order and their source provenance.

    Raises
    ------
    ConfigurationError
        Selection or profile is missing, malformed, empty or unknown.
    OSError
        Repository root or configuration provenance cannot be inspected.

    Notes
    -----
    No configuration contents are read again and no checks are executed.
    Provenance selects the current standalone/embedded filename as usual.
    """
    root = root.resolve()
    reason = 'legacy defaults and configured opt-in checks'
    selection = settings.get('checks')
    if profile is not None:
        profiles = require_table(settings.get('profiles', {}), name='profiles')
        if profile not in profiles:
            raise ConfigurationError(f'unknown profile: {profile}')
        table = require_table(profiles[profile], name=f'profiles.{profile}')
        if table.keys() != {'checks'}:
            raise ConfigurationError(f'profiles.{profile} requires only checks')
        selection = table['checks']
        reason = f'profile: {profile}'
    elif 'checks' in settings:
        reason = 'explicit checks'
    else:
        selection = [*BASELINE, *(v for k, v in OPTIONAL.items() if k in settings)]
    checks = read_strings(selection, 'checks')
    if not checks:
        raise ConfigurationError('checks must select at least one check')
    unknown = set(checks) - set(CHECKS)
    if unknown:
        raise ConfigurationError(
            f'unknown offline checks: {', '.join(sorted(unknown))}',
        )
    return CheckPlan(configuration_path(root), checks, reason)


# !SECTION
