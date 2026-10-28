"""
:mod:`popo.checks._source_boundaries` module.

Share dependency facts, boundary reporting and architecture input discovery.
"""

from collections.abc import Collection, Iterable
from itertools import chain
from pathlib import Path
from typing import NamedTuple, Protocol

from popo.config.source_boundaries import BoundaryConfig, BoundaryLayer

from ._source_inputs import discover, read_source

# SECTION: NAMED TUPLES


class ImportReference(NamedTuple):
    """
    Store a statically recognized import and its diagnostic location.

    Attributes
    ----------
    line : int
        One-based source line containing the imported name.
    target : str
        Imported module or qualified name; empty for unresolved Python imports.
    alias : str
        Locally bound Python name, or empty when alias analysis is unused.
    """

    line: int
    target: str
    alias: str = ''


class SymbolReference(NamedTuple):
    """
    Store a statically recognized symbol candidate and its location.

    Attributes
    ----------
    line : int
        One-based source line containing the candidate reference.
    name : str
        Native spelling or expanded Python alias, compared case-sensitively.
        Recognition does not prove runtime binding or dependency ownership.
    """

    line: int
    name: str


# !SECTION


# SECTION: FUNCTIONS


def boundary_sources(
    config: BoundaryConfig,
) -> tuple[dict[str, list[Path]], dict[Path, str], list[str]]:
    """
    Return layer selections, readable source texts and redacted failures.

    Parameters
    ----------
    config : BoundaryConfig
        Validated selections and directional layer references.

    Returns
    -------
    tuple[dict[str, list[Path]], dict[Path, str], list[str]]
        Layer selections, readable source texts, and redacted failures.
    """
    selections: dict[str, list[Path]] = {}
    sources: dict[Path, str] = {}
    failures: list[str] = []
    inspected: set[Path] = set()
    for layer in config.layers:
        paths, errors = discover(layer.inputs)
        failures.extend(f'{layer.name}: {error}' for error in errors)
        selections[layer.name] = paths
        for path in paths:
            if path in inspected:
                continue
            inspected.add(path)
            source, errors = read_source(path, config.root)
            failures.extend(errors)
            if source is not None:
                sources[path] = source
    return selections, sources, failures


# !SECTION


# SECTION: PROTOCOLS


class BoundaryAnalyzer[ParsedSource](Protocol):
    """
    Define language analysis consumed by the shared boundary runner.

    Implementations preserve read-only inspection and redacted findings.
    ParsedSource retains the native Python AST or Swift concrete-syntax view.
    Native adapters own parsing, ownership and reference recognition.
    The shared runner controls discovery, read reuse and layer/file ordering.
    """

    def findings(
        self,
        source: ParsedSource,
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
        source : ParsedSource
            Parsed native input; implementations must not read it again.
        path : pathlib.Path
            Input path lexically inside root, used for identity and reporting.
        root : pathlib.Path
            Consumer repository root.
        layer : BoundaryLayer
            Current layer's import, dependency and explicit-symbol rules.
        forbidden_targets : set[str]
            Ownership targets from the layers prohibited by the current one.
        owned_targets : set[str]
            Current layer's targets, used when native ownership rules need it.

        Returns
        -------
        list[str]
            Location-based import findings before symbol findings. Native
            analysis selects matching rules without changing either target set.

        Notes
        -----
        Python targets are modules; Swift targets are declared type names.
        Swift excludes locally owned types from cross-layer restrictions;
        explicit forbidden symbols still apply. Python uses module import
        restrictions and does not subtract current ownership from them.
        """
        ...

    def parse(
        self,
        source: str,
        relative: str,
    ) -> tuple[ParsedSource | None, list[str]]:
        """
        Collect native syntax and redacted parse findings without execution.

        Parameters
        ----------
        source : str
            Decoded source text supplied by the shared read-only runner.
        relative : str
            Repository-relative filename for location-only parse diagnostics.

        Returns
        -------
        tuple[ParsedSource or None, list[str]]
            Native parsed input and parse findings. None skips rule evaluation
            while still allowing ownership indexing when paths are sufficient.

        Raises
        ------
        UnicodeEncodeError
            Direct text cannot be encoded as UTF-8 by the native parser.

        Notes
        -----
        Python converts SyntaxError to a diagnostic and returns no AST. Swift
        retains recoverable syntax; recovery does not prove compiler validity.
        Implementations do not execute source or invoke consumer toolchains.
        """
        ...

    def targets(
        self,
        path: Path,
        root: Path,
        source: ParsedSource | None,
    ) -> set[str]:
        """
        Index native ownership from parsed input or sufficient path identity.

        Parameters
        ----------
        path : pathlib.Path
            Selected source path lexically inside root.
        root : pathlib.Path
            Consumer root used to derive repository-relative identity.
        source : ParsedSource or None
            Available native input, or None after a read or parse failure.

        Returns
        -------
        set[str]
            Native ownership targets used for cross-layer restrictions.
            An empty set means no targets could be established for this input.

        Notes
        -----
        Python module paths establish ownership even without readable syntax.
        Swift requires parsed declarations; extensions do not establish new
        ownership. Neither implementation resolves runtime dependencies.
        """
        ...


# !SECTION


# SECTION: FUNCTIONS


def import_findings(
    imports: Iterable[ImportReference],
    layer: BoundaryLayer,
    relative: str,
    *,
    forbidden_targets: Collection[str] = (),
    allow_descendants: bool = False,
    report_unresolved: bool = False,
) -> list[str]:
    """
    Compare native imports with explicit matching and reporting policies.

    Parameters
    ----------
    imports : collections.abc.Iterable[ImportReference]
        Recognized imports in native diagnostic order, consumed once.
    layer : BoundaryLayer
        Diagnostic name and optional module allowlist. None disables allowlist
        restrictions; an empty allowlist rejects every recognized import.
    relative : str
        Repository-relative diagnostic filename.
    forbidden_targets : collections.abc.Collection[str], optional
        Imported targets owned by forbidden layers, independent of allowlists.
    allow_descendants : bool, optional
        Match dotted descendants as well as exact names, as Python requires.
        Swift uses exact module matching instead.
    report_unresolved : bool, optional
        Report empty targets as unresolved relative imports, as Python does.
        Native Swift import recognition does not emit unresolved placeholders.

    Returns
    -------
    list[str]
        At most one finding per import, preserving order and duplicates.
        Unresolved references precede forbidden-layer checks, which precede
        allowlist checks. This function does not report symbol findings.

    Notes
    -----
    Native adapters own import discovery, alias handling and applicability.
    Matching is case-sensitive; descendant matching requires a dot boundary.
    No source is read, parsed or executed and no policy collection is mutated.
    """

    def matches(
        target: str,
        names: Collection[str],
    ) -> bool:
        """Apply exact matching with an optional dotted-descendant rule."""
        return any(
            target == name or (allow_descendants and target.startswith(name + '.'))
            for name in names
        )

    failures: list[str] = []
    for reference in imports:
        target = reference.target
        location = f'{relative}:{reference.line}: {layer.name}'
        if report_unresolved and not target:
            failures.append(f'{location}: unresolved relative import')
        elif matches(target, forbidden_targets):
            failures.append(f'{location}: forbidden layer import {target}')
        elif layer.allowed_imports is not None and not matches(
            target,
            layer.allowed_imports,
        ):
            failures.append(f'{location}: forbidden import {target}')
    return failures


def symbol_findings(
    references: Iterable[SymbolReference],
    forbidden_symbols: Collection[str],
    relative: str,
    layer_name: str,
) -> list[str]:
    """
    Filter native symbol candidates and report each line/name pair once.

    Parameters
    ----------
    references : collections.abc.Iterable[SymbolReference]
        Native observations, including duplicates or expanded alias spellings.
        Input order is unrestricted; the iterable is consumed once.
    forbidden_symbols : collections.abc.Collection[str]
        Exact case-sensitive names prohibited by the current layer.
    relative : str
        Repository-relative diagnostic filename.
    layer_name : str
        Consumer-owned layer name used to label findings.

    Returns
    -------
    list[str]
        Findings sorted by line then symbol, without source excerpts.

    Notes
    -----
    Native collectors own syntax, alias expansion and masking. This function
    performs no parsing, scope resolution, source reads or consumer execution.
    """
    forbidden = set(forbidden_symbols)
    matches = {reference for reference in references if reference.name in forbidden}
    return [
        f'{relative}:{line}: {layer_name}: forbidden symbol {name}'
        for line, name in sorted(matches)
    ]


def validate_boundaries[ParsedSource](
    config: BoundaryConfig,
    analyzer: BoundaryAnalyzer[ParsedSource],
) -> list[str]:
    """
    Run confined discovery, parsing, ownership indexing and layer analysis.

    Parameters
    ----------
    config : BoundaryConfig
        Validated selections and directional layer references.
    analyzer : BoundaryAnalyzer[ParsedSource]
        Language-specific parser, ownership rules and diagnostic collector.

    Returns
    -------
    list[str]
        Read/discovery findings, then parse findings, then layer/file findings.
        Parse each readable file and index each selected path's ownership once
        per invocation. Skip failed parses during rule inspection; native path
        ownership can remain available when reading or parsing fails.

    Raises
    ------
    KeyError
        A directly constructed policy references an unknown layer.
    ValueError
        A selected path is outside the configured root.

    Notes
    -----
    Analyzer exceptions propagate. Diagnostics are redacted by the input and
    analyzer contracts; this runner neither executes code nor catches bugs.
    """
    paths_by_layer, texts, failures = boundary_sources(config)
    sources: dict[Path, ParsedSource] = {}
    for path, text in texts.items():
        source, errors = analyzer.parse(text, path.relative_to(config.root).as_posix())
        failures.extend(errors)
        if source is not None:
            sources[path] = source
    targets_by_path = {
        path: analyzer.targets(path, config.root, sources.get(path))
        for path in dict.fromkeys(chain.from_iterable(paths_by_layer.values()))
    }
    targets_by_layer = {
        name: {target for path in paths for target in targets_by_path[path]}
        for name, paths in paths_by_layer.items()
    }
    for layer in config.layers:
        forbidden_targets = {
            target
            for name in layer.forbidden_layers
            for target in targets_by_layer[name]
        }
        for path in paths_by_layer[layer.name]:
            if path in sources:
                failures.extend(
                    analyzer.findings(
                        sources[path],
                        path,
                        config.root,
                        layer,
                        forbidden_targets,
                        targets_by_layer[layer.name],
                    ),
                )
    return failures


# !SECTION
