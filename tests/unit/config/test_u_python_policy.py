"""
:mod:`tests.unit.config.test_u_python_policy` module.

Verify independent Python policy loading and scoped-mode opt-in.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.config import ConfigurationError, load_config
from popo.config.python_policy import load_python_policy_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='policy_root')
def policy_root_fixture(
    tmp_path: Path,
    write_file: FileWriter,
    filename: str,
    header: str,
    mode: str | None,
) -> Path:
    """
    Write independent Python metadata and standalone or embedded policy.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory supplied by pytest.
    write_file : FileWriter
        Fixture writing UTF-8 files beneath the temporary consumer root.
    filename : str
        Standalone or embedded consumer-policy filename.
    header : str
        Matching Python-policy table header for the selected source.
    mode : str or None
        Raw TOML workflow-parser value, or None to omit the setting.

    Returns
    -------
    pathlib.Path
        Consumer root containing explicit Python compatibility metadata and
        the selected policy source, without loading or validating settings.
    """
    setting = '' if mode is None else f'workflow-parser={mode}'
    metadata = '[project]\nrequires-python=">=3.13,<3.15"\n'
    write_file(
        'pyproject.toml',
        metadata + (header + setting if filename == 'pyproject.toml' else ''),
    )
    if filename == 'popo.toml':
        write_file(filename, header + setting)
    return tmp_path


# !SECTION


# SECTION: TESTS


@pytest.mark.parametrize(
    'filename,header',
    [
        pytest.param('popo.toml', '[python-policy]\n', id='standalone'),
        pytest.param('pyproject.toml', '[tool.popo.python-policy]\n', id='embedded'),
    ],
)
class TestPythonPolicyConfiguration:
    """Preserve aggregate defaults while validating the optional parser."""

    @pytest.mark.parametrize(
        'loader',
        (
            pytest.param(load_python_policy_config, id='independent-loader'),
            pytest.param(load_config, id='aggregate-loader'),
        ),
    )
    @pytest.mark.parametrize(
        'mode',
        (
            pytest.param('"unknown"', id='unknown-parser'),
            pytest.param('""', id='empty-string'),
            pytest.param('false', id='boolean'),
            pytest.param('1', id='integer'),
            pytest.param('[]', id='array'),
            pytest.param('{}', id='table'),
        ),
    )
    def test_invalid_workflow_parser_is_rejected(
        self,
        policy_root: Path,
        loader: Callable[[Path], object],
    ) -> None:
        """
        Reject malformed parser settings independently through both loaders.

        Parameters
        ----------
        policy_root : pathlib.Path
            Fresh standalone or embedded policy with an invalid parser value.
        loader : collections.abc.Callable[[pathlib.Path], object]
            Independent Python-policy or aggregate loader under test.
        """
        before = snapshot_files(policy_root)
        with pytest.raises(ConfigurationError, match='workflow-parser'):
            loader(policy_root)
        assert snapshot_files(policy_root) == before

    @pytest.mark.parametrize(
        'mode,expected',
        (
            pytest.param(None, 'text', id='default-parser'),
            pytest.param('"text"', 'text', id='text-parser'),
            pytest.param('"scoped"', 'scoped', id='scoped-parser'),
        ),
    )
    def test_workflow_parser_selection(
        self,
        policy_root: Path,
        expected: str,
    ) -> None:
        """
        Keep both loaders aligned across policy sources without mutation.

        Parameters
        ----------
        policy_root : pathlib.Path
            Fresh standalone or embedded policy with a valid parser setting.
        expected : str
            Workflow parser selected explicitly or supplied by the default.
        """
        before = snapshot_files(policy_root)
        config = load_python_policy_config(policy_root)
        assert config.workflow_parser == expected
        assert config.requires_python == '>=3.13,<3.15'
        assert config == load_config(policy_root).python_policy
        assert snapshot_files(policy_root) == before


# !SECTION
