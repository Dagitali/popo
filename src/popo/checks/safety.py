# safety.py
# Bounded static checks, not a workflow sandbox or full npm lock validator.
"""Validate privileged-trigger policy and npm root metadata offline."""

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import yaml

from ..config.safety import SafetyConfig
from .automation import _Loader

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


def _head_checkout(
    value: object,
) -> bool:
    """Find direct pull-request head refs passed to the checkout action."""
    if isinstance(value, dict):
        action = value.get('uses')
        settings = value.get('with')
        if (
            isinstance(action, str)
            and action.startswith('actions/checkout@')
            and isinstance(settings, dict)
            and any(
                isinstance(item, str) and 'github.event.pull_request.head' in item
                for item in settings.values()
            )
        ):
            return True
        return any(_head_checkout(item) for item in value.values())
    if isinstance(value, list):
        return any(_head_checkout(item) for item in value)
    return False


def _scripts(
    value: object,
) -> list[str]:
    """Collect run commands recursively without interpreting their language."""
    if isinstance(value, dict):
        return [
            script
            for key, item in value.items()
            for script in (
                [item] if key == 'run' and isinstance(item, str) else _scripts(item)
            )
        ]
    if isinstance(value, list):
        return [script for item in value for script in _scripts(item)]
    return []


def _workflow(
    path: Path,
) -> dict[str, object]:
    """Parse a mapping with duplicate-key rejection and string event keys."""
    document: object = yaml.load(path.read_text(encoding='utf-8'), Loader=_Loader)
    if not isinstance(document, dict):
        raise ValueError('workflow must be a mapping')
    return cast(dict[str, object], document)


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

    Notes
    -----
    This is bounded static validation, not taint analysis or proof that code
    is trusted. npm checks compare root dependency specifications and exact
    resolved versions only; ``npm ci`` remains authoritative for full graphs.
    """
    day = today or datetime.now(UTC).date()
    failures: list[str] = []
    used: set[tuple[str, str]] = set()
    exceptions = {(entry[0], entry[1]): entry for entry in config.exceptions}
    paths: set[Path] = set()
    for pattern in config.workflows:
        matches = list(config.root.glob(pattern))
        if not matches:
            failures.append(f'no safety workflows match: {pattern}')
        paths.update(matches)
    for candidate in sorted(paths):
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
                elif exception[-1] < day:
                    failures.append(f'{relative}: expired {trigger} exception')
            if privileged and _head_checkout(document):
                failures.append(f'{relative}: privileged checkout of pull-request head')
            for script in _scripts(document):
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
        if scope not in used:
            failures.append(f'{scope[0]}: unused {scope[1]} exception')
        if entry[-1] < day and scope not in used:
            failures.append(f'{scope[0]}: expired {scope[1]} exception')
    for manifest, lockfile in config.npm_pairs:
        label = f'{manifest} -> {lockfile}'
        try:
            package: object = json.loads(
                _file(config.root, manifest).read_text('utf-8'),
            )
            lock: object = json.loads(_file(config.root, lockfile).read_text('utf-8'))
            if not isinstance(package, dict) or not isinstance(lock, dict):
                raise ValueError('npm documents must be objects')
            if lock.get('lockfileVersion') not in (2, 3):
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
                expected = package.get(
                    key,
                    {}
                    if key.endswith('Dependencies') or key == 'dependencies'
                    else None,
                )
                observed = locked.get(
                    key,
                    {}
                    if key.endswith('Dependencies') or key == 'dependencies'
                    else None,
                )
                if expected != observed:
                    failures.append(f'{label}: root {key} differs')
                if key not in ('name', 'version'):
                    if not isinstance(expected, dict):
                        raise ValueError(f'{key} must be an object')
                    for name, spec in expected.items():
                        if not isinstance(spec, str) or not spec.strip():
                            raise ValueError(f'{key} specifications must be strings')
                        if re.fullmatch(r'\d+\.\d+\.\d+(?:-[\w.-]+)?', spec):
                            installed = packages.get(f'node_modules/{name}')
                            if (
                                not isinstance(installed, dict)
                                or installed.get('version') != spec
                            ):
                                failures.append(
                                    f'{label}: resolved {name} differs from {spec}',
                                )
        except (OSError, UnicodeError, ValueError) as error:
            failures.append(f'{label}: {error}')
    return failures


# !SECTION
