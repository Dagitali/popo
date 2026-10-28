"""
:mod:`tests.unit.config.test_u_hosted` module.

Reject malformed hosted configuration and ambiguous approval scopes.
"""

from datetime import date
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.hosted import load_hosted_config
from tests.support.files import FileWriter

# SECTION: CONSTANTS


REPOSITORY_TOML = '[[tool.popo.hosted.repositories]]\nname="owner/repo"\n'


# !SECTION


# SECTION: TESTS


class TestHostedConfiguration:
    """Reject malformed hosted configuration and ambiguous approval scopes."""

    @pytest.mark.parametrize(
        ('section', 'message'),
        [
            ('repositories', 'duplicate repository'),
            ('exceptions', 'duplicate exception'),
        ],
    )
    def test_duplicate_scopes(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        hosted_exception_config: str,
        section: str,
        message: str,
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
        write_file('pyproject.toml', hosted_exception_config + extra)
        with pytest.raises(ConfigurationError, match=message):
            load_hosted_config(tmp_path)

    @pytest.mark.parametrize(
        'repository',
        ['owner/first', 'owner/second', 'OWNER/first'],
    )
    @pytest.mark.parametrize('check', ['label:bug', 'label:docs'])
    def test_exception_scope_uses_own_repository(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        repository: str,
        check: str,
    ) -> None:
        """Keep exception checks scoped to the exact configured repository."""
        write_file(
            'popo.toml',
            '[[hosted.repositories]]\nname="owner/first"\nlabels=["bug"]\n'
            '[[hosted.repositories]]\nname="owner/second"\nlabels=["docs"]\n'
            '[[hosted.exceptions]]\n'
            f'repository="{repository}"\ncheck="{check}"\n'
            'owner="team"\nreason="reviewed"\napproved-by="reviewer"\n'
            'approval="https://example.com/review"\nexpires="2026-10-31"',
        )
        expected = {'owner/first': 'label:bug', 'owner/second': 'label:docs'}
        if expected.get(repository) == check:
            config = load_hosted_config(tmp_path)
            assert len(config.repositories) == 2
            assert config.exceptions[0].repository == repository
            assert config.exceptions[0].check == check
        else:
            with pytest.raises(ConfigurationError, match='configured repository/check'):
                load_hosted_config(tmp_path)

    @pytest.mark.parametrize(
        ('config', 'message'),
        [
            ('', 'must be a TOML table'),
            (REPOSITORY_TOML, 'at least one expectation'),
            ('[tool.popo.hosted]\nrepositories=[]', 'nonempty array'),
            ('[tool.popo.hosted]\nunknown=true', 'unknown hosted configuration key'),
            (REPOSITORY_TOML + 'unknown=true', 'unknown hosted repository key'),
            (REPOSITORY_TOML + 'branches={""=[]}', 'branch names cannot be empty'),
            (
                '[tool.popo.hosted]\nexceptions="bad"\n'
                'repositories=[{name="owner/repo", labels=["bug"]}]',
                'hosted.exceptions must be an array',
            ),
            (REPOSITORY_TOML + 'labels=[1]', 'array of nonempty strings'),
            ('[[tool.popo.hosted.repositories]]\nname="bad"', 'owner/repository'),
            (REPOSITORY_TOML + 'labels=["bug","bug"]', 'labels contains duplicates'),
            (REPOSITORY_TOML + 'codeowners="yes"', 'codeowners must be boolean'),
            (
                REPOSITORY_TOML + 'settings={unknown=true}',
                'supported boolean expectations',
            ),
            (
                REPOSITORY_TOML + 'settings={secret-scanning=1}',
                'supported boolean expectations',
            ),
        ],
    )
    def test_invalid_config(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        config: str,
        message: str,
    ) -> None:
        """
        Reject absent, malformed, or unsupported hosted expectations.
        """
        write_file('pyproject.toml', config)
        with pytest.raises(ConfigurationError, match=message):
            load_hosted_config(tmp_path)

    @pytest.mark.parametrize(
        ('original', 'replacement', 'message'),
        [
            ('owner = "owner"', 'owner = ""', 'documented string fields'),
            ('reason = "Migration"', '', 'documented string fields'),
            (
                'approved-by = "reviewer"',
                'approved-by = false',
                'documented string fields',
            ),
            (
                'check = "label:bug"',
                'check = "label:other"',
                'configured repository/check',
            ),
            (
                'repository = "example/library"',
                'repository = "other/repository"',
                'configured repository/check',
            ),
            ('expires = "2026-10-31"', 'expires = "20261031"', 'ISO date'),
            ('expires = "2026-10-31"', 'expires = "2026-02-31"', 'ISO date'),
            (
                'expires = "2026-10-31"',
                'expires = 2026-10-31',
                'documented string fields',
            ),
            (
                'https://example.com/review',
                'http://example.com/review',
                'HTTPS evidence URL',
            ),
            ('https://example.com/review', 'https://', 'HTTPS evidence URL'),
            (
                'https://example.com/review',
                'https://[broken',
                'invalid exception approval URL',
            ),
            (
                'https://example.com/review',
                'https://example.com:abc/review',
                'invalid exception approval URL',
            ),
            (
                'https://example.com/review',
                'https://example.com:-1/review',
                'invalid exception approval URL',
            ),
            (
                'https://example.com/review',
                'https://example.com:65536/review',
                'invalid exception approval URL',
            ),
            (
                'https://example.com/review',
                'https://user:secret@example.com/review',
                'HTTPS evidence URL',
            ),
        ],
    )
    def test_invalid_exception(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        hosted_exception_config: str,
        original: str,
        replacement: str,
        message: str,
    ) -> None:
        """
        Reject incomplete approvals, unsafe URLs, and invalid expiry dates.
        """
        assert original in hosted_exception_config, 'Mutation marker missing'
        write_file(
            'pyproject.toml',
            hosted_exception_config.replace(original, replacement),
        )
        with pytest.raises(ConfigurationError, match=message):
            load_hosted_config(tmp_path)

    @pytest.mark.parametrize(
        'approval',
        (
            'https://example.com/review',
            'https://example.com:443/review',
            'https://[::1]:8443/review',
        ),
    )
    def test_valid_exception(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        hosted_exception_config: str,
        approval: str,
    ) -> None:
        """
        Load the exact approved scope and its inclusive expiry date.
        """
        write_file(
            'pyproject.toml',
            hosted_exception_config.replace('https://example.com/review', approval),
        )
        config = load_hosted_config(tmp_path)
        assert config.exceptions[0].approval == approval
        assert config.exceptions[0].expires == date(2026, 10, 31)
        assert config.repositories[0].labels == ('bug',)


# !SECTION
