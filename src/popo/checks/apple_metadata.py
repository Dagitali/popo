"""
:mod:`popo.checks.apple_metadata` module.

Inspect literal Apple metadata inputs without native tools or value disclosure.
"""

import plistlib
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

from ..config.apple_metadata import AppleRule
from ._openstep import parse_project
from ._xcode import configuration_settings
from ._xcode import mapping as _mapping

# SECTION: PROTECTED FUNCTIONS


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
    return configuration_settings(project, rule.target, rule.configurations)


# !SECTION


# SECTION: FUNCTIONS


def validate(
    root: Path,
    rules: tuple[AppleRule, ...],
) -> list[str]:
    """
    Validate independent metadata contracts and continue after input failures.

    Parameters
    ----------
    root : pathlib.Path
        Repository root confining every input, including symlink resolution.
    rules : tuple[AppleRule, ...]
        Validated consumer selection and expectations.

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
            for mapping in mappings:
                if any(
                    key not in mapping or not _same(mapping[key], value)
                    for key, value in rule.expected.items()
                ):
                    raise ValueError('expected metadata differs')
                if any(key in mapping for key in rule.absent):
                    raise ValueError('forbidden metadata present')
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
    return failures


# !SECTION
