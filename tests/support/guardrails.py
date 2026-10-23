"""Build isolated consumers with an explicit local/CI guardrail contract."""

from pathlib import Path

import pytest

from popo.config.guardrails import GuardrailsConfig, load_guardrails_config
from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture
def guardrail_consumer(
    write_file: FileWriter,
    tmp_path: Path,
) -> GuardrailsConfig:
    """Provide matching Make, local-hook and workflow entry points."""
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


# !SECTION
