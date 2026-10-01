"""
:mod:`tests.unit.checks.test_u_actions` module.

Test immutable action references and nested automation discovery.
"""

from pathlib import Path

import pytest

from popo.checks.actions import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestActions:
    """
    Verify action pinning, local exemptions, and recursive discovery.

    Notes
    -----
    Use temporary YAML files to test discovery and line-numbered pin
    diagnostics. Local and container exemptions are tested without fetching or
    executing referenced actions.
    """

    @pytest.mark.parametrize(
        'reference',
        [
            f'owner/action@{'a' * 40}',
            f'owner/action@{'A' * 40}',
            './local',
            'docker://alpine:3',
        ],
        ids=['lowercase-sha', 'uppercase-sha', 'local-action', 'container'],
    )
    def test_accepts_pinned_or_local_references(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        reference: str,
    ) -> None:
        """
        Verify full-SHA, local, and container references pass pin validation.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        reference : str
            Automation uses value selected for the pin or target-resolution
            scenario.
        """
        write_file('.github/ci.yaml', f'uses: {reference}\n')
        assert validate(tmp_path / '.github') == []

    def test_checks_nested_composite_actions_and_ignores_local_steps(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify recursive action discovery reports only the unpinned remote
        step.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        """
        action = write_file(
            'actions/setup/action.yaml',
            'steps:\n  - uses: ./local\n  - uses: docker://alpine:3\n'
            f'  - uses: "owner/action@{'A' * 40}" # pinned\n'
            '  - uses: owner/action@v1\n',
        )
        assert validate(tmp_path) == [
            f'{action}:5: remote action must use a full '
            '40-character commit SHA: owner/action@v1',
        ]

    @pytest.mark.parametrize(
        'reference',
        [
            'owner/action',
            'owner/action@main',
            'owner/action@abc123',
            f'@{'a' * 40}',
            'owner/action@',
            f'owner/action@{'g' * 40}',
        ],
    )
    def test_rejects_malformed_remote_reference(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        reference: str,
    ) -> None:
        """
        Verify malformed remote references produce a precise line-numbered
        failure.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        reference : str
            Automation uses value selected for the pin or target-resolution
            scenario.
        """
        action = write_file('action.yml', f'uses: {reference}\n')
        assert validate(tmp_path) == [
            f'{action}:1: remote action must use a full '
            f'40-character commit SHA: {reference}',
        ]

    def test_rejects_mutable_remote_action(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify a floating action tag fails while a local step remains exempt.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        write_file : FileWriter
            Fixture writer that creates parent directories and writes UTF-8
            repository files.
        """
        workflow = write_file(
            '.github/workflows/ci.yml',
            'steps:\n  - uses: actions/checkout@v4\n  - uses: ./local\n',
        )

        assert validate(tmp_path / '.github') == [
            f'{workflow}:2: remote action must use a full '
            '40-character commit SHA: actions/checkout@v4',
        ]

    def test_reports_missing_automation_directory(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify missing automation directories produce a discovery diagnostic.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        """
        assert validate(tmp_path / 'missing') == [
            f'automation directory does not exist: {tmp_path / 'missing'}',
        ]


# !SECTION
