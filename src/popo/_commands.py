"""
:mod:`popo._commands` module.

Native offline check adapters, argument defaults, and shared dispatch registry.
"""

import argparse
from collections.abc import Callable

from .checks import (
    actions,
    automation,
    changelog,
    dependencies,
    docs,
    files,
    guardrails,
    logs,
    python_boundaries,
    python_policy,
    python_source,
    safety,
    swift_boundaries,
    swift_policy,
    swift_source,
    test_results,
)
from .config import ConfigurationError, load_config
from .config.automation import load_automation_config
from .config.files import load_headers_config, load_required_files_config
from .config.guardrails import load_guardrails_config
from .config.python_boundaries import load_python_boundaries_config
from .config.python_policy import load_python_policy_config
from .config.safety import load_safety_config
from .config.source_checks import load_source_check
from .config.swift_boundaries import load_swift_boundaries_config
from .config.swift_policy import load_swift_policy_config
from .config.test_results import load_test_results_config

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
        an optional ``automation_directory`` (:class:`pathlib.Path` or
        ``None``); absence uses the default discovery directory.

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
    directory = getattr(args, 'automation_directory', None)
    if directory is None:
        directory = args.root.resolve() / '.github'
    return actions.validate(directory.resolve()), 'remote actions are immutably pinned'


def _automation(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Return configured automation diagnostics without printing.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed ``root`` and optional ``pins_only`` options. An absent
        ``pins_only`` option defaults to false for aggregate execution.

    Returns
    -------
    tuple[list[str], str]
        Contract diagnostics and the success message.

    Raises
    ------
    ConfigurationError
        Invalid consumer configuration, reported by :func:`~popo.cli.main`.
    OSError, UnicodeError
        If consumer configuration cannot be read or decoded, or its root
        cannot resolve. Validator-caught file errors remain diagnostics.
    """
    config = load_automation_config(args.root)
    return automation.validate(
        config,
        pins_only=getattr(args, 'pins_only', False),
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
    ValueError
        If the Python-policy loader cannot express dependency metadata relative
        to the consumer root, such as an absolute path outside it.
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
    ValueError
        If a Markdown destination is rejected by URL parsing, such as an
        invalid bracketed host. This error propagates rather than becoming
        a validation diagnostic.
    """
    return docs.validate(args.root.resolve()), 'local Markdown links are valid'


def _file_headers(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Dispatch configured header validation.

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
    OSError, UnicodeError
        If consumer configuration cannot be read or decoded, or its root
        cannot resolve. Validator-caught file errors remain diagnostics.
    """
    config = load_headers_config(args.root)
    if config is None:
        raise ConfigurationError('check-file-headers requires tool.popo.headers')
    return files.validate_headers(config), 'configured file headers are valid'


def _guardrail_parity(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Inspect explicit local and CI invocation contracts without execution.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed consumer root used to load the parity contract.

    Returns
    -------
    tuple[list[str], str]
        Contract diagnostics and a success-only summary. File, decoding, YAML
        and value errors caught by the validator are returned as diagnostics.

    Raises
    ------
    ConfigurationError
        If the parity policy is absent or malformed, paths or identifiers are
        unsafe, or the selected profile is invalid.
    OSError
        If the consumer root or configured paths cannot resolve, or consumer
        configuration cannot be read.
    UnicodeError
        If consumer configuration cannot be decoded as UTF-8.
    """
    return guardrails.validate(
        load_guardrails_config(args.root),
    ), 'guardrail entry points agree'


def _logs(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """Dispatch explicit artifact inspection without revealing log contents."""
    config = load_source_check(args.root, 'logs')
    return logs.validate(
        config,
        getattr(args, 'log_root', None),
    ), 'configured logs passed'


def _python_boundaries(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Dispatch consumer-owned Python architecture restrictions.

    Parameters
    ----------
    args : argparse.Namespace
        Explicit consumer repository root.

    Returns
    -------
    tuple[list[str], str]
        AST boundary findings and success-only summary.

    Raises
    ------
    ConfigurationError
        Boundary policy is absent or malformed.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    config = load_python_boundaries_config(args.root)
    return python_boundaries.validate(config), 'configured Python boundaries passed'


def _python_policy(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Load Python policy and return findings with a success summary.

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
    ValueError
        If the Python-policy loader cannot express dependency metadata relative
        to the consumer root, such as an absolute path outside it.
    """
    config = load_python_policy_config(args.root.resolve())
    return python_policy.validate(config), 'Python policy is consistent'


def _python_source(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Load Python source policy and return findings with a success summary.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing the consumer repository root.

    Returns
    -------
    tuple[list[str], str]
        Source-check findings and a summary to display only on success.

    Raises
    ------
    ConfigurationError
        The explicit python-source policy is missing or invalid.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded, or root resolution
        fails. Inspected input errors are returned as findings by the checker.

    Notes
    -----
    Dispatch the shared source-selection policy to the language-specific
    validator. Consumer source and development tools are not executed.
    """
    config = load_source_check(args.root, 'python-source')
    return python_source.validate(config), 'configured Python source checks passed'


def _required_files(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Dispatch configured required-file validation.

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
    OSError, UnicodeError
        If consumer configuration cannot be read or decoded, or its root
        cannot resolve. Validator-caught file errors remain diagnostics.
    """
    config = load_required_files_config(args.root)
    if config is None:
        raise ConfigurationError('check-required-files requires tool.popo.files')
    return files.validate_required(config), 'required files are present'


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

    Raises
    ------
    ConfigurationError
        If safety policy is absent or malformed.
    OSError, UnicodeError
        If consumer configuration cannot be read or decoded, or its root
        cannot resolve. Validator-caught file errors remain diagnostics.
    """
    config = load_safety_config(args.root)
    if not config.configured:
        raise ConfigurationError('check-repository-safety requires tool.popo.safety')
    return safety.validate(config), 'configured repository safety checks passed'


def _swift_policy(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Load Swift policy and return findings with a success summary.

    Parameters
    ----------
    args : argparse.Namespace
        Consumer root and optional compiler_version string. Aggregate checks
        omit the observation and do not invoke Swift to infer one.

    Returns
    -------
    tuple[list[str], str]
        Declaration/runtime-observation diagnostics and success-only summary.

    Raises
    ------
    ConfigurationError
        If the opt-in Swift policy is absent or invalid.
    OSError, UnicodeError
        If loading consumer configuration fails; inspected input errors are
        returned as diagnostics by the validator.
    """
    config = load_swift_policy_config(args.root)
    return swift_policy.validate(
        config,
        compiler_version=getattr(args, 'compiler_version', None),
    ), 'Swift toolchain declarations are consistent'


def _swift_source(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Load Swift source policy and return findings with a success summary.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing the consumer repository root.

    Returns
    -------
    tuple[list[str], str]
        Source-check findings and a summary to display only on success.

    Raises
    ------
    ConfigurationError
        The explicit swift-source policy is missing or invalid.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded, or root resolution
        fails. Inspected input errors are returned as findings by the checker.

    Notes
    -----
    Dispatch the shared source-selection policy to the language-specific
    validator. Consumer source and development tools are not executed.
    """
    config = load_source_check(args.root, 'swift-source')
    return swift_source.validate(config), 'configured Swift source checks passed'


def _swift_boundaries(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Dispatch consumer-owned Swift architecture restrictions.

    Parameters
    ----------
    args : argparse.Namespace
        Explicit consumer repository root.

    Returns
    -------
    tuple[list[str], str]
        Lexical boundary findings and success-only summary.

    Raises
    ------
    ConfigurationError
        Boundary policy is absent or malformed.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    config = load_swift_boundaries_config(args.root)
    return swift_boundaries.validate(config), 'configured Swift boundaries passed'


def _test_results(
    args: argparse.Namespace,
) -> tuple[list[str], str]:
    """
    Dispatch configured native-result acceptance checks without running tests.

    Parameters
    ----------
    args : argparse.Namespace
        Consumer root and optional results_root or summary artifact override.

    Returns
    -------
    tuple[list[str], str]
        Redacted findings and success-only summary.

    Raises
    ------
    ConfigurationError
        Result policy is absent or malformed.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    config = load_test_results_config(args.root)
    return test_results.validate(
        config,
        getattr(args, 'results_root', None),
        getattr(args, 'summary', None),
    ), 'configured test results passed'


# !SECTION


# SECTION: COMMAND REGISTRY


# Registry of native command handlers.
NATIVE_HANDLERS: dict[str, Command] = {
    'check-test-results': _test_results,
    'check-swift-boundaries': _swift_boundaries,
    'check-python-boundaries': _python_boundaries,
    'check-python-source': _python_source,
    'check-swift-source': _swift_source,
    'check-swift-policy': _swift_policy,
    'check-logs': _logs,
    'check-guardrail-parity': _guardrail_parity,
    'check-required-files': _required_files,
    'check-file-headers': _file_headers,
    'check-docs': _docs,
    'check-github-actions-pins': _actions,
    'check-automation-contracts': _automation,
    'check-repository-safety': _safety,
    'check-dependency-boundaries': _dependencies,
    'check-python-policy': _python_policy,
    'check-release-changelog': _changelog,
}


# !SECTION
