"""
:mod:`popo.config.apple_metadata` module.

Load opt-in, consumer-owned Apple property-list and Xcode setting contracts.
"""

import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ._common import ConfigurationError, read_popo, require_table

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class AppleRule:
    """
    Store one explicitly selected metadata contract.

    Attributes
    ----------
    identity : str
        Non-sensitive diagnostic identifier.
    path : str
        Literal repository-relative POSIX filename, never a glob.
    kind : str
        plist for XML/binary metadata or xcode for explicit build settings.
    expected : dict[str, Any]
        Typed exact values for selected keys; extra keys remain allowed.
    absent : tuple[str, ...]
        Keys forbidden in each selected mapping.
    target : str
        Exact native target name; empty for plist or project-scope rules.
    configurations : tuple[str, ...]
        Exact configuration names selected within that target.
    consistent : tuple[str, ...]
        Nonempty string settings required to agree across selected configs.
    """

    identity: str
    path: str
    kind: str
    expected: dict[str, Any]
    absent: tuple[str, ...]
    target: str
    configurations: tuple[str, ...]
    consistent: tuple[str, ...]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _strings(
    value: object,
) -> tuple[str, ...]:
    """
    Validate unique, nonblank string lists without echoing their contents.

    Parameters
    ----------
    value : object
        Untrusted policy field.

    Returns
    -------
    tuple[str, ...]
        Validated strings, possibly empty.

    Raises
    ------
    ConfigurationError
        A list, string or uniqueness requirement is violated.
    """
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ConfigurationError('apple-metadata: expected a list of nonblank strings')
    if len(set(value)) != len(value):
        raise ConfigurationError('apple-metadata: duplicate list entry')
    return tuple(value)


def _value(
    value: object,
) -> bool:
    """
    Recognize comparable TOML values supported by metadata contracts.

    Parameters
    ----------
    value : object
        Expected scalar, array or dictionary.

    Returns
    -------
    bool
        Whether values are finite and contain no dates or unsupported objects.
    """
    if type(value) in (str, bool, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_value(item) for item in value)
    return isinstance(value, dict) and all(
        isinstance(key, str) and _value(item) for key, item in value.items()
    )


# !SECTION


# SECTION: FUNCTIONS


def load_apple_metadata_config(
    root: Path,
) -> tuple[AppleRule, ...]:
    """
    Load a nonempty set of explicit, root-confined Apple metadata rules.

    Parameters
    ----------
    root : pathlib.Path
        Repository containing standalone or embedded policy.

    Returns
    -------
    tuple[AppleRule, ...]
        Strictly validated rules; input files are not opened here.

    Raises
    ------
    ConfigurationError
        Rules are missing, unsafe, duplicated or contain unsupported settings.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    table = require_table(read_popo(root).get('apple-metadata'), name='apple-metadata')
    rules = table.get('rules')
    if table.keys() != {'rules'} or not isinstance(rules, list) or not rules:
        raise ConfigurationError('apple-metadata: requires nonempty rules')
    result = []
    identities = set()
    for raw in rules:
        rule = require_table(raw, name='apple-metadata rule')
        if rule.keys() - {
            'id',
            'path',
            'kind',
            'expected',
            'absent',
            'target',
            'configurations',
            'consistent',
            'scope',
        }:
            raise ConfigurationError('apple-metadata: unknown rule setting')
        identity, path, kind = (rule.get(key) for key in ('id', 'path', 'kind'))
        if not isinstance(identity, str) or not re.fullmatch(
            r'[a-z][a-z0-9-]*',
            identity,
        ):
            raise ConfigurationError('apple-metadata: invalid rule id')
        if identity in identities:
            raise ConfigurationError('apple-metadata: duplicate rule id')
        identities.add(identity)
        if (
            not isinstance(path, str)
            or not path.strip()
            or PurePosixPath(path).is_absolute()
            or any(part in ('.', '..', '') for part in path.split('/'))
            or '\\' in path
            or any(ord(char) < 32 for char in path)
        ):
            raise ConfigurationError('apple-metadata: requires a confined literal path')
        if not isinstance(kind, str) or kind not in ('plist', 'xcode'):
            raise ConfigurationError('apple-metadata: kind must be plist or xcode')
        expected = rule.get('expected', {})
        if not isinstance(expected, dict) or not _value(expected):
            raise ConfigurationError('apple-metadata: unsupported expected values')
        absent = _strings(rule.get('absent', []))
        consistent = _strings(rule.get('consistent', []))
        configurations = _strings(rule.get('configurations', []))
        scope = rule.get('scope', 'target')
        if scope not in ('target', 'project'):
            raise ConfigurationError('apple-metadata: invalid xcode scope')
        target = rule.get('target', '')
        if not isinstance(target, str):
            raise ConfigurationError('apple-metadata: target must be a string')
        if set(expected) & set(absent) or set(consistent) & set(absent):
            raise ConfigurationError('apple-metadata: contradictory key requirements')
        if kind == 'plist' and rule.keys() & {
            'target',
            'configurations',
            'consistent',
            'scope',
        }:
            raise ConfigurationError(
                'apple-metadata: plist rules cannot select targets',
            )
        if kind == 'xcode' and (
            (scope == 'target' and not target.strip())
            or (scope == 'project' and 'target' in rule)
            or not configurations
            or any(not isinstance(item, str) for item in expected.values())
        ):
            raise ConfigurationError(
                'apple-metadata: xcode needs target, configurations and string values',
            )
        if not expected and not absent and not consistent:
            raise ConfigurationError('apple-metadata: empty rule requirements')
        result.append(
            AppleRule(
                identity,
                path,
                kind,
                expected,
                absent,
                target,
                configurations,
                consistent,
            ),
        )
    return tuple(result)


# !SECTION
