"""
:mod:`popo.config.apple_metadata` module.

Load opt-in, consumer-owned Apple property-list and Xcode setting contracts.
"""

import math
import re
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import Any

from ._common import ConfigurationError, read_literal_path, read_popo, require_table

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
    optional_expected : dict[str, Any]
        Exact values checked only where a key is explicitly present.
    required_anywhere : tuple[str, ...]
        Keys required in at least one selected mapping.
    absent_patterns : tuple[str, ...]
        Regular expressions searched against explicit top-level key names.
    all_configurations : bool
        Inspect every declared configuration, including unreferenced objects.
    """

    identity: str
    path: str
    kind: str
    expected: dict[str, Any]
    absent: tuple[str, ...]
    target: str
    configurations: tuple[str, ...]
    consistent: tuple[str, ...]
    optional_expected: dict[str, Any] = field(default_factory=dict)
    required_anywhere: tuple[str, ...] = ()
    absent_patterns: tuple[str, ...] = ()
    all_configurations: bool = False


@dataclass(frozen=True, slots=True)
class AppleCoverage:
    """
    Require discovered files to have explicit property-list rule coverage.

    Attributes
    ----------
    identity : str
        Non-sensitive diagnostic identifier shared with the rule namespace.
    include : tuple[str, ...]
        Root-confined discovery patterns whose union must match files.
    rule_ids : tuple[str, ...]
        Explicit plist rules allowed to cover those literal discovered paths.
    """

    identity: str
    include: tuple[str, ...]
    rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AppleMetadataConfig:
    """
    Keep literal expectations separate from discovered-file coverage.

    Attributes
    ----------
    rules : tuple[AppleRule, ...]
        Source metadata rules in consumer declaration order.
    coverage : tuple[AppleCoverage, ...]
        Optional discovery requirements in consumer declaration order.
    """

    rules: tuple[AppleRule, ...]
    coverage: tuple[AppleCoverage, ...]


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
) -> AppleMetadataConfig:
    """
    Load a nonempty set of explicit, root-confined Apple metadata rules.

    Parameters
    ----------
    root : pathlib.Path
        Repository containing standalone or embedded policy.

    Returns
    -------
    AppleMetadataConfig
        Strictly validated rules and coverage; inputs are not opened here.

    Raises
    ------
    ConfigurationError
        Rules are missing, unsafe, duplicated or contain unsupported settings.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    table = require_table(read_popo(root).get('apple-metadata'), name='apple-metadata')
    rules = table.get('rules')
    if table.keys() - {'rules', 'coverage'} or not isinstance(rules, list) or not rules:
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
            'optional-expected',
            'required-anywhere',
            'absent-patterns',
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
        path = read_literal_path(path, 'apple-metadata')
        if not isinstance(kind, str) or kind not in ('plist', 'xcode'):
            raise ConfigurationError('apple-metadata: kind must be plist or xcode')
        expected = rule.get('expected', {})
        if not isinstance(expected, dict) or not _value(expected):
            raise ConfigurationError('apple-metadata: unsupported expected values')
        optional = rule.get('optional-expected', {})
        if not isinstance(optional, dict) or not _value(optional):
            raise ConfigurationError('apple-metadata: unsupported optional values')
        required = _strings(rule.get('required-anywhere', []))
        patterns = _strings(rule.get('absent-patterns', []))
        try:
            compiled_patterns = tuple(re.compile(pattern) for pattern in patterns)
        except re.error:
            raise ConfigurationError('apple-metadata: invalid key pattern') from None
        absent = _strings(rule.get('absent', []))
        consistent = _strings(rule.get('consistent', []))
        configurations = _strings(rule.get('configurations', []))
        scope = rule.get('scope', 'target')
        if scope not in ('target', 'project', 'all-configurations'):
            raise ConfigurationError('apple-metadata: invalid xcode scope')
        target = rule.get('target', '')
        if not isinstance(target, str):
            raise ConfigurationError('apple-metadata: target must be a string')
        positive = set(expected).union(optional, consistent, required)
        if (
            not expected.keys().isdisjoint(optional)
            or not positive.isdisjoint(absent)
            or any(
                pattern.search(key) for pattern in compiled_patterns for key in positive
            )
        ):
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
            or (scope != 'target' and 'target' in rule)
            or (scope != 'all-configurations' and not configurations)
            or (scope == 'all-configurations' and 'configurations' in rule)
            or any(
                not isinstance(item, str)
                for item in chain(expected.values(), optional.values())
            )
        ):
            raise ConfigurationError(
                'apple-metadata: xcode needs target, configurations and string values',
            )
        if not any((expected, optional, absent, consistent, required, patterns)):
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
                optional,
                required,
                patterns,
                scope == 'all-configurations',
            ),
        )
    coverage = table.get('coverage', [])
    if not isinstance(coverage, list):
        raise ConfigurationError('apple-metadata: coverage must be a list')
    discovered = []
    plist_ids = {item.identity for item in result if item.kind == 'plist'}
    for raw in coverage:
        item = require_table(raw, name='apple-metadata coverage')
        if item.keys() != {'id', 'include', 'rule-ids'}:
            raise ConfigurationError('apple-metadata: invalid coverage settings')
        identity = item['id']
        if (
            not isinstance(identity, str)
            or not re.fullmatch(r'[a-z][a-z0-9-]*', identity)
            or identity in identities
        ):
            raise ConfigurationError('apple-metadata: invalid or duplicate coverage id')
        identities.add(identity)
        include = _strings(item['include'])
        rule_ids = _strings(item['rule-ids'])
        if not include or not rule_ids or not set(rule_ids) <= plist_ids:
            raise ConfigurationError(
                'apple-metadata: coverage needs patterns and plist rules',
            )
        for pattern in include:
            read_literal_path(pattern, 'apple-metadata')
            if '**' in pattern or any(
                char in str(Path(pattern).parent) for char in '*?['
            ):
                raise ConfigurationError(
                    'apple-metadata: coverage needs literal directories '
                    'and filename globs',
                )
        discovered.append(AppleCoverage(identity, include, rule_ids))
    return AppleMetadataConfig(tuple(result), tuple(discovered))


# !SECTION
