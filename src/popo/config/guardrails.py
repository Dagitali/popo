"""
:mod:`popo.config.guardrails` module.

Load an explicit Make, pre-commit and workflow invocation contract.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ._common import ConfigurationError, read_popo, read_string, require_table
from .selection import parse_plan

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class GuardrailsConfig:
    """
    Store root-confined inputs and literal invocation identifiers.

    Attributes
    ----------
    root : pathlib.Path
        Resolved consumer repository boundary.
    makefile, hooks, workflow : pathlib.Path
        Resolved input paths confined to root; existence is checked later.
    target : str
        Literal Make target delegating to the selected Popo profile.
    hook : str
        Unique local pre-commit hook ID that invokes the Make target.
    job, step : str
        Workflow job and step IDs identifying the CI invocation.
    profile : str
        Explicit profile whose check selection was validated during loading.

    Notes
    -----
    Direct construction does not validate paths, identifiers, or profiles.
    """

    root: Path
    makefile: Path
    hooks: Path
    workflow: Path
    target: str
    hook: str
    job: str
    step: str
    profile: str


# !SECTION


# SECTION: FUNCTIONS


def load_guardrails_config(
    root: Path,
) -> GuardrailsConfig:
    """Validate a consumer-owned parity contract without executing commands.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository root.

    Returns
    -------
    GuardrailsConfig
        Explicit paths, identifiers and a validated profile selection.

    Raises
    ------
    ConfigurationError
        Absent or malformed configuration, unknown keys, unsafe paths or names,
        or an invalid selected profile. Profiles may select this read-only
        parity checker: inspection never invokes the declared commands.
    OSError, UnicodeError
        Unreadable configuration or paths that cannot resolve.
    """
    root = root.resolve()
    settings = read_popo(root)
    table = require_table(settings.get('guardrails'), name='guardrails')
    defaults = {
        'makefile': 'Makefile',
        'hooks': '.pre-commit-config.yaml',
        'workflow': '.github/workflows/ci.yml',
        'target': 'guardrails',
        'hook': 'popo',
        'job': 'guardrails',
        'step': 'popo',
        'profile': 'guardrails',
    }
    if set(table) - set(defaults):
        raise ConfigurationError('unknown guardrails setting')
    values = {
        key: read_string(table, key, default=value) for key, value in defaults.items()
    }
    for key in ('target', 'hook', 'job', 'step', 'profile'):
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*', values[key]):
            raise ConfigurationError(f'guardrails.{key} must be a literal identifier')
    paths: dict[str, Path] = {}
    for key in ('makefile', 'hooks', 'workflow'):
        relative = Path(values[key])
        resolved = (root / relative).resolve()
        if (
            relative.is_absolute()
            or '..' in relative.parts
            or not resolved.is_relative_to(root)
        ):
            raise ConfigurationError(
                f'guardrails.{key} must stay inside the repository',
            )
        paths[key] = resolved
    parse_plan(root, settings, values['profile'])
    return GuardrailsConfig(
        root,
        paths['makefile'],
        paths['hooks'],
        paths['workflow'],
        values['target'],
        values['hook'],
        values['job'],
        values['step'],
        values['profile'],
    )


# !SECTION
