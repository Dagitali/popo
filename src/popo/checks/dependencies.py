"""
:mod:`popo.checks.dependencies` module.

Validate dependency metadata against installer or constraint inputs.
"""

import re
import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from popo.config import DependencyConfig

# SECTION: PROTECTED FUNCTIONS


def _constraint_versions(
    constraints: dict[str, Requirement],
    source: Path,
) -> tuple[dict[str, str], list[str]]:
    """
    Extract version text from constraints containing one equality specifier.

    Parameters
    ----------
    constraints : dict[str, packaging.requirements.Requirement]
        Parsed requirements keyed by normalized package name.
    source : pathlib.Path
        Input path used to label diagnostics; not read by this helper.

    Returns
    -------
    tuple[dict[str, str], list[str]]
        Accepted names mapped to their ``==`` version text and diagnostics
        for URL requirements, multiple specifiers, or other operators.
        Partial results are retained when some constraints are rejected.

    Notes
    -----
    This helper extracts text, not installed versions. It does not evaluate
    environment markers or extras, or separately reject wildcard equality text.
    """
    versions: dict[str, str] = {}
    failures: list[str] = []
    for name, requirement in constraints.items():
        specifiers = list(requirement.specifier)
        if requirement.url is not None or len(specifiers) != 1:
            failures.append(
                f'{source}: constraint must use name==version: {requirement!s}',
            )
            continue
        specifier = specifiers[0]
        if specifier.operator != '==':
            failures.append(
                f'{source}: constraint must use name==version: {requirement!s}',
            )
            continue
        versions[name] = specifier.version
    return versions, failures


def _minimum_versions(
    dependencies: dict[str, Requirement],
    source: Path,
) -> tuple[dict[str, str], list[str]]:
    """
    Extract declared lower-bound text while enforcing bounded dependencies.

    Parameters
    ----------
    dependencies : dict[str, packaging.requirements.Requirement]
        Parsed runtime requirements keyed by normalized package name.
    source : pathlib.Path
        Input path used to label diagnostics; not read by this helper.

    Returns
    -------
    tuple[dict[str, str], list[str]]
        Accepted names mapped to their single ``>=`` bound and diagnostics
        for requirements with URLs, no unique lower bound, or no ``<``/``<=``
        upper bound. Valid entries remain in the result when others fail.

    Notes
    -----
    Bounds are inspected structurally, not solved for satisfiability. Markers
    and extras are not evaluated, and other specifier operators may coexist.
    """
    versions: dict[str, str] = {}
    failures: list[str] = []
    for name, requirement in dependencies.items():
        lower = [
            item.version for item in requirement.specifier if item.operator == '>='
        ]
        upper = [item for item in requirement.specifier if item.operator in {'<', '<='}]
        if requirement.url is not None or len(lower) != 1 or not upper:
            failures.append(
                f'{source}: dependency must declare one >= lower bound and an upper '
                f'bound: {str(requirement)!r}',
            )
            continue
        versions[name] = lower[0]
    return versions, failures


def _requirement_lines(
    path: Path,
) -> tuple[list[str], list[str]]:
    """
    Read requirement declarations and collect unsupported installer directives.

    Parameters
    ----------
    path : pathlib.Path
        UTF-8 requirements or constraints file.

    Returns
    -------
    tuple[list[str], list[str]]
        Stripped nonempty declarations and diagnostics for lines beginning
        with ``-``. Diagnostics retain the original one-based line numbers.

    Raises
    ------
    OSError
        If the requirements file cannot be read.
    UnicodeError
        If requirements text cannot be decoded as UTF-8.

    Notes
    -----
    Blank lines and full-line comments are ignored. Inline comments begin
    with whitespace followed by ``#``; adjacent URL fragments are preserved.
    Includes, installer options, and line continuations are not expanded.
    Requirement syntax is validated separately by _requirements.
    """
    values: list[str] = []
    failures: list[str] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding='utf-8').splitlines(),
        start=1,
    ):
        value = re.split(r'\s+#', raw_line, maxsplit=1)[0].strip()
        if not value or value.startswith('#'):
            continue
        if value.startswith('-'):
            failures.append(
                f'{path}:{line_number}: installer directives are not supported: '
                f'{value!r}',
            )
            continue
        values.append(value)
    return values, failures


def _requirements(
    values: list[str],
    source: Path,
) -> tuple[dict[str, Requirement], list[str]]:
    """
    Parse declarations and reject duplicate normalized package names.

    Parameters
    ----------
    values : list[str]
        Requirement declarations after comment and directive processing.
    source : pathlib.Path
        Input path used to label diagnostics; not read by this helper.

    Returns
    -------
    tuple[dict[str, packaging.requirements.Requirement], list[str]]
        Parsed requirements indexed by canonicalized name, plus diagnostics
        for invalid declarations or duplicate names. The first valid entry
        wins when spelling, extras, or markers produce the same package key.

    Notes
    -----
    Partial results accompany failures. Environment markers are retained,
    not evaluated against the checker runtime.
    """
    parsed: dict[str, Requirement] = {}
    failures: list[str] = []
    for value in values:
        try:
            requirement = Requirement(value)
        except InvalidRequirement as error:
            failures.append(f'{source}: invalid requirement {value!r}: {error}')
            continue
        name = canonicalize_name(requirement.name)
        if name in parsed:
            failures.append(f'{source}: duplicate dependency {name!r}')
            continue
        parsed[name] = requirement
    return parsed, failures


# !SECTION


def validate(
    config: DependencyConfig,
) -> list[str]:
    """
    Return dependency-boundary policy violations.

    Parameters
    ----------
    config : popo.config.DependencyConfig
        Metadata and requirements paths, plus the selected comparison mode.

    Returns
    -------
    list[str]
        Missing-input, parsing, requirement, or consistency failures; empty
        when the declarations satisfy the configured policy.

    Raises
    ------
    OSError
        If an existing metadata or requirements file cannot be read.
    UnicodeError
        If either input cannot be decoded as UTF-8.

    Notes
    -----
    Exact mode compares normalized requirement declarations. Minimum-constraints
    mode compares declared lower bounds with exact fixture pins. Neither mode
    installs packages or verifies the currently installed dependency versions.

    Only project.dependencies is inspected, not optional dependencies or
    dependency groups. Environment markers are not evaluated: exact mode
    retains them in declaration comparisons, while minimum-constraints mode
    compares extracted bounds without using markers or extras to select entries.
    Missing inputs, invalid TOML, and parsing or bound-extraction failures
    return before the final mapping comparison.
    """

    missing = [
        path for path in (config.metadata, config.requirements) if not path.is_file()
    ]
    if missing:
        return [f'dependency-policy file does not exist: {path}' for path in missing]
    try:
        document = tomllib.loads(config.metadata.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as error:
        return [f'{config.metadata}: invalid TOML: {error}']
    raw_dependencies = document.get('project', {}).get('dependencies', [])
    if not isinstance(raw_dependencies, list) or not all(
        isinstance(value, str) for value in raw_dependencies
    ):
        return [f'{config.metadata}: project.dependencies must be a string array']
    expected, failures = _requirements(raw_dependencies, config.metadata)
    lines, line_failures = _requirement_lines(config.requirements)
    actual, requirement_failures = _requirements(lines, config.requirements)
    failures.extend(line_failures)
    failures.extend(requirement_failures)
    if failures:
        return failures
    if config.mode == 'exact':
        normalized_expected = {name: str(value) for name, value in expected.items()}
        normalized_actual = {name: str(value) for name, value in actual.items()}
    else:
        normalized_expected, expected_failures = _minimum_versions(
            expected,
            config.metadata,
        )
        normalized_actual, actual_failures = _constraint_versions(
            actual,
            config.requirements,
        )
        failures.extend(expected_failures)
        failures.extend(actual_failures)
        if failures:
            return failures
    if normalized_expected != normalized_actual:
        failures.append(
            f'{config.requirements}: expected {normalized_expected!r}; '
            f'received {normalized_actual!r}',
        )
    return failures


# !SECTION
