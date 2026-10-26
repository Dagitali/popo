"""
:mod:`tests.integration.test_i_source_checks` module.

Exercise opt-in source and artifact commands through the public dispatcher.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from popo.cli import main

# SECTION: TESTS


class TestSourceCommands:
    """Verify selection, JSON reporting and private-artifact boundaries."""

    @pytest.mark.parametrize(
        'command,domain,filename,source',
        (
            ('check-python-source', 'python-source', 'rule.py', 'x = 1'),
            (
                'check-swift-documentation',
                'swift-documentation',
                'Rule.swift',
                '/// File and rule overview.\nstruct Rule {}',
            ),
            ('check-logs', 'logs', 'console.log', 'Clean startup'),
        ),
    )
    def test_individual_and_profile_dispatch(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        command: str,
        domain: str,
        filename: str,
        source: str,
    ) -> None:
        extra = '\npatterns = { failure = "FORBIDDEN" }' if domain == 'logs' else ''
        (tmp_path / 'popo.toml').write_text(
            f'[profiles.selected]\nchecks = ["{command}"]\n'
            f'[{domain}]\ninclude = ["{filename}"]{extra}',
        )
        (tmp_path / filename).write_text(source)
        for arguments in ([command], ['check-all', '--profile', 'selected']):
            assert main([*arguments, '--root', str(tmp_path), '--format', 'json']) == 0
            report = json.loads(capsys.readouterr().out)
            assert report['passed']
            assert report['checks'][0]['check'] == command
        (tmp_path / filename).unlink()
        assert main([command, '--root', str(tmp_path), '--format', 'json']) == 1
        assert not json.loads(capsys.readouterr().out)['passed']

    @pytest.mark.parametrize(
        'command',
        ('check-python-source', 'check-swift-documentation', 'check-logs'),
    )
    def test_absent_configuration_reports_failure(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        command: str,
    ) -> None:
        assert main([command, '--root', str(tmp_path), '--format', 'json']) == 1
        report = json.loads(capsys.readouterr().out)
        assert 'configuration:' in report['checks'][0]['diagnostics'][0]['message']

    def test_explicit_external_log_root_redacts_financial_contents(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        consumer = tmp_path / 'consumer'
        artifact = tmp_path / 'artifacts'
        consumer.mkdir()
        artifact.mkdir()
        (consumer / 'popo.toml').write_text(
            '[logs]\ninclude = ["*.log"]\npatterns = { warning = "WARNING" }',
        )
        (artifact / 'console.log').write_text('WARNING: PRIVATE BALANCE')
        assert (
            main(
                [
                    'check-logs',
                    '--root',
                    str(consumer),
                    '--log-root',
                    str(artifact),
                    '--format',
                    'json',
                ],
            )
            == 1
        )
        output = capsys.readouterr().out
        assert 'PRIVATE BALANCE' not in output
        assert 'WARNING' not in output
        assert 'console.log:1: warning' in output

    def test_aggregate_continues_after_invalid_domain_configuration(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            'checks = ["check-python-source", "check-logs"]\n'
            '[python-source]\ninclude = []\n'
            '[logs]\ninclude = ["*.log"]\npatterns = { warning = "WARNING" }',
        )
        assert main(['check-all', '--root', str(tmp_path), '--format', 'json']) == 1
        report = json.loads(capsys.readouterr().out)
        assert [item['check'] for item in report['checks']] == [
            'check-python-source',
            'check-logs',
        ]
        assert all(not item['passed'] for item in report['checks'])


# !SECTION
