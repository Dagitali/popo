"""
:mod:`popo.cli` module.

Command-line interface for popo.
"""

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import cast

from popo import __version__
from popo.checks import actions, changelog, dependencies, docs, python_policy
from popo.config import ConfigurationError, load_config
from popo.support import report

# SECTION: TYPE ALIASES


Command = Callable[[argparse.Namespace], tuple[list[str], str]]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _actions(args: argparse.Namespace) -> tuple[list[str], str]:
    directory = args.automation_directory
    if directory is None:
        directory = args.root.resolve() / '.github'
    return actions.validate(directory.resolve()), 'remote actions are immutably pinned'


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--root',
        type=Path,
        default=Path.cwd(),
        help='Repository root (default: current directory)',
    )


def _all(args: argparse.Namespace) -> tuple[list[str], str]:
    root = args.root.resolve()
    config = load_config(root)
    failures = [
        *docs.validate(root),
        *actions.validate(root / '.github'),
        *dependencies.validate(config.dependencies),
        *python_policy.validate(config.python_policy),
    ]
    return failures, 'all configured repository checks passed'


def _changelog(args: argparse.Namespace) -> tuple[list[str], str]:
    path = args.changelog
    if path is None:
        path = args.root.resolve() / 'CHANGELOG.md'
    version = args.release.removeprefix('v')
    return (
        changelog.validate(path.resolve(), args.release),
        f'changelog contains a dated section for {version}',
    )


def _dependencies(args: argparse.Namespace) -> tuple[list[str], str]:
    config = load_config(args.root.resolve()).dependencies
    return dependencies.validate(config), 'dependency boundaries are synchronized'


def _docs(args: argparse.Namespace) -> tuple[list[str], str]:
    return docs.validate(args.root.resolve()), 'local Markdown links are valid'


def _python(args: argparse.Namespace) -> tuple[list[str], str]:
    config = load_config(args.root.resolve()).python_policy
    return python_policy.validate(config), 'Python policy is consistent'


# !SECTION


# SECTION: FUNCTIONS


def create_parser() -> argparse.ArgumentParser:
    """Create the complete command-line parser."""

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
    """Run a popo command."""

    args = create_parser().parse_args(argv)
    command = cast(Command, args.handler)
    try:
        failures, success = command(args)
    except ConfigurationError as error:
        failures, success = [f'configuration: {error}'], ''
    return report(failures, success=success)


# !SECTION
