"""
:mod:`popo.cli` module.

Command-line interface for popo.
"""

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import yaml

from . import __version__
from .checks import (
    actionlint,
    actions,
    automation,
    changelog,
    dependencies,
    docs,
    files,
    guardrails,
    hosted,
    python_policy,
    safety,
)
from .config import ConfigurationError, load_config
from .config.automation import load_automation_config
from .config.files import load_headers_config, load_required_files_config
from .config.guardrails import load_guardrails_config
from .config.hosted import load_hosted_config
from .config.safety import load_safety_config
from .config.selection import load_plan
from .reporting import CheckResult, report_results
from .support import report

# SECTION: TYPE ALIASES


type Command = Callable[[argparse.Namespace], tuple[list[str], str]]


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


def _automation(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
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


def _guardrail_parity(args: argparse.Namespace) -> tuple[list[str], str]:
    """Inspect explicit local and CI invocation contracts without execution."""
    return guardrails.validate(
        load_guardrails_config(args.root),
    ), 'guardrail entry points agree'


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


def _safety(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Dispatch opt-in read-only safety validation.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed consumer root.

    Returns
    -------
    tuple[list[str], str]
        Diagnostics and success-only message.
    """
    config = load_safety_config(args.root)
    if not config.configured:
        raise ConfigurationError('check-repository-safety requires tool.popo.safety')
    return safety.validate(config), 'configured repository safety checks passed'


def _required_files(args: argparse.Namespace) -> tuple[list[str], str]:
    """Dispatch configured required-file validation.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed consumer root.

    Returns
    -------
    tuple[list[str], str]
        Failures and a success-only summary.

    Raises
    ------
    ConfigurationError
        If the policy is absent or malformed.
    """
    config = load_required_files_config(args.root)
    if config is None:
        raise ConfigurationError('check-required-files requires tool.popo.files')
    return files.validate_required(config), 'required files are present'


def _file_headers(args: argparse.Namespace) -> tuple[list[str], str]:
    """Dispatch configured header validation.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed consumer root.

    Returns
    -------
    tuple[list[str], str]
        Failures and a success-only summary.

    Raises
    ------
    ConfigurationError
        If the policy is absent or malformed.
    """
    config = load_headers_config(args.root)
    if config is None:
        raise ConfigurationError('check-file-headers requires tool.popo.headers')
    return files.validate_headers(config), 'configured file headers are valid'


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

    handlers: dict[str, Command | None] = {
        'check-guardrail-parity': _guardrail_parity,
        'check-required-files': _required_files,
        'check-file-headers': _file_headers,
        'check-docs': _docs,
        'check-github-actions-pins': _actions,
        'check-automation-contracts': _automation,
        'check-repository-safety': _safety,
        'check-actionlint': None,
        'check-dependency-boundaries': _dependencies,
        'check-python-policy': _python,
        'check-release-changelog': _changelog,
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
    validators. Reuse their argument defaults for each selected handler.
    """
    plan = load_plan(args.root, args.profile)
    parser = create_parser()
    results: list[CheckResult] = []
    for check in plan.checks:
        selected = parser.parse_args([check, '--root', str(args.root)])
        results.append(_invoke(selected))
    return results


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
        Zero for a successful check or one for reported validation and
        configuration failures. Results are printed through shared reporting.
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
    Other exceptions, including file-read and decoding errors, propagate. Check
    reports go to standard output; :mod:`argparse` handles its own help and
    error streams.
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
