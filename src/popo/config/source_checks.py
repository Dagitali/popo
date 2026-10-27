"""
:mod:`popo.config.source_checks` module.

Load opt-in source-convention and redacted-log policies.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ._common import ConfigurationError, read_popo, read_strings, require_table

# SECTION: CONSTANTS


SOURCE_DEFAULTS: dict[str, object] = {
    'documentation-width': 79,
    'max-file-lines': 1000,
    'parameter-lines': False,
    'parameter-docs': False,
    'return-docs': False,
    'raises-docs': False,
    'file-overviews': False,
    'declaration-docs': False,
    'source-guide': '',
}
DOMAINS: dict[str, dict[str, object]] = {
    'python-source': SOURCE_DEFAULTS
    | {'annotations': False, 'alphabetical-methods': False},
    'swift-source': SOURCE_DEFAULTS
    | {
        'member-docs': False,
        'file-overviews': True,
        'declaration-docs': True,
        'declaration-spacing': True,
    },
    'logs': {'patterns': {}},
}


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class SourceCheckConfig:
    """
    Store validated consumer policy without inspecting source files.

    Attributes
    ----------
    root : pathlib.Path
        Resolved consumer repository boundary.
    domain : str
        Explicit opt-in policy table name.
    include, exclude : tuple[str, ...]
        Root-relative glob patterns and exclusion patterns.
    settings : dict[str, object]
        Validated domain options; validators do not mutate this mapping.
    """

    root: Path
    domain: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    settings: dict[str, object]


# !SECTION


# SECTION: FUNCTIONS


def load_source_check(
    root: Path,
    domain: str,
) -> SourceCheckConfig:
    """
    Load an explicitly configured source or log policy.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root containing standalone or embedded policy.
    domain : str
        Supported policy name from ``DOMAINS``.

    Returns
    -------
    SourceCheckConfig
        Strictly validated settings and confined discovery patterns.

    Raises
    ------
    ConfigurationError
        Missing policy, unknown settings, invalid types or unsafe paths.
    OSError, UnicodeError
        Configuration cannot be read or decoded.
    """
    defaults = DOMAINS[domain]
    table = require_table(read_popo(root).get(domain), name=domain)
    unknown = table.keys() - defaults.keys() - {'include', 'exclude'}
    if unknown:
        raise ConfigurationError(f'{domain}: unknown settings: {sorted(unknown)}')
    include = read_strings(table.get('include', []), f'{domain}.include')
    exclude = read_strings(table.get('exclude', []), f'{domain}.exclude')
    if not include:
        raise ConfigurationError(f'{domain}.include must not be empty')
    for pattern in (*include, *exclude):
        if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
            raise ConfigurationError(f'{domain}: patterns must stay inside root')
    settings = defaults | {key: table[key] for key in defaults if key in table}
    for key, default in defaults.items():
        value = settings[key]
        if type(value) is not type(default):
            raise ConfigurationError(f'{domain}.{key}: invalid setting type')
        if type(value) is int and value < 1:
            raise ConfigurationError(f'{domain}.{key}: expected a positive integer')
    if 'source-guide' in settings:
        guide = Path(str(settings['source-guide']))
        if guide.is_absolute() or '..' in guide.parts:
            raise ConfigurationError('source-guide must stay inside root')
    if domain == 'logs':
        patterns = require_table(settings['patterns'], name='logs.patterns')
        if not patterns or any(
            not re.fullmatch(r'[A-Za-z0-9_.-]+', key)
            or not isinstance(value, str)
            or not value.strip()
            or value.splitlines() != [value]
            for key, value in patterns.items()
        ):
            raise ConfigurationError(
                'logs.patterns requires named nonempty single-line literals',
            )
    return SourceCheckConfig(root.resolve(), domain, include, exclude, settings)


# !SECTION
