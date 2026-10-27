"""
:mod:`tests.unit.config.test_u_validation_policies` module.

Reject malformed generic result and Swift architecture configuration.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.config._common import ConfigurationError
from popo.config.swift_boundaries import load_swift_boundaries_config
from popo.config.test_results import load_test_results_config

# SECTION: TESTS


class TestResultPolicy:
    """Keep adapter selection explicit and counts strongly typed."""

    @pytest.mark.parametrize(
        'settings',
        (
            '',
            'adapter="unknown"\ninclude=["*.json"]',
            'adapter="xcode-summary"\ninclude=[]',
            'adapter="xcode-summary"\ninclude=["../*.json"]',
            'adapter="xcode-summary"\ninclude=["*.json"]\nmaximum-skipped=true',
            'adapter="xcode-summary"\ninclude=["*.json"]\nmaximum-warnings=-1',
            'adapter="xcode-summary"\ninclude=["*.json"]\nminimum-tests="1"',
            'adapter="xcode-summary"\ninclude=["*.json"]\nquery="arbitrary"',
        ),
    )
    def test_invalid_result_policy(
        self: Self,
        tmp_path: Path,
        settings: str,
    ) -> None:
        """
        Reject unknown formats, unsafe selection and noninteger thresholds.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        settings : str
            Standalone TOML settings deliberately violating loader contracts.
        """
        (tmp_path / 'popo.toml').write_text('[test-results]\n' + settings)
        with pytest.raises(ConfigurationError):
            load_test_results_config(tmp_path)


class TestBoundaryPolicy:
    """Keep graph references, imports and paths consumer-owned and bounded."""

    @pytest.mark.parametrize(
        'settings',
        (
            'layers=[]',
            'unknown=true',
            '[[swift-boundaries.layers]]\nname="bad name"\ninclude=["*.swift"]',
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["../*.swift"]',
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\nforbidden-layers=["unknown"]',
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\nforbidden-layers=["core"]',
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\nallowed-imports=["bad.module"]',
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\n'
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]',
        ),
    )
    def test_invalid_boundary_policy(
        self: Self,
        tmp_path: Path,
        settings: str,
    ) -> None:
        """
        Reject invalid names, unknown/self references and escaping globs.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        settings : str
            Standalone TOML settings deliberately violating loader contracts.
        """
        (tmp_path / 'popo.toml').write_text('[swift-boundaries]\n' + settings)
        with pytest.raises(ConfigurationError):
            load_swift_boundaries_config(tmp_path)


# !SECTION
