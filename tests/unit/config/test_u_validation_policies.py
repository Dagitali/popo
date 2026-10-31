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
from tests.support.files import FileWriter, snapshot_files

# SECTION: CONSTANTS


RESULT_SETTINGS = 'adapter="xcode-summary"\ninclude=["*.json"]'


# !SECTION


# SECTION: TESTS


class TestResultPolicy:
    """Keep adapter selection explicit and counts strongly typed."""

    @pytest.mark.parametrize(
        ('settings', 'message'),
        (
            pytest.param(
                '',
                'test-results.adapter must be xcode-summary',
                id='missing-adapter',
            ),
            pytest.param(
                'adapter="unknown"\ninclude=["*.json"]',
                'test-results.adapter must be xcode-summary',
                id='unknown-adapter',
            ),
            pytest.param(
                'adapter="xcode-summary"\ninclude=[]',
                'test-results.include must not be empty',
                id='empty-selection',
            ),
            pytest.param(
                'adapter="xcode-summary"\ninclude=["../*.json"]',
                'test-results.include must stay inside the selected root',
                id='escaping-selection',
            ),
            pytest.param(
                RESULT_SETTINGS + '\nquery="arbitrary"',
                'unknown test-results setting',
                id='unknown-setting',
            ),
            *(
                pytest.param(
                    f'{RESULT_SETTINGS}\n{field}={value}',
                    f'test-results.{field} requires a nonnegative integer',
                    id=f'{field}-{label}',
                )
                for field in (
                    'minimum-tests',
                    'minimum-passed',
                    'maximum-failed',
                    'maximum-skipped',
                    'maximum-warnings',
                )
                for label, value in (
                    ('boolean', 'true'),
                    ('negative', '-1'),
                    ('string', '"1"'),
                    ('float', '1.0'),
                )
            ),
        ),
    )
    def test_invalid_result_policy(
        self: Self,
        tmp_path: Path,
        write_file: FileWriter,
        settings: str,
        message: str,
    ) -> None:
        """
        Reject unknown formats, unsafe selection and unsupported settings.

        Every count rejects boolean, negative, string and float values; valid
        adapter and selection settings isolate each threshold failure.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        write_file : FileWriter
            Shared UTF-8 writer creating the isolated consumer policy.
        settings : str
            Standalone TOML settings deliberately violating loader contracts.
        message : str
            Complete diagnostic identifying the intended invalid field.
        """
        write_file('popo.toml', '[test-results]\n' + settings)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_test_results_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before


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
                '[[DOMAIN.layers]]\nname="core"\ninclude=["source"]\n'
                'allowed-import=["UnexpectedTypo"]',
                'unknown boundary layer setting',
            ),
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
        write_file: FileWriter,
        language: str,
        settings: str,
        message: str,
    ) -> None:
        """
        Reject invalid names, unknown/self references and escaping globs.

        Misspelled layer rules must fail instead of silently weakening policy.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        write_file : FileWriter
            Shared UTF-8 writer creating the isolated consumer policy.
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
        write_file('popo.toml', f'[{domain}]\n{settings}')
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            load_boundaries_config(tmp_path, domain)
        assert snapshot_files(tmp_path) == before

    def test_swift_imports_reject_dotted_modules(
        self: Self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Reject dotted Swift modules through the native configuration loader.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Shared UTF-8 writer creating the isolated consumer policy.
        """
        write_file(
            'popo.toml',
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\n'
            'allowed-imports=["bad.module"]',
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match='must be identifiers'):
            load_swift_boundaries_config(tmp_path)
        assert snapshot_files(tmp_path) == before


# !SECTION
