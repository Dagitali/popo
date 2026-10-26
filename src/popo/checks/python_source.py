"""
:mod:`popo.checks.python_source` module.

Inspect configured Python conventions through ASTs without importing code.
"""

import ast

from popo.config.source_checks import SourceCheckConfig

from ._source_inputs import discover, read_source

# SECTION: FUNCTIONS


def validate(
    config: SourceCheckConfig,
) -> list[str]:
    """
    Return source-convention findings without executing inspected modules.

    Parameters
    ----------
    config : SourceCheckConfig
        Python source paths and opt-in convention settings.

    Returns
    -------
    list[str]
        Location and rule diagnostics, never source or exception contents.
    """
    paths, failures = discover(config)
    options = config.settings
    for path in paths:
        source, errors = read_source(path, config.root)
        failures.extend(errors)
        if source is None:
            continue
        relative = path.relative_to(config.root).as_posix()
        lines = source.splitlines()
        if len(lines) > int(str(options['max-module-lines'])):
            failures.append(f'{relative}: module exceeds configured line limit')
        try:
            tree = ast.parse(source)
        except SyntaxError as error:
            failures.append(f'{relative}:{error.lineno}: invalid Python source')
            continue
        for node in ast.walk(tree):
            if (
                isinstance(
                    node,
                    (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                )
                and ast.get_docstring(node, clean=False) is not None
            ):
                doc = node.body[0]
                for number in range(doc.lineno, (doc.end_lineno or doc.lineno) + 1):
                    if len(lines[number - 1]) > int(str(options['docstring-width'])):
                        failures.append(f'{relative}:{number}: docstring line too long')
            if isinstance(node, ast.ClassDef) and options['alphabetical-methods']:
                names = [
                    member.name
                    for member in node.body
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and (
                        member_parameters := [
                            *member.args.posonlyargs,
                            *member.args.args,
                        ]
                    )
                    and member_parameters[0].arg == 'self'
                ]
                if names != sorted(names):
                    failures.append(
                        f'{relative}:{node.lineno}: instance methods not alphabetical',
                    )
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = node.args
            parameters = [
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
                *filter(None, (args.vararg, args.kwarg)),
            ]
            if options['annotations'] and (
                node.returns is None
                or any(arg.annotation is None for arg in parameters)
            ):
                failures.append(
                    f'{relative}:{node.lineno}: missing signature annotations',
                )
            if (
                not options['parameter-lines']
                or not parameters
                or (len(parameters) == 1 and parameters[0].arg == 'self')
            ):
                continue
            positional = [*args.posonlyargs, *args.args]
            defaults = [
                *zip(
                    positional[len(positional) - len(args.defaults) :],
                    args.defaults,
                    strict=True,
                ),
                *(
                    (arg, default)
                    for arg, default in zip(
                        args.kwonlyargs,
                        args.kw_defaults,
                        strict=True,
                    )
                    if default is not None
                ),
            ]
            if (
                len({arg.lineno for arg in parameters}) != len(parameters)
                or any(
                    arg.lineno <= node.lineno or arg.lineno != arg.end_lineno
                    for arg in parameters
                )
                or any(
                    arg.lineno != default.lineno or arg.lineno != default.end_lineno
                    for arg, default in defaults
                )
            ):
                failures.append(
                    f'{relative}:{node.lineno}: parameters require separate lines',
                )
    return failures


# !SECTION
