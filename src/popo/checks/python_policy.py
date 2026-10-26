"""
:mod:`popo.checks.python_policy` module.

Validate a repository's declared Python-version policy.
"""

import re
import sys
import tomllib
from pathlib import Path
from typing import cast

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from popo.config import PythonPolicyConfig
from popo.support import automation_paths

from ._toolchain_policy import workflow_observations

# SECTION: CONSTANTS


ENV_REFERENCE_PATTERN = re.compile(r'\$\{\{\s*env\.([A-Z][A-Z0-9_]*)\s*}}')
MATRIX_REFERENCE_PATTERN = re.compile(
    r'\$\{\{\s*matrix\.([A-Za-z][A-Za-z0-9_-]*)\s*}}',
)
WORKFLOW_VERSION_PATTERN = re.compile(
    r'^[ \t]*python-version:[ \t]*(.+?)[ \t]*$',
    re.MULTILINE,
)


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _local_findings(
    config: PythonPolicyConfig,
) -> list[str]:
    """
    Compare local metadata, tool settings and the preferred version file.

    Read shared package/Ruff metadata once, reporting a single parse failure.
    Missing files and invalid TOML become findings; read/decode errors
    propagate.
    Exact text comparisons are intentional, unlike workflow range membership.
    """
    failures: list[str] = []
    metadata, metadata_failures = _read_toml(config.metadata)
    failures.extend(metadata_failures)
    if metadata is not None:
        project = _table(metadata.get('project'))
        mypy = _table(_table(metadata.get('tool')).get('mypy'))
        if project.get('requires-python') != config.requires_python:
            failures.append(
                f'{config.metadata}: project.requires-python must equal '
                f'{config.requires_python!r}',
            )
        if mypy.get('python_version') != config.mypy_python_version:
            failures.append(
                f'{config.metadata}: tool.mypy.python_version must equal '
                f'{config.mypy_python_version!r}',
            )

    ruff = metadata
    if config.ruff_config != config.metadata:
        ruff, ruff_failures = _read_toml(config.ruff_config)
        failures.extend(ruff_failures)
    if ruff is not None:
        if config.ruff_config == config.metadata:
            value = _table(_table(ruff.get('tool')).get('ruff')).get(
                'target-version',
            )
        else:
            value = ruff.get('target-version')
        if value != config.ruff_target_version:
            failures.append(
                f'{config.ruff_config}: Ruff target-version must equal '
                f'{config.ruff_target_version!r}',
            )

    if not config.python_version_file.is_file():
        failures.append(
            f'Python-policy file does not exist: {config.python_version_file}',
        )
    elif config.python_version_file.read_text(encoding='utf-8').strip() != (
        config.python_version
    ):
        failures.append(
            f'{config.python_version_file}: expected {config.python_version!r}',
        )

    return failures


def _normalize_scalar(
    value: str,
) -> str:
    """
    Strip a space-prefixed comment and matching outer quotes from a scalar.

    Parameters
    ----------
    value : str
        Textual workflow value; this is not parsed as a YAML scalar.

    Returns
    -------
    str
        Text before the first literal space-plus-# sequence, trimmed, with
        matching single or double outer quotes removed. Comment stripping
        is not quote-aware and escape sequences are not interpreted.
    """
    value = value.split(' #', maxsplit=1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _read_toml(
    path: Path,
) -> tuple[dict[str, object] | None, list[str]]:
    """
    Read TOML, returning a document and no failures on success.

    Parameters
    ----------
    path : pathlib.Path
        UTF-8 TOML input to read without modification.

    Returns
    -------
    tuple[dict[str, object] or None, list[str]]
        Parsed document and an empty failure list, or ``None`` and a diagnostic
        when the path is not a file or TOML parsing fails.

    Raises
    ------
    OSError
        If the existing file cannot be read.
    UnicodeError
        If the input cannot be decoded as UTF-8.
    """
    if not path.is_file():
        return None, [f'Python-policy file does not exist: {path}']
    try:
        return tomllib.loads(path.read_text(encoding='utf-8')), []
    except tomllib.TOMLDecodeError as error:
        return None, [f'{path}: invalid TOML: {error}']


def _resolve_versions(
    value: str,
    content: str,
) -> tuple[str, ...]:
    """
    Resolve supported textual version declarations without evaluating YAML.

    Parameters
    ----------
    value : str
        Normalized scalar, inline list, or env/matrix reference to resolve.
    content : str
        Complete workflow text searched for a referenced declaration.

    Returns
    -------
    tuple[str, ...]
        Inline-list values, a referenced environment value, or values from
        an inline or contiguous block-list matrix. An unresolved recognized
        reference returns an empty tuple; other values are returned unchanged
        as a single item for subsequent version validation.

    Notes
    -----
    Searches select the first matching declaration in the text, without
    modeling YAML scope, job boundaries, matrix include/exclude rules, or
    general expression evaluation. Resolved values are not recursively
    expanded.
    """
    if value.startswith('[') and value.endswith(']'):
        return tuple(_normalize_scalar(item) for item in value[1:-1].split(','))
    if env_match := ENV_REFERENCE_PATTERN.fullmatch(value):
        name = re.escape(env_match.group(1))
        declaration = re.search(
            rf'^[ \t]*{name}:[ \t]*(.+?)[ \t]*$',
            content,
            re.MULTILINE,
        )
        return () if declaration is None else (_normalize_scalar(declaration.group(1)),)
    if matrix_match := MATRIX_REFERENCE_PATTERN.fullmatch(value):
        name = re.escape(matrix_match.group(1))
        declaration = re.search(
            rf'^[ \t]*{name}:[ \t]*\[(?P<values>[^]]+)\]',
            content,
            re.MULTILINE,
        )
        if declaration is not None:
            return tuple(
                _normalize_scalar(item)
                for item in declaration.group('values').split(',')
            )
        declaration = re.search(
            rf'^[ \t]+{name}:[ \t]*$'
            rf'(?P<items>(?:\n[ \t]+-[ \t]+[^\n]+)+)',
            content,
            re.MULTILINE,
        )
        if declaration is None:
            return ()
        values = re.findall(
            r'^[ \t]+-[ \t]+(.+?)[ \t]*$',
            declaration.group('items'),
            re.MULTILINE,
        )
        return tuple(_normalize_scalar(item) for item in values)
    return (value,)


def _table(
    value: object,
) -> dict[str, object]:
    """
    Return a dictionary unchanged, or an empty mapping for other values.

    Parameters
    ----------
    value : object
        Candidate nested configuration table.

    Returns
    -------
    dict[str, object]
        Original dictionary without entry validation, or a new empty mapping.
        Non-dictionary values do not raise
        :exc:`~popo.config.ConfigurationError` here.
    """
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _workflow_findings(
    config: PythonPolicyConfig,
    supported: SpecifierSet,
) -> list[str]:
    """
    Collect workflow declaration and version-range findings in file order.

    Keep each file's parse findings before its unsupported-version findings.
    Legacy text mode propagates read/decode errors and requires inputs only
    when a setup-python action marker is present. Scoped mode reports
    read/decode errors and requires inputs in each file.
    Neither mode executes workflows or resolves arbitrary expressions.
    """
    failures: list[str] = []
    if not config.workflow_directory.is_dir():
        failures.append(
            f'workflow directory does not exist: {config.workflow_directory}',
        )
        return failures
    paths = automation_paths(config.workflow_directory)
    if config.workflow_parser == 'scoped' and not paths:
        failures.append('no Python policy workflows found')
    for path in paths:
        if config.workflow_parser == 'scoped':
            observations, errors = workflow_observations(path, 'python-version')
            failures.extend(f'{path}: {error}' for error in errors)
            configured = [observation.value for observation in observations]
        else:
            content = path.read_text(encoding='utf-8')
            configured = [
                resolved
                for raw in map(
                    _normalize_scalar,
                    WORKFLOW_VERSION_PATTERN.findall(content),
                )
                for resolved in (_resolve_versions(raw, content) or (raw,))
            ]
            if 'actions/setup-python@' in content and not configured:
                failures.append(f'{path}: setup-python requires an explicit version')
        for value in configured:
            try:
                accepted = Version(value) in supported
            except InvalidVersion:
                accepted = False
            if not accepted:
                failures.append(f'{path}: unsupported Python version {value!r}')
    return failures


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: PythonPolicyConfig,
    *,
    running_version: str | None = None,
) -> list[str]:
    """
    Collect declaration drift and compare the Python runtime version.

    Parameters
    ----------
    config : popo.config.PythonPolicyConfig
        Expected consumer policy and paths to metadata, tool configuration,
        the version file, and automation files.
    running_version : str or None, optional
        Runtime version to check. When absent or empty, use the running
        interpreter's major and minor version.

    Returns
    -------
    list[str]
        Policy, input, runtime, tool, and workflow inconsistencies; empty
        when the inspected declarations satisfy the configured policy.

    Raises
    ------
    packaging.version.InvalidVersion
        If an explicitly supplied, nonempty ``running_version`` is not a valid
        version. Invalid workflow versions instead produce diagnostics.
    OSError
        If an existing input cannot be read.
    UnicodeError
        If an input cannot be decoded as UTF-8.

    Notes
    -----
    Consumer policy is supplied by the configuration, not inferred from Popo's
    own supported-version range. This check does not install interpreters.
    Metadata specifier text, mypy and Ruff settings, and the stripped version
    file are compared exactly with configured expectations. Runtime and
    resolved workflow versions are tested for membership in the configured
    specifier set. Default workflow resolution uses text and supports literals,
    inline lists, environment references, and inline or contiguous block-list
    matrices; it does not evaluate arbitrary expressions or model job-local
    YAML scope. Optional scoped mode uses the shared strict YAML observer,
    requires version inputs per file, and reports unresolved declarations or
    unsupported matrices without guessing. Workflow read/decode errors become
    diagnostics in scoped mode; legacy text mode propagates them.
    Unresolved environment and matrix references produce version
    diagnostics even when other declarations resolve. Shared package/Ruff
    metadata is read once per validation, including a single parse diagnostic.
    """

    try:
        supported = SpecifierSet(config.requires_python)
    except InvalidSpecifier as error:
        return [f'invalid requires-python policy {config.requires_python!r}: {error}']
    active_version = running_version or (
        f'{sys.version_info.major}.{sys.version_info.minor}'
    )
    failures: list[str] = []
    if Version(active_version) not in supported:
        failures.append(
            f'checker runtime: Python {config.requires_python} is required; '
            f'received {active_version}',
        )

    failures.extend(_local_findings(config))
    failures.extend(_workflow_findings(config, supported))
    return failures


# !SECTION
