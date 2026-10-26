"""
:mod:`tests.unit.configs.test_u_selection` module.

Exercise consumer-language-independent configuration and check planning.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config._common import read_popo
from popo.config.selection import BASELINE, load_plan
from tests.support.files import FileWriter

# SECTION: TESTS


class TestConsumerConfiguration:
    """Keep standalone precedence deterministic and configuration read-only."""

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

    def test_opt_in_defaults(
        self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """Legacy defaults retain declared optional domains in stable order."""
        write_file(
            'popo.toml',
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

    @pytest.mark.parametrize(
        'filename,prefix',
        [('popo.toml', ''), ('pyproject.toml', '[tool.popo]\n')],
    )
    def test_explicit_selection(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        filename: str,
        prefix: str,
    ) -> None:
        """
        Full command names select only the requested checks in either source.
        """
        write_file(filename, prefix + 'checks=["check-required-files","check-docs"]')
        plan = load_plan(tmp_path)
        assert plan.checks == ('check-required-files', 'check-docs')
        assert plan.reason == 'explicit checks'

    def test_profile(
        self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        """An explicit profile replaces the default selection."""
        write_file(
            'popo.toml',
            'checks=["check-docs"]\n[profiles.quick]\nchecks=["check-github-actions-pins"]',
        )
        assert load_plan(tmp_path, 'quick').checks == ('check-github-actions-pins',)
        assert load_plan(tmp_path, 'quick').reason == 'profile: quick'
        assert load_plan(tmp_path).checks == ('check-docs',)

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
        write_file: FileWriter,
        tmp_path: Path,
        settings: str,
        profile: str | None,
        message: str,
    ) -> None:
        """Reject invalid selections before any validator executes."""
        write_file('popo.toml', settings)
        with pytest.raises(ConfigurationError, match=message):
            load_plan(tmp_path, profile)


# !SECTION
