"""
:mod:`popo.checks._toolchain_policy` module.

Observe scoped workflow toolchain declarations without execution.
"""

import re
from collections import ChainMap
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from ._yaml import read_mapping, require_mapping

# SECTION: CONSTANTS


IDENTIFIER_PATTERN = re.compile(r'[A-Za-z_][A-Za-z0-9_-]*')
REFERENCE_PATTERN = re.compile(r'\$\{\{\s*(env|matrix)\.([A-Za-z_][A-Za-z0-9_-]*)\s*}}')


# !SECTION


# SECTION: TYPE ALIASES


type ObservationKind = Literal['runtime', 'compiler', 'preferred', 'tools']


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class VersionObservation:
    """
    Retain a version's source, selector and interpretation.

    Attributes
    ----------
    source : pathlib.Path or None
        Input file, or None for an explicitly supplied compiler observation.
        Native adapters retain provenance even for legacy textual readers.
    location : str
        Field selector or CLI option identifying the observation. Legacy Python
        text uses an input key without claiming YAML scope.
    value : str
        Declared version text; language-specific comparison validates it.
    kind : ObservationKind
        Runtime, compiler, preferred local selection or package tools version.
    """

    source: Path | None
    location: str
    value: str
    kind: ObservationKind = 'compiler'


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _literal(
    value: object,
) -> str:
    """Require nonblank string versions without nested expressions."""
    if not isinstance(value, str) or not value.strip() or '${{' in value:
        raise ValueError('expected literal string version')
    return value.strip()


def _resolve(
    value: object,
    workflow: dict[str, object],
    job: dict[str, object],
    step: dict[str, object],
) -> tuple[str, ...]:
    """Resolve only literals, scoped environment values and simple matrices."""
    if not isinstance(value, str):
        raise ValueError('expected string version')
    match = REFERENCE_PATTERN.fullmatch(value.strip())
    if match is None:
        return (_literal(value),)
    scope, name = match.groups()
    if scope == 'env':
        environments = [
            require_mapping(owner.get('env', {}), 'env')
            for owner in (workflow, job, step)
        ]
        environment = ChainMap(*reversed(environments))
        return (_literal(environment.get(name)),)
    strategy = require_mapping(job.get('strategy', {}), 'strategy')
    matrix = require_mapping(strategy.get('matrix', {}), 'matrix')
    if {'include', 'exclude'} & matrix.keys():
        raise ValueError('matrix include/exclude are unsupported')
    values = matrix.get(name)
    if not isinstance(values, list) or not values:
        raise ValueError('expected a nonempty matrix list')
    return tuple(_literal(item) for item in values)


# !SECTION


# SECTION: FUNCTIONS


def workflow_observations(
    path: Path,
    key: str,
    *,
    kind: ObservationKind = 'compiler',
) -> tuple[tuple[VersionObservation, ...], list[str]]:
    """
    Read selected action/reusable-workflow inputs with scoped provenance.

    Parameters
    ----------
    path : pathlib.Path
        UTF-8 workflow file; callers enforce the repository boundary.
    key : str
        Literal input key, such as python-version or swift-version.
    kind : ObservationKind, optional
        Interpretation supplied by the caller; no tool identity is inferred.

    Returns
    -------
    tuple[tuple[VersionObservation, ...], list[str]]
        Observations and redacted diagnostics, relative to this input file.
        Read, decode, YAML, shape and resolution errors become diagnostics.

    Notes
    -----
    Inspect jobs.*.with and jobs.*.steps[*].with. Environment precedence is
    workflow, job, then step. Matrix references use only their own job's
    strategy. General expressions, recursive references and include/exclude
    expansion are unsupported. Every selected file must declare the input.
    This does not prove workflow execution, trigger coverage or tool identity.
    No workflow, action or manifest code is executed.
    """
    observations: list[VersionObservation] = []
    failures: list[str] = []
    found = False
    try:
        workflow = read_mapping(path)
        jobs = require_mapping(workflow.get('jobs', {}), 'jobs')
        for job_id, value in jobs.items():
            if not IDENTIFIER_PATTERN.fullmatch(job_id):
                raise ValueError('invalid job identifier')
            job = require_mapping(value, 'job')
            steps = job.get('steps', [])
            if not isinstance(steps, list):
                raise ValueError('steps must be a list')
            owners = [(f'jobs.{job_id}.with', job)]
            owners.extend(
                (f'jobs.{job_id}.steps[{index}].with', require_mapping(step, 'step'))
                for index, step in enumerate(steps)
            )
            for location, owner in owners:
                inputs = require_mapping(owner.get('with', {}), 'with')
                if key not in inputs:
                    continue
                found = True
                selector = f'{location}.{key}'
                try:
                    versions = _resolve(inputs[key], workflow, job, owner)
                except ValueError:
                    failures.append(
                        f'{selector}: unresolved or unsupported version declaration',
                    )
                    continue
                observations.extend(
                    VersionObservation(path, selector, version, kind)
                    for version in versions
                )
    except (OSError, UnicodeError, ValueError, yaml.YAMLError):
        failures.append('cannot read a valid workflow version declaration')
    if not found and not failures:
        failures.append(f'no explicit {key} declarations')
    return tuple(observations), failures


# !SECTION
