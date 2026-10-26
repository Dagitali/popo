"""
:mod:`popo.checks._swift_declarations` module.

Collect Swift declaration facts through bounded lexical syntax.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from ._source_declarations import DeclarationFacts, SourceFacts

# SECTION: CONSTANTS


DECLARATION_PATTERN = re.compile(
    r'^\s*(?:(?:@\w+(?:\([^\n]*\))?|public|private|fileprivate|internal|'
    r'final|nonisolated|open|package|indirect|distributed|static|class|override|'
    r'mutating|nonmutating|required|convenience|lazy|weak|unowned)\s+)*'
    r'(?P<kind>struct|class|enum|actor|protocol|extension|func|init|deinit|'
    r'subscript|var|let)\b',
)
FUNCTION_NAME_PATTERN = re.compile(r'\s+`?\w+')
PARAMETER_NAME_PATTERN = re.compile(r'`?(\w+)`?')
RETURN_PATTERN = re.compile(r'->\s*(.*?)\s*(?:\bwhere\b|$)', re.S)
STRING_START_PATTERN = re.compile(r'(#+)?("""|")')
THROWS_PATTERN = re.compile(r'\b(?:rethrows|throws)\b')

NOMINAL_KINDS = frozenset({'struct', 'class', 'enum', 'actor', 'protocol', 'extension'})
CALLABLE_KINDS = frozenset({'func', 'init', 'subscript'})

NONVALUE_RETURN_TYPES = frozenset({'Void', '()', 'Swift.Void', 'Never', 'Swift.Never'})


# !SECTION


# SECTION: PROTECTED DATA CLASSES


@dataclass(frozen=True, slots=True)
class _DeclarationSyntax:
    """
    Retain bounded lexical declaration syntax for the Swift front end.

    Attributes
    ----------
    line : int
        One-based source declaration line.
    attachment_start : int
        Zero-based first attribute line, or declaration line when no separate
        attributes precede it; attached documentation ends before this line.
    kind : str
        Recognized declaration keyword; operator functions are unsupported.
    parameter_names : tuple[str, ...] or None
        Internal argument names, or None when a signature is unsupported.
    returns, raises, parameter_lines : bool
        Non-Void result, throws/rethrows syntax, and separate-line parameters.
    """

    line: int
    attachment_start: int
    kind: str
    parameter_names: tuple[str, ...] | None = ()
    returns: bool = False
    raises: bool = False
    parameter_lines: bool = True


@dataclass(frozen=True, slots=True)
class _Signature:
    """
    Store one callable's signature observations and lexical boundaries.

    Attributes
    ----------
    parameter_names : tuple[str, ...] or None
        Documentable internal names in source order, omitting unnamed
        arguments; None marks an unsupported signature.
    parameter_lines : bool
        Whether parameter/default spans satisfy the physical-layout rule.
    tail : str
        Bounded text after the parameter list for return/throws inspection.
    end : int
        Offset after the bounded signature; discovery locates its body from
        here. Unsupported signatures retain the original input position.

    Notes
    -----
    Swift requires lexical balancing; this is not a compiler AST. Unsupported
    signatures have None names, false layout and an empty tail. Python's
    counterpart stores native-AST annotation facts instead of text boundaries.
    """

    parameter_names: tuple[str, ...] | None
    parameter_lines: bool
    tail: str
    end: int


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class Declaration:
    """
    Store shared declaration facts and Swift-specific observations.

    Attributes
    ----------
    facts : DeclarationFacts
        Documentation and signature requirements from the lexical front end.
    documentation_start : int
        One-based attached documentation line for spacing findings.
    separated : bool
        Whether a blank line precedes documentation, or it begins the file.
    """

    facts: DeclarationFacts
    documentation_start: int
    separated: bool


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _declaration(
    syntax: _DeclarationSyntax,
    lines: list[str],
    documentation: set[int],
) -> Declaration:
    """
    Convert one declaration's lexical syntax into facts and observations.

    Parameters
    ----------
    syntax : _DeclarationSyntax
        Nominal, member or callable record from _declaration_syntax.
    lines : list[str]
        Original source lines used to retain documentation text and spacing.
    documentation : set[int]
        One-based triple-slash documentation lines from lexical masking.

    Returns
    -------
    Declaration
        Shared documentation/signature facts and Swift attachment/spacing
        facts. Documentation attaches across attribute-only lines; unsupported
        callable signatures retain None names for explicit diagnostics.

    Notes
    -----
    Bounded signature facts were collected lexically. Unlike Python's AST body
    analysis, Swift return and raise requirements come from signature syntax;
    declaration conversion neither compiles code nor infers body semantics.
    """
    start = syntax.attachment_start
    while start and start in documentation:
        start -= 1
    doc = '\n'.join(
        line.lstrip()[3:] for line in lines[start : syntax.attachment_start]
    )
    facts = DeclarationFacts(
        syntax.line,
        syntax.kind,
        doc,
        syntax.parameter_names,
        'Returns' if syntax.returns else '',
        syntax.raises,
        syntax.parameter_lines,
    )
    return Declaration(facts, start + 1, not start or not lines[start - 1].strip())


def _declaration_syntax(
    code: str,
) -> Iterator[_DeclarationSyntax]:
    """
    Yield lexical declaration records from one masked-source traversal.

    Parameters
    ----------
    code : str
        Position-preserving masked view from :func:`lexical_view`.

    Yields
    ------
    _DeclarationSyntax
        Nominal, member and named callable locations and contracts, retaining
        documentation attachment positions and unsupported-signature markers.

    Notes
    -----
    Recognize line-leading declarations and attribute-only preceding lines.
    Balanced parentheses handle multiline signatures; this does not model
    macro expansion, conditional-compilation semantics or full Swift grammar.
    Both conditional branches are inspected. Unsupported callable signatures
    have parameter_names=None so opted-in contract checks can fail explicitly.
    """
    lines = code.splitlines(keepends=True)
    offset = 0
    scopes: list[str] = []
    owners: dict[int, str] = {}
    for index, line in enumerate(lines):
        match = DECLARATION_PATTERN.match(line)
        if match is not None and (not scopes or scopes[-1] == 'nominal'):
            start = index
            while start and lines[start - 1].lstrip().startswith('@'):
                start -= 1
            kind = match['kind']
            parameters: tuple[str, ...] | None = ()
            tail, separate = '', True
            body = code.find('{', offset + match.end())
            if kind in CALLABLE_KINDS:
                signature = _signature(code, offset + match.end())
                parameters = signature.parameter_names
                tail = signature.tail
                separate = signature.parameter_lines
                body = signature.end
                while body < len(code) and code[body].isspace():
                    body += 1
                if body == len(code) or code[body] != '{':
                    body = -1
                if kind == 'func' and not FUNCTION_NAME_PATTERN.match(
                    line[match.end() :],
                ):
                    parameters = None
            if body >= 0 and (kind in NOMINAL_KINDS or kind in CALLABLE_KINDS):
                owners[body] = 'nominal' if kind in NOMINAL_KINDS else 'callable'
            result = RETURN_PATTERN.search(tail)
            returns = (
                (kind == 'func' or kind == 'subscript')
                and result is not None
                and result[1].strip() not in NONVALUE_RETURN_TYPES
            )
            yield _DeclarationSyntax(
                index + 1,
                start,
                kind,
                parameters,
                returns,
                bool(THROWS_PATTERN.search(tail.partition('->')[0])),
                separate,
            )
        for column, char in enumerate(line):
            if char == '{':
                scopes.append(owners.get(offset + column, 'block'))
            elif char == '}' and scopes:
                scopes.pop()
        offset += len(line)


def _declarations(
    syntax: Iterable[_DeclarationSyntax],
    lines: list[str],
    documentation: set[int],
) -> Iterator[Declaration]:
    """
    Convert declaration syntax into shared facts and Swift observations.

    Parameters
    ----------
    syntax : collections.abc.Iterable[_DeclarationSyntax]
        Lexical declaration records in discovery order.
    lines : list[str]
        Original source lines used to retain documentation text and spacing.
    documentation : set[int]
        One-based triple-slash documentation lines from lexical masking.

    Yields
    ------
    Declaration
        Shared documentation/signature facts and Swift attachment/spacing
        facts. Documentation attaches across attribute-only lines; unsupported
        callable signatures retain None names for explicit diagnostics.
    """
    for item in syntax:
        yield _declaration(item, lines, documentation)


def _parameter_lines(
    code: str,
    position: int,
    parameters_start: int,
    parameters: list[tuple[int, str]],
) -> bool:
    """
    Check physical parameter/default spans using lexical source offsets.

    Parameters
    ----------
    code : str
        Position-preserving masked Swift source.
    position : int
        Declaration-keyword end offset identifying the declaration line.
    parameters_start : int
        Offset immediately after the signature's opening parenthesis.
    parameters : list[tuple[int, str]]
        Parameter offsets/text relative to parameters_start from _parameters.

    Returns
    -------
    bool
        Whether parameters occupy distinct lines after the declaration and
        each parameter, including its default, remains on one physical line.
        Empty lists pass; Swift has no Python self-receiver exception.
    """
    positions = [
        parameters_start + start + len(part) - len(part.lstrip())
        for start, part in parameters
    ]
    line_numbers = [code.count('\n', 0, offset) for offset in positions]
    return (
        len(set(line_numbers)) == len(parameters)
        and all(number > code.count('\n', 0, position) for number in line_numbers)
        and all('\n' not in part.strip() for _, part in parameters)
    )


def _parameters(
    text: str,
) -> list[tuple[int, str]]:
    """
    Extract parameter syntax in the front end's established order.

    Parameters
    ----------
    text : str
        Masked text inside a balanced callable parameter list.

    Returns
    -------
    list[tuple[int, str]]
        Source-ordered parameter offsets and text, split only at outer commas.
        Nested type/default delimiters are retained. Name interpretation and
        physical-line checks are separate operations; this is not a Swift AST.
    """
    parts: list[tuple[int, str]] = []
    stack: list[str] = []
    start, default = 0, False
    pairs = {')': '(', ']': '[', '}': '{', '>': '<'}
    for index, char in enumerate(text):
        if char in '([{' or (char == '<' and not default):
            stack.append(char)
        elif (
            char in pairs
            and not (char == '>' and index and text[index - 1] == '-')
            and stack
            and stack[-1] == pairs[char]
        ):
            stack.pop()
        elif not stack:
            if char == '=':
                default = True
            elif char == ',':
                parts.append((start, text[start:index]))
                start, default = index + 1, False
    parts.append((start, text[start:]))
    return [(start, part) for start, part in parts if part.strip()]


def _signature(
    code: str,
    position: int,
) -> _Signature:
    """
    Extract one callable's signature observations from bounded source text.

    Parameters
    ----------
    code : str
        Position-preserving masked Swift source.
    position : int
        Offset after the declaration keyword; layout is measured from its line.

    Returns
    -------
    _Signature
        Documentable names, physical layout, trailing signature text and the
        offset after the bounded signature. Unsupported signatures retain
        None names, false layout, empty text and the original position.

    Notes
    -----
    Swift needs lexical balancing because no compiler AST is available here.
    Python instead reads its native AST arguments; neither front end executes
    consumer code or resolves types. Named argument syntax is bounded rather
    than a full Swift grammar, and unnamed arguments do not require docs.
    """
    opening = code.find('(', position)
    if opening < 0 or any(char in code[position:opening] for char in '{};'):
        return _Signature(None, False, '', position)
    depth, end = 1, opening + 1
    while end < len(code) and depth:
        depth += (code[end] == '(') - (code[end] == ')')
        end += 1
    if depth:
        return _Signature(None, False, '', position)
    names: list[str] = []
    parameters = _parameters(code[opening + 1 : end - 1])
    for _, parameter in parameters:
        # Deliberately accept named arguments, not arbitrary signature syntax.
        prefix, colon, _ = parameter.partition(':')
        identifiers = PARAMETER_NAME_PATTERN.findall(prefix)
        if not colon or not identifiers or '(' in prefix:
            return _Signature(None, False, '', position)
        if identifiers[-1] != '_':
            names.append(identifiers[-1])
    stop = end
    while stop < len(code) and code[stop] not in '{};':
        if code[stop] == '\n':
            following = code[stop + 1 :].lstrip()
            tail = code[end:stop].rstrip()
            if not following.startswith(('async', 'throws', 'rethrows', '->', 'where')):
                if not tail.endswith(('->', ',', 'where')):
                    break
        stop += 1
    return _Signature(
        tuple(names),
        _parameter_lines(code, position, opening + 1, parameters),
        code[end:stop],
        stop,
    )


# !SECTION


# SECTION: FUNCTIONS


def lexical_view(
    source: str,
) -> tuple[str, set[int]]:
    """
    Mask comments/strings and identify actual triple-slash doc lines.

    Parameters
    ----------
    source : str
        Swift text; inspected code is never executed.

    Returns
    -------
    tuple[str, set[int]]
        Same-length code view and one-based triple-slash comment line numbers.

    Notes
    -----
    Nested block comments and ordinary, multiline and raw strings are masked.
    Regex literals and interpolation expressions are not parsed as Swift code.
    This lexical view is not syntax validation or a compiler substitute.
    """
    result = list(source)
    documentation: set[int] = set()
    index, line = 0, 1
    while index < len(source):
        start = index
        if source.startswith('//', index):
            if (
                source.startswith('///', index)
                and not source[source.rfind('\n', 0, index) + 1 : index].strip()
            ):
                documentation.add(line)
            end = source.find('\n', index)
            index = len(source) if end == -1 else end
        elif source.startswith('/*', index):
            index += 2
            depth = 1
            while index < len(source) and depth:
                if source.startswith('/*', index):
                    depth += 1
                    index += 2
                elif source.startswith('*/', index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
        elif match := STRING_START_PATTERN.match(source, index):
            hashes = match.group(1) or ''
            closing = match.group(2) + hashes
            index += len(match.group())
            while index < len(source):
                if source.startswith('\\' + hashes, index):
                    index += 2 + len(hashes)
                elif source.startswith(closing, index):
                    index += len(closing)
                    break
                else:
                    index += 1
        else:
            line += source[index] == '\n'
            index += 1
            continue
        for offset in range(start, min(index, len(source))):
            if result[offset] != '\n':
                result[offset] = ' '
        line += source[start:index].count('\n')
    return ''.join(result), documentation


def parse(
    source: str,
) -> SourceFacts[Declaration]:
    """
    Collect immutable Swift source and declaration facts.

    Parameters
    ----------
    source : str
        Swift source; no compiler or consumer code is executed.

    Returns
    -------
    SourceFacts[Declaration]
        Overview, real triple-slash documentation lines and declarations.
        Syntax discovery and fact construction are separate stages. Unsupported
        recognized signatures retain None parameter names.

    Notes
    -----
    Mask nested comments and ordinary, multiline and raw strings first. Docs
    attach across attribute-only lines. Callable and closure bodies do not
    supply member declarations. Balanced parentheses support named signatures;
    this remains a lexical subset, not Swift syntax or semantic validation.
    """
    code, documentation = lexical_view(source)
    lines = source.splitlines()
    first_code = next(
        (index for index, line in enumerate(code.splitlines()) if line.strip()),
        len(lines),
    )
    overview = any(
        number <= first_code and lines[number - 1].startswith('/// ')
        for number in documentation
    )
    declarations = _declarations(_declaration_syntax(code), lines, documentation)
    return SourceFacts(overview, tuple(sorted(documentation)), tuple(declarations))


# !SECTION
