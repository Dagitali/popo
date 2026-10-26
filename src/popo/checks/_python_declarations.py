"""
:mod:`popo.checks._python_declarations` module.

Collect Python declaration facts through the standard-library AST.
"""

import ast
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from ._source_declarations import DeclarationFacts, SourceFacts

# SECTION: TYPE ALIASES


# Native AST nodes already carry parsed declaration and parameter syntax; no
# wrappers are needed.
type _CallableSyntax = ast.FunctionDef | ast.AsyncFunctionDef
type _DeclarationSyntax = ast.ClassDef | _CallableSyntax
type _ParameterSyntax = ast.arg


# !SECTION


# SECTION: CONSTANTS


CALLABLE_KINDS = frozenset({'function'})
NOMINAL_KINDS = frozenset({'class'})
NONVALUE_RETURN_TYPES = frozenset(
    {
        '',
        'None',
        'NoReturn',
        'Never',
        'typing.NoReturn',
        'typing.Never',
    },
)

DECLARATION_NODES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


# !SECTION


# SECTION: PROTECTED DATA CLASSES


@dataclass(frozen=True, slots=True)
class _Signature:
    """
    Store one callable's signature observations before body analysis.

    Attributes
    ----------
    parameter_names : tuple[str, ...]
        Documentable names in established AST grouping, excluding a leading
        positional self or cls receiver.
    parameter_lines : bool
        Whether parameter/default spans satisfy the physical-layout rule.
    returns : bool
        Whether the return annotation alone requires a Returns section.
        Explicit value returns or yields can add requirements in _declaration.
    annotated : bool
        Whether every parameter, including receivers, and the return have
        annotations. Annotation contents are observed, not resolved.

    Notes
    -----
    Native AST arguments already provide parsed syntax. This record retains
    derived signature facts, not another syntax tree or body observations.
    """

    parameter_names: tuple[str, ...]
    parameter_lines: bool
    returns: bool
    annotated: bool


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class Declaration:
    """
    Store shared declaration facts and Python-specific observations.

    Attributes
    ----------
    facts : DeclarationFacts
        Documentation and signature requirements from the AST front end.
    annotated : bool
        Whether all callable parameters and the return have annotations.
        True for classes, where this observation is not used.
    instance_methods : tuple[str, ...]
        Direct class methods with an initial positional parameter named self,
        in declaration order; empty for functions and classes without them.
    """

    facts: DeclarationFacts
    annotated: bool = True
    instance_methods: tuple[str, ...] = ()


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _body(
    node: _CallableSyntax,
) -> Iterator[ast.AST]:
    """Walk a callable body without attributing nested callables' contracts.

    Parameters
    ----------
    node : _CallableSyntax
        Function or async-function node whose own body supplies requirements.

    Yields
    ------
    ast.AST
        Body nodes outside nested function, async-function, class and lambda
        scopes. Traversal collects facts; it does not model execution order.

    Notes
    -----
    Python has native body nodes to inspect. Swift's bounded front end instead
    derives callable contracts from signatures and tracks lexical scope while
    discovering declarations; it does not infer exceptions from body text.
    """
    pending: list[ast.AST] = list(node.body)
    while pending:
        current = pending.pop()
        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
        ):
            continue
        yield current
        pending.extend(ast.iter_child_nodes(current))


def _declaration(
    syntax: _DeclarationSyntax,
) -> Declaration:
    """
    Convert one declaration's native syntax into facts and observations.

    Parameters
    ----------
    syntax : _DeclarationSyntax
        Class, function or async-function node from _declaration_syntax.

    Returns
    -------
    Declaration
        Shared documentation/signature facts and Python annotation/order facts.
        Classes retain their direct self-receiver methods. Callables retain
        signature annotations and explicit return/yield/raise requirements.

    Notes
    -----
    Signature observations come from _signature using native AST arguments.
    Body analysis excludes nested definitions; explicit raises include locally
    caught ones.
    Type annotations are observed, not resolved or validated.
    """
    if isinstance(syntax, ast.ClassDef):
        methods = tuple(
            member.name
            for member in syntax.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and (parameters := [*member.args.posonlyargs, *member.args.args])
            and parameters[0].arg == 'self'
        )
        return Declaration(
            DeclarationFacts(
                syntax.lineno,
                'class',
                ast.get_docstring(syntax) or '',
                (),
            ),
            instance_methods=methods,
        )
    signature = _signature(syntax)
    returns = signature.returns
    yields = raises = False
    for item in _body(syntax):
        if isinstance(item, (ast.Yield, ast.YieldFrom)):
            yields = True
        elif isinstance(item, ast.Raise):
            raises = True
        elif isinstance(item, ast.Return):
            returns |= item.value is not None and not (
                isinstance(item.value, ast.Constant) and item.value.value is None
            )
    return Declaration(
        DeclarationFacts(
            syntax.lineno,
            'function',
            ast.get_docstring(syntax) or '',
            signature.parameter_names,
            'Yields' if yields else 'Returns' if returns else '',
            raises,
            signature.parameter_lines,
        ),
        signature.annotated,
    )


def _declaration_syntax(
    tree: ast.Module,
) -> Iterator[_DeclarationSyntax]:
    """
    Yield native declaration nodes from one breadth-first AST traversal.

    Parameters
    ----------
    tree : ast.Module
        Parsed Python module; no consumer code is imported or executed.

    Yields
    ------
    _DeclarationSyntax
        Native class, function and async-function nodes, including nested
        declarations. Python supplies complete syntax nodes rather than
        lexical records.
    """
    for node in ast.walk(tree):
        if isinstance(node, DECLARATION_NODES):
            yield node


def _declarations(
    syntax: Iterable[_DeclarationSyntax],
) -> Iterator[Declaration]:
    """
    Convert declaration syntax into shared facts and Python observations.

    Parameters
    ----------
    syntax : collections.abc.Iterable[_DeclarationSyntax]
        Native declaration nodes in discovery order.

    Yields
    ------
    Declaration
        Shared documentation/signature facts and Python annotation/order facts.
        Callable requirements exclude nested bodies; classes retain only their
        directly declared self-receiver methods for ordering checks.
    """
    for item in syntax:
        yield _declaration(item)


def _file_overview(
    tree: ast.Module,
) -> bool:
    """
    Identify a file overview using the front end's documentation convention.

    Parameters
    ----------
    tree : ast.Module
        Parsed Python module; comments and literals are already classified.

    Returns
    -------
    bool
        Whether the module has a nonempty, cleaned leading docstring. Class
        and callable docstrings do not establish a file overview.

    Notes
    -----
    Python's parser supplies module-docstring identity. Swift instead uses
    lexical comment locations before the first code line. Neither front end
    executes inspected code or validates the overview's prose quality.
    """
    return bool(ast.get_docstring(tree))


def _parameter_lines(
    node: _CallableSyntax,
    parameters: list[_ParameterSyntax],
) -> bool:
    """
    Check physical parameter/default spans using native AST locations.

    Parameters
    ----------
    node : _CallableSyntax
        Function or async-function node identifying the declaration line.
    parameters : list[_ParameterSyntax]
        Native ast.arg nodes from _parameters; defaults come from node.args.

    Returns
    -------
    bool
        Whether parameters occupy distinct lines after the declaration and
        each parameter/default remains on one physical line. Preserve Python's
        exception for an empty list or a sole parameter named self.
    """
    if not parameters or (len(parameters) == 1 and parameters[0].arg == 'self'):
        return True
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults = [
        *zip(
            positional[len(positional) - len(args.defaults) :],
            args.defaults,
            strict=True,
        ),
        *(
            (arg, default)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
            if default is not None
        ),
    ]
    return (
        len({arg.lineno for arg in parameters}) == len(parameters)
        and all(
            arg.lineno > node.lineno and arg.lineno == arg.end_lineno
            for arg in parameters
        )
        and all(
            arg.lineno == default.lineno == default.end_lineno
            for arg, default in defaults
        )
    )


def _parameters(
    node: _CallableSyntax,
) -> list[_ParameterSyntax]:
    """
    Extract parameter syntax in the front end's established order.

    Parameters
    ----------
    node : _CallableSyntax
        Function or async-function AST node with an already parsed signature.

    Returns
    -------
    list[_ParameterSyntax]
        Native ast.arg nodes for positional-only, positional, keyword-only,
        vararg and kwarg parameters in established grouping order.
        Receiver removal and annotation/layout checks are separate operations.
        Native AST locations retain parameter and default-expression spans.
    """
    args = node.args
    return [
        *args.posonlyargs,
        *args.args,
        *args.kwonlyargs,
        *(arg for arg in (args.vararg, args.kwarg) if arg is not None),
    ]


def _signature(
    node: _CallableSyntax,
) -> _Signature:
    """
    Extract one callable's signature observations from native AST nodes.

    Parameters
    ----------
    node : _CallableSyntax
        Function or async-function node with an already parsed signature.

    Returns
    -------
    _Signature
        Documentable names, physical layout, return-annotation requirement and
        annotation completeness. Receiver annotations remain required even
        though receiver names are omitted from documentation requirements.

    Notes
    -----
    Quoted non-value return annotations follow the same rules as unquoted
    forms. Body-derived return/yield/raise requirements belong to _declaration,
    which uses _body to exclude nested scopes. No consumer code executes.
    """
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    parameters = _parameters(node)
    names = [arg.arg for arg in parameters]
    if positional and positional[0].arg in {'self', 'cls'}:
        names.remove(positional[0].arg)
    result_type = node.returns
    annotation = ast.unparse(result_type) if result_type is not None else ''
    if isinstance(result_type, ast.Constant) and isinstance(result_type.value, str):
        annotation = result_type.value
    returns = annotation not in NONVALUE_RETURN_TYPES
    return _Signature(
        tuple(names),
        _parameter_lines(node, parameters),
        returns,
        node.returns is not None
        and all(arg.annotation is not None for arg in parameters),
    )


# !SECTION


# SECTION: FUNCTIONS


def parse(
    source: str,
) -> SourceFacts[Declaration]:
    """
    Collect immutable Python source and declaration facts.

    Parameters
    ----------
    source : str
        Source text; modules are never imported or executed.

    Returns
    -------
    SourceFacts[Declaration]
        Module overview, documentation line numbers and declaration records.
        Syntax discovery and fact construction are separate stages. The AST
        front end owns parameter extraction and body analysis.

    Raises
    ------
    SyntaxError
        If the standard-library parser rejects the source. The file validator
        converts this into a location-only diagnostic.

    Notes
    -----
    Positional-only, keyword-only, async and variadic signatures are included.
    Nested functions and classes receive their own records. Their bodies do
    not contribute return/yield/raise requirements to the enclosing function.
    Quoted non-value return annotations use the same rules as unquoted ones.
    Explicit raises include locally caught ones; indirect exceptions and escape
    analysis are not inferred. Type annotations are observed, not validated.
    """
    tree = ast.parse(source)
    documentation: set[int] = set()
    syntax = tuple(_declaration_syntax(tree))
    for node in (tree, *syntax):
        if ast.get_docstring(node, clean=False) is not None:
            doc = node.body[0]
            documentation.update(
                range(doc.lineno, (doc.end_lineno or doc.lineno) + 1),
            )
    return SourceFacts(
        _file_overview(tree),
        tuple(sorted(documentation)),
        tuple(_declarations(syntax)),
    )


# !SECTION
