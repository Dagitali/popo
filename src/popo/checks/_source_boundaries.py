"""
:mod:`popo.checks._source_boundaries` module.

Share dependency facts, symbol reporting and architecture input discovery.
"""

from collections.abc import Collection, Iterable
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
    ParsedSource retains the language's native AST or masked lexical text.
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
        """Return imports before symbols; leave target sets unchanged."""
        ...

    def parse(
        self,
        source: str,
        relative: str,
    ) -> tuple[ParsedSource | None, list[str]]:
        """Return parsed input or redacted parse diagnostics."""
        ...

    def targets(
        self,
        path: Path,
        root: Path,
        source: ParsedSource | None,
    ) -> set[str]:
        """Index owned targets from parsed input or paths when sufficient."""
        ...


# !SECTION


# SECTION: FUNCTIONS


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
        Parse each readable file once; skip failed parses during inspection.

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
    targets_by_layer = {
        name: {
            target
            for path in paths
            for target in analyzer.targets(path, config.root, sources.get(path))
        }
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
