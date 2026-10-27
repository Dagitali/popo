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


class TestSourceSelectionPolicy:
    """Apply common pattern contracts without coupling consumer languages."""

    @pytest.mark.parametrize('domain', ('python-source', 'swift-source', 'logs'))
    @pytest.mark.parametrize('setting', ('include', 'exclude'))
    @pytest.mark.parametrize(
        'pattern',
        ('../outside', '/absolute', 'nested/../outside'),
    )
    def test_escaping_patterns_identify_the_setting(
        self,
        tmp_path: Path,
        domain: str,
        setting: str,
        pattern: str,
    ) -> None:
        """Reject unsafe includes and excludes with specific setting names."""
        policy = {'include': ['*.py'], 'exclude': []} | {setting: [pattern]}
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude={policy['include']!r}\n'
            f'exclude={policy['exclude']!r}\n',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=rf'{domain}\.{setting} must stay'):
            load_source_check(tmp_path, domain)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('domain', ('python-source', 'swift-source', 'logs'))
    def test_empty_optional_exclusions_remain_valid(
        self,
        tmp_path: Path,
        domain: str,
    ) -> None:
        """Preserve pattern order and allow consumers to omit exclusions."""
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude=["second/*", "first/*"]\n'
            + ('patterns={diagnostic="warning"}' if domain == 'logs' else ''),
            encoding='utf-8',
        )
        config = load_source_check(tmp_path, domain)
        assert config.include == ('second/*', 'first/*')
        assert config.exclude == ()


# !SECTION
