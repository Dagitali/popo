"""
:mod:`tests.unit.configs.test_u_hosted` module.

Reject malformed hosted configuration and ambiguous approval scopes.
"""

from datetime import date
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.hosted import load_hosted_config

# SECTION: TESTS


class TestHostedConfiguration:
    """Reject malformed hosted configuration and ambiguous approval scopes."""

    @pytest.mark.parametrize(
        'section',
        ['repositories', 'exceptions'],
    )
    def test_duplicate_scopes(
        self,
        tmp_path: Path,
        hosted_exception_config: str,
        section: str,
    ) -> None:
        """
        Reject duplicate repository inventory and exception scopes.
        """
        if section == 'repositories':
            extra = (
                '\n[[tool.popo.hosted.repositories]]\n'
                'name="example/library"\nlabels=["bug"]'
            )
        else:
            extra = (
                '\n[[tool.popo.hosted.exceptions]]'
                + hosted_exception_config.split('[[tool.popo.hosted.exceptions]]', 1)[1]
            )
        (tmp_path / 'pyproject.toml').write_text(hosted_exception_config + extra)
        with pytest.raises(ConfigurationError):
            load_hosted_config(tmp_path)

    @pytest.mark.parametrize(
        'config',
        [
            '',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"',
            '[tool.popo.hosted]\nrepositories=[]',
            '[tool.popo.hosted]\nunknown=true',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nunknown=true',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nbranches={""=[]}',
            '[tool.popo.hosted]\nexceptions="bad"\n'
            'repositories=[{name="owner/repo", labels=["bug"]}]',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nlabels=[1]',
            '[[tool.popo.hosted.repositories]]\nname="bad"',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nlabels=["bug","bug"]',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\ncodeowners="yes"',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nsettings={unknown=true}',
            '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nsettings={secret-scanning=1}',
        ],
    )
    def test_invalid_config(
        self,
        tmp_path: Path,
        config: str,
    ) -> None:
        """
        Reject absent, malformed, or unsupported hosted expectations.
        """
        (tmp_path / 'pyproject.toml').write_text(config)
        with pytest.raises(ConfigurationError):
            load_hosted_config(tmp_path)

    @pytest.mark.parametrize(
        ('original', 'replacement'),
        [
            ('owner = "owner"', 'owner = ""'),
            ('reason = "Migration"', ''),
            ('approved-by = "reviewer"', 'approved-by = false'),
            ('check = "label:bug"', 'check = "label:other"'),
            ('repository = "example/library"', 'repository = "other/repository"'),
            ('expires = "2026-10-31"', 'expires = "20261031"'),
            ('expires = "2026-10-31"', 'expires = "2026-02-31"'),
            ('expires = "2026-10-31"', 'expires = 2026-10-31'),
            ('https://example.com/review', 'http://example.com/review'),
            ('https://example.com/review', 'https://'),
            ('https://example.com/review', 'https://[broken'),
            ('https://example.com/review', 'https://user:secret@example.com/review'),
        ],
    )
    def test_invalid_exception(
        self,
        tmp_path: Path,
        hosted_exception_config: str,
        original: str,
        replacement: str,
    ) -> None:
        """
        Reject incomplete approvals, unsafe URLs, and invalid expiry dates.
        """
        (tmp_path / 'pyproject.toml').write_text(
            hosted_exception_config.replace(original, replacement),
        )
        with pytest.raises(ConfigurationError):
            load_hosted_config(tmp_path)

    def test_valid_exception(
        self,
        tmp_path: Path,
        hosted_exception_config: str,
    ) -> None:
        """
        Load the exact approved scope and its inclusive expiry date.
        """
        (tmp_path / 'pyproject.toml').write_text(hosted_exception_config)
        config = load_hosted_config(tmp_path)
        assert config.exceptions[0].expires == date(2026, 10, 31)
        assert config.repositories[0].labels == ('bug',)


# !SECTION
