"""
:mod:`tests.unit.checks.test_u_actions` module.

Test immutable action references and nested automation discovery.
"""

from pathlib import Path

import pytest

from popo.checks.actions import validate
from tests.support.files import FileWriter, snapshot_files

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

    def test_checks_nested_composite_actions_and_ignores_local_steps(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify checks nested composite actions and ignores local steps.

        Verify recursive action discovery reports only the unpinned remote
        step.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
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
        'reference,accepted',
        [
            pytest.param('owner/action@' + 'a' * 40, True, id='lowercase-sha'),
            pytest.param('owner/action@' + 'A' * 40, True, id='uppercase-sha'),
            pytest.param('./local', True, id='local-action'),
            pytest.param('docker://alpine:3', True, id='container'),
            pytest.param('owner/action', False, id='no-revision'),
            pytest.param('owner/action@main', False, id='branch'),
            pytest.param('owner/action@abc123', False, id='short-sha'),
            pytest.param('@' + 'a' * 40, False, id='no-action'),
            pytest.param('owner/action@', False, id='empty-revision'),
            pytest.param('owner/action@' + 'g' * 40, False, id='nonhex-revision'),
        ],
    )
    @pytest.mark.parametrize(
        'template',
        [
            pytest.param('uses: {reference}', id='plain'),
            pytest.param('- uses: "{reference}" # pinned?', id='double-quoted'),
            pytest.param("- uses: '{reference}' # pinned?", id='single-quoted'),
        ],
    )
    def test_reference_pin_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        reference: str,
        accepted: bool,
        template: str,
    ) -> None:
        """
        Validate immutable, local and container action references.

        Require precise line-numbered failures regardless of YAML quoting or
        trailing comments, without fetching or executing referenced actions.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        reference : str
            Automation uses value selected for the pin-policy scenario.
        accepted : bool
            Whether the reference is immutable or exempt from remote pinning.
        template : str
            Plain or quoted uses line with optional list marker and comment.
        """
        action = write_file(
            '.github/ci.yaml',
            'name: Fixture\n' + template.format(reference=reference) + '\n',
        )
        before = snapshot_files(tmp_path)
        assert validate(tmp_path / '.github') == (
            []
            if accepted
            else [
                f'{action}:2: remote action must use a full '
                f'40-character commit SHA: {reference}',
            ]
        )
        assert snapshot_files(tmp_path) == before

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
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
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
            Temporary directory for isolated test inputs.
        """
        assert validate(tmp_path / 'missing') == [
            f'automation directory does not exist: {tmp_path / 'missing'}',
        ]


# !SECTION
