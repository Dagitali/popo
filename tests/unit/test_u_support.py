"""
:mod:`tests.unit.test_u_support` module.

Cover missing automation directories and uninstalled-package version fallback.
"""

import runpy
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.support import automation_paths

# SECTION: TESTS


class TestSupport:
    """
    Verify safe defaults when optional repository or installation data is
    absent.

    Notes
    -----
    Exercise absent automation directories and missing installed-distribution
    metadata. Version lookup is patched for source execution and restored after
    the scenario; no package installation is required.
    """

    def test_missing_automation_directory(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify shared discovery returns no paths for an absent directory.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
        assert automation_paths(tmp_path / 'absent') == []

    def test_uninstalled_version(
        self,
        repository_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Verify absent distribution metadata uses the source-import fallback.

        Parameters
        ----------
        repository_root : pathlib.Path
            Checkout containing canonical project files.
        monkeypatch : pytest.MonkeyPatch
            Restore environment, attributes, and working directory.
        """
        version = Mock(side_effect=PackageNotFoundError('popo'))
        monkeypatch.setattr('importlib.metadata.version', version)
        namespace = runpy.run_path(str(repository_root / 'src/popo/__init__.py'))
        assert namespace['__version__'] == '0.1.0'
        assert namespace['__all__'] == ['__version__']
        version.assert_called_once_with('popo')


# !SECTION
