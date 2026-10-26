"""
:mod:`tests.unit.configs.test_u_guardrails` module.

Validate explicit invocation identifiers and confined contract inputs.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.guardrails import GuardrailsConfig, load_guardrails_config
from tests.support.files import FileWriter

# SECTION: TESTS


class TestGuardrailConfiguration:
    """Reject ambiguous or unsafe entry-point settings before inspection."""

    def test_defaults(
        self,
        guardrail_consumer: GuardrailsConfig,
    ) -> None:
        """Resolve each default path under the consumer root."""
        assert guardrail_consumer.target == 'guardrails'
        assert guardrail_consumer.makefile == guardrail_consumer.root / 'Makefile'

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
        """
        write_file(
            'popo.toml',
            '[profiles.guardrails]\nchecks=["check-guardrail-parity"]\n[guardrails]',
        )
        assert load_guardrails_config(tmp_path).profile == 'guardrails'

    def test_symlink_escape(
        self,
        guardrail_consumer: GuardrailsConfig,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """Resolved contract paths must remain within the consumer root."""
        path = guardrail_consumer.makefile
        path.unlink()
        symlink(path, guardrail_consumer.root.parent / 'outside')
        with pytest.raises(ConfigurationError, match='inside the repository'):
            load_guardrails_config(guardrail_consumer.root)


# !SECTION
