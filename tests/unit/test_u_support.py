"""
:mod:`tests.unit.test_u_support` module.

Cover automation discovery, release versions and source-import fallback.
"""

import runpy
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.support import automation_paths, normalize_release
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


@pytest.mark.parametrize('prefix', ('', 'v'), ids=('plain', 'v-prefixed'))
class TestReleaseNormalization:
    """Require canonical ASCII releases with only an optional lowercase v."""

    @pytest.mark.parametrize('version', ['0.0.0', '1.2.3', '10.20.30'])
    def test_normalize_release_ascii_components(
        self,
        version: str,
        prefix: str,
    ) -> None:
        """Preserve ASCII version components and remove only the v prefix."""
        assert normalize_release(prefix + version) == version

    @pytest.mark.parametrize('digit', ['١', '１'])
    @pytest.mark.parametrize('component', [0, 1, 2])
    def test_normalize_release_rejects_non_ascii_digits(
        self,
        digit: str,
        component: int,
        prefix: str,
    ) -> None:
        """Reject Unicode digits even after a valid ASCII leading digit."""
        parts = ['1', '2', '3']
        parts[component] += digit
        with pytest.raises(ValueError, match='release version must use'):
            normalize_release(prefix + '.'.join(parts))

    @pytest.mark.parametrize(
        'version',
        (
            '',
            '1',
            '1.2',
            '1.2.3.4',
            '01.2.3',
            '1.02.3',
            '1.2.03',
            '1.2.3-rc.1',
            '1.2.3+build',
            ' 1.2.3',
            '1.2.3 ',
            'V1.2.3',
        ),
    )
    def test_normalize_release_rejects_noncanonical_versions(
        self,
        prefix: str,
        version: str,
    ) -> None:
        """Reject partial versions, zero padding, suffixes and extra syntax."""
        with pytest.raises(ValueError, match='^release version must use '):
            normalize_release(prefix + version)


class TestSupport:
    """
    Verify safe defaults when optional repository or installation data is
    absent.

    Notes
    -----
    Exercise automation discovery, absent directories and missing installed-
    distribution metadata. Version lookup is patched for source execution and
    restored after the scenario; no package installation is required.
    """

    def test_automation_discovery_preserves_sorted_glob_matches(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Sort both YAML suffixes recursively without filtering directories.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            Callable for writing test files.
        """
        for filename in ('z.yml', 'a.yaml', 'nested/c.yml', 'ignored.txt'):
            write_file(filename, 'fixture')
        (tmp_path / 'folder.yaml').mkdir()
        before = snapshot_files(tmp_path)
        assert automation_paths(tmp_path) == [
            tmp_path / name
            for name in ('a.yaml', 'folder.yaml', 'nested/c.yml', 'z.yml')
        ]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('kind', ('absent', 'file', 'empty-directory'))
    def test_empty_automation_discovery(
        self,
        tmp_path: Path,
        kind: str,
    ) -> None:
        """
        Verify shared discovery returns no paths without a populated directory.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        kind : str
            Absent path, ordinary file or existing empty directory.
        """
        path = tmp_path / 'automation'
        if kind == 'file':
            path.write_text('fixture', encoding='utf-8')
        elif kind == 'empty-directory':
            path.mkdir()
        assert automation_paths(path) == []

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
