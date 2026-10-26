"""Extract Python declaration facts once through the standard-library AST."""

import ast
from collections.abc import Iterator
from dataclasses import dataclass

from ._source_declarations import DeclarationFacts, SourceFacts

# SECTION: CONSTANTS


CALLABLE_KINDS = frozenset({'function'})
NOMINAL_KINDS = frozenset({'class'})

DECLARATION_NODES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
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


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class Declaration:
    """
    Keep shared facts and Python-only annotation/order observations.

    Attributes
    ----------
    facts : DeclarationFacts
        Documentation and signature requirements extracted from the AST.
    annotated : bool
        Whether all callable parameters and its return have annotations.
        True for classes, where this observation is not used.
    instance_methods : tuple[str, ...]
        Direct class methods with an initial positional parameter named self,
        in declaration order; empty for functions and classes without them.
    """

    facts: DeclarationFacts
    annotated: bool = True
    instance_methods: tuple[str, ...] = ()


def _body(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[ast.AST]:
    """
    Walk a callable body without attributing nested callables' contracts."""
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


def _parameter_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    parameters: list[ast.arg],
) -> bool:
    """
    Check physical parameter/default spans, preserving the self exception.
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


def _callable(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Declaration:
    """
    Extract each signature and explicit return/yield/raise requirement once.
    """
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    parameters = [*positional, *args.kwonlyargs]
    parameters.extend(arg for arg in (args.vararg, args.kwarg) if arg is not None)
    names = [arg.arg for arg in parameters]
    if positional and positional[0].arg in {'self', 'cls'}:
        names.remove(positional[0].arg)
    result_type = node.returns
    annotation = ast.unparse(result_type) if result_type is not None else ''
    if isinstance(result_type, ast.Constant) and isinstance(result_type.value, str):
        annotation = result_type.value
    returns = annotation not in NONVALUE_RETURN_TYPES
    yields = raises = False
    for item in _body(node):
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
            node.lineno,
            'function',
            ast.get_docstring(node) or '',
            tuple(names),
            'Yields' if yields else 'Returns' if returns else '',
            raises,
            _parameter_lines(node, parameters),
        ),
        node.returns is not None
        and all(arg.annotation is not None for arg in parameters),
    )


# !SECTION


# SECTION: FUNCTIONS


def parse(
    source: str,
) -> SourceFacts[Declaration]:
    """Parse Python and collect immutable source/declaration observations.

    Parameters
    ----------
    source : str
        Source text; modules are never imported or executed.

    Returns
    -------
    SourceFacts[Declaration]
        Module overview, documentation line numbers and declaration records.
        AST traversal and parameter extraction are owned by this frontend.

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
    declarations: list[Declaration] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, *DECLARATION_NODES)):
            if ast.get_docstring(node, clean=False) is not None:
                doc = node.body[0]
                documentation.update(
                    range(doc.lineno, (doc.end_lineno or doc.lineno) + 1),
                )
        if isinstance(node, ast.ClassDef):
            methods = tuple(
                member.name
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                and (parameters := [*member.args.posonlyargs, *member.args.args])
                and parameters[0].arg == 'self'
            )
            declarations.append(
                Declaration(
                    DeclarationFacts(
                        node.lineno,
                        'class',
                        ast.get_docstring(node) or '',
                        (),
                    ),
                    instance_methods=methods,
                ),
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            declarations.append(_callable(node))
    return SourceFacts(
        bool(ast.get_docstring(tree)),
        tuple(sorted(documentation)),
        tuple(declarations),
    )


# !SECTION
