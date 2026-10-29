"""
:mod:`popo.checks._python_syntax` module.

Parse Python syntax and locate documentation without consumer-code execution.
"""

import ast
from collections.abc import Iterable, Iterator

# SECTION: TYPE ALIASES


# These are the only native syntax nodes that can own Python docstrings.
# Swift uses a single tree_sitter.Node type, so it needs no matching union.
type DocstringOwner = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


# !SECTION


# SECTION: FUNCTIONS


def documentation_lines(
    owners: Iterable[DocstringOwner],
) -> tuple[int, ...]:
    """
    Collect documentation lines from caller-selected syntax nodes.

    Parameters
    ----------
    owners : collections.abc.Iterable[DocstringOwner]
        Native module, class or callable nodes in any order, including repeats.
        The caller retains responsibility for declaration discovery and scope.

    Returns
    -------
    tuple[int, ...]
        Sorted unique one-based lines, including delimiters and empty
        docstrings. Other string literals do not supply documentation spans.

    Notes
    -----
    Use uncleaned native docstring identity and original AST locations.
    No source is parsed again, imported or executed; nodes are not modified.
    """
    lines: set[int] = set()
    for owner in owners:
        if ast.get_docstring(owner, clean=False) is not None:
            doc = owner.body[0]
            lines.update(range(doc.lineno, (doc.end_lineno or doc.lineno) + 1))
    return tuple(sorted(lines))


def nodes(
    root: ast.AST,
) -> Iterator[ast.AST]:
    """
    Traverse native syntax without executing or modifying consumer code.

    Parameters
    ----------
    root : ast.AST
        Parsed subtree whose root is included in traversal.

    Yields
    ------
    ast.AST
        Root and descendants in the standard-library breadth-first order.
        Callers retain responsibility for declaration and scope filtering.

    Notes
    -----
    Preserve ast.walk semantics for existing declaration and boundary checks.
    Unlike Swift traversal, Python visits all AST children, including f-string
    expressions. Comments are not AST nodes; literal text is not reparsed as
    executable syntax.
    """
    yield from ast.walk(root)


def parse(
    source: str,
) -> ast.Module:
    """
    Parse Python source for read-only declaration and boundary analysis.

    Parameters
    ----------
    source : str
        Decoded source text; consumer modules and defaults are not executed.
        No consumer files are read or written.

    Returns
    -------
    ast.Module
        Native syntax with original AST locations for language-specific
        analysis. No wrapper replaces Python's existing AST node types.

    Raises
    ------
    SyntaxError
        Python syntax is invalid. Callers decide how to report it and whether
        file-limit checks run before returning its diagnostic.
    UnicodeEncodeError
        Direct text contains code points that cannot be encoded as UTF-8.

    Notes
    -----
    Parsing does not import consumer modules, resolve types or evaluate runtime
    behavior. Invalid Python raises SyntaxError rather than yielding recovery
    nodes. Documentation locations are collected separately from native AST
    owners through documentation_lines; source masking is unnecessary.
    """
    return ast.parse(source)


def syntax_findings(
    error: SyntaxError,
    relative: str,
) -> list[str]:
    """
    Format a Python parse failure without source text or exception messages.

    Parameters
    ----------
    error : SyntaxError
        Native parser failure; only its one-based line number is reported.
    relative : str
        Caller-supplied repository-relative diagnostic filename.

    Returns
    -------
    list[str]
        One location-only finding, shared by source and boundary checking.

    Notes
    -----
    Python parsing raises instead of returning recovery nodes. This formatter
    serves that exception contract; Swift retains recoverable syntax and does
    not use an equivalent parse-exception formatter.
    """
    return [f'{relative}:{error.lineno}: invalid Python source']


# !SECTION
