"""
:mod:`popo.config._common` module.

Shared configuration errors, TOML reading, and value validation.
"""

import tomllib
from pathlib import Path
from typing import cast

# SECTION: ERRORS


class ConfigurationError(ValueError):
    """Raised when popo configuration is invalid."""


# !SECTION


# SECTION: FUNCTIONS


def read_popo(
    root: Path,
) -> dict[str, object]:
    """
    Read the optional root metadata and require tool.popo to be a table.

    Parameters
    ----------
    root : pathlib.Path
        Repository directory containing optional pyproject.toml metadata.

    Returns
    -------
    dict[str, object]
        Consumer settings, or an empty dictionary when absent.

    Raises
    ------
    ConfigurationError
        If root TOML is invalid or tool or tool.popo is not a table.
    OSError, UnicodeError
        If existing metadata cannot be read or decoded as UTF-8.
    """
    path = root / 'pyproject.toml'
    document: dict[str, object] = {}
    if path.is_file():
        try:
            document = tomllib.loads(path.read_text(encoding='utf-8'))
        except tomllib.TOMLDecodeError as error:
            raise ConfigurationError(f'{path}: invalid TOML: {error}') from error
    tool = require_table(document.get('tool', {}), name='tool')
    return require_table(tool.get('popo', {}), name='tool.popo')


def read_string(
    table: dict[str, object],
    key: str,
    *,
    default: str,
) -> str:
    """
    Read a nonempty string, using the default only when the key is absent.

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
        If value is not a dictionary.
    """
    if not isinstance(value, dict):
        raise ConfigurationError(f'{name} must be a TOML table')
    return cast(dict[str, object], value)


# !SECTION
