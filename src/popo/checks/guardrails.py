"""
:mod:`popo.checks.guardrails` module.

Inspect literal guardrail entry points without executing consumer code.
"""

from pathlib import Path
from typing import cast

import yaml

from ..config.guardrails import GuardrailsConfig
from ._yaml import WorkflowLoader

# SECTION: PROTECTED FUNCTIONS


def _hooks(
    config: GuardrailsConfig,
) -> list[str]:
    """Require a local system hook that checks the entire repository."""
    document = _read_yaml(config.hooks)
    matches = [
        (repo.get('repo'), hook)
        for repo in map(_mapping, _items(document.get('repos')))
        for hook in map(_mapping, _items(repo.get('hooks')))
        if hook.get('id') == config.hook
    ]
    expected = {
        'entry': f'make {config.target}',
        'language': 'system',
        'pass_filenames': False,
        'always_run': True,
    }
    if len(matches) == 1:
        repository, hook = matches[0]
        if (
            repository == 'local'
            and all(
                type(hook.get(key)) is type(value) and hook.get(key) == value
                for key, value in expected.items()
            )
            and hook.get('args', []) == []
        ):
            return []
    return [
        f'{config.hooks}: {config.hook} must be one local system hook invoking '
        f'make {config.target} with always_run=true and pass_filenames=false, '
        'without args',
    ]


def _items(
    value: object,
) -> list[object]:
    """Read list-valued YAML fields without iterating scalars or mappings."""
    return cast(list[object], value) if isinstance(value, list) else []


def _make(
    config: GuardrailsConfig,
) -> list[str]:
    """
    Require one literal target with one canonical profile invocation.

    Non-recipe Make comments and blank lines do not terminate a recipe block.
    Tab-prefixed comments remain recipe entries under this literal contract.
    """
    lines = config.makefile.read_text(encoding='utf-8').splitlines()
    targets = [i for i, line in enumerate(lines) if line == f'{config.target}:']
    command = f'popo check-all --profile {config.profile}'
    if len(targets) != 1:
        return [f'{config.makefile}: require one literal {config.target}: target']
    recipe: list[str] = []
    for line in lines[targets[0] + 1 :]:
        if not line.strip() or line.lstrip(' ').startswith('#'):
            continue
        if not line.startswith('\t'):
            break
        recipe.append(line.strip().removeprefix('@'))
    if recipe != [command]:
        return [
            f'{config.makefile}: {config.target} recipe must be exactly {command!r}',
        ]
    return []


def _mapping(
    value: object,
) -> dict[str, object]:
    """Treat unexpected YAML shapes as absent contract fields."""
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _read_yaml(
    path: Path,
) -> dict[str, object]:
    """
    Read safe YAML with duplicate-key rejection and literal workflow keys.
    """
    return _mapping(yaml.load(path.read_text(encoding='utf-8'), Loader=WorkflowLoader))


def _workflow(
    config: GuardrailsConfig,
) -> list[str]:
    """Require the declared job's step to delegate to the same Make target."""
    document = _read_yaml(config.workflow)
    job = _mapping(_mapping(document.get('jobs')).get(config.job))
    matches = [
        step
        for value in _items(job.get('steps'))
        if (step := _mapping(value)).get('id') == config.step
    ]
    for owner in (document, job, *matches):
        directory = _mapping(_mapping(owner.get('defaults')).get('run')).get(
            'working-directory',
            '.',
        )
        if directory not in ('.', './') or owner.get('working-directory', '.') not in (
            '.',
            './',
        ):
            return [
                f'{config.workflow}: guardrail invocation must use the repository root',
            ]
    if (
        len(matches) != 1
        or not isinstance(matches[0].get('run'), str)
        or str(matches[0]['run']).strip() != f'make {config.target}'
        or 'uses' in matches[0]
    ):
        return [
            f'{config.workflow}: {config.job}/{config.step} '
            f'must run make {config.target}',
        ]
    return []


# !SECTION


# SECTION: FUNCTION


def validate(
    config: GuardrailsConfig,
) -> list[str]:
    """Check explicit invocation contracts and collect independent failures.

    Parameters
    ----------
    config : GuardrailsConfig
        Validated consumer paths, identifiers and profile.

    Returns
    -------
    list[str]
        Missing inputs, malformed YAML and literal invocation mismatches.
        File I/O, decoding, YAML and value errors become diagnostics. No Make,
        hook, workflow or package code is executed; network is never accessed.

    Notes
    -----
    This checks declared wiring, not shell equivalence or hosted enforcement.
    Includes, variables, conditional execution and tool installation are
    outside this contract; consumers retain responsibility for their execution
    context.
    """
    failures: list[str] = []
    for check in (_make, _hooks, _workflow):
        try:
            failures.extend(check(config))
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
            failures.append(f'guardrail parity: {error}')
    return failures


# !SECTION
