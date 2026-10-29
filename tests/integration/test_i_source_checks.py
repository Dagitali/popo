"""
:mod:`tests.integration.test_i_source_checks` module.

Exercise opt-in source and artifact commands through the public dispatcher.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Self

import pytest

from popo.cli import main
from popo.config.selection import load_plan
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestSourceCommands:
    """Verify selection, JSON reporting and private-artifact boundaries."""

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

    @pytest.mark.parametrize(
        'command,domain,filename,source',
        (
            ('check-python-source', 'python-source', 'rule.py', 'x = 1'),
            (
                'check-swift-source',
                'swift-source',
                'Rule.swift',
                '/// File and rule overview.\nstruct Rule {}',
            ),
            ('check-logs', 'logs', 'console.log', 'Clean startup'),
        ),
    )
    @pytest.mark.parametrize('present', [True, False], ids=['present', 'missing'])
    def test_selected_dispatch_preserves_inputs(
        self: Self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        command: str,
        domain: str,
        filename: str,
        source: str,
        select_check: Callable[[Path, str], tuple[str, ...]],
        present: bool,
        cli_format: str | None,
        format_arguments: tuple[str, ...],
    ) -> None:
        extra = '\npatterns = { failure = "FORBIDDEN" }' if domain == 'logs' else ''
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude = ["{filename}"]{extra}',
        )
        if present:
            (tmp_path / filename).write_text(source, encoding='utf-8')
        assert command in load_plan(tmp_path).checks
        arguments = select_check(tmp_path, command)
        before = snapshot_files(tmp_path)
        assert main([*arguments, '--root', str(tmp_path), *format_arguments]) == (
            0 if present else 1
        )
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            report = json.loads(output.out)
            assert report['passed'] is present
            assert [item['check'] for item in report['checks']] == [command]
            if not present:
                assert report['checks'][0]['diagnostics'][0]['message'] == (
                    f'no inputs match: {filename}'
                )
        else:
            assert output.out.startswith('PASS: ' if present else 'FAIL: ')
        assert snapshot_files(tmp_path) == before


# !SECTION
