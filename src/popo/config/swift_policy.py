"""
:mod:`popo.config.swift_policy` module.

Swift-policy settings and explicit defaults independent of Python metadata.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ._common import (
    ConfigurationError,
    read_popo,
    read_string,
    read_strings,
    require_table,
)

# SECTION: CONSTANTS


IDENTIFIER_PATTERN = re.compile(r'[A-Za-z_][A-Za-z0-9_-]*')
VERSION_PATTERN = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?', re.ASCII)


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class SwiftPolicyConfig:
    """
    Store immutable expected Swift policy and its declaration locations.

    Attributes
    ----------
    root : pathlib.Path
        Resolved consumer root, independent of Popo's Python runtime policy.
    compiler_versions : tuple[str, ...]
        Explicit supported stable compiler versions, not version ranges.
    preferred_version : str
        Expected local compiler selection, normalized to numeric components
        during comparison; not necessarily equal to the tools minimum.
    tools_version : str
        Expected package minimum tools version, compared independently of the
        preferred compiler; not a Swift language-mode setting.
    manifest : pathlib.Path
        Package manifest whose literal first line declares the tools minimum.
        Its contents are read without executing package code.
    version_file : pathlib.Path
        File declaring the preferred local compiler version.
    workflow_globs : tuple[str, ...]
        Nonempty relative workflow selection; every pattern must match.
    workflow_version_key : str
        Action/reusable-workflow input identifying compiler selections.
    require_preferred_in_ci : bool
        Whether at least one resolved CI selection must match the preference.

    Notes
    -----
    The loader bases relative configured paths on the repository root.
    Existence and resolved containment are checked by validation. Direct
    construction does not read files or validate settings or version syntax.
    No language-mode or deployment-target equivalence is inferred.
    """

    root: Path
    compiler_versions: tuple[str, ...]
    preferred_version: str
    tools_version: str
    manifest: Path
    version_file: Path
    workflow_globs: tuple[str, ...]
    workflow_version_key: str = 'swift-version'
    require_preferred_in_ci: bool = True


# !SECTION


# SECTION: FUNCTIONS


def load_swift_policy_config(
    root: Path,
) -> SwiftPolicyConfig:
    """
    Load Swift policy from the selected consumer configuration.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root with standalone or embedded configuration.

    Returns
    -------
    SwiftPolicyConfig
        Internally consistent stable compiler policy and confined path syntax.

    Raises
    ------
    ConfigurationError
        Missing/unknown settings, malformed values, unsupported versions,
        duplicate normalized compilers, or inconsistent minimum/preference.
    OSError, UnicodeError
        Consumer configuration cannot be read/decoded or root cannot resolve.

    Notes
    -----
    Require explicit Swift policy settings in the selected configuration.
    Declaration files are not read or executed, and Python metadata is not
    used to derive defaults.
    """
    root = root.resolve()
    return parse_swift_policy(root, read_popo(root))


def parse_swift_policy(
    root: Path,
    popo: dict[str, object],
) -> SwiftPolicyConfig:
    """
    Parse explicit Swift settings with declaration-path defaults.

    Parameters
    ----------
    root : pathlib.Path
        Repository root used to join configured relative paths; the loader
        supplies a resolved root.
    popo : dict[str, object]
        Parsed Popo settings from the selected policy source.

    Returns
    -------
    SwiftPolicyConfig
        Internally consistent stable compiler policy and confined path syntax.

    Raises
    ------
    ConfigurationError
        Missing/unknown settings, malformed values, unsupported versions,
        duplicate normalized compilers, or inconsistent minimum/preference.

    Notes
    -----
    Require an explicit policy table and reject unknown settings. Validate
    stable numeric compiler versions, preference membership and tools-minimum
    compatibility before constructing the model. Unlike Python policy parsing,
    no dependency metadata is read and no compiler selection is inferred.

    Parsing checks relative path syntax without reading declaration files.
    Existence and resolved containment are checked by the policy checker.
    """
    table = require_table(popo.get('swift-policy'), name='swift-policy')
    defaults = {
        'preferred-version': '',
        'tools-version': '',
        'manifest': 'Package.swift',
        'version-file': '.swift-version',
        'workflow-version-key': 'swift-version',
    }
    if (
        table.keys()
        - defaults.keys()
        - {'compiler-versions', 'workflow-globs', 'require-preferred-in-ci'}
    ):
        raise ConfigurationError('unknown swift-policy setting')
    versions = read_strings(table.get('compiler-versions', []), 'compiler-versions')
    workflows = read_strings(table.get('workflow-globs', []), 'workflow-globs')
    values = {
        key: read_string(table, key, default=default)
        for key, default in defaults.items()
    }
    required = table.get('require-preferred-in-ci', True)
    if not versions or not workflows or type(required) is not bool:
        raise ConfigurationError(
            'Swift policy requires compilers, workflows and a boolean CI preference',
        )
    try:
        normalized = tuple(parse_version(value) for value in versions)
        preferred = parse_version(values['preferred-version'])
        tools = parse_version(values['tools-version'])
    except ValueError as error:
        raise ConfigurationError(
            'Swift policy requires stable numeric versions',
        ) from error
    if (
        len(set(normalized)) != len(normalized)
        or preferred not in normalized
        or any(version < tools for version in normalized)
    ):
        raise ConfigurationError(
            'Swift compiler versions, preference and tools minimum conflict',
        )
    for value in (*workflows, values['manifest'], values['version-file']):
        path = Path(value)
        if path.is_absolute() or '..' in path.parts:
            raise ConfigurationError('Swift policy paths must stay inside root')
    if not IDENTIFIER_PATTERN.fullmatch(values['workflow-version-key']):
        raise ConfigurationError('workflow-version-key must be a literal identifier')
    return SwiftPolicyConfig(
        root=root,
        compiler_versions=versions,
        preferred_version=values['preferred-version'],
        tools_version=values['tools-version'],
        manifest=root / values['manifest'],
        version_file=root / values['version-file'],
        workflow_globs=workflows,
        workflow_version_key=values['workflow-version-key'],
        require_preferred_in_ci=required,
    )


def parse_version(
    value: str,
) -> tuple[int, int, int]:
    """
    Parse stable Swift major.minor[.patch] text without Python specifiers.

    Parameters
    ----------
    value : str
        Version text with optional surrounding whitespace.

    Returns
    -------
    tuple[int, int, int]
        Numeric components; an omitted patch means zero, not a version family.

    Raises
    ------
    ValueError
        Unsupported syntax, including snapshots, suffixes or leading zeroes.
    """
    match = VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError('expected stable Swift major.minor[.patch] version')
    return int(match[1]), int(match[2]), int(match[3] or 0)


# !SECTION
