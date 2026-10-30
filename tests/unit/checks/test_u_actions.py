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

    @pytest.mark.parametrize(
        'filename,reference',
        (
            pytest.param(
                'actions/setup/action.yaml',
                'owner/action@v1',
                id='nested-composite-action',
            ),
            pytest.param(
                '.github/workflows/ci.yml',
                'actions/checkout@v4',
                id='nested-workflow',
            ),
        ),
    )
    def test_nested_automation_preserves_pin_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
        reference: str,
    ) -> None:
        """
        Report floating action tags in nested workflows and composite actions.

        Verify recursive action discovery reports only the unpinned remote
        step. Local steps and container references remain exempt, and a
        full uppercase SHA remains accepted alongside the mutable remote tag.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        filename : str
            Nested workflow or composite-action path beneath the selected root.
        reference : str
            Floating remote action tag that must produce the sole finding.
        """
        action = write_file(
            filename,
            'steps:\n  - uses: ./local\n  - uses: docker://alpine:3\n'
            f'  - uses: "owner/action@{'A' * 40}" # pinned\n'
            f'  - uses: {reference}\n',
        )
        before = snapshot_files(tmp_path)
        assert validate(tmp_path) == [
            f'{action}:5: remote action must use a full '
            f'40-character commit SHA: {reference}',
        ]
        assert snapshot_files(tmp_path) == before

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
