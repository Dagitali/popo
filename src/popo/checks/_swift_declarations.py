"""
:mod:`popo.checks._swift_declarations` module.

Collect Swift declaration facts through concrete syntax and bounded contracts.
"""

import re
from collections.abc import Collection, Iterable, Iterator, Sequence
from dataclasses import dataclass

from ._source_declarations import (
    CallableRequirements,
    DeclarationFacts,
    ParameterSpan,
    SourceFacts,
    parameter_lines,
)
from ._swift_syntax import ParsedSwiftSource
from ._swift_syntax import parse as parse_syntax

# SECTION: CONSTANTS


CALLABLE_KINDS = frozenset({'func', 'init', 'subscript'})
NOMINAL_KINDS = frozenset({'struct', 'class', 'enum', 'actor', 'protocol', 'extension'})
NONVALUE_RETURN_TYPES = frozenset(
    {
        'Void',
        '()',
        'Swift.Void',
        'Never',
        'Swift.Never',
    },
)

# Native Swift grammar node types identify declarations before keyword handling.
# Selective imports also contain declaration keywords and must not be classified
# by their tokens alone. Typealiases remain outside source-documentation policy.
DECLARATION_NODE_TYPES = frozenset(
    {
        'class_declaration',
        'protocol_declaration',
        'function_declaration',
        'protocol_function_declaration',
        'init_declaration',
        'deinit_declaration',
        'subscript_declaration',
        'property_declaration',
        'protocol_property_declaration',
    },
)

DECLARATION_PATTERN = re.compile(
    r'^\s*(?:(?:@\w+(?:\([^\n]*\))?|public|private|fileprivate|internal|'
    r'final|nonisolated|open|package|indirect|distributed|static|class|override|'
    r'mutating|nonmutating|required|convenience|lazy|weak|unowned)\s+)*'
    r'(?P<kind>struct|class|enum|actor|protocol|extension|func|init|deinit|'
    r'subscript|var|let)\b',
)
FUNCTION_NAME_PATTERN = re.compile(r'\s+`?\w+')
PARAMETER_NAME_PATTERN = re.compile(r'`?(\w+)`?')
RETURN_PATTERN = re.compile(r'->\s*(.*?)\s*(?:\bwhere\b|$)', re.DOTALL)
SIGNATURE_CONTINUATION_PATTERN = re.compile(r'\s*(?:async|throws|rethrows|->|where)')
THROWS_PATTERN = re.compile(r'\b(?:rethrows|throws)\b')


# !SECTION


# SECTION: PROTECTED DATA CLASSES


@dataclass(frozen=True, slots=True)
class _DeclarationSyntax:
    """
    Normalize native/recovered syntax and documentation attachment context.

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
    requirements : CallableRequirements
        Result and exception documentation requirements from bounded signature
        text; bodies are not analyzed and types are not resolved.
    parameter_lines : bool
        Whether native parameter/default spans satisfy the layout rule.
    attach_documentation : bool
        Whether preceding doc lines may attach; false after same-line code.
    """

    line: int
    attachment_start: int
    kind: str
    parameter_names: tuple[str, ...] | None = ()
    requirements: CallableRequirements = CallableRequirements()
    parameter_lines: bool = True
    attach_documentation: bool = True


@dataclass(frozen=True, slots=True)
class _ParameterSyntax:
    """
    Retain one parameter's lexical syntax before name/layout analysis.

    Attributes
    ----------
    offset : int
        Zero-based character offset within the text supplied to _parameters,
        including any leading whitespace before this parameter.
    text : str
        Masked parameter text without its separating comma. Retain type/default
        delimiters and leading whitespace for later layout checks.

    Notes
    -----
    Nonblank fragments are retained without resolving names or types. The
    signature helper decides whether their syntax is supported. Python's
    counterpart aliases native ast.arg nodes, retaining AST locations instead
    of lexical offsets and text; neither front end executes defaults.
    """

    offset: int
    text: str


@dataclass(frozen=True, slots=True)
class _Signature:
    """
    Store native callable signature observations.

    Attributes
    ----------
    parameter_names : tuple[str, ...] or None
        Documentable internal names in source order, omitting unnamed
        arguments; None marks an unsupported signature.
    parameter_lines : bool
        Whether native parameter/default spans satisfy the layout rule.
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
    Its parameter fields structurally satisfy the shared SignatureRecord.
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
        Documentation/signature requirements from the concrete-syntax front
        end.
    documentation_start : int
        One-based attached documentation line for spacing findings.
    separated : bool
        Whether a blank line precedes documentation, or it begins the file.
    """

    # Structurally satisfies DeclarationRecord; native observations stay here.
    facts: DeclarationFacts
    documentation_start: int
    separated: bool


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _declaration(
    syntax: _DeclarationSyntax,
    lines: list[str],
    documentation: Collection[int],
) -> Declaration:
    """
    Convert one declaration's syntax into facts and observations.

    Parameters
    ----------
    syntax : _DeclarationSyntax
        Nominal, member or callable record from _declaration_syntax.
    lines : list[str]
        Original source lines used to retain documentation text and spacing.
    documentation : collections.abc.Collection[int]
        One-based triple-slash documentation lines from concrete-syntax
        masking.

    Returns
    -------
    Declaration
        Shared documentation/signature facts and Swift attachment/spacing
        facts. Documentation attaches across attribute-only lines; unsupported
        callable signatures retain None names for explicit diagnostics.

    Notes
    -----
    Discovery uses native syntax or recovery; signatures retain bounded rules.
    Swift return and raise requirements come from signature syntax;
    declaration conversion neither compiles code nor infers body semantics.
    """
    doc, start, separated = _documentation(syntax, lines, documentation)
    facts = DeclarationFacts.from_requirements(
        line=syntax.line,
        kind=syntax.kind,
        documentation=doc,
        signature=syntax,
        requirements=syntax.requirements,
    )
    return Declaration(facts, start, separated)


def _declaration_syntax(
    code: str,
    syntax: ParsedSwiftSource | None = None,
) -> Iterator[_DeclarationSyntax]:
    """
    Discover declaration syntax through native node-type classification.

    Parameters
    ----------
    code : str
        Character-position-preserving masked source used by signature rules.
    syntax : ParsedSwiftSource or None, optional
        Native tree from original source. Direct helper callers may omit it;
        their supplied view is parsed instead.

    Yields
    ------
    _DeclarationSyntax
        Nominal/member declarations in source order, excluding callable and
        closure bodies. Native nodes support same-line declarations.

    Notes
    -----
    Keep bounded signature rules and their unsupported markers. If the grammar
    recovers malformed or unsupported source, use the established lexical
    discovery path so recovery cannot silently discard those diagnostics.
    Neither native trees nor recovery provide compiler validation.
    """
    syntax = syntax or parse_syntax(code)
    if syntax.root.has_error:
        yield from _lexical_declaration_syntax(code)
        return
    pending = list(reversed(syntax.root.named_children))
    while pending:
        node = pending.pop()
        if node.type not in DECLARATION_NODE_TYPES:
            continue
        keyword = next(
            child
            for child in node.children
            if child.type
            in NOMINAL_KINDS
            | CALLABLE_KINDS
            | {
                'deinit',
                'value_binding_pattern',
                'pattern',
            }
        )
        kind = (keyword.text or b'').decode().split()[0]
        position = syntax.offset(keyword) + len(kind)
        signature = _signature(code, position) if kind in CALLABLE_KINDS else None
        parameters = signature.parameter_names if signature else ()
        if kind == 'func' and not FUNCTION_NAME_PATTERN.match(code, position):
            parameters = None
        yield _DeclarationSyntax(
            keyword.start_point.row + 1,
            node.start_point.row,
            kind,
            parameters,
            _requirements(kind, signature.tail if signature else ''),
            signature.parameter_lines if signature else True,
            not code[
                syntax.line_offsets[node.start_point.row] : syntax.offset(node)
            ].strip(),
        )
        if kind in NOMINAL_KINDS:
            pending.extend(
                reversed(
                    [
                        child
                        for body in node.children_by_field_name('body')
                        for child in body.named_children
                    ],
                ),
            )


def _declarations(
    syntax: Iterable[_DeclarationSyntax],
    lines: list[str],
    documentation: Collection[int],
) -> Iterator[Declaration]:
    """
    Convert declaration syntax into shared facts and Swift observations.

    Parameters
    ----------
    syntax : collections.abc.Iterable[_DeclarationSyntax]
        Native/recovered declaration observations in discovery order.
    lines : list[str]
        Original source lines used to retain documentation text and spacing.
    documentation : collections.abc.Collection[int]
        One-based triple-slash documentation lines from concrete-syntax
        masking.

    Yields
    ------
    Declaration
        Shared documentation/signature facts and Swift attachment/spacing
        facts. Documentation attaches across attribute-only lines; unsupported
        callable signatures retain None names for explicit diagnostics.
    """
    for item in syntax:
        yield _declaration(item, lines, documentation)


def _documentation(
    syntax: _DeclarationSyntax,
    lines: list[str],
    documentation: Collection[int],
) -> tuple[str, int, bool]:
    """
    Extract attached documentation using native syntax conventions.

    Parameters
    ----------
    syntax : _DeclarationSyntax
        Native/recovered declaration with attachment boundary observations.
    lines : list[str]
        Original source lines retaining comment prefixes and blank lines.
    documentation : collections.abc.Collection[int]
        One-based standalone triple-slash lines recognized by native syntax.

    Returns
    -------
    tuple[str, int, bool]
        Attached text without comment prefixes, one-based documentation start
        and whether a blank line precedes it or it starts the file. Without
        attached text, retain the established attachment-boundary location.

    Notes
    -----
    Attachment crosses attribute-only lines but is disabled after same-line
    code. Unlike Python's native docstring ownership, Swift requires explicit
    attachment and spacing observations. No markup contracts are interpreted
    and no source is executed; missing-documentation policy is evaluated later.
    """
    start = syntax.attachment_start
    while syntax.attach_documentation and start and start in documentation:
        start -= 1
    doc = '\n'.join(
        line.lstrip()[3:] for line in lines[start : syntax.attachment_start]
    )
    return doc, start + 1, not start or not lines[start - 1].strip()


def _file_overview(
    code: str,
    lines: list[str],
    documentation: Collection[int],
) -> bool:
    """
    Identify a file overview using the front end's documentation convention.

    Parameters
    ----------
    code : str
        Position-preserving masked Swift source from the native syntax view.
    lines : list[str]
        Original source lines retaining comment prefixes and indentation.
    documentation : collections.abc.Collection[int]
        One-based triple-slash documentation lines from concrete-syntax
        masking.

    Returns
    -------
    bool
        Whether a column-zero triple-slash comment followed by a space occurs
        before the first code line. Comments inside literals and trailing
        comments do not establish a file overview.

    Notes
    -----
    Swift uses concrete-syntax comment spans rather than module-docstring
    identity. This is a bounded comment convention, not compiler validation;
    neither front end executes code or validates the overview's prose quality.
    """
    first_code = next(
        (index for index, line in enumerate(code.splitlines()) if line.strip()),
        len(lines),
    )
    return any(
        number <= first_code and lines[number - 1].startswith('/// ')
        for number in documentation
    )


def _lexical_declaration_syntax(
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
            yield _DeclarationSyntax(
                index + 1,
                start,
                kind,
                parameters,
                _requirements(kind, tail),
                separate,
            )
        for column, char in enumerate(line):
            if char == '{':
                scopes.append(owners.get(offset + column, 'block'))
            elif char == '}' and scopes:
                scopes.pop()
        offset += len(line)


def _parameter_lines(
    code: str,
    position: int,
    parameters_start: int,
    parameters: Sequence[_ParameterSyntax],
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
    parameters : collections.abc.Sequence[_ParameterSyntax]
        Lexical offset/text records relative to parameters_start from
        _parameters.

    Returns
    -------
    bool
        Whether parameters occupy distinct lines after the declaration and
        each parameter, including its default, remains on one physical line.
        Empty lists pass; Swift has no Python self-receiver exception.
    """
    positions = [
        parameters_start
        + parameter.offset
        + len(parameter.text)
        - len(parameter.text.lstrip())
        for parameter in parameters
    ]
    line_numbers = [code.count('\n', 0, offset) + 1 for offset in positions]
    return parameter_lines(
        code.count('\n', 0, position) + 1,
        (
            ParameterSpan(number, number + parameter.text.strip().count('\n'))
            for number, parameter in zip(line_numbers, parameters, strict=True)
        ),
    )


def _parameter_names(
    parameters: Sequence[_ParameterSyntax],
) -> tuple[str, ...] | None:
    """
    Interpret documentable names from native parameter syntax.

    Parameters
    ----------
    parameters : collections.abc.Sequence[_ParameterSyntax]
        Masked lexical fragments in source order from _parameters.
        The sequence is inspected without modification.

    Returns
    -------
    tuple[str, ...] or None
        Internal argument names, excluding unnamed arguments, or None when
        bounded name syntax is unsupported. An empty tuple is supported and
        differs from that unsupported marker.

    Notes
    -----
    External labels do not replace internal names. Unlike Python AST receiver
    exclusion, this bounded interpretation validates named-argument prefixes.
    Layout checks remain separate; no defaults or consumer code are executed.
    """
    names: list[str] = []
    for parameter in parameters:
        # Deliberately accept named arguments, not arbitrary signature syntax.
        prefix, colon, _ = parameter.text.partition(':')
        identifiers = PARAMETER_NAME_PATTERN.findall(prefix)
        if not colon or not identifiers or '(' in prefix:
            return None
        if identifiers[-1] != '_':
            names.append(identifiers[-1])
    return tuple(names)


def _parameters(
    text: str,
) -> list[_ParameterSyntax]:
    """
    Extract parameter syntax in the front end's established order.

    Parameters
    ----------
    text : str
        Masked text inside a balanced callable parameter list.

    Returns
    -------
    list[_ParameterSyntax]
        Source-ordered lexical records, split only at outer commas. Their
        named offset/text fields preserve the original parameter spans.
        Nested type/default delimiters are retained. Name interpretation and
        physical-line checks are separate operations; this is not a Swift AST.
    """
    parts: list[_ParameterSyntax] = []
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
                parts.append(_ParameterSyntax(start, text[start:index]))
                start, default = index + 1, False
    parts.append(_ParameterSyntax(start, text[start:]))
    return [part for part in parts if part.text.strip()]


def _requirements(
    kind: str,
    tail: str,
) -> CallableRequirements:
    """
    Derive callable result and exception documentation requirements.

    Parameters
    ----------
    kind : str
        Declaration keyword; only func and subscript require return sections.
    tail : str
        Bounded text after the parameter list, or empty for noncallables and
        unsupported signatures.

    Returns
    -------
    CallableRequirements
        Returns for a recognized non-Void/non-Never result, plus exception
        documentation for throws/rethrows before the return arrow. Other
        declaration kinds do not require a result section. Swift does not
        derive Yields here.

    Notes
    -----
    Swift inspects bounded signature syntax. Python instead combines native
    annotations and explicit body observations; neither approach resolves
    types, executes code or proves exception escape behavior. Shared
    normalization selects the result section after native observations.
    """
    return CallableRequirements.from_observations(
        returns=_returns(kind, tail),
        exceptions=bool(THROWS_PATTERN.search(tail.partition('->')[0])),
    )


def _returns(
    kind: str,
    tail: str,
) -> bool:
    """
    Determine whether native result syntax requires documentation.

    Parameters
    ----------
    kind : str
        Native declaration keyword; only func and subscript supply results.
    tail : str
        Bounded signature text after the parameter list.

    Returns
    -------
    bool
        Whether an eligible declaration has a recognized return arrow whose
        stripped result spelling is outside NONVALUE_RETURN_TYPES. Missing
        arrows and other declaration kinds do not require result sections.

    Notes
    -----
    Swift uses bounded signature text and does not infer body return/yield
    requirements. Its non-value spellings differ from Python's annotation
    spellings; this classification neither resolves types nor compiles source.
    """
    result = RETURN_PATTERN.search(tail)
    return (
        kind in {'func', 'subscript'}
        and result is not None
        and result[1].strip() not in NONVALUE_RETURN_TYPES
    )


def _signature(
    code: str,
    position: int,
) -> _Signature:
    """
    Extract one callable's native signature observations.

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
    Swift retains bounded signature interpretation over masked concrete
    syntax. Python instead reads its native AST arguments. Neither front end
    executes consumer code or resolves types. Names use a bounded Swift grammar
    subset; unnamed arguments do not require documentation.
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
    parameters = _parameters(code[opening + 1 : end - 1])
    names = _parameter_names(parameters)
    if names is None:
        return _Signature(None, False, '', position)
    stop = end
    while stop < len(code) and code[stop] not in '{};':
        if (
            code[stop] == '\n'
            and not SIGNATURE_CONTINUATION_PATTERN.match(code, stop + 1)
            and not code[end:stop].rstrip().endswith(('->', ',', 'where'))
        ):
            break
        stop += 1
    return _Signature(
        names,
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
    Tree-sitter locates nested block comments and ordinary, multiline/raw
    strings and regex literals. Entire literals, including interpolation, are
    masked. UTF-8 node offsets are converted without changing character or
    line positions. Recovery nodes do not establish valid Swift syntax.
    """
    syntax = parse_syntax(source)
    return syntax.code, set(syntax.documentation)


def parse(
    source: str,
) -> SourceFacts[Declaration]:
    """
    Collect immutable Swift source and declaration facts.

    Parameters
    ----------
    source : str
        Decoded source text; consumer modules and defaults are not executed.
        No consumer files are read or written.

    Returns
    -------
    SourceFacts[Declaration]
        Overview, real triple-slash documentation lines and declarations.
        Syntax discovery and fact construction are separate stages. Unsupported
        recognized signatures retain None parameter names.

    Raises
    ------
    UnicodeEncodeError
        Direct text contains code points that cannot be encoded as UTF-8.

    Notes
    -----
    Use Tree-sitter concrete syntax for comment/literal masking and structural
    declaration discovery. Docs attach across attribute-only lines, but not
    after preceding code on the same line. Callable and closure bodies do not
    supply member declarations, unlike Python's nested-declaration discovery.
    Source order is preserved. Balanced signature rules retain explicit
    unsupported markers. Grammar recovery uses bounded lexical discovery to
    preserve diagnostics for malformed/unsupported inputs. Neither path
    resolves types or establishes compiler or semantic validation.
    """
    syntax = parse_syntax(source)
    code, documentation = syntax.code, syntax.documentation
    lines = source.splitlines()
    declarations = _declarations(
        _declaration_syntax(code, syntax),
        lines,
        documentation,
    )
    return SourceFacts(
        _file_overview(code, lines, documentation),
        tuple(sorted(documentation)),
        tuple(declarations),
    )


# !SECTION
