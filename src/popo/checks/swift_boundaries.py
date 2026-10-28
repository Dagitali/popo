"""
:mod:`popo.checks.swift_boundaries` module.

Inspect Swift import and symbol boundaries through concrete syntax.
"""

import re
from collections.abc import Collection, Iterator
from pathlib import Path

from popo.config.source_boundaries import BoundaryConfig, BoundaryLayer

from ._source_boundaries import (
    ImportReference,
    SymbolReference,
    symbol_findings,
    validate_boundaries,
)
from ._swift_syntax import ParsedSwiftSource, nodes
from ._swift_syntax import parse as parse_syntax

# SECTION: PROTECTED CLASSES


class _SwiftBoundaryAnalyzer:
    """
    Adapt native syntax, ownership and dependency rules to BoundaryAnalyzer.

    Notes
    -----
    Native helpers collect imports, symbols and ownership targets. The shared
    runner owns discovery, read reuse and layer/file ordering; this adapter
    neither executes source nor resolves runtime dependency bindings.
    """

    @staticmethod
    def findings(
        source: ParsedSwiftSource,
        path: Path,
        root: Path,
        layer: BoundaryLayer,
        forbidden_targets: set[str],
        owned_targets: set[str],
    ) -> list[str]:
        """
        Evaluate native boundary rules without modifying target ownership.

        Notes
        -----
        Swift excludes locally owned types from forbidden-layer targets before
        adding explicit symbols. Neither supplied target set is modified.
        """
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
    ) -> tuple[ParsedSwiftSource, list[str]]:
        """
        Collect native syntax and redacted parse findings without execution.

        Notes
        -----
        Swift retains recovery nodes and returns no parse diagnostics. Recovery
        does not establish compiler validity; parser exceptions propagate.
        """
        return parse_syntax(source), []

    @staticmethod
    def targets(
        path: Path,
        root: Path,
        source: ParsedSwiftSource | None,
    ) -> set[str]:
        """
        Index native ownership from parsed input or sufficient path identity.

        Notes
        -----
        Swift needs parsed declarations; absent source supplies no ownership.
        path and root remain unused because filenames do not establish types.
        """
        return _targets(source)


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
    syntax: ParsedSwiftSource,
) -> list[ImportReference]:
    """
    Collect Swift imports in source order from native import nodes.

    Attributed and selective imports retain the module name and its source
    line. Alias fields remain empty because this checker does not resolve
    Swift aliases. Native spans recognize same-line and attributed imports
    without treating comment, string or regex contents as declarations.
    """
    return [
        ImportReference(
            name.start_point.row + 1,
            (name.text or b'').decode('utf-8').split('.')[0].strip('`'),
        )
        for node in nodes(syntax.root)
        if node.type == 'import_declaration'
        for name in node.named_children
        if name.type == 'identifier'
    ]


def _source_findings(
    syntax: ParsedSwiftSource,
    layer: BoundaryLayer,
    forbidden_targets: set[str],
    relative: str,
) -> list[str]:
    """
    Collect Swift import findings before cross-layer symbol findings per file.

    Inspect parsed source. Forbidden targets already combine explicit symbols
    with other layers' type names after excluding locally owned type names.
    """
    return [
        *_import_findings(_imports(syntax), layer, relative),
        *_symbol_findings(syntax.code, forbidden_targets, relative, layer.name),
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
    return symbol_findings(
        _symbols(code),
        forbidden_symbols,
        relative,
        layer_name,
    )


def _symbols(
    code: str,
) -> Iterator[SymbolReference]:
    """
    Collect native symbol candidates without resolving runtime bindings.

    Parameters
    ----------
    code : str
        Swift text with comments, strings and regex literals already masked.

    Yields
    ------
    SymbolReference
        Whole identifier tokens with their one-based physical source lines.
        Duplicate candidates are retained for shared filtering/reporting.

    Notes
    -----
    Import tokens remain candidates. Unlike Python AST analysis, dotted-name
    expansion and scope resolution are not performed by this token guard.
    """
    for number, line in enumerate(code.splitlines(), start=1):
        for name in re.findall(r'\b\w+\b', line):
            yield SymbolReference(number, name)


def _targets(
    source: ParsedSwiftSource | None,
) -> set[str]:
    """
    Collect ownership targets using the language's native identity rules.

    Parameters
    ----------
    source : ParsedSwiftSource or None
        Native syntax view, or None after an input read failure.

    Returns
    -------
    set[str]
        Declared nominal/typealias names with backticks removed, excluding
        extensions. Missing source supplies an empty set, not filename-derived
        ownership. Duplicate names collapse without inferring qualified names.

    Notes
    -----
    Ownership requires parsed declarations, unlike Python module paths.
    Native traversal masks noncode; recovery does not prove compiler validity.
    No macro expansion or runtime dependency resolution is performed.
    """
    return (
        {
            (name.text or b'').decode('utf-8').strip('`')
            for node in nodes(source.root)
            if node.type
            in {
                'class_declaration',
                'protocol_declaration',
                'typealias_declaration',
            }
            and not any(child.type == 'extension' for child in node.children)
            if (name := node.child_by_field_name('name')) is not None
        }
        if source is not None
        else set()
    )


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

    Use Tree-sitter native nodes for imports and declared type ownership.
    Imports include attributed and selective forms and use exact module
    allowlists. Mask comments, strings and regex literals before symbol token
    matching. Same-line declarations are recognized; grammar recovery is not
    compiler validation. Forbidden layers supply declared type names.
    This is a conservative token guard, not semantic dependency resolution.
    Same-name types owned by the current layer are excluded from cross-layer
    restrictions; explicit forbidden symbols still apply. Nested/local names,
    regex literals, macros and conditional compilation are not resolved.
    """
    return validate_boundaries(config, _SwiftBoundaryAnalyzer())


# !SECTION
