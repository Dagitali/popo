"""
:mod:`popo.cli` module.

Command-line interface for popo.
"""

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import cast

from . import __version__
from .checks import (
    actions,
    automation,
    changelog,
    dependencies,
    docs,
    python_policy,
)
from .config import ConfigurationError, load_config
from .config.automation import load_automation_config
from .support import report

# SECTION: TYPE ALIASES


Command = Callable[[argparse.Namespace], tuple[list[str], str]]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _actions(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Return action-pin failures and the success message without printing.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments with ``root`` (:class:`pathlib.Path`) and
        ``automation_directory`` (:class:`pathlib.Path` or ``None``).

    Returns
    -------
    tuple[list[str], str]
        Validation failures and the message to use only when no failures exist.

    Raises
    ------
    OSError
        If a discovered automation file cannot be read or a path cannot
        resolve.
    UnicodeError
        If automation text cannot be decoded as UTF-8.

    Notes
    -----
    Default to ``.github`` under the resolved root. An explicit relative
    ``automation_directory`` is resolved against the process working directory,
    not against ``args.root``.
    """
    directory = args.automation_directory
    if directory is None:
        directory = args.root.resolve() / '.github'
    return actions.validate(directory.resolve()), 'remote actions are immutably pinned'


def _add_root(
    parser: argparse.ArgumentParser,
) -> None:
    """
    Add ``--root``, capturing the working directory as its default immediately.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser to mutate by adding the repository-root option.

    Raises
    ------
    OSError
        If the current working directory cannot be determined.
    """
    parser.add_argument(
        '--root',
        type=Path,
        default=Path.cwd(),
        help='Repository root (default: current directory)',
    )


def _all(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Aggregate documentation, action, dependency, and Python-policy failures.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing ``root`` (:class:`pathlib.Path`), the
        consumer repository.

    Returns
    -------
    tuple[list[str], str]
        Combined failures in check order and the success-only report message.

    Raises
    ------
    ConfigurationError
        If loading consumer configuration fails validation.
    OSError
        If a path cannot resolve or an input cannot be read.
    UnicodeError
        If an inspected input cannot be decoded as UTF-8.

    Notes
    -----
    Load consumer configuration, then run those checks in order without
    stopping for returned failures. Include automation contracts only when
    their configuration table is present. Exceptions still propagate. The
    release changelog check is excluded because it requires an explicit
    release version. Return the collected diagnostics and success message
    without printing.
    """
    root = args.root.resolve()
    config = load_config(root)
    failures = [
        *docs.validate(root),
        *actions.validate(root / '.github'),
        *dependencies.validate(config.dependencies),
        *python_policy.validate(config.python_policy),
    ]
    automation_config = load_automation_config(root)
    if automation_config.configured:
        failures.extend(automation.validate(automation_config))
    return failures, 'all configured repository checks passed'


def _automation(args: argparse.Namespace) -> tuple[list[str], str]:
    """
    Dispatch configured automation validation through the public CLI.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed ``root`` and ``pins_only`` options.

    Returns
    -------
    tuple[list[str], str]
        Contract diagnostics and the success message.

    Raises
    ------
    ConfigurationError
        Invalid consumer configuration, reported by :func:`main`.
    """
    config = load_automation_config(args.root)
    return automation.validate(
        config,
        pins_only=args.pins_only,
    ), 'automation contracts are valid'


def _changelog(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Return release-heading failures and the success message without printing.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed ``root`` (:class:`pathlib.Path`), ``release`` (:class:`str`),
        and ``changelog`` (:class:`pathlib.Path` or ``None``).

    Returns
    -------
    tuple[list[str], str]
        Changelog diagnostics and the success-only report message. Invalid
        release syntax is returned as a diagnostic, not raised as
        :exc:`ValueError`.

    Raises
    ------
    OSError
        If the changelog path cannot resolve or the file cannot be read.
    UnicodeError
        If the changelog cannot be decoded as UTF-8.

    Notes
    -----
    Default to CHANGELOG.md under the resolved root. An explicit relative
    changelog path is resolved against the process working directory instead.
    """
    path = args.changelog
    if path is None:
        path = args.root.resolve() / 'CHANGELOG.md'
    version = args.release.removeprefix('v')
    return (
        changelog.validate(path.resolve(), args.release),
        f'changelog contains a dated section for {version}',
    )


def _dependencies(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Load dependency policy and return failures with its success message.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing ``root`` (:class:`pathlib.Path`), the
        consumer repository.

    Returns
    -------
    tuple[list[str], str]
        Dependency diagnostics and the message to use only on success.

    Raises
    ------
    ConfigurationError
        If loading consumer configuration fails validation.
    OSError
        If the root cannot resolve or an input cannot be read.
    UnicodeError
        If an input cannot be decoded as UTF-8.
    """
    config = load_config(args.root.resolve()).dependencies
    return dependencies.validate(config), 'dependency boundaries are synchronized'


def _docs(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Check the resolved root's Markdown and return failures and success text.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing ``root`` (:class:`pathlib.Path`), the
        consumer repository.

    Returns
    -------
    tuple[list[str], str]
        Markdown diagnostics and the message to use only on success.

    Raises
    ------
    OSError
        If a path cannot resolve or inspected Markdown cannot be read.
    UnicodeError
        If inspected Markdown cannot be decoded as UTF-8.
    """
    return docs.validate(args.root.resolve()), 'local Markdown links are valid'


def _python(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Load Python policy and return failures with its success message.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing ``root`` (:class:`pathlib.Path`), the
        consumer repository.

    Returns
    -------
    tuple[list[str], str]
        Python-policy diagnostics and the message to use only on success.

    Raises
    ------
    ConfigurationError
        If loading consumer configuration fails validation.
    OSError
        If the root cannot resolve or an input cannot be read.
    UnicodeError
        If an input cannot be decoded as UTF-8.
    """
    config = load_config(args.root.resolve()).python_policy
    return python_policy.validate(config), 'Python policy is consistent'


# !SECTION


# SECTION: FUNCTIONS


def create_parser() -> argparse.ArgumentParser:
    """
    Create the complete command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser with supported subcommands, options, and dispatch handlers.
        Constructing the parser does not run repository checks.

    Notes
    -----
    A subcommand is required. Each --root default captures the current working
    directory during construction. Explicit relative --changelog and
    --automation-directory paths are interpreted relative to the working
    directory when dispatched, independently of --root.
    """

    parser = argparse.ArgumentParser(description='Command-line interface for popo.')
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )
    commands = parser.add_subparsers(dest='command', required=True)

    docs_parser = commands.add_parser('check-docs')
    _add_root(docs_parser)
    docs_parser.set_defaults(handler=_docs)

    actions_parser = commands.add_parser('check-github-actions-pins')
    _add_root(actions_parser)
    actions_parser.add_argument('--automation-directory', type=Path)
    actions_parser.set_defaults(handler=_actions)

    automation_parser = commands.add_parser(
        'check-automation-contracts',
        help='Validate automation using consumer tool.popo.automation settings',
    )
    _add_root(automation_parser)
    automation_parser.add_argument(
        '--pins-only',
        action='store_true',
        help='Check parsed references without input, composite, or metadata checks',
    )
    automation_parser.set_defaults(handler=_automation)

    dependency_parser = commands.add_parser('check-dependency-boundaries')
    _add_root(dependency_parser)
    dependency_parser.set_defaults(handler=_dependencies)

    python_parser = commands.add_parser('check-python-policy')
    _add_root(python_parser)
    python_parser.set_defaults(handler=_python)

    changelog_parser = commands.add_parser('check-release-changelog')
    _add_root(changelog_parser)
    changelog_parser.add_argument('release')
    changelog_parser.add_argument('--changelog', type=Path)
    changelog_parser.set_defaults(handler=_changelog)

    all_parser = commands.add_parser('check-all')
    _add_root(all_parser)
    all_parser.set_defaults(handler=_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Run a popo command.

    Parameters
    ----------
    argv : list[str] or None, optional
        Arguments excluding the executable name. When omitted, :mod:`argparse`
        reads the process arguments; an empty list is not treated as omission.

    Returns
    -------
    int
        Zero for a successful check or one for reported validation and
        configuration failures. Results are printed through shared reporting.

    Raises
    ------
    SystemExit
        With status zero for help or version output, or status two for invalid
        arguments. These parser exits are distinct from returned check
        statuses.

    Notes
    -----
    :exc:`~popo.config.ConfigurationError` is converted to a reported failure.
    Other exceptions, including file-read and decoding errors, propagate. Check
    reports go to standard output; :mod:`argparse` handles its own help and
    error streams.
    """

    args = create_parser().parse_args(argv)
    command = cast(Command, args.handler)
    try:
        failures, success = command(args)
    except ConfigurationError as error:
        failures, success = [f'configuration: {error}'], ''
    return report(failures, success=success)


# !SECTION
