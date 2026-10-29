"""
:mod:`tests.support.guardrails` module.

Build isolated consumers with an explicit local/CI guardrail contract.
"""

from pathlib import Path

import pytest

from popo.config.guardrails import GuardrailsConfig, load_guardrails_config
from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture(
    name='guardrail_arguments',
    params=[
        pytest.param(('check-guardrail-parity',), id='standalone'),
        pytest.param(('check-all',), id='default-selection'),
        pytest.param(('check-all', '--profile', 'guardrails'), id='named-profile'),
    ],
)
def guardrail_arguments_fixture(
    request: pytest.FixtureRequest,
) -> tuple[str, ...]:
    """
    Select one command per consumer, including self-inspecting profiles.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Selected standalone, default-selection or named-profile invocation.

    Returns
    -------
    tuple[str, ...]
        Command and profile switches, without root or output-format options.
        Named-profile cases run the exact profile delegated to Make. They
        inspect declarations without executing the Make recipe.
    """
    return tuple(str(argument) for argument in request.param)


@pytest.fixture(name='guardrail_consumer')
def guardrail_consumer_fixture(
    write_file: FileWriter,
    tmp_path: Path,
) -> GuardrailsConfig:
    """
    Provide matching Make, local-hook and workflow entry points.

    Parameters
    ----------
    write_file : FileWriter
        Fixture writing UTF-8 files beneath the temporary consumer root.
    tmp_path : Path
        Per-test temporary directory supplied by pytest.

    Returns
    -------
    GuardrailsConfig
        Consumer configuration pointing to isolated Make, hook and CI inputs.
    """
    write_file(
        'popo.toml',
        """checks=["check-guardrail-parity"]
[profiles.guardrails]
checks=["check-docs","check-guardrail-parity"]
[guardrails]
""",
    )
    write_file('Makefile', 'guardrails:\n\tpopo check-all --profile guardrails\n')
    write_file(
        '.pre-commit-config.yaml',
        """repos:
  - repo: local
    hooks:
      - id: popo
        name: Repository guardrails
        entry: make guardrails
        language: system
        always_run: true
        pass_filenames: false
""",
    )
    write_file(
        '.github/workflows/ci.yml',
        """name: Guardrails
on: [push]
jobs:
  guardrails:
    runs-on: ubuntu-latest
    steps:
      - id: popo
        run: make guardrails
""",
    )
    return load_guardrails_config(tmp_path)


@pytest.fixture(name='guardrail_diagnostics')
def guardrail_diagnostics_fixture(
    guardrail_consumer: GuardrailsConfig,
) -> dict[str, str]:
    """
    Describe expected contract failures independently of checker execution.

    Parameters
    ----------
    guardrail_consumer : GuardrailsConfig
        Isolated consumer supplying paths and literal invocation identifiers.

    Returns
    -------
    dict[str, str]
        Complete public diagnostics for each supported kind of wiring drift.
        Keeping the oracle here lets unit, CLI and installed tests assert the
        same contract without importing private checker helpers.
    """
    config = guardrail_consumer
    command = f'popo check-all --profile {config.profile}'
    return {
        'target': f'{config.makefile}: require one literal {config.target}: target',
        'make': (
            f'{config.makefile}: {config.target} recipe must be exactly {command!r}'
        ),
        'hook': (
            f'{config.hooks}: {config.hook} must be one local system hook invoking '
            f'make {config.target} with always_run=true and pass_filenames=false, '
            'without args'
        ),
        'workflow': (
            f'{config.workflow}: {config.job}/{config.step} '
            f'must run make {config.target}'
        ),
        'directory': (
            f'{config.workflow}: guardrail invocation must use the repository root'
        ),
    }


@pytest.fixture(
    name='guardrail_failure',
    params=['matching', 'make', 'hook', 'workflow'],
)
def guardrail_failure_fixture(
    request: pytest.FixtureRequest,
    guardrail_consumer: GuardrailsConfig,
    guardrail_diagnostics: dict[str, str],
) -> str | None:
    """
    Prepare one isolated drift scenario and return its expected diagnostic.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Selected matching, Make, hook or workflow scenario.
    guardrail_consumer : GuardrailsConfig
        Fresh consumer mutated only during scenario preparation.
    guardrail_diagnostics : dict[str, str]
        Complete expected messages, independent of the validator.

    Returns
    -------
    str or None
        Expected failure, or ``None`` when all declared entry points match.
    """
    scenario = str(request.param)
    if scenario == 'matching':
        return None
    path, before, after = {
        'make': (guardrail_consumer.makefile, '\tpopo check-all', '\tfalse #'),
        'hook': (guardrail_consumer.hooks, 'entry: make ', 'entry: other '),
        'workflow': (guardrail_consumer.workflow, 'run: make ', 'run: other '),
    }[scenario]
    content = path.read_text(encoding='utf-8')
    assert content.count(before) == 1, f'Scenario marker must occur once in {path}'
    path.write_text(content.replace(before, after), encoding='utf-8')
    return guardrail_diagnostics[scenario]


# !SECTION
