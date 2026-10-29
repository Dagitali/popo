"""
:mod:`popo.checks.python_boundaries` module.

Inspect Python import and symbol boundaries through static AST analysis.
"""

import ast
from collections.abc import Collection, Iterator
from pathlib import Path

from popo.config.source_boundaries import BoundaryConfig, BoundaryLayer

from ._python_syntax import nodes, syntax_findings
from ._python_syntax import parse as parse_syntax
from ._source_boundaries import (
    ImportReference,
    SymbolReference,
    import_findings,
    symbol_findings,
    validate_boundaries,
)

# SECTION: PROTECTED CLASSES


class _PythonBoundaryAnalyzer:
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
        source: ast.Module,
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
        source : ast.Module
            Parsed Python module whose imports and symbols are inspected.
        path : Path
            Input path inspected by the operation.
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
        Python applies forbidden module targets to imports and keeps explicit
        symbol restrictions independent of ownership. owned_targets is unused.
        """
        return _source_findings(
            source,
            _module(path, root),
            path.stem == '__init__',
            layer,
            forbidden_targets,
            path.relative_to(root).as_posix(),
        )

    @staticmethod
    def parse(
        source: str,
        relative: str,
    ) -> tuple[ast.Module | None, list[str]]:
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
        tuple[ast.Module | None, list[str]]
            Parsed Python module and no findings, or None and redacted syntax
            diagnostics.

        Raises
        ------
        UnicodeError
            If the supplied text cannot be encoded for the native parser.

        Notes
        -----
        Python converts SyntaxError to a redacted diagnostic and returns None.
        Other parser exceptions propagate under the native syntax contract.
        """
        try:
            return parse_syntax(source), []
        except SyntaxError as error:
            return None, syntax_findings(error, relative)

    @staticmethod
    def targets(
        path: Path,
        root: Path,
        source: ast.Module | None,
    ) -> set[str]:
        """
        Index native ownership from parsed input or sufficient path identity.

        Parameters
        ----------
        path : Path
            Input path inspected by the operation.
        root : Path
            Consumer repository root used to resolve and label input paths.
        source : ast.Module | None
            Parsed Python module, or None after a read or parse failure.

        Returns
        -------
        set[str]
            Native ownership targets available from the supplied input.

        Notes
        -----
        Python needs only path identity, including after read/parse failure.
        source remains unused because module ownership is path-derived.
        """
        return _targets(path, root)


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _import_findings(
    imports: list[ImportReference],
    layer: BoundaryLayer,
    forbidden_targets: set[str],
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
    forbidden_targets : set[str]
        Module names owned by layers prohibited by the current one.
    relative : str
        Repository-relative diagnostic filename.

    Returns
    -------
    list[str]
        Import findings in observation order, without deduplication.

    Notes
    -----
    Python reports unresolved relative imports, checks forbidden-layer
    modules before allowlists and permits configured dotted descendants.
    Native collection remains separate; no dependency resolution is performed.
    """
    return import_findings(
        imports,
        layer,
        relative,
        forbidden_targets=forbidden_targets,
        allow_descendants=True,
        report_unresolved=True,
    )


def _imports(
    source: ast.AST,
    module: str,
    package: bool,
) -> list[ImportReference]:
    """
    Collect native import observations without executing consumer code.

    Parameters
    ----------
    source : ast.AST
        Parsed Python source, including nested and conditional imports.
    module : str
        Dotted module identity derived from the repository-relative path.
    package : bool
        Whether source belongs to an __init__.py package module.

    Returns
    -------
    list[ImportReference]
        Imports sorted by line, target and alias, retaining duplicates.
        Relative imports use module/package identity; unresolved relative
        imports have empty targets and aliases. Aliases describe local
        bindings, not scope-aware resolution.

    Notes
    -----
    Native AST nodes retain dotted imports, from-import members and aliases.
    Dynamic imports and runtime module lookup are not evaluated.
    """
    imports: list[ImportReference] = []
    for node in nodes(source):
        if isinstance(node, ast.Import):
            imports.extend(
                ImportReference(
                    node.lineno,
                    item.name,
                    item.asname or item.name.split('.')[0],
                )
                for item in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ''
            if node.level:
                parts = module.split('.') if package else module.split('.')[:-1]
                if node.level > len(parts):
                    imports.append(ImportReference(node.lineno, '', ''))
                    continue
                prefix = '.'.join(
                    [*parts[: len(parts) - node.level + 1], *filter(None, [prefix])],
                )
            imports.extend(
                ImportReference(
                    node.lineno,
                    f'{prefix}.{item.name}'.strip('.'),
                    item.asname or item.name,
                )
                for item in node.names
            )
    return sorted(imports)


def _module(
    path: Path,
    root: Path,
) -> str:
    """
    Derive dotted Python module identity from a repository-relative path.

    Parameters
    ----------
    path : pathlib.Path
        Selected Python source path; existence and syntax are not inspected.
    root : pathlib.Path
        Consumer root used for lexical relative-path conversion.

    Returns
    -------
    str
        Dotted identity after removing the suffix, a leading src directory
        and a final __init__ component. A root src.py keeps its module name;
        a root __init__.py yields an empty identity.

    Raises
    ------
    ValueError
        The path is lexically outside root.

    Notes
    -----
    Alternate source roots, installed packages and runtime imports are not
    resolved. Swift ownership uses declared type names rather than filenames,
    so it does not require an equivalent path-to-module helper.
    """
    parts = list(path.relative_to(root).with_suffix('').parts)
    if len(parts) > 1 and parts[0] == 'src':
        parts.pop(0)
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join(parts)


def _source_findings(
    source: ast.AST,
    module: str,
    package: bool,
    layer: BoundaryLayer,
    forbidden_targets: set[str],
    relative: str,
) -> list[str]:
    """
    Collect import findings before symbol findings for one parsed source.

    Parameters
    ----------
    source : ast.AST
        Parsed Python source reused for import and symbol collection.
    module : str
        Dotted module identity for resolving relative imports.
    package : bool
        Whether the source is an __init__.py package module.
    layer : BoundaryLayer
        Consumer-owned import and explicit-symbol restrictions.
    forbidden_targets : set[str]
        Module names owned by forbidden layers, applied to import rules.
    relative : str
        Repository-relative filename for diagnostics.

    Returns
    -------
    list[str]
        Import findings in native observation order, then symbol findings
        sorted by line/name. No source is read, parsed again or executed.

    Notes
    -----
    Relative imports resolve using the supplied module/package identity.
    Explicit symbols remain independent of module ownership; alias expansion
    does not establish runtime binding or local scope resolution.
    """
    imports = _imports(source, module, package)
    return [
        *_import_findings(imports, layer, forbidden_targets, relative),
        *_symbol_findings(
            source,
            imports,
            layer.forbidden_symbols,
            relative,
            layer.name,
        ),
    ]


def _symbol_findings(
    tree: ast.AST,
    imports: list[ImportReference],
    forbidden_symbols: Collection[str],
    relative: str,
    layer_name: str,
) -> list[str]:
    """
    Report forbidden native symbol observations in stable location order.

    Parameters
    ----------
    tree : ast.AST
        Parsed Python source reused for name and dotted-attribute inspection.
    imports : list[ImportReference]
        Recognized imports supplying conservative local alias expansion.
    forbidden_symbols : collections.abc.Collection[str]
        Explicit configured symbols, independent of module ownership.
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
    Match original names and dotted attributes as well as expanded aliases.
    Local shadows, re-exports and runtime bindings remain unresolved. Import
    declarations alone do not supply symbol observations.
    Native candidate collection stays in _symbols; shared symbol_findings
    owns restriction filtering, deduplication and diagnostic order.
    """
    return symbol_findings(
        _symbols(tree, imports),
        forbidden_symbols,
        relative,
        layer_name,
    )


def _symbols(
    tree: ast.AST,
    imports: list[ImportReference],
) -> Iterator[SymbolReference]:
    """
    Collect native symbol candidates without resolving runtime bindings.

    Parameters
    ----------
    tree : ast.AST
        Parsed Python source; comments and literal text are not reparsed.
    imports : list[ImportReference]
        Recognized imports used for conservative local alias expansion.

    Yields
    ------
    SymbolReference
        Names and dotted attributes with original and expanded spellings.
        Duplicate candidates are retained for shared filtering/reporting.

    Notes
    -----
    Local shadows, re-exports and runtime bindings are not resolved. Unlike
    Swift token matching, import declarations alone do not yield references.
    """
    aliases = {item.alias: item.target for item in imports}
    for node in nodes(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.asname is None:
                    head = item.name.split('.')[0]
                    aliases[head] = head
    for node in nodes(tree):
        if not isinstance(node, (ast.Name, ast.Attribute)):
            continue
        name = node.id if isinstance(node, ast.Name) else ast.unparse(node)
        head, separator, tail = name.partition('.')
        expanded = aliases.get(head, head) + separator + tail
        yield SymbolReference(node.lineno, name)
        yield SymbolReference(node.lineno, expanded)


def _targets(
    path: Path,
    root: Path,
) -> set[str]:
    """
    Collect ownership targets using the language's native identity rules.

    Parameters
    ----------
    path : pathlib.Path
        Selected Python source path, including unreadable or invalid files.
    root : pathlib.Path
        Consumer root used to derive repository-relative module identity.

    Returns
    -------
    set[str]
        One dotted module name, stripping a leading src directory and a final
        __init__ component. A root __init__.py retains the empty module name.

    Raises
    ------
    ValueError
        The path is lexically outside root.

    Notes
    -----
    Ownership does not require parsed syntax, unlike Swift declared types.
    Alternate source roots and installed-package resolution are not inferred.
    """
    return {_module(path, root)}


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: BoundaryConfig,
) -> list[str]:
    """
    Validate Python import-layer and explicit symbol restrictions offline.

    Parameters
    ----------
    config : BoundaryConfig
        Validated layers with confined source selections and import rules.

    Returns
    -------
    list[str]
        Discovery and read findings first, then boundary findings in layer
        order and sorted file order, with imports before symbols per file.
        Python syntax findings, when applicable, precede boundary findings.
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

    Map repository paths, optionally beneath src, to dotted module names.
    Relative imports resolve against their containing package. Import rules
    permit a configured module and its descendants. Forbidden layers apply to
    imported modules, including imports inside functions and conditional
    branches. Explicit forbidden symbols match names and dotted
    attributes, expanding import aliases conservatively; local shadowing is
    not resolved. Strings and comments are ignored. Dynamic imports, alternate
    package roots, re-export chains and runtime dependency resolution are not
    evaluated. Invalid syntax and unresolved relative imports fail explicitly.
    """
    return validate_boundaries(config, _PythonBoundaryAnalyzer())


# !SECTION
