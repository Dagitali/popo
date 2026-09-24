"""
:mod:`tests.unit.test_pre_commit` module.

Protect local hook interpreter selection and filename handling.
"""

import tomllib
from pathlib import Path

import pytest
import yaml

# SECTION: TESTS


class TestLocalHooks:
    """Keep hooks usable without a bare Python executable on the caller's PATH."""

    @pytest.mark.parametrize(
        'hook_id',
        ['popo-self-check', 'ruff-check', 'ruff-format'],
    )
    def test_interpreter_and_scope(self, repository_root: Path, hook_id: str) -> None:
        config = yaml.safe_load(
            (repository_root / '.pre-commit-config.yaml').read_text(encoding='utf-8'),
        )
        hook = next(
            hook
            for repo in config['repos']
            if repo['repo'] == 'local'
            for hook in repo['hooks']
            if hook['id'] == hook_id
        )
        if hook_id == 'popo-self-check':
            assert hook['entry'] == 'make self-check'
            assert hook['language'] == 'system'
            assert hook['pass_filenames'] is False
            assert hook['always_run'] is True
        else:
            metadata = tomllib.loads(
                (repository_root / 'pyproject.toml').read_text(encoding='utf-8'),
            )
            requirement = next(
                value
                for value in metadata['project']['optional-dependencies']['dev']
                if value.startswith('ruff>=')
            )
            assert hook['language'] == 'python'
            assert config['default_language_version']['python'] == 'python3'
            assert hook['additional_dependencies'] == [requirement]
            assert hook.get('pass_filenames', True) is True
            assert hook['types_or'] == ['python', 'pyi']
            assert hook['entry'] == (
                'python -m ruff check'
                if hook_id == 'ruff-check'
                else 'python -m ruff format --check'
            )


# !SECTION
