"""
:mod:`popo.config.source_boundaries` module.

Load shared consumer layers and directional import/symbol restrictions.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ._common import (
    ConfigurationError,
    read_patterns,
    read_popo,
    read_strings,
    require_table,
)
from .source_checks import SourceCheckConfig

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class BoundaryLayer:
    """
    Describe one layer's selection and forbidden upward dependencies.

    Attributes
    ----------
    name : str
        Unique diagnostic identifier, independent of consumer folder names.
    inputs : SourceCheckConfig
        Confined file selection with global exclusions.
    allowed_imports : tuple[str, ...] or None
        Permitted modules, or None when import restrictions are disabled.
    forbidden_layers, forbidden_symbols : tuple[str, ...]
        Other layers supplying forbidden modules or type names, and explicit
        symbols prohibited even when declared locally.
    """

    name: str
    inputs: SourceCheckConfig
    allowed_imports: tuple[str, ...] | None
    forbidden_layers: tuple[str, ...]
    forbidden_symbols: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BoundaryConfig:
    """
    Store validated consumer layers in deterministic declaration order.

    Attributes
    ----------
    root : pathlib.Path
        Resolved consumer repository boundary.
    layers : tuple[BoundaryLayer, ...]
        Unique names and validated references; direct construction bypasses
        loading and does not inspect source files.
    """

    root: Path
    layers: tuple[BoundaryLayer, ...]


# !SECTION


# SECTION: FUNCTIONS


def load_boundaries_config(
    root: Path,
    domain: str,
) -> BoundaryConfig:
    """
    Load opt-in architecture restrictions without executing consumer code.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository with standalone or embedded policy.

    domain : str
        Python or Swift boundary configuration table name.

    Returns
    -------
    BoundaryConfig
        Layers with confined globs, import policy and resolved layer names.

    Raises
    ------
    ConfigurationError
        Settings, identifiers, paths or layer references are invalid.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    root = root.resolve()
    table = require_table(read_popo(root).get(domain), name=domain)
    if table.keys() - {'layers', 'exclude'}:
        raise ConfigurationError(f'unknown {domain} setting')
    exclude = read_patterns(
        table.get('exclude', []),
        f'{domain}.exclude',
        required=False,
    )
    items = table.get('layers')
    if not isinstance(items, list) or not items:
        raise ConfigurationError(f'{domain}.layers must be a nonempty array')
    layers = []
    for item in items:
        layer = require_table(item, name=f'{domain} layer')
        if layer.keys() - {
            'name',
            'include',
            'allowed-imports',
            'forbidden-layers',
            'forbidden-symbols',
        }:
            raise ConfigurationError('unknown boundary layer setting')
        name = layer.get('name')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise ConfigurationError('Boundary layer name must be a literal identifier')
        imports = (
            read_strings(layer['allowed-imports'], 'allowed-imports')
            if 'allowed-imports' in layer
            else None
        )
        symbols = read_strings(layer.get('forbidden-symbols', []), 'forbidden-symbols')
        if any(
            not re.fullmatch(
                r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*'
                if domain == 'python-boundaries'
                else r'[A-Za-z_]\w*',
                symbol,
                re.ASCII,
            )
            for symbol in (*symbols, *(imports or ()))
        ):
            raise ConfigurationError('Boundary imports and symbols must be identifiers')
        layers.append(
            BoundaryLayer(
                name,
                SourceCheckConfig(
                    root,
                    domain,
                    read_patterns(layer.get('include', []), 'layer.include'),
                    exclude,
                    {},
                ),
                imports,
                read_strings(layer.get('forbidden-layers', []), 'forbidden-layers'),
                symbols,
            ),
        )
    names = {layer.name for layer in layers}
    if len(names) != len(layers):
        raise ConfigurationError('duplicate Boundary layer name')
    for rule in layers:
        if set(rule.forbidden_layers) - names or rule.name in rule.forbidden_layers:
            raise ConfigurationError(
                'forbidden-layers requires other known layer names',
            )
    return BoundaryConfig(root, tuple(layers))


# !SECTION
