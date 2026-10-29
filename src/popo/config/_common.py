"""
:mod:`popo.config._common` module.

Shared configuration errors, TOML reading, and value validation.
"""

import tomllib
from datetime import date
from pathlib import Path
from typing import cast

# SECTION: ERRORS


class ConfigurationError(ValueError):
    """
    Signal invalid consumer configuration as a :exc:`ValueError` subtype.

    Notes
    -----
    Loaders use this exception for invalid TOML, table structure, setting
    types, and policy values. The inherited :exc:`ValueError` constructor
    accepts the error message. Configuration loading does not wrap filesystem
    or decoding errors in this class; those propagate separately. CLI handlers
    catch this exception and return a reported configuration failure.
    """


# !SECTION


# SECTION: FUNCTIONS


def configuration_path(
    root: Path,
) -> Path:
    """Select standalone consumer policy before Python project metadata.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository root.

    Returns
    -------
    pathlib.Path
        Existing or symlinked ``popo.toml``, otherwise ``pyproject.toml``.
        A dangling standalone symlink remains selected so reading fails rather
        than silently falling back. Selection never merges or creates files.
    """
    standalone = root / 'popo.toml'
    return (
        standalone
        if standalone.exists() or standalone.is_symlink()
        else root / 'pyproject.toml'
    )


def parse_iso_date(
    value: str,
) -> date:
    """
    Parse a valid calendar date in canonical YYYY-MM-DD form.

    Parameters
    ----------
    value : str
        Date text without surrounding whitespace or alternative ISO syntax.

    Returns
    -------
    datetime.date
        Parsed calendar date, without applying expiry or timezone policy.

    Raises
    ------
    ValueError
        The date is impossible or its text is not canonical YYYY-MM-DD.
        Compact dates, week dates and surrounding whitespace are rejected.

    Notes
    -----
    Configuration loaders retain responsibility for field types and their
    domain-specific diagnostics. This helper reads no files and does not
    decide whether a valid date is past, present or future.
    """
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('expected canonical YYYY-MM-DD date')
    return parsed


def read_patterns(
    value: object,
    name: str,
    *,
    required: bool = True,
) -> tuple[str, ...]:
    """
    Validate root-relative input patterns without touching the filesystem.

    Parameters
    ----------
    value : object
        Candidate list of unique nonempty glob strings.
    name : str
        Setting identifier included in configuration diagnostics.
    required : bool, optional
        Reject empty lists when true; defaults to true.

    Returns
    -------
    tuple[str, ...]
        Ordered patterns without absolute paths or parent traversal.

    Raises
    ------
    ConfigurationError
        Values are malformed, required patterns are empty or paths escape.
    """
    patterns = read_strings(value, name)
    if required and not patterns:
        raise ConfigurationError(f'{name} must not be empty')
    if any(Path(item).is_absolute() or '..' in Path(item).parts for item in patterns):
        raise ConfigurationError(f'{name} must stay inside the selected root')
    return patterns


def read_popo(
    root: Path,
) -> dict[str, object]:
    """
    Read standalone policy or optional Python metadata without merging.

    Parameters
    ----------
    root : pathlib.Path
        Repository containing optional popo.toml or pyproject.toml policy.

    Returns
    -------
    dict[str, object]
        Consumer settings, or an empty dictionary when absent.

    Raises
    ------
    ConfigurationError
        If selected TOML is invalid, or Python metadata contains a non-table
        tool or tool.popo value. Standalone policy is returned at its root.
    OSError, UnicodeError
        If selected configuration cannot be read or decoded as UTF-8.
    """
    path = configuration_path(root)
    document: dict[str, object] = {}
    if path.exists() or path.is_symlink():
        try:
            document = tomllib.loads(path.read_text(encoding='utf-8'))
        except tomllib.TOMLDecodeError as error:
            raise ConfigurationError(f'{path}: invalid TOML: {error}') from error
    if path.name == 'popo.toml':
        return document
    tool = require_table(document.get('tool', {}), name='tool')
    return require_table(tool.get('popo', {}), name='tool.popo')


def read_string(
    table: dict[str, object],
    key: str,
    *,
    default: str,
) -> str:
    """
    Read a nonempty string, using ``default`` only when ``key`` is absent.

    Parameters
    ----------
    table : dict[str, object]
        Configuration table to inspect without mutation.
    key : str
        Setting name, also used in failure diagnostics.
    default : str
        Value to validate and return if the key is absent.

    Returns
    -------
    str
        Nonempty setting or default, without stripping whitespace.

    Raises
    ------
    ConfigurationError
        If the selected value is not a string or is empty.
    """
    value = table.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f'{key} must be a non-empty string')
    return value


def read_strings(
    value: object,
    name: str,
    *,
    unique: bool = True,
) -> tuple[str, ...]:
    """
    Require nonempty strings in an array, optionally rejecting duplicates.

    Parameters
    ----------
    value : object
        Candidate configuration array; an empty array is permitted.
    name : str
        Setting name used in failure diagnostics.
    unique : bool, optional
        Reject duplicate values by default. Disable for policies that allow
        repeated discovery patterns or references.

    Returns
    -------
    tuple[str, ...]
        Values in declaration order without stripping whitespace or mutation.

    Raises
    ------
    ConfigurationError
        If the value is not an array of nonblank strings or contains duplicates
        when uniqueness is required. Reject typos instead of coercing values.
    """
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ConfigurationError(f'{name} must be an array of nonempty strings')
    result = tuple(cast(list[str], value))
    if unique and len(set(result)) != len(result):
        raise ConfigurationError(f'{name} contains duplicates')
    return result


def require_table(
    value: object,
    *,
    name: str,
) -> dict[str, object]:
    """
    Require a configuration table without copying or validating its entries.

    Parameters
    ----------
    value : object
        Candidate TOML table.
    name : str
        Table name used to label failure diagnostics.

    Returns
    -------
    dict[str, object]
        The original dictionary, with its type narrowed for callers.

    Raises
    ------
    ConfigurationError
        If ``value`` is not a dictionary.
    """
    if not isinstance(value, dict):
        raise ConfigurationError(f'{name} must be a TOML table')
    return cast(dict[str, object], value)


# !SECTION
