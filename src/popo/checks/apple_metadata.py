"""
:mod:`popo.checks.apple_metadata` module.

Inspect literal Apple metadata inputs without native tools or value disclosure.
"""

import os
import plistlib
import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

from ..config.apple_metadata import AppleCoverage, AppleRule
from ._openstep import parse_project
from ._xcode import configuration_settings
from ._xcode import mapping as _mapping

# SECTION: PROTECTED FUNCTIONS


def _discovered_paths(
    root: Path,
    patterns: tuple[str, ...],
) -> set[Path]:
    """
    Discover filename matches without suppressing directory access failures.

    Parameters
    ----------
    root : pathlib.Path
        Repository confining every explicitly selected directory.
    patterns : tuple[str, ...]
        Validated literal directories followed by filename globs.

    Returns
    -------
    set[pathlib.Path]
        Lexical paths matched in the selected directories, without recursion.

    Raises
    ------
    OSError, ValueError
        A directory cannot be read or resolves outside the selected root.
    """
    paths: set[Path] = set()
    for pattern in patterns:
        relative = Path(pattern)
        directory = root / relative.parent
        if not directory.resolve().is_relative_to(root.resolve()):
            raise ValueError('discovery directory escapes root')
        with os.scandir(directory) as entries:
            paths.update(
                directory / entry.name
                for entry in entries
                if fnmatchcase(entry.name, relative.name)
            )
    return paths


def _same(
    actual: object,
    expected: object,
) -> bool:
    """
    Compare metadata recursively without equating Boolean and integer values.

    Parameters
    ----------
    actual : object
        Value read from native metadata.
    expected : object
        Consumer-owned exact expectation.

    Returns
    -------
    bool
        Whether types and all nested values match exactly.
    """
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _same(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _same(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


def _settings(
    project: dict[str, Any],
    rule: AppleRule,
) -> list[dict[str, Any]]:
    """
    Resolve a native target or root project and named build configurations.

    Parameters
    ----------
    project : dict[str, Any]
        Decoded OpenStep object graph.
    rule : AppleRule
        Exact target and configuration selection.

    Returns
    -------
    list[dict[str, Any]]
        Explicit build settings; no inheritance or variable expansion occurs.

    Raises
    ------
    KeyError, TypeError, ValueError
        Targets, configuration lists or references are missing or ambiguous.
    """
    if rule.all_configurations:
        settings = [
            _mapping(item['buildSettings'])
            for item in _mapping(project['objects']).values()
            if isinstance(item, dict) and item.get('isa') == 'XCBuildConfiguration'
        ]
        if not settings:
            raise ValueError('no declared configurations')
        return settings
    return configuration_settings(project, rule.target, rule.configurations)


# !SECTION


# SECTION: FUNCTIONS


def validate(
    root: Path,
    rules: tuple[AppleRule, ...],
    coverage: tuple[AppleCoverage, ...] = (),
) -> list[str]:
    """
    Validate independent metadata contracts and continue after input failures.

    Parameters
    ----------
    root : pathlib.Path
        Repository root confining every input, including symlink resolution.
    rules : tuple[AppleRule, ...]
        Validated consumer selection and expectations.
    coverage : tuple[AppleCoverage, ...], optional
        Explicit discovered-file coverage requirements; defaults to none.

    Returns
    -------
    list[str]
        Rule identifiers and redacted reasons, without values or raw errors.
        Missing, malformed, escaping and mismatched inputs fail their rule.

    Notes
    -----
    Files are read once per path/adapter in this invocation, including failed
    reads and parses. Later invocations inspect inputs afresh. Only literal
    source values are checked. This does not resolve xcconfig inheritance,
    inspect signatures, invoke Xcode or establish App Store compliance.
    """
    failures = []
    documents: dict[tuple[Path, str], dict[str, Any] | None] = {}
    for rule in rules:
        try:
            path = root / rule.path
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('input escapes root')
            key = (path, rule.kind)
            if key not in documents:
                documents[key] = None
                data = path.read_bytes()
                documents[key] = _mapping(
                    plistlib.loads(data)
                    if rule.kind == 'plist'
                    else parse_project(data.decode('utf-8')),
                )
            document = documents[key]
            if document is None:
                raise ValueError('metadata read or parse previously failed')
            mappings = [document] if rule.kind == 'plist' else _settings(document, rule)
            forbidden_keys = tuple(
                re.compile(pattern).search for pattern in rule.absent_patterns
            )
            for mapping in mappings:
                if any(
                    key not in mapping or not _same(mapping[key], value)
                    for key, value in rule.expected.items()
                ):
                    raise ValueError('expected metadata differs')
                if any(
                    key in mapping and not _same(mapping[key], value)
                    for key, value in rule.optional_expected.items()
                ):
                    raise ValueError('optional metadata differs')
                if any(search(key) for key in mapping for search in forbidden_keys):
                    raise ValueError('forbidden key pattern present')
                if any(key in mapping for key in rule.absent):
                    raise ValueError('forbidden metadata present')
            if any(
                not any(key in mapping for mapping in mappings)
                for key in rule.required_anywhere
            ):
                raise ValueError('required setting absent everywhere')
            for name in rule.consistent:
                values = [mapping.get(name) for mapping in mappings]
                if any(
                    not isinstance(value, str) or not value.strip() for value in values
                ):
                    raise ValueError('consistent setting missing')
                if any(value != values[0] for value in values[1:]):
                    raise ValueError('inconsistent setting')
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RecursionError,
            OverflowError,
            ExpatError,
        ):
            failures.append(
                f'{rule.identity}: metadata missing, invalid or violates policy',
            )
    for contract in coverage:
        try:
            covered = {
                rule.path for rule in rules if rule.identity in contract.rule_ids
            }
            paths = _discovered_paths(root, contract.include)
            if not paths or any(
                not path.resolve().is_relative_to(root.resolve())
                or not path.is_file()
                or path.relative_to(root).as_posix() not in covered
                for path in paths
            ):
                raise ValueError('discovered metadata lacks coverage')
        except (OSError, ValueError, RecursionError):
            failures.append(
                f'{contract.identity}: metadata discovery or coverage failed',
            )
    return failures


# !SECTION
