"""
:mod:`popo.checks.swift_boundaries` module.

Inspect Swift import and symbol boundaries through lexical masking.
"""

import re
from collections.abc import Collection
from pathlib import Path

from popo.config.source_boundaries import BoundaryConfig, BoundaryLayer

from ._source_boundaries import ImportReference, validate_boundaries
from ._swift_declarations import lexical_view

# SECTION: CONSTANTS


IMPORT_PATTERN = re.compile(
    r'(?m)^[ \t]*(?:@\w+(?:\([^\n]*\))?\s+)*import\s+'
    r'(?:(?:struct|class|enum|protocol|typealias|func|let|var)\s+)?(\w+)',
)
TYPE_PATTERN = re.compile(
    r'(?m)^[ \t]*(?:(?:@\w+(?:\([^\n]*\))?|public|private|fileprivate|'
    r'internal|open|package|final|indirect|nonisolated|distributed)\s+)*'
    r'(?:struct|class|enum|actor|protocol|typealias)\s+'
    r'(?!(?:func|var|let|subscript)\b)`?(\w+)',
)


# !SECTION


# SECTION: PROTECTED CLASSES


class _SwiftBoundaryAnalyzer:
    """Adapt lexical masking, declaration ownership and Swift token rules."""

    @staticmethod
    def findings(
        source: str,
        path: Path,
        root: Path,
        layer: BoundaryLayer,
        forbidden_targets: set[str],
        owned_targets: set[str],
    ) -> list[str]:
        """Exclude locally owned types before adding explicit symbol rules."""
        forbidden_symbols = (forbidden_targets - owned_targets) | set(
            layer.forbidden_symbols,
        )
        return _source_findings(
            source,
            layer,
            forbidden_symbols,
            path.relative_to(root).as_posix(),
        )

    @staticmethod
    def parse(
        source: str,
        relative: str,
    ) -> tuple[str, list[str]]:
        """Mask comments and strings without asserting valid Swift syntax."""
        return lexical_view(source)[0], []

    @staticmethod
    def targets(
        path: Path,
        root: Path,
        source: str | None,
    ) -> set[str]:
        """Index declared types only when masked source is available."""
        return set(TYPE_PATTERN.findall(source)) if source is not None else set()


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _import_findings(
    imports: list[ImportReference],
    layer: BoundaryLayer,
    relative: str,
) -> list[str]:
    """Report Swift modules excluded by the layer's exact import allowlist."""
    failures: list[str] = []
    for reference in imports:
        line, target = reference.line, reference.target
        if layer.allowed_imports is not None and target not in layer.allowed_imports:
            failures.append(
                f'{relative}:{line}: {layer.name}: forbidden import {target}',
            )
    return failures


def _imports(
    code: str,
) -> list[ImportReference]:
    """
    Collect Swift imports in source order from lexically masked text.

    Attributed and selective imports retain the module name and its source
    line. Alias fields remain empty because this checker does not resolve
    Swift aliases. The supplied text must already have comments and strings
    masked with line positions preserved.
    """
    return [
        ImportReference(code.count('\n', 0, match.start(1)) + 1, match.group(1))
        for match in IMPORT_PATTERN.finditer(code)
    ]


def _source_findings(
    code: str,
    layer: BoundaryLayer,
    forbidden_targets: set[str],
    relative: str,
) -> list[str]:
    """
    Collect Swift import findings before cross-layer symbol findings per file.

    Inspect masked source. Forbidden targets already combine explicit symbols
    with other layers' type names after excluding locally owned type names.
    """
    return [
        *_import_findings(_imports(code), layer, relative),
        *_symbol_findings(code, forbidden_targets, relative, layer.name),
    ]


def _symbol_findings(
    code: str,
    forbidden_symbols: Collection[str],
    relative: str,
    layer_name: str,
) -> list[str]:
    """
    Report configured Swift symbols once per source line.

    Match whole identifier tokens in masked text. Deduplicate each
    (line, configured symbol) pair and sort by line/name. The supplied
    restrictions combine explicit symbols and forbidden-layer type names;
    lexical matches do not resolve scopes or runtime bindings.
    """
    failures: list[str] = []
    for number, line in enumerate(code.splitlines(), start=1):
        for symbol in sorted(
            set(re.findall(r'\b\w+\b', line)).intersection(forbidden_symbols),
        ):
            failures.append(
                f'{relative}:{number}: {layer_name}: forbidden symbol {symbol}',
            )
    return failures


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: BoundaryConfig,
) -> list[str]:
    """
    Validate Swift import and cross-layer symbol restrictions offline.

    Parameters
    ----------
    config : BoundaryConfig
        Validated layers with confined source selections and import rules.

    Returns
    -------
    list[str]
        Discovery and read findings first, then boundary findings in layer
        order and sorted file order, with imports before symbols per file.
        Empty when selected inputs satisfy the configured restrictions.
        Diagnostics include locations without source excerpts or raw errors.

    Raises
    ------
    KeyError
        A forbidden layer is absent from a directly constructed configuration.
    ValueError
        A selected path cannot be expressed relative to config.root.
        Loaded configurations satisfy these layer and confinement contracts.

    Notes
    -----
    Read confined inputs as UTF-8 once across overlapping selections. Missing,
    unsafe or unreadable inputs produce failing diagnostics; readable files
    continue through analysis. Each layer's rules apply to overlapping files.
    Import restrictions are disabled when the allowlist is absent and reject
    every recognized import when it is empty. No consumer code is executed.

    Reuse Swift masking for nested comments and ordinary/raw strings. Imports
    include attributed and selective forms and use exact module allowlists.
    Forbidden layers supply declared type names for token matching.
    This is a conservative token guard, not semantic dependency resolution.
    Same-name types owned by the current layer are excluded from cross-layer
    restrictions; explicit forbidden symbols still apply. Nested/local names,
    regex literals, macros and conditional compilation are not resolved.
    """
    return validate_boundaries(config, _SwiftBoundaryAnalyzer())


# !SECTION
