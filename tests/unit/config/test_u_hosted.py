"""
:mod:`tests.unit.config.test_u_hosted` module.

Reject malformed hosted configuration and ambiguous approval scopes.
"""

from datetime import date
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.hosted import ExceptionPolicy, load_hosted_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: CONSTANTS


REPOSITORY_TOML = '[[tool.popo.hosted.repositories]]\nname="owner/repo"\n'


# !SECTION


# SECTION: TESTS


class TestHostedConfiguration:
    """Reject malformed hosted configuration and ambiguous approval scopes."""

    @pytest.mark.parametrize(
        ('section', 'message'),
        [
            ('repositories', 'duplicate repository policy'),
            ('exceptions', 'duplicate exception scope'),
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

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        hosted_exception_config : str
            Valid hosted policy and explicit approval TOML.
        section : str
            Repository inventory or exception scope being duplicated.
        message : str
            Expected error message or scenario diagnostic.
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
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_hosted_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

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
        """
        Keep exception checks scoped to the exact configured repository.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        repository : str
            Repository identity used in hosted policy or evidence.
        check : str
            Check identity used in policy selection or hosted evidence.
        """
        write_file(
            'popo.toml',
            '[[hosted.repositories]]\nname="owner/first"\nlabels=["bug"]\n'
            '[[hosted.repositories]]\nname="owner/second"\nlabels=["docs"]\n'
            '[[hosted.exceptions]]\n'
            f'repository="{repository}"\ncheck="{check}"\n'
            'owner="team"\nreason="reviewed"\napproved-by="reviewer"\n'
            'approval="https://example.com/review"\nexpires="2026-10-31"',
        )
        before = snapshot_files(tmp_path)
        expected = {'owner/first': 'label:bug', 'owner/second': 'label:docs'}
        if expected.get(repository) == check:
            config = load_hosted_config(tmp_path)
            assert len(config.repositories) == 2
            assert config.exceptions[0].repository == repository
            assert config.exceptions[0].check == check
        else:
            with pytest.raises(
                ConfigurationError,
                match='exception must target a configured repository/check',
            ):
                load_hosted_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        ('config', 'message'),
        [
            ('', 'tool.popo.hosted must be a TOML table'),
            (REPOSITORY_TOML, 'each repository needs at least one expectation'),
            (
                '[tool.popo.hosted]\nrepositories=[]',
                'hosted.repositories must be a nonempty array',
            ),
            ('[tool.popo.hosted]\nunknown=true', 'unknown hosted configuration key'),
            (REPOSITORY_TOML + 'unknown=true', 'unknown hosted repository key'),
            (REPOSITORY_TOML + 'branches={""=[]}', 'branch names cannot be empty'),
            (
                '[tool.popo.hosted]\nexceptions="bad"\n'
                'repositories=[{name="owner/repo", labels=["bug"]}]',
                'hosted.exceptions must be an array',
            ),
            (
                REPOSITORY_TOML + 'labels=[1]',
                'labels must be an array of nonempty strings',
            ),
            (
                '[[tool.popo.hosted.repositories]]\nname="bad"',
                'repository name must be owner/repository',
            ),
            (REPOSITORY_TOML + 'labels=["bug","bug"]', 'labels contains duplicates'),
            (REPOSITORY_TOML + 'codeowners="yes"', 'codeowners must be boolean'),
            (
                REPOSITORY_TOML + 'settings={unknown=true}',
                'settings must contain supported boolean expectations',
            ),
            (
                REPOSITORY_TOML + 'settings={secret-scanning=1}',
                'settings must contain supported boolean expectations',
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

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        config : str
            Consumer configuration text supplied by the scenario.
        message : str
            Expected error message or scenario diagnostic.
        """
        write_file('pyproject.toml', config)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_hosted_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        ('original', 'replacement', 'message'),
        [
            (
                'owner = "owner"',
                'owner = ""',
                'exceptions require all documented string fields',
            ),
            (
                'reason = "Migration"',
                '',
                'exceptions require all documented string fields',
            ),
            (
                'approved-by = "reviewer"',
                'approved-by = false',
                'exceptions require all documented string fields',
            ),
            (
                'check = "label:bug"',
                'check = "label:other"',
                'exception must target a configured repository/check',
            ),
            (
                'repository = "example/library"',
                'repository = "other/repository"',
                'exception must target a configured repository/check',
            ),
            (
                'expires = "2026-10-31"',
                'expires = "20261031"',
                'exception expires must be an ISO date',
            ),
            (
                'expires = "2026-10-31"',
                'expires = "2026-02-31"',
                'exception expires must be an ISO date',
            ),
            (
                'expires = "2026-10-31"',
                'expires = 2026-10-31',
                'exceptions require all documented string fields',
            ),
            (
                'https://example.com/review',
                'http://example.com/review',
                'exception approval must be an HTTPS evidence URL',
            ),
            (
                'https://example.com/review',
                'https://',
                'exception approval must be an HTTPS evidence URL',
            ),
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
                'exception approval must be an HTTPS evidence URL',
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

        Each mutation changes exactly one field and leaves policy bytes intact.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        hosted_exception_config : str
            Valid hosted policy and explicit approval TOML.
        original : str
            Original source or policy text retained for comparison.
        replacement : str
            Replacement text inserted into the scenario input.
        message : str
            Expected error message or scenario diagnostic.
        """
        assert hosted_exception_config.count(original) == 1
        write_file(
            'pyproject.toml',
            hosted_exception_config.replace(original, replacement, 1),
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_hosted_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'approval',
        (
            pytest.param('https://example.com/review', id='https'),
            pytest.param('https://example.com:443/review', id='explicit-port'),
            pytest.param('https://[::1]:8443/review', id='ipv6'),
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
        Retain approved exception fields and literal HTTPS evidence URLs.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing the approval policy.
        write_file : FileWriter
            UTF-8 writer creating the consumer policy.
        hosted_exception_config : str
            Valid policy with one repository and one reviewed exception.
        approval : str
            Accepted HTTPS URL, including optional ports and IPv6 hosts.
        """
        original = 'https://example.com/review'
        assert hosted_exception_config.count(original) == 1
        write_file(
            'pyproject.toml',
            hosted_exception_config.replace(original, approval, 1),
        )
        before = snapshot_files(tmp_path)
        config = load_hosted_config(tmp_path)
        assert config.exceptions == (
            ExceptionPolicy(
                repository='example/library',
                check='label:bug',
                owner='owner',
                reason='Migration',
                approved_by='reviewer',
                approval=approval,
                expires=date(2026, 10, 31),
            ),
        )
        assert config.repositories[0].labels == ('bug',)
        assert snapshot_files(tmp_path) == before


# !SECTION
