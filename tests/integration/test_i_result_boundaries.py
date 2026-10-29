"""
:mod:`tests.integration.test_i_result_boundaries` module.

Exercise result and architecture commands through public CLI selection.
"""

import json
from pathlib import Path
from typing import Self
from unittest.mock import Mock

import pytest

from popo.cli import main
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestValidationCommands:
    """Verify profiles, redaction and aggregate failure continuation."""

    @pytest.mark.parametrize(
        'command',
        (
            'check-test-results',
            'check-swift-boundaries',
            'check-python-boundaries',
            'check-python-source',
            'check-swift-source',
            'check-logs',
        ),
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
        before = snapshot_files(tmp_path)
        assert main([command, '--root', str(tmp_path), '--format', 'json']) == 1
        output = capsys.readouterr()
        assert output.err == ''
        report = json.loads(output.out)
        assert report['command'] == command
        assert report['passed'] is False
        assert len(report['checks']) == 1
        check = report['checks'][0]
        assert check['check'] == command
        assert check['passed'] is False
        assert len(check['diagnostics']) == 1
        diagnostic = check['diagnostics'][0]
        assert diagnostic['severity'] == 'error'
        assert 'configuration:' in diagnostic['message']
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'policy,expected',
        [
            pytest.param(
                'checks=["check-test-results","check-swift-boundaries"]\n'
                '[test-results]\nadapter="unknown"\ninclude=["*.json"]',
                (
                    (
                        'check-test-results',
                        'configuration: test-results.adapter must be xcode-summary',
                    ),
                    (
                        'check-swift-boundaries',
                        'configuration: swift-boundaries must be a TOML table',
                    ),
                ),
                id='result-and-boundary',
            ),
            pytest.param(
                'checks=["check-python-source","check-logs"]\n'
                '[python-source]\ninclude=[]\n'
                '[logs]\ninclude=["*.log"]\npatterns={warning="WARNING"}',
                (
                    (
                        'check-python-source',
                        'configuration: python-source.include must not be empty',
                    ),
                    ('check-logs', 'no inputs match: *.log'),
                ),
                id='source-and-logs',
            ),
        ],
    )
    def test_aggregate_continues_after_domain_configuration_failure(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        policy: str,
        expected: tuple[tuple[str, str], ...],
    ) -> None:
        """
        One malformed domain cannot hide other selected diagnostics.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing public CLI text or JSON output.
        policy : str
            Explicit aggregate selection with an invalid first domain.
        expected : tuple[tuple[str, str], ...]
            Selected commands and their complete failure messages, in order.
        """
        (tmp_path / 'popo.toml').write_text(policy, encoding='utf-8')
        before = snapshot_files(tmp_path)
        assert main(['check-all', '--root', str(tmp_path), '--format', 'json']) == 1
        output = capsys.readouterr()
        assert output.err == ''
        assert json.loads(output.out) == {
            'schema_version': 1,
            'command': 'check-all',
            'passed': False,
            'checks': [
                {
                    'check': command,
                    'passed': False,
                    'diagnostics': [{'severity': 'error', 'message': message}],
                    'summary': '',
                }
                for command, message in expected
            ],
        }
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'options',
        [
            pytest.param(
                ('--summary', 'one.json', '--results-root', '.'),
                id='summary-first',
            ),
            pytest.param(
                ('--results-root', '.', '--summary', 'one.json'),
                id='root-first',
            ),
        ],
    )
    def test_artifact_overrides_are_mutually_exclusive(
        self: Self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        options: tuple[str, ...],
    ) -> None:
        """Reject ambiguous input requests before reading policy or artifacts."""
        reader = Mock(side_effect=AssertionError('unexpected input read'))
        monkeypatch.setattr(Path, 'read_text', reader)
        monkeypatch.setattr(Path, 'read_bytes', reader)
        with pytest.raises(SystemExit, check=lambda error: error.code == 2):
            main(['check-test-results', '--root', str(tmp_path), *options])
        reader.assert_not_called()
        output = capsys.readouterr()
        assert output.out == ''
        assert 'not allowed with argument' in output.err
        assert '--summary' in output.err
        assert '--results-root' in output.err

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


# !SECTION
