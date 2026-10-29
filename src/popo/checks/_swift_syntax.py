"""
:mod:`popo.checks._swift_syntax` module.

Parse Swift syntax and locate documentation without consumer-code execution.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import tree_sitter_swift
from tree_sitter import Language, Node, Parser

# SECTION: CONSTANTS


LANGUAGE = Language(tree_sitter_swift.language())
MASKED_KINDS = frozenset(
    {
        'comment',
        'multiline_comment',
        'line_string_literal',
        'multi_line_string_literal',
        'raw_string_literal',
        'regex_literal',
    },
)


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class ParsedSwiftSource:
    """
    Retain native syntax and a character-position-preserving inspection view.

    Attributes
    ----------
    root : tree_sitter.Node
        Source root, including recovery nodes for malformed/unsupported syntax.
        An unterminated block-comment tail is excluded from recovered code.
    source : bytes
        Original UTF-8 input; node offsets refer to these bytes.
    code : str
        Comments, strings and regex literals masked except for newlines.
        Character offsets and original line numbers remain unchanged.
    documentation : frozenset[int]
        One-based standalone triple-slash comment lines.
    line_offsets : tuple[int, ...]
        Character offsets of LF-separated line starts for byte conversion,
        followed by an unused end sentinel at len(decoded source) + 1.

    Notes
    -----
    This concrete syntax tree does not resolve types, macros, imports or
    conditional compilation. Recovery is not proof of valid Swift syntax.
    Python returns its native ast.Module directly; this record holds extra
    masking, comment and byte-position state needed by the Swift front end.
    """

    root: Node
    source: bytes
    code: str
    documentation: frozenset[int]
    line_offsets: tuple[int, ...]

    def offset(
        self,
        node: Node,
    ) -> int:
        """
        Translate a node's UTF-8 byte position to an original text offset.

        Parameters
        ----------
        node : tree_sitter.Node
            Native node from this view's original source or recovered prefix.
            Byte positions and line numbers must belong to that same input.

        Returns
        -------
        int
            Zero-based character offset of the node's start in original text.
            Non-ASCII prefixes and CRLF line endings retain original lengths.

        Raises
        ------
        IndexError
            A node from incompatible input refers beyond the line-offset table.
        UnicodeDecodeError
            Incompatible byte positions split the stored UTF-8 line prefix.

        Notes
        -----
        This converts a location without reading or reparsing source. Matching
        node provenance is a caller contract, not checked by tree identity.
        Python callers retain native AST locations without this Swift view.
        """
        row, column = node.start_point
        return self.line_offsets[row] + len(
            self.source[node.start_byte - column : node.start_byte].decode('utf-8'),
        )


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _mask(
    text: str,
) -> str:
    """
    Preserve character positions and newlines while shielding noncode.

    Parameters
    ----------
    text : str
        Original text from which a header or masked view is derived.

    Returns
    -------
    str
        Spaces replacing noncode characters, with newlines unchanged.
    """
    return ''.join('\n' if char == '\n' else ' ' for char in text)


def _source_view(
    root: Node,
    source: bytes,
) -> tuple[Node, str, tuple[Node, ...]]:
    """
    Mask native noncode spans and retain actual comment nodes in source order.

    The returned root excludes an unterminated block-comment tail that grammar
    recovery could reinterpret as code. Masking preserves character positions
    and newlines. Documentation recognition remains in documentation_lines.

    Parameters
    ----------
    root : Node
        Native Tree-sitter root corresponding to the source bytes.
    source : bytes
        UTF-8 source bytes corresponding to the native syntax root.

    Returns
    -------
    tuple[Node, str, tuple[Node, ...]]
        Usable syntax root, position-preserving masked text and comment nodes.

    Raises
    ------
    UnicodeDecodeError
        If the source is not valid UTF-8 or node spans split a character.
    """
    raw = source
    chunks: list[str] = []
    comments: list[Node] = []
    end = 0
    unclosed = -1
    for node in nodes(root):
        if node.type not in MASKED_KINDS:
            continue
        unclosed = raw.find(b'/*', end, node.start_byte)
        if unclosed >= 0:
            break
        chunks.append(raw[end : node.start_byte].decode('utf-8'))
        text = raw[node.start_byte : node.end_byte].decode('utf-8')
        if node.type == 'comment':
            comments.append(node)
        chunks.append(_mask(text))
        end = node.end_byte
    else:
        unclosed = raw.find(b'/*', end)
    if unclosed >= 0:
        # The grammar may recover an unfinished comment as operators/code.
        # Preserve lexical shielding and exclude its contents from native facts.
        chunks.append(raw[end:unclosed].decode('utf-8'))
        chunks.append(_mask(raw[unclosed:].decode('utf-8')))
        root = Parser(LANGUAGE).parse(raw[:unclosed]).root_node
        end = len(raw)
    chunks.append(raw[end:].decode('utf-8'))
    return root, ''.join(chunks), tuple(comments)


# !SECTION


# SECTION: FUNCTIONS


def documentation_lines(
    owners: Iterable[Node],
    source: bytes,
) -> tuple[int, ...]:
    """
    Collect documentation lines from caller-selected syntax nodes.

    Parameters
    ----------
    owners : collections.abc.Iterable[tree_sitter.Node]
        Native nodes in any order, including repeats. Only standalone
        triple-slash comment nodes supply documentation; other nodes do not.
    source : bytes
        Original UTF-8 source used to distinguish leading from trailing
        comments. Nodes must refer to this source or its recovered prefix.

    Returns
    -------
    tuple[int, ...]
        Sorted unique one-based documentation lines. Unlike Python docstring
        spans, Swift documentation consists of individual comment lines.

    Notes
    -----
    No source is parsed again, imported or executed; nodes are not modified.
    Select nodes through the recovered source view to exclude unterminated
    comment tails. Native byte columns require source text for prefix checks.
    """
    return tuple(
        sorted(
            {
                node.start_point.row + 1
                for node in owners
                if node.type == 'comment'
                and source.startswith(b'///', node.start_byte, node.end_byte)
                and not source[
                    node.start_byte - node.start_point.column : node.start_byte
                ]
                .decode('utf-8')
                .strip()
            },
        ),
    )


def nodes(
    root: Node,
) -> Iterator[Node]:
    """
    Traverse native syntax without executing or modifying consumer code.

    Parameters
    ----------
    root : tree_sitter.Node
        Parsed subtree whose root is included in traversal.

    Yields
    ------
    tree_sitter.Node
        Root and named descendants in depth-first source order. Comments and
        literals are leaves; their contents cannot supply declarations.

    Notes
    -----
    Unlike Python AST traversal, Tree-sitter includes comments and literal
    syntax. Do not descend into masked nodes or inspect interpolation bodies.
    Callers retain responsibility for declaration and scope filtering.
    """
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        if node.type not in MASKED_KINDS:
            pending.extend(reversed(node.named_children))


def parse(
    source: str,
) -> ParsedSwiftSource:
    """
    Parse Swift source for read-only declaration and boundary analysis.

    Parameters
    ----------
    source : str
        Decoded source text; consumer modules and defaults are not executed.
        No consumer files are read or written.

    Returns
    -------
    ParsedSwiftSource
        Native syntax with original Tree-sitter locations, a masked source
        view and documentation lines for language-specific analysis. The view
        converts UTF-8 byte positions without changing character offsets.

    Raises
    ------
    UnicodeEncodeError
        Direct text contains code points that cannot be encoded as UTF-8.

    Notes
    -----
    Parsing does not import consumer modules, resolve types or evaluate runtime
    behavior. Malformed or unsupported Swift can produce recovery nodes rather
    than Python's SyntaxError. root.has_error exposes retained grammar errors;
    a recovered tree does not establish compiler or semantic validity.
    Return recovery observations for caller interpretation. Grammar recovery
    does not raise the Python parse errors handled by syntax_findings.

    Mask comments, strings and regex literals. Unterminated block-comment tails
    are excluded from the recovered root and remain masked even when grammar
    recovery would reinterpret them as code. Documentation locations use
    documentation_lines after this shielding, so hidden text cannot supply
    documentation, declarations or imports.
    """
    raw = source.encode('utf-8')
    root = Parser(LANGUAGE).parse(raw).root_node
    root, code, comments = _source_view(root, raw)
    return ParsedSwiftSource(
        root,
        raw,
        code,
        frozenset(documentation_lines(comments, raw)),
        (0, *(match.end() for match in re.finditer('\n', source)), len(source) + 1),
    )


# !SECTION
