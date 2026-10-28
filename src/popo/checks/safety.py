# safety.py
# Bounded static checks, not a workflow sandbox or full npm lock validator.
"""
:mod:`popo.checks.safety` module.

Validate privileged-trigger policy and npm root metadata offline.
"""

import json
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from ..config.safety import SafetyConfig
from ._yaml import mapping_nodes, read_mapping

# SECTION: CONSTANTS


NPM_EXACT_VERSION_PATTERN = re.compile(
    r'\d+\.\d+\.\d+(?:-[\w.-]+)?'
    r'(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?',
)


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _file(
    root: Path,
    relative: str,
) -> Path:
    """Resolve a configured path and reject symlink escapes."""
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'path escapes repository: {relative}')
    return path


def _npm_findings(
    root: Path,
    manifest: str,
    lockfile: str,
) -> Iterator[str]:
    """Yield npm drift before later read, parse or shape errors propagate."""
    label = f'{manifest} -> {lockfile}'
    package: object = json.loads(_file(root, manifest).read_text('utf-8'))
    lock: object = json.loads(_file(root, lockfile).read_text('utf-8'))
    if not isinstance(package, dict) or not isinstance(lock, dict):
        raise ValueError('npm documents must be objects')
    version = lock.get('lockfileVersion')
    if type(version) is not int or version not in (2, 3):
        raise ValueError('only npm lockfile versions 2 and 3 are supported')
    packages = lock.get('packages')
    if not isinstance(packages, dict) or not isinstance(packages.get(''), dict):
        raise ValueError('lockfile packages root is required')
    locked = packages['']
    for key in (
        'name',
        'version',
        'dependencies',
        'devDependencies',
        'optionalDependencies',
    ):
        default: dict[str, object] | None = None if key in ('name', 'version') else {}
        expected = package.get(key, default)
        observed = locked.get(key, default)
        if expected != observed:
            yield f'{label}: root {key} differs'
        if key not in ('name', 'version'):
            if not isinstance(expected, dict):
                raise ValueError(f'{key} must be an object')
            for name, spec in expected.items():
                if not isinstance(spec, str) or not spec.strip():
                    raise ValueError(f'{key} specifications must be strings')
                if NPM_EXACT_VERSION_PATTERN.fullmatch(spec):
                    installed = packages.get(f'node_modules/{name}')
                    if (
                        not isinstance(installed, dict)
                        or installed.get('version') != spec
                    ):
                        yield f'{label}: resolved {name} differs from {spec}'


def _workflow(
    path: Path,
) -> dict[str, object]:
    """Parse a mapping with duplicate-key rejection and string event keys."""
    return read_mapping(path, label='workflow')


def _workflow_content(
    value: object,
) -> tuple[bool, tuple[str, ...]]:
    """
    Collect checkout and script observations in one cycle-safe traversal.

    Parameters
    ----------
    value : object
        Parsed workflow graph; only mappings and lists are traversed.

    Returns
    -------
    tuple[bool, tuple[str, ...]]
        Whether a checkout directly references pull-request head data, and run
        strings in native mapping traversal order. Recursive/shared containers
        are visited once; identical scripts on distinct mappings are retained.

    Notes
    -----
    Checkout observations apply only when the caller identifies a privileged
    trigger. Scripts are collected for every workflow. Findings remain the
    caller's responsibility; no command language or expression is evaluated.
    """
    head_checkout = False
    scripts: list[str] = []
    for node in mapping_nodes(value):
        if isinstance(script := node.get('run'), str):
            scripts.append(script)
        action = node.get('uses')
        settings = node.get('with')
        head_checkout = head_checkout or (
            isinstance(action, str)
            and action.startswith('actions/checkout@')
            and isinstance(settings, dict)
            and any(
                isinstance(item, str) and 'github.event.pull_request.head' in item
                for item in settings.values()
            )
        )
    return head_checkout, tuple(scripts)


def _workflow_paths(
    config: SafetyConfig,
) -> tuple[list[Path], list[str]]:
    """Discover unique workflows, retaining findings for failed patterns."""
    paths: set[Path] = set()
    failures: list[str] = []
    for pattern in config.workflows:
        try:
            matches = list(config.root.glob(pattern))
        except (OSError, ValueError):
            failures.append(f'cannot discover safety workflows: {pattern}')
            continue
        if not matches:
            failures.append(f'no safety workflows match: {pattern}')
        paths.update(matches)
    return sorted(paths), failures


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: SafetyConfig,
    *,
    today: date | None = None,
) -> list[str]:
    """
    Check consumer safety expectations using only local reads.

    Parameters
    ----------
    config : SafetyConfig
        Validated policy, including explicit source-manifest/lockfile pairs.
    today : datetime.date or None, optional
        Exception review date; defaults to the UTC calendar date.

    Returns
    -------
    list[str]
        Failures including missing files, parse errors, drift, unsafe shell
        interpolation, and expired or unused privileged-trigger exceptions.
        Workflow discovery errors become diagnostics; independent workflows
        and npm pairs are still inspected.

    Notes
    -----
    This is bounded static validation, not taint analysis or proof that code
    is trusted. npm checks compare root dependency specifications and exact
    resolved versions only; ``npm ci`` remains authoritative for full graphs.
    """
    day = today or datetime.now(UTC).date()
    paths, failures = _workflow_paths(config)
    used: set[tuple[str, str]] = set()
    exceptions = {(entry.workflow, entry.trigger): entry for entry in config.exceptions}
    for candidate in paths:
        relative = candidate.relative_to(config.root).as_posix()
        try:
            document = _workflow(_file(config.root, relative))
            events = document.get('on', {})
            if not isinstance(events, (str, list, dict)):
                raise ValueError('workflow on must be a string, list, or mapping')
            if isinstance(events, list) and not all(
                isinstance(item, str) for item in events
            ):
                raise ValueError('workflow event list must contain strings')
            privileged = False
            for trigger in ('pull_request_target', 'workflow_run'):
                present = (
                    events == trigger if isinstance(events, str) else trigger in events
                )
                if not present:
                    continue
                privileged = True
                scope = (relative, trigger)
                used.add(scope)
                exception = exceptions.get(scope)
                if exception is None:
                    failures.append(
                        f'{relative}: privileged trigger {trigger} needs exception',
                    )
                elif exception.expires < day:
                    failures.append(f'{relative}: expired {trigger} exception')
            head_checkout, scripts = _workflow_content(document)
            if privileged and head_checkout:
                failures.append(f'{relative}: privileged checkout of pull-request head')
            for script in scripts:
                if re.search(
                    r'\$\{\{[^}]*github\.event\.(pull_request|issue|comment|discussion)\b',
                    script,
                ):
                    failures.append(
                        f'{relative}: event data interpolated directly into run',
                    )
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
            failures.append(f'{relative}: {error}')
    for scope, entry in exceptions.items():
        if scope in used:
            continue
        failures.append(f'{scope[0]}: unused {scope[1]} exception')
        if entry.expires < day:
            failures.append(f'{scope[0]}: expired {scope[1]} exception')
    for manifest, lockfile in config.npm_pairs:
        try:
            failures.extend(_npm_findings(config.root, manifest, lockfile))
        except (OSError, UnicodeError, ValueError) as error:
            failures.append(f'{manifest} -> {lockfile}: {error}')
    return failures


# !SECTION
