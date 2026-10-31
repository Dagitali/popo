"""
:mod:`tests.unit.config.test_u_selection` module.

Exercise consumer-language-independent configuration and check planning.
"""

import re
from collections.abc import Callable
from pathlib import Path
from unittest.mock import call, patch

import pytest

from popo.config import ConfigurationError
from popo.config._common import read_popo
from popo.config.selection import BASELINE, load_plan
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='write_selection', params=('popo.toml', 'pyproject.toml'))
def write_selection_fixture(
    request: pytest.FixtureRequest,
    write_file: FileWriter,
) -> Callable[[str], Path]:
    """
    Write selection scenarios to either supported consumer-policy source.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Standalone or embedded policy filename selected for this scenario.
    write_file : FileWriter
        UTF-8 writer rooted in the requesting test's temporary repository.

    Returns
    -------
    collections.abc.Callable[[str], pathlib.Path]
        Writer accepting root settings and simple single-bracket table
        headers. Embedded cases prefix those tables with tool.popo; this
        fixture does not parse arbitrary TOML or merge existing files.
    """
    filename = str(request.param)

    def write(
        settings: str,
    ) -> Path:
        """
        Place the same selection scenario under its policy namespace.

        Parameters
        ----------
        settings : str
            Consumer policy text inserted into the scenario.

        Returns
        -------
        Path
            Path of the selected standalone or embedded policy file.
        """
        if filename == 'pyproject.toml':
            settings = '[tool.popo]\n' + re.sub(r'(?m)^\[', '[tool.popo.', settings)
        return write_file(filename, settings)

    return write


# !SECTION


# SECTION: TESTS


class TestCheckSelection:
    """
    Cover check selection.

    Validate explicit selection without imposing a language or running code.
    """

    def test_defaults(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Absent selection preserves all legacy baseline checks.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        plan = load_plan(tmp_path)
        assert plan.checks == BASELINE
        assert plan.source == tmp_path / 'pyproject.toml'
        assert 'legacy' in plan.reason

    def test_explicit_selection(
        self,
        write_selection: Callable[[str], Path],
        tmp_path: Path,
    ) -> None:
        """
        Full command names select only the requested checks in either source.

        Parameters
        ----------
        write_selection : Callable[[str], Path]
            Fixture writing the selected consumer policy.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        source = write_selection('checks=["check-required-files","check-docs"]')
        plan = load_plan(tmp_path)
        assert plan.source == source
        assert plan.checks == ('check-required-files', 'check-docs')
        assert plan.reason == 'explicit checks'

    @pytest.mark.parametrize(
        'settings,profile,message',
        [
            ('checks=[]', None, 'at least one'),
            ('checks="check-docs"', None, 'array'),
            ('checks=[1]', None, 'array'),
            ('checks=[" "]', None, 'array'),
            ('checks=["check-docs","check-docs"]', None, 'duplicates'),
            ('checks=["check-all"]', None, 'unknown offline checks'),
            ('checks=["audit-github-settings"]', None, 'unknown offline checks'),
            ('checks=["check-actionlint"]', None, 'unknown offline checks'),
            ('checks=["check-release-changelog"]', None, 'unknown offline checks'),
            ('checks=["check-typo"]', None, 'unknown offline checks'),
            ('checks=false', None, 'array'),
            ('profiles=[]', 'quick', 'table'),
            ('', 'quick', 'unknown profile'),
            ('[profiles]\nquick=1', 'quick', 'table'),
            ('[profiles.quick]\nother=[]', 'quick', 'requires only checks'),
            ('[profiles.quick]\nchecks=[]', 'quick', 'at least one'),
        ],
    )
    def test_invalid_selection(
        self,
        write_selection: Callable[[str], Path],
        tmp_path: Path,
        settings: str,
        profile: str | None,
        message: str,
    ) -> None:
        """
        Reject invalid selections before any validator executes.

        Parameters
        ----------
        write_selection : Callable[[str], Path]
            Fixture writing the selected consumer policy.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        settings : str
            Consumer policy text inserted into the scenario.
        profile : str | None
            Named check profile, or None for the default selection.
        message : str
            Expected error message or scenario diagnostic.
        """
        write_selection(settings)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            load_plan(tmp_path, profile)
        assert snapshot_files(tmp_path) == before

    def test_opt_in_defaults(
        self,
        write_selection: Callable[[str], Path],
        tmp_path: Path,
    ) -> None:
        """
        Legacy defaults retain declared optional domains in stable order.

        Parameters
        ----------
        write_selection : Callable[[str], Path]
            Fixture writing the selected consumer policy.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        write_selection(
            '[automation]\n[safety]\n[files]\n[headers]\n[guardrails]',
        )
        assert load_plan(tmp_path).checks == (
            *BASELINE,
            'check-automation-contracts',
            'check-repository-safety',
            'check-required-files',
            'check-file-headers',
            'check-guardrail-parity',
        )

    def test_profile(
        self,
        write_selection: Callable[[str], Path],
        tmp_path: Path,
    ) -> None:
        """
        An explicit profile replaces the default selection.

        Parameters
        ----------
        write_selection : Callable[[str], Path]
            Fixture writing the selected consumer policy.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        source = write_selection(
            'checks=["check-docs"]\n[profiles.quick]\nchecks=["check-github-actions-pins"]',
        )
        plan = load_plan(tmp_path, 'quick')
        assert plan.checks == ('check-github-actions-pins',)
        assert plan.reason == 'profile: quick'
        assert plan.source == source
        assert load_plan(tmp_path).checks == ('check-docs',)


class TestConsumerConfiguration:
    """Keep standalone precedence deterministic and configuration read-only."""

    @pytest.mark.parametrize('content', ['[', 'checks = 1\nchecks = 2'])
    def test_invalid_standalone(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        content: str,
    ) -> None:
        """
        Malformed standalone TOML cannot silently fall back to defaults.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        content : str
            Text written to the scenario input.
        """
        write_file('popo.toml', content)
        write_file('pyproject.toml', '[tool.popo]\nchecks=["check-docs"]')
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match='invalid TOML'):
            read_popo(tmp_path)
        assert snapshot_files(tmp_path) == before

    def test_standalone_precedence(
        self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """
        A standalone policy does not parse or merge Python metadata.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        standalone = write_file('popo.toml', 'checks=["check-docs"]')
        write_file('pyproject.toml', '[')
        before = snapshot_files(tmp_path)
        with patch.object(
            Path,
            'read_text',
            autospec=True,
            side_effect=Path.read_text,
        ) as read:
            assert read_popo(tmp_path) == {'checks': ['check-docs']}
            assert load_plan(tmp_path).source == standalone
        assert read.call_args_list == [
            call(standalone, encoding='utf-8'),
            call(standalone, encoding='utf-8'),
        ]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('loader', (read_popo, load_plan), ids=('settings', 'plan'))
    @pytest.mark.parametrize('kind', ['directory', 'dangling'])
    def test_unreadable_standalone(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        loader: Callable[[Path], object],
        kind: str,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Reject unreadable standalone inputs despite valid fallback metadata.

        Neither settings reads nor plan loading may inspect Python metadata
        after selecting the malformed standalone input.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            UTF-8 writer creating valid fallback Python metadata.
        loader : collections.abc.Callable[[pathlib.Path], object]
            Settings reader or aggregate-plan loader under test.
        kind : str
            Directory or dangling-symlink shape of the standalone policy.
        symlink : Callable[[Path, Path], None]
            Platform-aware fixture creating a symbolic link or skipping
            support.
        """
        write_file('pyproject.toml', '[tool.popo]\nchecks=["check-docs"]')
        path = tmp_path / 'popo.toml'
        if kind == 'directory':
            path.mkdir()
        else:
            symlink(path, tmp_path / 'absent')
        before = snapshot_files(tmp_path)
        with (
            patch.object(
                Path,
                'read_text',
                autospec=True,
                side_effect=Path.read_text,
            ) as read,
            pytest.raises(OSError),
        ):
            loader(tmp_path)
        read.assert_called_once_with(path, encoding='utf-8')
        assert snapshot_files(tmp_path) == before
        assert path.is_dir() if kind == 'directory' else path.is_symlink()


# !SECTION
