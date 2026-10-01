"""
:mod:`tests.unit.configs.test_u_automation` module.

Test validation of consumer automation configuration.
"""

from pathlib import Path

import pytest

from popo.config import ConfigurationError, load_automation_config
from tests.support.files import FileWriter

# SECTION: TESTS


@pytest.mark.parametrize(
    'setting',
    [
        'unknown = []',
        'workflow-globs = "x"',
        'action-globs = [1]',
        'yaml-globs = ["../x"]',
        'template-globs = ["/absolute"]',
        'local-repositories = ["owner"]',
        'template-placeholder-refs = ["a/b"]',
    ],
)
def test_invalid_configuration(
    tmp_path: Path,
    write_file: FileWriter,
    setting: str,
) -> None:
    """
    Verify automation loading rejects unsupported keys, types, and unsafe
    patterns.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    setting : str
        Automation TOML setting selected to exercise invalid configuration.
    """
    write_file('pyproject.toml', '[tool.popo.automation]\n' + setting)
    with pytest.raises(ConfigurationError):
        load_automation_config(tmp_path)


# !SECTION
