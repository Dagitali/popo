"""
:mod:`tests.e2e.test_e_validation_commands` module.

Inspect installed result/boundary commands outside the source checkout.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: TESTS


class TestInstalledValidation:
    """Exercise wheel and sdist entry points with private synthetic evidence."""

    @pytest.mark.parametrize('module', (False, True), ids=('console', 'module'))
    @pytest.mark.parametrize(
        'command',
        ('check-test-results', 'check-swift-boundaries', 'check-python-boundaries'),
    )
    def test_installed_checks_are_read_only_and_redacted(
        self: Self,
        installation: Installation,
        tmp_path: Path,
        module: bool,
        command: str,
    ) -> None:
        """
        Reject negative fixtures and accept corrected inputs after installation.

        Parameters
        ----------
        installation : Installation
            Wheel or sdist installed outside the checkout.
        tmp_path : pathlib.Path
            Disposable consumer root and artifacts.
        module : bool
            Use the installed module rather than the console executable.
        command : str
            Explicit generic validator selected for the scenario.
        """
        if command == 'check-test-results':
            policy = '[test-results]\nadapter="xcode-summary"\ninclude=["*.json"]'
            path = tmp_path / 'summary.json'
            valid = json.dumps(
                dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0),
            )
            invalid = json.dumps(
                dict(
                    totalTestCount=1,
                    passedTests=1,
                    failedTests=0,
                    skippedTests=0,
                    runtimeWarnings=[{'message': 'PRIVATE BALANCE'}],
                ),
            )
            extra = ['--summary', str(path)]
        elif command == 'check-python-boundaries':
            policy = '[[python-boundaries.layers]]\n'
            policy += 'name="core"\ninclude=["*.py"]\nallowed-imports=["pathlib"]'
            path = tmp_path / 'rule.py'
            valid = 'from pathlib import Path'
            invalid = 'import os\naccount = "PRIVATE BALANCE"'
            extra = []
        else:
            policy = '[swift-boundaries]\n[[swift-boundaries.layers]]\n'
            policy += 'name="core"\ninclude=["*.swift"]\nallowed-imports=["Foundation"]'
            path = tmp_path / 'Rule.swift'
            valid = 'import Foundation\nstruct Rule {}'
            invalid = 'import SwiftUI\nlet account = "PRIVATE BALANCE"'
            extra = []
        (tmp_path / 'popo.toml').write_text(policy)
        for text, status in ((invalid, 1), (valid, 0)):
            path.write_text(text)
            before = snapshot_files(tmp_path)
            result = installation.run(
                command,
                '--root',
                str(tmp_path),
                '--format',
                'json',
                *extra,
                module=module,
            )
            assert result.returncode == status, result.stderr
            assert json.loads(result.stdout)['passed'] == (status == 0)
            assert 'PRIVATE BALANCE' not in result.stdout + result.stderr
            assert snapshot_files(tmp_path) == before


# !SECTION
