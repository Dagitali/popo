"""
:mod:`popo.checks.swift_policy` module.

Validate Swift toolchain policy without installing or invoking compilers.
"""

import re
from pathlib import Path

from popo.config.swift_policy import SwiftPolicyConfig, parse_version

from ._toolchain_policy import (
    ObservationKind,
    VersionObservation,
    workflow_observations,
)

# SECTION: CONSTANTS


TOOLS_HEADER_PATTERN = re.compile(
    r'^[ \t]*//[ \t]*swift-tools-version:[ \t]*(\S+)[ \t]*$',
)


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _local_observations(
    config: SwiftPolicyConfig,
) -> tuple[list[VersionObservation], list[str]]:
    """
    Collect local compiler and first-line manifest minimum observations.

    Parameters
    ----------
    config : popo.config.swift_policy.SwiftPolicyConfig
        Expected consumer policy and local declaration paths.

    Returns
    -------
    tuple[list[VersionObservation], list[str]]
        Collected declarations and input findings, in configured input order.

    Raises
    ------
    ValueError
        A local declaration path is lexically outside the configured root.

    Notes
    -----
    Keep preferred compiler and tools minimum as distinct observation kinds.
    Return missing, unsafe, unreadable or malformed-header inputs as findings;
    version syntax and equality are checked later. No manifest code is run.
    """
    observations: list[VersionObservation] = []
    failures: list[str] = []
    declarations: tuple[tuple[Path, ObservationKind], ...] = (
        (config.version_file, 'preferred'),
        (config.manifest, 'tools'),
    )
    for path, kind in declarations:
        text, errors = _read_text(path, config.root)
        failures.extend(errors)
        if text is None:
            continue
        if kind == 'tools':
            header = TOOLS_HEADER_PATTERN.fullmatch(
                text.splitlines()[0] if text else '',
            )
            if header is None:
                failures.append(
                    f'{path.relative_to(config.root).as_posix()}: '
                    'missing literal first-line tools version',
                )
                continue
            text = header[1]
        observations.append(
            VersionObservation(path, 'local declaration', text.strip(), kind),
        )
    return observations, failures


def _read_text(
    path: Path,
    root: Path,
) -> tuple[str | None, list[str]]:
    """
    Read one confined UTF-8 input, redacting filesystem error details.

    Parameters
    ----------
    path : pathlib.Path
        UTF-8 version file or package manifest to read without modification.
    root : pathlib.Path
        Repository root for confinement checks.

    Returns
    -------
    tuple[str or None, list[str]]
        Text and no findings on success, or None and a diagnostic for an
        escaping path or a read/decode/resolution error.

    Raises
    ------
    ValueError
        The input path is lexically outside root, which can occur when direct
        construction bypasses the configuration parser.
    """
    relative = path.relative_to(root).as_posix()
    try:
        if not path.resolve().is_relative_to(root):
            return None, [f'{relative}: Swift policy input escapes repository root']
        return path.read_text(encoding='utf-8'), []
    except (OSError, UnicodeError, ValueError):
        return None, [f'{relative}: cannot read Swift policy input']


def _workflow_observations(
    config: SwiftPolicyConfig,
) -> tuple[list[VersionObservation], list[str]]:
    """
    Discover confined workflows and collect scoped compiler observations.

    Parameters
    ----------
    config : popo.config.swift_policy.SwiftPolicyConfig
        Expected consumer policy, workflow globs and version input key.

    Returns
    -------
    tuple[list[VersionObservation], list[str]]
        Collected declarations and discovery/input findings. Observations are
        ordered by sorted file path and then by declaration traversal order.

    Notes
    -----
    Deduplicate and sort files selected by explicit consumer globs. Return
    discovery, containment and scoped YAML errors as findings; version syntax,
    membership and preferred compiler coverage are checked later. No workflow
    is run, and arbitrary expressions are not resolved.
    """
    failures: list[str] = []
    paths: set[Path] = set()
    for pattern in config.workflow_globs:
        try:
            matches = [path for path in config.root.glob(pattern) if path.is_file()]
            if not matches:
                failures.append(f'no Swift policy workflows match: {pattern}')
            paths.update(matches)
        except (OSError, ValueError):
            failures.append('cannot discover Swift policy workflows')
    ci: list[VersionObservation] = []
    for path in sorted(paths):
        try:
            if not path.resolve().is_relative_to(config.root):
                failures.append(
                    f'{path.relative_to(config.root).as_posix()}: '
                    'workflow escapes repository root',
                )
                continue
        except (OSError, ValueError):
            failures.append('cannot resolve Swift policy workflow')
            continue
        values, errors = workflow_observations(path, config.workflow_version_key)
        ci.extend(values)
        failures.extend(
            f'{path.relative_to(config.root).as_posix()}: {error}' for error in errors
        )
    return ci, failures


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: SwiftPolicyConfig,
    *,
    compiler_version: str | None = None,
) -> list[str]:
    """
    Collect declaration drift and optionally compare a Swift compiler version.

    Parameters
    ----------
    config : popo.config.swift_policy.SwiftPolicyConfig
        Explicit consumer compiler policy; no Python metadata is consulted.
    compiler_version : str or None, optional
        Caller-supplied compiler observation. No Swift executable is invoked;
        omission means declaration checking only, not runtime verification.

    Returns
    -------
    list[str]
        Location-based diagnostics for missing, unsafe, malformed, unresolved
        or inconsistent inputs. Input I/O/decode/YAML/version errors are
        returned as findings. Configuration loading happens separately.

    Raises
    ------
    ValueError
        Configured compiler, preferred or tools versions have invalid syntax
        when direct construction bypasses the configuration parser. Invalid
        observed versions instead produce diagnostics. A local declaration
        path lexically outside root also propagates ValueError.

    Notes
    -----
    Compare stable numeric compiler versions, preferred local selection and
    the package's literal first-line tools-version header independently. Tools
    version is a minimum, not compiler equality or a language-mode setting.
    Workflow references use scoped env/simple matrix observations. No manifest,
    action, workflow, compiler, formatter or network operation is executed.
    Language modes, deployment targets and dependency resolution are outside
    this check. Explicit observed compilers need membership, not preference.
    """
    observations, failures = _local_observations(config)
    ci, errors = _workflow_observations(config)
    failures.extend(errors)
    observations.extend(ci)
    if compiler_version is not None:
        observations.append(
            VersionObservation(None, '--compiler-version', compiler_version),
        )
    allowed = {parse_version(value) for value in config.compiler_versions}
    preferred = parse_version(config.preferred_version)
    expected = {'preferred': preferred, 'tools': parse_version(config.tools_version)}
    ci_sources = {item.source for item in ci}
    ci_versions: set[tuple[int, int, int]] = set()
    for item in observations:
        label = (
            item.location
            if item.source is None
            else f'{item.source.relative_to(config.root).as_posix()}: {item.location}'
        )
        try:
            version = parse_version(item.value)
        except ValueError:
            failures.append(f'{label}: invalid stable Swift version')
            continue
        if item.kind == 'compiler' and item.source in ci_sources:
            ci_versions.add(version)
        if item.kind == 'compiler' and version not in allowed:
            failures.append(f'{label}: compiler version is not supported by policy')
        elif item.kind != 'compiler' and version != expected[item.kind]:
            failures.append(f'{label}: {item.kind} version differs from policy')
    if ci_versions and config.require_preferred_in_ci and preferred not in ci_versions:
        failures.append('Swift CI declarations do not include the preferred compiler')
    return failures


# !SECTION
