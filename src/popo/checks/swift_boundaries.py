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
    import_findings,
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

        Parameters
        ----------
        source : ParsedSwiftSource
            Parsed Swift syntax view used for native boundary observations.
        path : Path
            Source path inside root, used to label boundary diagnostics.
        root : Path
            Consumer repository root used to resolve and label input paths.
        layer : BoundaryLayer
            Boundary layer supplying import and symbol restrictions.
        forbidden_targets : set[str]
            Ownership targets belonging to forbidden layers.
        owned_targets : set[str]
            Ownership targets belonging to the current layer.

        Returns
        -------
        list[str]
            Ordered diagnostics for the native source and configured boundary
            rules.

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

        Parameters
        ----------
        source : str
            Decoded input text to inspect without executing it.
        relative : str
            Repository-relative path used in diagnostics or input selection.

        Returns
        -------
        tuple[ParsedSwiftSource, list[str]]
            Recovery-capable Swift syntax view and an empty parse-diagnostic
            list.

        Raises
        ------
        UnicodeEncodeError

            If the supplied text cannot be encoded for the native parser.

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

        Parameters
        ----------
        path : Path
            Source path accepted for analyzer parity; not used for Swift
            ownership.
        root : Path
            Repository root accepted for analyzer parity; not used for Swift
            ownership.
        source : ParsedSwiftSource | None
            Parsed Swift syntax view, or None when no source is available.

        Returns
        -------
        set[str]
            Declared nominal/type-alias ownership names; empty without parsed
            source. Extensions do not establish ownership.

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
    """
    Evaluate native imports using shared boundary reporting.

    Parameters
    ----------
    imports : list[ImportReference]
        Native import observations in established reporting order.
    layer : BoundaryLayer
        Current layer's diagnostic name and optional import allowlist.
    relative : str
        Repository-relative diagnostic filename.

    Returns
    -------
    list[str]
        Import findings in observation order, without deduplication.

    Notes
    -----
    Swift compares module names exactly. Forbidden-layer type ownership is
    evaluated through symbol rules rather than import-module restrictions.
    Native collection remains separate; no dependency resolution is performed.
    """
    return import_findings(
        imports,
        layer,
        relative,
    )


def _imports(
    source: ParsedSwiftSource,
) -> list[ImportReference]:
    """
    Collect native import observations without executing consumer code.

    Parameters
    ----------
    source : ParsedSwiftSource
        Native syntax view with comment/literal contents shielded.

    Returns
    -------
    list[ImportReference]
        Imports in native source order, retaining duplicates. Attributed and
        selective forms retain module names and source lines. Alias fields
        remain empty because this checker does not resolve Swift aliases.

    Notes
    -----
    Native spans recognize same-line and attributed imports without treating
    comments, strings or regex contents as declarations. Imported members do
    not replace the module name used for allowlist checks.
    """
    return [
        ImportReference(
            name.start_point.row + 1,
            (name.text or b'').decode('utf-8').split('.')[0].strip('`'),
        )
        for node in nodes(source.root)
        if node.type == 'import_declaration'
        for name in node.named_children
        if name.type == 'identifier'
    ]


def _source_findings(
    source: ParsedSwiftSource,
    layer: BoundaryLayer,
    forbidden_symbols: set[str],
    relative: str,
) -> list[str]:
    """
    Collect import findings before symbol findings for one parsed source.

    Parameters
    ----------
    source : ParsedSwiftSource
        Native syntax for imports and masked text for symbol collection.
    layer : BoundaryLayer
        Consumer-owned import and explicit-symbol restrictions.
    forbidden_symbols : set[str]
        Combined explicit symbols and forbidden-layer type names, after local
        ownership exclusions. These are symbol restrictions, not module names.
    relative : str
        Repository-relative filename for diagnostics.

    Returns
    -------
    list[str]
        Import findings in native observation order, then symbol findings
        sorted by line/name. No source is read, parsed again or executed.

    Notes
    -----
    Import allowlists match exact modules; symbol rules use masked tokens.
    An absent allowlist skips native import collection, while an empty one
    rejects every import. Symbol analysis remains independent of that choice.
    Forbidden-layer type names have already been combined with explicit
    symbols by the adapter, preserving locally owned type exclusions.
    """
    return [
        *_import_findings(
            _imports(source) if layer.allowed_imports is not None else [],
            layer,
            relative,
        ),
        *_symbol_findings(source.code, forbidden_symbols, relative, layer.name),
    ]


def _symbol_findings(
    code: str,
    forbidden_symbols: Collection[str],
    relative: str,
    layer_name: str,
) -> list[str]:
    """
    Report forbidden native symbol observations in stable location order.

    Parameters
    ----------
    code : str
        Position-preserving Swift text with comments, strings and regex
        literals masked before whole-identifier matching.
    forbidden_symbols : collections.abc.Collection[str]
        Explicit symbols combined with forbidden-layer type names after
        locally owned types are excluded from cross-layer restrictions.
    relative : str
        Repository-relative diagnostic filename.
    layer_name : str
        Consumer-owned layer name used to label findings.

    Returns
    -------
    list[str]
        One finding per matching line/configured-symbol pair, sorted by line
        then symbol. Matching is exact and case-sensitive; source excerpts
        and duplicate observations are excluded from reporting.

    Notes
    -----
    Match whole identifier tokens, including import tokens, without dotted
    alias expansion. Lexical matches do not resolve scopes or runtime bindings.
    Native candidate collection stays in _symbols; shared symbol_findings
    owns restriction filtering, deduplication and diagnostic order.
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
