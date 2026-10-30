"""
:mod:`tests.unit.config.test_u_python_source` module.

Reject invalid Python source settings independently of source inspection.
"""

from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.source_checks import load_source_check
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestPythonSourceConfiguration:
    """Validate Python rule switches and limits before inspecting inputs."""

    @pytest.mark.parametrize(
        'settings,message',
        (
            pytest.param(
                'include = []',
                'python-source.include must not be empty',
                id='empty-selection',
            ),
            pytest.param(
                'include = ["*.py"]\nannotations = 1',
                'python-source.annotations: invalid setting type',
                id='nonboolean-rule',
            ),
            pytest.param(
                'include = ["*.py"]\nmax-file-lines = 0',
                'python-source.max-file-lines: expected a positive integer',
                id='nonpositive-limit',
            ),
            pytest.param(
                'include = ["*.py"]\nunknown = true',
                "python-source: unknown settings: ['unknown']",
                id='unknown-setting',
            ),
        ),
    )
    def test_invalid_configuration(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        settings: str,
        message: str,
    ) -> None:
        """
        Reject invalid configuration with exact setting-specific diagnostics.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Shared UTF-8 writer creating the isolated consumer policy.
        settings : str
            Consumer policy text inserted into the scenario.
        message : str
            Complete expected diagnostic for the selected invalid setting.
        """
        write_file('popo.toml', '[python-source]\n' + settings)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_source_check(tmp_path, 'python-source')
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before


# !SECTION
