"""
:mod:`tests.unit.checks.test_u_logs` module.

Exercise redacted log diagnostics and artifact boundaries.
"""

from pathlib import Path
from typing import Self
from unittest.mock import patch

import pytest

from popo.checks import logs
from popo.config.source_checks import load_source_check
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(
    name='artifact_root',
    params=(pytest.param(False, id='repository'), pytest.param(True, id='artifact')),
)
def artifact_root_fixture(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> Path | None:
    """
    Select default repository discovery or an explicit disposable log root.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Consumer repository shared with the requesting test.
    request : pytest.FixtureRequest
        Whether this case uses a separate artifact directory.

    Returns
    -------
    pathlib.Path or None
        Created artifact directory, or None to exercise the default root.
    """
    if not request.param:
        return None
    root = tmp_path / 'artifacts'
    root.mkdir()
    return root


# !SECTION


# SECTION: TESTS


class TestRedactedLogs:
    """Keep private lines out of both rule findings and read errors."""

    def test_named_literal_findings_and_clean_inputs(
        self: Self,
        tmp_path: Path,
        artifact_root: Path | None,
        write_file: FileWriter,
    ) -> None:
        """
        Verify named literal findings and clean inputs.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        artifact_root : Path | None
            Explicit artifact directory, or None to use the consumer root.
        write_file : FileWriter
            Shared UTF-8 writer creating the consumer policy.
        """
        write_file(
            'popo.toml',
            '[logs]\ninclude = ["**/*.log"]\n'
            '[logs.patterns]\nlayout = "Invalid frame dimension"',
        )
        artifact = artifact_root or tmp_path
        log = artifact / 'private.log'
        log.write_text(
            'Normal\nInvalid frame dimension: PRIVATE BALANCE\n',
            encoding='utf-8',
        )
        config = load_source_check(tmp_path, 'logs')
        assert logs.validate(config, artifact_root) == ['private.log:2: layout']
        log.write_text('Normal\n', encoding='utf-8')
        assert logs.validate(config, artifact_root) == []
        log.unlink()
        assert logs.validate(config, artifact_root) == ['no inputs match: **/*.log']

    def test_overlapping_rules_preserve_redacted_order(
        self: Self,
        tmp_path: Path,
        artifact_root: Path | None,
        write_file: FileWriter,
    ) -> None:
        """
        Report each matching rule once per line, in declaration order.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        artifact_root : Path | None
            Explicit artifact directory, or None to use the consumer root.
        write_file : FileWriter
            Shared UTF-8 writer creating the consumer policy.
        """
        write_file(
            'popo.toml',
            '[logs]\ninclude=["**/*.log"]\npatterns={warning="WARN", broad="WAR"}',
        )
        boundary = artifact_root or tmp_path
        for filename in ('z.log', 'a.log'):
            (boundary / filename).write_text(
                'WARN WARN PRIVATE\nclean\nWARN PRIVATE',
                encoding='utf-8',
            )
        config = load_source_check(tmp_path, 'logs')
        before = snapshot_files(tmp_path)
        assert logs.validate(config, artifact_root) == [
            f'{filename}:{line}: {rule}'
            for filename in ('a.log', 'z.log')
            for line in (1, 3)
            for rule in ('warning', 'broad')
        ]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('error', [OSError, ValueError])
    def test_root_resolution_failures_are_redacted(
        self: Self,
        tmp_path: Path,
        write_file: FileWriter,
        error: type[Exception],
        artifact_root: Path | None,
    ) -> None:
        """
        Report inaccessible input roots without exposing exception details.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Shared UTF-8 writer creating the consumer policy.
        error : type[Exception]
            Error value or exception class injected by the scenario.
        artifact_root : Path | None
            Explicit artifact directory, or None to use the consumer root.
        """
        write_file(
            'popo.toml',
            '[logs]\ninclude=["*.log"]\npatterns={warning="WARNING"}',
        )
        config = load_source_check(tmp_path, 'logs')

        before = snapshot_files(tmp_path)
        with patch.object(
            Path,
            'resolve',
            autospec=True,
            side_effect=error('PRIVATE ROOT'),
        ) as resolve:
            assert logs.validate(config, artifact_root) == [
                'cannot resolve selected input root',
            ]
        resolve.assert_called_once_with(artifact_root or config.root)
        assert snapshot_files(tmp_path) == before


# !SECTION
