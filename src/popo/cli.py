"""
:mod:`popo.cli` module.

Command-line interface for popo.
"""

import argparse
import json
from pathlib import Path
from typing import cast

import yaml

from . import __version__
from ._commands import NATIVE_HANDLERS, Command
from .checks import actionlint, hosted
from .config import ConfigurationError
from .config.hosted import load_hosted_config
from .config.selection import load_plan
from .reporting import CheckResult, report_results
from .support import report

# SECTION: PROTECTED FUNCTIONS


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

    Raises
    ------
    OSError
        If a root-option default cannot obtain the current working directory.

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

    handlers: dict[str, Command | None] = {
        **NATIVE_HANDLERS,
        'check-actionlint': None,
        'check-all': None,
        'audit-github-settings': None,
        'explain': None,
    }
    help_text = {
        'check-automation-contracts': (
            'Validate automation using consumer tool.popo.automation settings'
        ),
        'check-repository-safety': (
            'Check opt-in privileged triggers, shell interpolation, and npm pairs'
        ),
        'check-actionlint': (
            'Run actionlint with temporary self-reference compatibility'
        ),
        'audit-github-settings': 'Explicit read-only hosted drift audit (requires gh)',
    }
    parsers: dict[str, argparse.ArgumentParser] = {}
    for name, handler in handlers.items():
        subparser = (
            commands.add_parser(name, help=help_text[name])
            if name in help_text
            else commands.add_parser(name)
        )
        _add_root(subparser)
        if name not in ('check-actionlint', 'audit-github-settings'):
            subparser.add_argument('--format', choices=('text', 'json'), default='text')
        if name in ('check-all', 'explain'):
            subparser.add_argument(
                '--profile',
                help='Explicit configured check profile',
            )
        if handler is not None:
            subparser.set_defaults(handler=handler)
        parsers[name] = subparser

    parsers['check-github-actions-pins'].add_argument(
        '--automation-directory',
        type=Path,
    )
    parsers['check-automation-contracts'].add_argument(
        '--pins-only',
        action='store_true',
        help='Check parsed references without input, composite, or metadata checks',
    )
    parsers['check-actionlint'].add_argument('--actionlint', default='actionlint')
    parsers['check-actionlint'].add_argument('paths', nargs='*')
    parsers['check-release-changelog'].add_argument('release')
    parsers['check-release-changelog'].add_argument('--changelog', type=Path)
    parsers['audit-github-settings'].add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
    )
    return parser


def _selected_results(args: argparse.Namespace) -> list[CheckResult]:
    """Execute selected offline checks and retain each check's identity.

    Explicit checks or a named profile replace the baseline selection.
    Otherwise retain documentation, action-pin, dependency and Python-policy
    checks plus configured opt-in domains. Preserve declaration order and
    continue after reported validation or domain configuration failures; other
    exceptions propagate. Release checks need a version and remain separate,
    as do external-tool and hosted checks. Constructing parsers does not run
    validators. Native adapters supply their own optional argument defaults,
    so aggregate execution does not reconstruct or reparse command lines.
    """
    plan = load_plan(args.root, args.profile)
    return [
        _invoke(
            argparse.Namespace(
                command=check,
                root=args.root,
                handler=NATIVE_HANDLERS[check],
            ),
        )
        for check in plan.checks
    ]


def _invoke(args: argparse.Namespace) -> CheckResult:
    """
    Convert a native check's configuration errors into identified results.
    """
    command = cast(Command, args.handler)
    try:
        failures, success = command(args)
    except ConfigurationError as error:
        failures, success = [f'configuration: {error}'], ''
    return CheckResult(args.command, tuple(failures), success)


def _explain(args: argparse.Namespace) -> int:
    """Describe selection and provenance without running any validators."""
    plan = load_plan(args.root, args.profile)
    explanation = {
        'schema_version': 1,
        'root': str(args.root.resolve()),
        'configuration': str(plan.source),
        'configuration_exists': plan.source.exists(),
        'selection': plan.reason,
        'checks': list(plan.checks),
    }
    if args.format == 'json':
        print(json.dumps(explanation))
    else:
        print(f'Configuration: {plan.source}')
        print(f'Selection: {plan.reason}')
        for check in plan.checks:
            print(f'  {check}')
    return 0


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
        Zero for a successful check or explanation, or one for reported
        validation and configuration failures. Native check results use shared
        text or JSON reporting; explanation reports selection without checks.
        check-actionlint instead returns the exact external validator status.
        audit-github-settings returns one for drift or inaccessible evidence;
        approved, unexpired exceptions do not fail the audit.

    Raises
    ------
    SystemExit
        With status zero for help or version output, or status two for invalid
        arguments. These parser exits are distinct from returned check
        statuses.

    Notes
    -----
    :exc:`~popo.config.ConfigurationError` is converted to a reported failure.
    Native adapters may return I/O and decoding errors as diagnostics;
    uncaught exceptions propagate. Check reports go to standard output;
    :mod:`argparse` handles its own help and error streams.
    check-actionlint reports source/tool errors as status one and preserves
    the external linter's streams and exact returned exit status.
    audit-github-settings is an explicit network operation, excluded from
    check-all. It prints sanitized text or JSON findings to standard output.
    """

    args = create_parser().parse_args(argv)
    if args.command == 'audit-github-settings':
        try:
            result = hosted.audit(load_hosted_config(args.root))
        except (ConfigurationError, OSError, UnicodeError) as error:
            if args.format == 'json':
                print(json.dumps({'error': f'configuration: {error}'}))
                return 1
            return report([f'configuration: {error}'], success='')
        if args.format == 'json':
            print(result.to_json())
        else:
            print(f'GitHub settings audit: {result.observed_at}')
            for item in result.findings:
                print(f'{item.status}: {item.repository} {item.check}: {item.detail}')
                print(f'  evidence: {item.evidence}')
        return int(result.failed)
    if args.command == 'check-actionlint':
        try:
            return actionlint.run(args.root, args.paths, args.actionlint)
        except (
            ConfigurationError,
            OSError,
            UnicodeError,
            ValueError,
            yaml.YAMLError,
        ) as error:
            return report([f'actionlint: {error}'], success='')
    try:
        if args.command == 'explain':
            return _explain(args)
        results = (
            _selected_results(args) if args.command == 'check-all' else [_invoke(args)]
        )
    except ConfigurationError as error:
        results = [CheckResult('configuration', (f'configuration: {error}',), '')]
    return report_results(args.command, results, args.format)


# !SECTION
