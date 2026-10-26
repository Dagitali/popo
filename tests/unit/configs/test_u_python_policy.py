"""Verify independent Python policy loading and scoped-mode opt-in."""

from pathlib import Path

import pytest

from popo.config import ConfigurationError, load_config
from popo.config.python_policy import load_python_policy_config
from tests.support.files import FileWriter

# SECTION: TESTS


class TestPythonPolicyConfiguration:
    """Preserve aggregate defaults while validating the new optional parser."""

    @pytest.mark.parametrize('mode', [None, 'text', 'scoped', 'unknown', ''])
    def test_workflow_parser_selection(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        mode: str | None,
    ) -> None:
        setting = '' if mode is None else f'workflow-parser="{mode}"'
        write_file(
            'pyproject.toml',
            '[project]\nrequires-python=">=3.13,<3.15"\n'
            f'[tool.popo.python-policy]\n{setting}',
        )
        if mode in {None, 'text', 'scoped'}:
            config = load_python_policy_config(tmp_path)
            assert config.workflow_parser == (mode or 'text')
            assert config == load_config(tmp_path).python_policy
        else:
            with pytest.raises(ConfigurationError, match='workflow-parser'):
                load_python_policy_config(tmp_path)


# !SECTION
