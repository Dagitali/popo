"""
:mod:`tests.unit.config.test_u_guardrails` module.

Validate explicit invocation identifiers and confined contract inputs.
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.config import ConfigurationError, guardrails, selection
from popo.config._common import read_popo
from popo.config.guardrails import GuardrailsConfig, load_guardrails_config
from tests.support.files import FileWriter

# SECTION: TESTS


class TestGuardrailConfiguration:
    """Reject ambiguous or unsafe entry-point settings before inspection."""

    @pytest.mark.parametrize(
        'attribute,relative',
        [
            ('makefile', 'Makefile'),
            ('hooks', '.pre-commit-config.yaml'),
            ('workflow', '.github/workflows/ci.yml'),
        ],
    )
    def test_defaults(
        self,
        guardrail_consumer: GuardrailsConfig,
        attribute: str,
        relative: str,
    ) -> None:
        """
        Resolve each default path under the consumer root.

        Parameters
        ----------
        guardrail_consumer : GuardrailsConfig
            Isolated consumer paths and guardrail parity expectations.
        attribute : str
            Attribute whose observation is replaced in this scenario.
        relative : str
            Repository-relative path used in diagnostics or input selection.
        """
        assert guardrail_consumer.target == 'guardrails'
        assert (
            getattr(guardrail_consumer, attribute) == guardrail_consumer.root / relative
        )

    @pytest.mark.parametrize(
        'settings,message',
        [
            ('', 'table'),
            ('guardrails=[]', 'table'),
            ('[guardrails]\nunknown=true', 'unknown guardrails setting'),
            ('[guardrails]\ntarget="make check"', 'literal identifier'),
            ('[guardrails]\nhook=""', 'non-empty string'),
            ('[guardrails]\nworkflow="../ci.yml"', 'inside the repository'),
            ('[guardrails]\nworkflow="/tmp/ci.yml"', 'inside the repository'),
            ('[guardrails]\nprofile="missing"', 'unknown profile'),
        ],
    )
    def test_invalid_settings(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        settings: str,
        message: str,
    ) -> None:
        """
        Fail configuration rather than resolving unsafe paths or commands.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        settings : str
            Consumer policy text inserted into the scenario.
        message : str
            Expected error message or scenario diagnostic.
        """
        write_file('popo.toml', settings)
        with pytest.raises(ConfigurationError, match=message):
            load_guardrails_config(tmp_path)

    def test_self_inspecting_profile(
        self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """
        The delegated profile may inspect its own inert invocation contract.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        write_file(
            'popo.toml',
            '[profiles.guardrails]\nchecks=["check-guardrail-parity"]\n[guardrails]',
        )
        assert load_guardrails_config(tmp_path).profile == 'guardrails'

    @pytest.mark.parametrize('attribute', ('makefile', 'hooks', 'workflow'))
    def test_symlink_escape(
        self,
        guardrail_consumer: GuardrailsConfig,
        symlink: Callable[[Path, Path], None],
        attribute: str,
    ) -> None:
        """
        Resolved contract paths must remain within the consumer root.

        Parameters
        ----------
        guardrail_consumer : GuardrailsConfig
            Isolated consumer paths and guardrail parity expectations.
        symlink : Callable[[Path, Path], None]
            Platform-aware fixture creating a symbolic link or skipping
            support.
        attribute : str
            Attribute whose observation is replaced in this scenario.
        """
        path = getattr(guardrail_consumer, attribute)
        path.unlink()
        symlink(path, guardrail_consumer.root.parent / 'outside')
        with pytest.raises(ConfigurationError, match='inside the repository'):
            load_guardrails_config(guardrail_consumer.root)


class TestGuardrailConfigurationSnapshot:
    """Validate entry points and their profile from one configuration read."""

    @pytest.mark.parametrize('filename', ('popo.toml', 'pyproject.toml'))
    def test_profile_uses_the_same_snapshot(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        filename: str,
    ) -> None:
        """
        Do not combine entry points with a subsequently changed profile.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        filename : str
            Input filename used in the scenario.
        """
        prefix = '' if filename == 'popo.toml' else 'tool.popo.'
        (tmp_path / filename).write_text(
            f'[{prefix}guardrails]\n'
            f'[{prefix}profiles.guardrails]\nchecks=["check-docs"]',
            encoding='utf-8',
        )
        original = read_popo(tmp_path)
        reader = Mock(side_effect=[original, {}])
        monkeypatch.setattr(guardrails, 'read_popo', reader)
        monkeypatch.setattr(selection, 'read_popo', reader)
        assert load_guardrails_config(tmp_path).profile == 'guardrails'
        reader.assert_called_once_with(tmp_path)
        assert original['profiles'] == {'guardrails': {'checks': ['check-docs']}}


# !SECTION
