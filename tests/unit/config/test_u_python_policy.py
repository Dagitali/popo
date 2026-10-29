"""
:mod:`tests.unit.config.test_u_python_policy` module.

Verify independent Python policy loading and scoped-mode opt-in.
"""

from pathlib import Path

import pytest

from popo.config import ConfigurationError, load_config
from popo.config.python_policy import load_python_policy_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


@pytest.mark.parametrize(
    'filename,header',
    [
        pytest.param('popo.toml', '[python-policy]\n', id='standalone'),
        pytest.param('pyproject.toml', '[tool.popo.python-policy]\n', id='embedded'),
    ],
)
class TestPythonPolicyConfiguration:
    """Preserve aggregate defaults while validating the new optional parser."""

    @pytest.mark.parametrize('mode', [None, 'text', 'scoped', 'unknown', ''])
    def test_workflow_parser_selection(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        filename: str,
        header: str,
        mode: str | None,
    ) -> None:
        """
        Keep both loaders aligned across policy sources without mutation.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        filename : str
            Input filename used in the scenario.
        header : str
            Leading header text supplied to the scenario.
        mode : str | None
            Dependency comparison mode selected for the scenario.
        """
        setting = '' if mode is None else f'workflow-parser="{mode}"'
        metadata = '[project]\nrequires-python=">=3.13,<3.15"\n'
        write_file(
            'pyproject.toml',
            metadata + (header + setting if filename == 'pyproject.toml' else ''),
        )
        if filename == 'popo.toml':
            write_file(filename, header + setting)
        before = snapshot_files(tmp_path)
        if mode in {None, 'text', 'scoped'}:
            config = load_python_policy_config(tmp_path)
            assert config.workflow_parser == (mode or 'text')
            assert config.requires_python == '>=3.13,<3.15'
            assert config == load_config(tmp_path).python_policy
        else:
            for load in (load_python_policy_config, load_config):
                with pytest.raises(ConfigurationError, match='workflow-parser'):
                    load(tmp_path)
        assert snapshot_files(tmp_path) == before


# !SECTION
