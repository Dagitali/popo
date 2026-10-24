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
    python_policy,
    safety,
)
from .config import ConfigurationError, load_config
from .config.automation import load_automation_config
from .config.files import load_headers_config, load_required_files_config
from .config.guardrails import load_guardrails_config
from .config.safety import load_safety_config

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
        If the shared configuration loader cannot express dependency metadata
        relative to the consumer root, such as an absolute path outside it.
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


def _guardrail_parity(args: argparse.Namespace) -> tuple[list[str], str]:
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
    ValueError
        If the shared configuration loader cannot express dependency metadata
        relative to the consumer root, such as an absolute path outside it.
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


def _required_files(args: argparse.Namespace) -> tuple[list[str], str]:
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


def _file_headers(args: argparse.Namespace) -> tuple[list[str], str]:
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


# !SECTION


# SECTION: COMMAND REGISTRY


# Registry of native command handlers.
NATIVE_HANDLERS: dict[str, Command] = {
    'check-guardrail-parity': _guardrail_parity,
    'check-required-files': _required_files,
    'check-file-headers': _file_headers,
    'check-docs': _docs,
    'check-github-actions-pins': _actions,
    'check-automation-contracts': _automation,
    'check-repository-safety': _safety,
    'check-dependency-boundaries': _dependencies,
    'check-python-policy': _python,
    'check-release-changelog': _changelog,
}


# !SECTION
