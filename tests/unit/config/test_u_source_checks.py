"""
:mod:`tests.unit.config.test_u_source_checks` module.

Verify shared selection validation across source and log policy domains.
"""

from pathlib import Path

import pytest

from popo.config._common import ConfigurationError
from popo.config.source_checks import load_source_check
from tests.support.files import snapshot_files

# SECTION: TESTS


@pytest.mark.parametrize('domain', ('python-source', 'swift-source', 'logs'))
class TestSourceSelectionPolicy:
    """Apply common pattern contracts without coupling consumer languages."""

    @pytest.mark.parametrize('setting', ('include', 'exclude'))
    @pytest.mark.parametrize(
        'pattern',
        ('../outside', 'absolute', 'nested/../outside'),
    )
    def test_escaping_patterns_identify_the_setting(
        self,
        tmp_path: Path,
        domain: str,
        setting: str,
        pattern: str,
    ) -> None:
        """Reject unsafe includes and excludes with specific setting names."""
        selected = (
            str(tmp_path.parent / 'outside') if pattern == 'absolute' else pattern
        )
        policy = {'include': ['*.py'], 'exclude': []} | {setting: [selected]}
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude={policy['include']!r}\n'
            f'exclude={policy['exclude']!r}\n',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=rf'{domain}\.{setting} must stay'):
            load_source_check(tmp_path, domain)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'exclusions',
        [
            pytest.param(None, id='omitted'),
            pytest.param((), id='explicit-empty'),
            pytest.param(('second/*', 'first/*'), id='ordered-patterns'),
        ],
    )
    def test_optional_exclusions_preserve_order(
        self,
        tmp_path: Path,
        domain: str,
        exclusions: tuple[str, ...] | None,
    ) -> None:
        """Preserve pattern order with omitted, empty or explicit exclusions."""
        selection = '' if exclusions is None else f'exclude={list(exclusions)!r}\n'
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude=["second/*", "first/*"]\n'
            + selection
            + ('patterns={diagnostic="warning"}' if domain == 'logs' else ''),
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        config = load_source_check(tmp_path, domain)
        assert config.include == ('second/*', 'first/*')
        assert config.exclude == (exclusions or ())
        assert snapshot_files(tmp_path) == before


# !SECTION
