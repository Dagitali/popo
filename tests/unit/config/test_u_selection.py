"""
:mod:`tests.unit.config.test_u_selection` module.

Exercise consumer-language-independent configuration and check planning.
"""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config._common import read_popo
from popo.config.selection import BASELINE, load_plan
from tests.support.files import FileWriter

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
        """Place the same selection scenario under its policy namespace."""
        if filename == 'pyproject.toml':
            settings = '[tool.popo]\n' + re.sub(r'(?m)^\[', '[tool.popo.', settings)
        return write_file(filename, settings)

    return write


# !SECTION


# SECTION: TESTS


class TestCheckSelection:
    """
    Validate explicit selection without imposing a language or running code.
    """

    def test_defaults(
        self,
        tmp_path: Path,
    ) -> None:
        """Absent selection preserves all legacy baseline checks."""
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
        """Reject invalid selections before any validator executes."""
        write_selection(settings)
        with pytest.raises(ConfigurationError, match=message):
            load_plan(tmp_path, profile)

    def test_opt_in_defaults(
        self,
        write_selection: Callable[[str], Path],
        tmp_path: Path,
    ) -> None:
        """Legacy defaults retain declared optional domains in stable order."""
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
        """An explicit profile replaces the default selection."""
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
        """Malformed standalone TOML cannot silently fall back to defaults."""
        write_file('popo.toml', content)
        with pytest.raises(ConfigurationError, match='invalid TOML'):
            read_popo(tmp_path)

    def test_standalone_precedence(
        self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """A standalone policy does not parse or merge Python metadata."""
        standalone = write_file('popo.toml', 'checks=["check-docs"]')
        metadata = write_file('pyproject.toml', '[')
        before = [p.read_bytes() for p in (standalone, metadata)]
        assert read_popo(tmp_path) == {'checks': ['check-docs']}
        assert load_plan(tmp_path).source == standalone
        assert [p.read_bytes() for p in (standalone, metadata)] == before

    @pytest.mark.parametrize('kind', ['directory', 'dangling'])
    def test_unreadable_standalone(
        self,
        tmp_path: Path,
        kind: str,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        An invalid standalone input cannot silently select another source.
        """
        path = tmp_path / 'popo.toml'
        if kind == 'directory':
            path.mkdir()
        else:
            symlink(path, tmp_path / 'absent')
        with pytest.raises(OSError):
            read_popo(tmp_path)


# !SECTION
