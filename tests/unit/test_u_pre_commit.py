"""
:mod:`tests.unit.test_u_pre_commit` module.

Protect local hook interpreter selection and filename handling.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

# SECTION: FIXTURES


@pytest.fixture(
    name='hook_config',
    scope='module',
)
def hook_config_fixture(
    repository_root: Path,
) -> dict[str, Any]:
    """
    Parse hook configuration once and index its local hooks.

    Parameters
    ----------
    repository_root : pathlib.Path
        Checkout containing the pre-commit configuration.

    Returns
    -------
    dict[str, typing.Any]
        Configuration with a local hook index for contract assertions.

    Raises
    ------
    OSError, UnicodeError, yaml.YAMLError
        If configuration cannot be read or parsed.
    """
    config = yaml.safe_load(
        (repository_root / '.pre-commit-config.yaml').read_text(encoding='utf-8'),
    )
    config['local_hooks'] = {
        hook['id']: hook
        for repo in config['repos']
        if repo['repo'] == 'local'
        for hook in repo['hooks']
    }
    return config


# !SECTION


# SECTION: TESTS


class TestLocalHooks:
    """
    Protect hook interpreter, stage, and filename contracts.

    Notes
    -----
    Inspect configuration without installing or executing hooks.
    """

    @pytest.mark.parametrize(
        ('hook_id', 'entry'),
        [
            ('ruff-check', 'python -m ruff check'),
            ('ruff-format', 'python -m ruff format --check'),
        ],
        ids=['lint', 'format'],
    )
    def test_ruff_hooks(
        self,
        hook_config: dict[str, Any],
        repository_root: Path,
        hook_id: str,
        entry: str,
    ) -> None:
        """
        Pin managed Ruff hooks to the development dependency contract.

        Parameters
        ----------
        hook_config : dict[str, typing.Any]
            Parsed pre-commit configuration.
        repository_root : pathlib.Path
            Checkout containing canonical dependency metadata.
        hook_id : str
            Local Ruff hook to inspect.
        entry : str
            Expected interpreter and Ruff invocation.
        """
        metadata = tomllib.loads(
            (repository_root / 'pyproject.toml').read_text(encoding='utf-8'),
        )
        ruff_requirement = next(
            value
            for value in metadata['project']['optional-dependencies']['dev']
            if value.startswith('ruff>=')
        )
        hook = hook_config['local_hooks'][hook_id]
        assert hook['entry'] == entry
        assert hook['language'] == 'python'
        assert hook_config['default_language_version']['python'] == 'python3'
        assert hook['additional_dependencies'] == [ruff_requirement]
        assert hook.get('pass_filenames', True) is True
        assert hook['types_or'] == ['python', 'pyi']

    @pytest.mark.parametrize(
        ('hook_id', 'entry', 'stage'),
        [
            ('popo-self-check', 'make self-check', 'pre-commit'),
            ('make-check-pre-push', 'make check-pre-push', 'pre-push'),
        ],
        ids=['self-check', 'pre-push'],
    )
    def test_system_hooks(
        self,
        hook_config: dict[str, Any],
        hook_id: str,
        entry: str,
        stage: str,
    ) -> None:
        """
        Require Make-based hooks to validate the entire checkout.

        Parameters
        ----------
        hook_config : dict[str, typing.Any]
            Parsed pre-commit configuration.
        hook_id : str
            Local system hook to inspect.
        entry : str
            Expected Make command.
        stage : str
            Expected execution stage.
        """
        hook = hook_config['local_hooks'][hook_id]
        assert hook['entry'] == entry
        assert hook['language'] == 'system'
        assert hook['pass_filenames'] is False
        assert hook['always_run'] is True
        assert hook.get('stages', hook_config['default_stages']) == [stage]
        assert 'pre-push' in hook_config['default_install_hook_types']


# !SECTION
