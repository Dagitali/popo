"""
:mod:`tests.integration.test_i_result_boundaries` module.

Exercise result and architecture commands through public CLI selection.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from popo.cli import main
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestValidationCommands:
    """Verify profiles, redaction and aggregate failure continuation."""

    @pytest.mark.parametrize('command', ('check-python-boundaries', 'check-all'))
    def test_python_boundary_selection_and_reporting(
        self,
        python_boundary_case: tuple[Path, str | None],
        capsys: pytest.CaptureFixture[str],
        command: str,
    ) -> None:
        """Report the native boundary outcome through direct/aggregate JSON."""
        root, expected = python_boundary_case
        before = snapshot_files(root)
        assert main([command, '--root', str(root), '--format', 'json']) == int(
            expected is not None,
        )
        report = json.loads(capsys.readouterr().out)
        assert report['command'] == command
        assert report['passed'] is (expected is None)
        assert len(report['checks']) == 1
        check = report['checks'][0]
        assert check['check'] == 'check-python-boundaries'
        assert check['passed'] is (expected is None)
        if expected is None:
            assert check['diagnostics'] == []
        else:
            assert any(expected in item['message'] for item in check['diagnostics'])
            assert all(item['severity'] == 'error' for item in check['diagnostics'])
        assert snapshot_files(root) == before

    def test_results_use_explicit_artifacts_and_json_reporting(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        One selected report overrides sibling discovery and stays read-only.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing public CLI text or JSON output.
        """
        consumer = tmp_path / 'consumer'
        artifacts = tmp_path / 'artifacts'
        consumer.mkdir()
        artifacts.mkdir()
        (consumer / 'popo.toml').write_text(
            '[test-results]\nadapter="xcode-summary"\ninclude=["*.json"]',
        )
        report = artifacts / 'summary.json'
        report.write_text(
            json.dumps(
                {
                    'totalTestCount': 1,
                    'passedTests': 1,
                    'failedTests': 0,
                    'skippedTests': 0,
                },
            ),
        )
        (artifacts / 'unselected.json').write_text('PRIVATE invalid content')
        before = snapshot_files(tmp_path)
        arguments = [
            'check-test-results',
            '--root',
            str(consumer),
            '--summary',
            str(report),
            '--format',
            'json',
        ]
        assert main(arguments) == 0
        assert json.loads(capsys.readouterr().out)['passed']
        assert snapshot_files(tmp_path) == before
        report.write_text('{PRIVATE invalid JSON')
        assert main(arguments) == 1
        output = capsys.readouterr().out
        assert 'PRIVATE' not in output
        assert not json.loads(output)['passed']

    def test_boundary_profile_and_negative_reference(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Public profile selection runs the configured graph without writes.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing public CLI text or JSON output.
        """
        (tmp_path / 'popo.toml').write_text(
            '[profiles.layers]\nchecks=["check-swift-boundaries"]\n'
            '[swift-boundaries]\n'
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["Core.swift"]\n'
            'forbidden-layers=["ui"]\n'
            '[[swift-boundaries.layers]]\nname="ui"\ninclude=["UI.swift"]',
        )
        (tmp_path / 'Core.swift').write_text('struct Rule {}')
        (tmp_path / 'UI.swift').write_text('struct Screen {}')
        before = snapshot_files(tmp_path)
        args = [
            'check-all',
            '--profile',
            'layers',
            '--root',
            str(tmp_path),
            '--format',
            'json',
        ]
        assert main(args) == 0
        assert (
            json.loads(capsys.readouterr().out)['checks'][0]['check']
            == 'check-swift-boundaries'
        )
        assert snapshot_files(tmp_path) == before
        (tmp_path / 'Core.swift').write_text('let dependency: Screen')
        assert main(args) == 1
        assert 'forbidden symbol Screen' in capsys.readouterr().out

    @pytest.mark.parametrize(
        'command',
        ('check-test-results', 'check-swift-boundaries', 'check-python-boundaries'),
    )
    def test_absent_configuration_fails(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        command: str,
    ) -> None:
        """
        Do not silently infer policy when the selected domain is absent.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing public CLI text or JSON output.
        command : str
            Explicit public validator selected for this consumer scenario.
        """
        assert main([command, '--root', str(tmp_path), '--format', 'json']) == 1
        assert not json.loads(capsys.readouterr().out)['passed']

    def test_aggregate_continues_after_domain_configuration_failure(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        One malformed domain cannot hide other selected diagnostics.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing public CLI text or JSON output.
        """
        (tmp_path / 'popo.toml').write_text(
            'checks=["check-test-results","check-swift-boundaries"]\n'
            '[test-results]\nadapter="unknown"\ninclude=["*.json"]',
        )
        assert main(['check-all', '--root', str(tmp_path), '--format', 'json']) == 1
        checks = json.loads(capsys.readouterr().out)['checks']
        assert [item['check'] for item in checks] == [
            'check-test-results',
            'check-swift-boundaries',
        ]
        assert all(not item['passed'] for item in checks)

    def test_artifact_overrides_are_mutually_exclusive(self: Self) -> None:
        """Reject ambiguous input requests before reading policy or artifacts."""
        with pytest.raises(SystemExit) as error:
            main(['check-test-results', '--summary', 'one.json', '--results-root', '.'])
        assert error.value.code == 2


# !SECTION
