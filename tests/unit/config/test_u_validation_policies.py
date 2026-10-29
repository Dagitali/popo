"""
:mod:`tests.unit.config.test_u_validation_policies` module.

Reject malformed result and Python/Swift architecture configuration.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.config._common import ConfigurationError
from popo.config.source_boundaries import load_boundaries_config
from popo.config.swift_boundaries import load_swift_boundaries_config
from popo.config.test_results import load_test_results_config

# SECTION: CONSTANTS


RESULT_SETTINGS = 'adapter="xcode-summary"\ninclude=["*.json"]'


# !SECTION


# SECTION: TESTS


class TestResultPolicy:
    """Keep adapter selection explicit and counts strongly typed."""

    @pytest.mark.parametrize(
        'settings,message',
        (
            ('', 'adapter must be xcode-summary'),
            ('adapter="unknown"\ninclude=["*.json"]', 'adapter must be xcode-summary'),
            ('adapter="xcode-summary"\ninclude=[]', 'include must not be empty'),
            (
                'adapter="xcode-summary"\ninclude=["../*.json"]',
                'include must stay inside the selected root',
            ),
            (RESULT_SETTINGS + '\nquery="arbitrary"', 'unknown test-results setting'),
        ),
    )
    def test_invalid_result_policy(
        self: Self,
        tmp_path: Path,
        settings: str,
        message: str,
    ) -> None:
        """
        Reject unknown formats, unsafe selection and unsupported settings.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        settings : str
            Standalone TOML settings deliberately violating loader contracts.
        message : str
            Diagnostic identifying the intended invalid configuration field.
        """
        (tmp_path / 'popo.toml').write_text('[test-results]\n' + settings)
        with pytest.raises(ConfigurationError, match=message):
            load_test_results_config(tmp_path)

    @pytest.mark.parametrize(
        'field',
        (
            'minimum-tests',
            'minimum-passed',
            'maximum-failed',
            'maximum-skipped',
            'maximum-warnings',
        ),
    )
    @pytest.mark.parametrize('value', ('true', '-1', '"1"', '1.0'))
    def test_thresholds_require_nonnegative_integers(
        self,
        tmp_path: Path,
        field: str,
        value: str,
    ) -> None:
        """
        Reject boolean, negative, string and float values for every count.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        field : str
            Configuration or report field selected for mutation.
        value : str
            Unvalidated value supplied to the operation.
        """
        (tmp_path / 'popo.toml').write_text(
            f'[test-results]\n{RESULT_SETTINGS}\n{field}={value}',
            encoding='utf-8',
        )
        with pytest.raises(
            ConfigurationError,
            match=rf'test-results\.{field} requires a nonnegative integer',
        ):
            load_test_results_config(tmp_path)


class TestBoundaryPolicy:
    """
    Keep graph references, imports and paths consumer-owned and bounded.

    Apply common policy contracts independently of language syntax.
    """

    @pytest.mark.parametrize('language', ('python', 'swift'))
    @pytest.mark.parametrize(
        'settings,message',
        (
            ('', 'layers must be a nonempty array'),
            ('layers=[]', 'layers must be a nonempty array'),
            ('unknown=true', 'unknown .* setting'),
            (
                '[[DOMAIN.layers]]\nname="bad name"\ninclude=["*.SOURCE"]',
                'name must be a literal identifier',
            ),
            (
                '[[DOMAIN.layers]]\nname="core"\ninclude=["../*.SOURCE"]',
                'must stay inside the selected root',
            ),
            (
                '[[DOMAIN.layers]]\nname="core"\ninclude=["*.SOURCE"]\n'
                'forbidden-layers=["unknown"]',
                'requires other known layer names',
            ),
            (
                '[[DOMAIN.layers]]\nname="core"\ninclude=["*.SOURCE"]\n'
                'forbidden-layers=["core"]',
                'requires other known layer names',
            ),
            (
                '[[DOMAIN.layers]]\nname="core"\ninclude=["*.SOURCE"]\n'
                '[[DOMAIN.layers]]\nname="core"\ninclude=["*.SOURCE"]',
                'duplicate Boundary layer name',
            ),
        ),
    )
    def test_invalid_policy(
        self: Self,
        tmp_path: Path,
        language: str,
        settings: str,
        message: str,
    ) -> None:
        """
        Reject invalid names, unknown/self references and escaping globs.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        language : str
            Python or Swift policy namespace, independent of source syntax.
        settings : str
            Standalone TOML settings deliberately violating loader contracts.
        message : str
            Expected diagnostic identifying the violated policy contract.
        """
        domain = f'{language}-boundaries'
        suffix = 'py' if language == 'python' else 'swift'
        settings = settings.replace('DOMAIN', domain).replace('SOURCE', suffix)
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\n{settings}',
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match=message):
            load_boundaries_config(tmp_path, domain)

    def test_swift_imports_reject_dotted_modules(
        self: Self,
        tmp_path: Path,
    ) -> None:
        """
        Reject dotted Swift modules through the native configuration loader.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        (tmp_path / 'popo.toml').write_text(
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\n'
            'allowed-imports=["bad.module"]',
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match='must be identifiers'):
            load_swift_boundaries_config(tmp_path)

    @pytest.mark.parametrize('language', ('python', 'swift'))
    def test_unknown_layer_settings_are_rejected(
        self,
        tmp_path: Path,
        language: str,
    ) -> None:
        """
        Reject misspelled rules instead of silently weakening layer policy.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        language : str
            Native source language selected by the scenario.
        """
        domain = f'{language}-boundaries'
        (tmp_path / 'popo.toml').write_text(
            f'[[{domain}.layers]]\nname="core"\ninclude=["source"]\n'
            'allowed-import=["UnexpectedTypo"]',
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match='unknown boundary layer setting'):
            load_boundaries_config(tmp_path, domain)


# !SECTION
