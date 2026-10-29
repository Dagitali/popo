"""
:mod:`tests.e2e.test_e_swift_policy` module.

Validate installed Swift policy commands without installing Swift.
"""

import json
from pathlib import Path

import pytest

from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: TESTS


class TestInstalledSwiftPolicy:
    """
    Cover installed swift policy.

    Check wheel/sdist console/module behavior and preserve consumer bytes.
    """

    @pytest.mark.parametrize('module', [False, True], ids=['console', 'module'])
    def test_consumer_policy(
        self,
        installation: Installation,
        swift_policy_consumer: Path,
        module: bool,
    ) -> None:
        """
        Verify consumer policy.

        Parameters
        ----------
        installation : Installation
            Artifact installed in an isolated environment outside the checkout.
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        module : bool
            Whether source is treated as a module in the scenario.
        """
        root = swift_policy_consumer
        before = snapshot_files(root)
        result = installation.run(
            'check-swift-policy',
            '--root',
            str(root),
            '--format',
            'json',
            module=module,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)['passed']
        assert snapshot_files(root) == before
        result = installation.run(
            'check-swift-policy',
            '--root',
            str(root),
            '--compiler-version',
            '6.3.0',
            '--format',
            'json',
            module=module,
        )
        assert result.returncode == 1, result.stderr
        assert not json.loads(result.stdout)['passed']
        assert snapshot_files(root) == before


# !SECTION
