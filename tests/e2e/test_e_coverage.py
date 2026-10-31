"""
:mod:`tests.e2e.test_e_coverage` module.

Verify installed coverage reporting from wheel and source distributions.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from tests.support.coverage import export_report
from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: TESTS


class TestInstalledCoverage:
    """
    Exercise installed adapters outside the checkout without native exports.
    """

    @pytest.mark.parametrize('adapter', ('llvm', 'xccov'))
    @pytest.mark.parametrize('module', (False, True), ids=('console', 'module'))
    @pytest.mark.parametrize('format_', ('markdown', 'json'))
    def test_installed_summary_is_read_only_and_private(
        self: Self,
        installation: Installation,
        tmp_path: Path,
        adapter: str,
        module: bool,
        format_: str,
    ) -> None:
        """
        Emit complete measurements and reject unavailable installed inputs.

        Parameters
        ----------
        installation : Installation
            Wheel or sdist installed in an isolated verification environment.
        tmp_path : pathlib.Path
            Disposable consumer directory outside the package checkout.
        adapter : str
            Coverage adapter selected for the synthetic report.
        module : bool
            Use the installed module entry point instead of the console script.
        format_ : str
            Aggregate Markdown or versioned JSON output.
        """
        source = tmp_path / 'input[1].json'
        arguments = (
            'coverage-summary',
            str(source),
            '--adapter',
            adapter,
            '--include',
            '**/App/**/*.swift',
            '--format',
            format_,
        )
        source.write_text(
            json.dumps(export_report(adapter, [('PRIVATE/App/F.swift', 3, 4)])),
        )
        before = snapshot_files(tmp_path)
        result = installation.run(*arguments, module=module)
        assert result.returncode == 0, result.stderr
        assert 'PRIVATE' not in result.stdout + result.stderr
        if format_ == 'json':
            assert json.loads(result.stdout)['metrics']['lines']['percent'] == 75.0
        else:
            assert '| lines | 3 | 4 | 75.0% |' in result.stdout
        assert snapshot_files(tmp_path) == before
        source.write_text(json.dumps(export_report(adapter, [])))
        before = snapshot_files(tmp_path)
        result = installation.run(*arguments, module=module)
        assert result.returncode == 1
        assert result.stdout == ''
        assert 'measurement unavailable' in result.stderr
        assert snapshot_files(tmp_path) == before


# !SECTION
