"""
:mod:`tests.unit.checks.test_u_test_results` module.

Exercise strict report schema, configurable acceptance and private diagnostics.
"""

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Self
from unittest.mock import Mock

import pytest

from popo.checks.test_results import validate, xcode_summary
from popo.config.test_results import THRESHOLDS, load_test_results_config
from popo.config.test_results import TestResultsConfig as ResultConfig
from tests.support.files import snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='passing')
def passing_fixture() -> dict[str, object]:
    """
    Supply one accepted Xcode-summary record per scenario.

    Returns
    -------
    dict[str, object]
        Independent native counts with no failures, skips or warnings.
    """
    return {'totalTestCount': 1, 'passedTests': 1, 'failedTests': 0, 'skippedTests': 0}


@pytest.fixture(name='relaxed_thresholds')
def relaxed_thresholds_fixture() -> dict[str, int]:
    """
    Supply fresh relaxed acceptance limits without weakening schema rules.

    Returns
    -------
    dict[str, int]
        Zero minimum counts and maximum counts of one for failures, skips and
        warnings. Arithmetic and input-shape requirements remain mandatory.
    """
    return THRESHOLDS | {
        'minimum-tests': 0,
        'minimum-passed': 0,
        'maximum-failed': 1,
        'maximum-skipped': 1,
        'maximum-warnings': 1,
    }


@pytest.fixture(name='result_config')
def result_config_fixture(
    tmp_path: Path,
) -> ResultConfig:
    """
    Load independent report selection and thresholds for each input test.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Disposable consumer root used by the requesting test.

    Returns
    -------
    ResultConfig
        JSON selection and fresh acceptance settings from the public loader.
    """
    (tmp_path / 'popo.toml').write_text(
        '[test-results]\nadapter="xcode-summary"\ninclude=["*.json"]',
        encoding='utf-8',
    )
    return load_test_results_config(tmp_path)


# !SECTION


# SECTION: TESTS


class TestResultAdapter:
    """Validate the named report schema without echoing native payloads."""

    @pytest.mark.parametrize(
        'changes,thresholds',
        (
            (
                {'totalTestCount': 0, 'passedTests': 0},
                ('minimum-tests', 'minimum-passed'),
            ),
            (
                {'passedTests': 0, 'failedTests': 1},
                ('minimum-passed', 'maximum-failed'),
            ),
            ({'totalTestCount': 2, 'failedTests': 1}, ('maximum-failed',)),
            ({'totalTestCount': 2, 'skippedTests': 1}, ('maximum-skipped',)),
            (
                {'runtimeWarnings': [{'message': 'PRIVATE BALANCE'}]},
                ('maximum-warnings',),
            ),
        ),
    )
    def test_acceptance_is_consumer_configurable(
        self: Self,
        passing: dict[str, object],
        relaxed_thresholds: dict[str, int],
        changes: dict[str, object],
        thresholds: tuple[str, ...],
    ) -> None:
        """
        Reject all threshold violations and permit an explicit relaxed policy.

        Parameters
        ----------
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        relaxed_thresholds : dict[str, int]
            Fresh acceptance limits allowing each selected violation.
        changes : dict[str, object]
            Count or warning replacements introducing acceptance violations.
        thresholds : tuple[str, ...]
            Every failing acceptance setting, in diagnostic order.
        """
        report = passing | changes
        findings = xcode_summary(report, THRESHOLDS)
        assert findings == [
            f'{threshold} acceptance threshold not satisfied'
            for threshold in thresholds
        ]
        assert 'PRIVATE BALANCE' not in str(findings)
        assert xcode_summary(report, relaxed_thresholds) == []

    @pytest.mark.parametrize(
        'field',
        ('totalTestCount', 'passedTests', 'failedTests', 'skippedTests'),
    )
    @pytest.mark.parametrize('value', (True, False, -1, '1', 1.0, None, ...))
    def test_counts_are_required_nonnegative_integers(
        self: Self,
        passing: dict[str, object],
        field: str,
        value: object,
    ) -> None:
        """
        Reject malformed or missing counts before arithmetic acceptance.

        Parameters
        ----------
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        field : str
            Required native count field selected for mutation.
        value : object
            Malformed value or the sentinel selecting field removal.
        """
        if value is ...:
            del passing[field]
        else:
            passing[field] = value
        assert xcode_summary(passing, THRESHOLDS) == ['malformed native test counts']

    @pytest.mark.parametrize('total', (0, 2))
    def test_inconsistent_totals_are_not_threshold_overrides(
        self: Self,
        passing: dict[str, object],
        relaxed_thresholds: dict[str, int],
        total: int,
    ) -> None:
        """
        Always require internally consistent counts even with relaxed limits.

        Parameters
        ----------
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        relaxed_thresholds : dict[str, int]
            Explicit relaxed policy that cannot bypass count arithmetic.
        total : int
            Total below or above the sum of the component counts.
        """
        passing['totalTestCount'] = total
        assert xcode_summary(passing, relaxed_thresholds) == [
            'native test counts disagree with total',
        ]

    @pytest.mark.parametrize('root', (None, [], 'PRIVATE', 1, False))
    def test_invalid_root_is_redacted(
        self: Self,
        root: object,
    ) -> None:
        """
        Require a mapping and avoid including invalid root contents.

        Parameters
        ----------
        root : object
            Invalid JSON root supplied directly to the named adapter.
        """
        assert xcode_summary(root, THRESHOLDS) == ['malformed native test counts']

    @pytest.mark.parametrize('warnings', (False, 0, {}, '', None))
    def test_warning_collections_must_be_lists(
        self: Self,
        passing: dict[str, object],
        warnings: object,
    ) -> None:
        """
        Do not treat malformed false-like warning fields as clean evidence.

        Parameters
        ----------
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        warnings : object
            Malformed false-like warning value that must not count as clean
            evidence.
        """
        assert xcode_summary(passing | {'runtimeWarnings': warnings}, THRESHOLDS) == [
            'malformed native runtime warnings',
        ]


class TestResultInputs:
    """Keep artifact selection explicit, confined and read-only."""

    def test_all_selected_reports_must_pass(
        self: Self,
        tmp_path: Path,
        result_config: ResultConfig,
        passing: dict[str, object],
    ) -> None:
        """
        A clean sibling cannot hide malformed or failed result evidence.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        result_config : ResultConfig
            Fresh loaded policy selecting JSON reports in this consumer root.
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        """
        (tmp_path / 'good.json').write_text(json.dumps(passing))
        (tmp_path / 'bad.json').write_text('{}')
        assert validate(result_config) == [
            'bad.json: malformed native test counts',
        ]

    def test_single_summary_is_literal_and_does_not_read_siblings(
        self: Self,
        tmp_path: Path,
        result_config: ResultConfig,
        passing: dict[str, object],
    ) -> None:
        """
        Escape filename glob characters and honor only the explicit report.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        result_config : ResultConfig
            Fresh loaded policy selecting JSON reports in this consumer root.
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        """
        selected = tmp_path / 'summary[1].json'
        selected.write_text(json.dumps(passing))
        (tmp_path / 'summary1.json').write_text('PRIVATE invalid JSON')
        assert validate(result_config, summary=selected) == []

    @pytest.mark.parametrize(
        'case',
        ('missing', 'invalid-json', 'invalid-utf8', 'escaped'),
    )
    def test_unusable_evidence_fails_closed(
        self: Self,
        tmp_path: Path,
        result_config: ResultConfig,
        symlink: Callable[[Path, Path], None],
        case: str,
    ) -> None:
        """
        Reject missing, malformed or escaping evidence.

        Parameters
        ----------
        tmp_path : Path
            Pytest-managed directory containing only disposable consumer
            inputs.
        result_config : ResultConfig
            Fresh loaded policy selecting JSON reports in this consumer root.
        symlink : collections.abc.Callable[[pathlib.Path, pathlib.Path], None]
            Capability-aware link creator that preserves unexpected errors.
        case : str
            Independent missing, malformed, unreadable or escaping input
            scenario.
        """
        path = tmp_path / 'summary.json'
        if case == 'invalid-json':
            path.write_text('{PRIVATE')
        elif case == 'invalid-utf8':
            path.write_bytes(b'\xff')
        elif case == 'escaped':
            outside = tmp_path.parent / 'outside.json'
            outside.write_bytes(b'\xffPRIVATE report')
            symlink(path, outside)
        before = snapshot_files(tmp_path)
        findings = validate(result_config)
        expected = {
            'missing': ['no inputs match: *.json'],
            'invalid-json': ['summary.json: invalid test-result JSON'],
            'invalid-utf8': ['summary.json: cannot read UTF-8 input'],
            'escaped': [
                'summary.json: input escapes selected root',
                'no inputs match: *.json',
            ],
        }
        assert findings == expected[case]
        assert 'PRIVATE' not in str(findings)
        assert snapshot_files(tmp_path) == before


class TestDirectResultConfiguration:
    """Fail safely when direct callers bypass loader and CLI guarantees."""

    def test_conflicting_overrides_fail_before_discovery(
        self,
        tmp_path: Path,
        result_config: ResultConfig,
    ) -> None:
        """
        Do not inspect artifacts when root and summary overrides conflict.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        result_config : ResultConfig
            Isolated test-result policy and report-writing helpers.
        """
        assert validate(result_config, tmp_path, tmp_path / 'missing.json') == [
            'choose either a result root or a single summary',
        ]

    @pytest.mark.parametrize('error_type', (OSError, ValueError))
    def test_root_resolution_errors_are_redacted(
        self,
        tmp_path: Path,
        result_config: ResultConfig,
        monkeypatch: pytest.MonkeyPatch,
        error_type: type[Exception],
    ) -> None:
        """
        Report unusable artifact roots without disclosing exception text.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        result_config : ResultConfig
            Isolated test-result policy and report-writing helpers.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        error_type : type[Exception]
            Exception class injected into the inspected operation.
        """
        monkeypatch.setattr(Path, 'resolve', Mock(side_effect=error_type('PRIVATE')))
        assert validate(result_config) == ['cannot resolve selected result root']

    @pytest.mark.parametrize('valid_json', (False, True))
    def test_unsupported_adapter_preserves_json_error_precedence(
        self,
        tmp_path: Path,
        result_config: ResultConfig,
        valid_json: bool,
    ) -> None:
        """
        Reject unknown adapters without hiding malformed JSON evidence.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        result_config : ResultConfig
            Isolated test-result policy and report-writing helpers.
        valid_json : bool
            Whether the report contains syntactically valid JSON.
        """
        (tmp_path / 'report.json').write_text(
            '{}' if valid_json else '{PRIVATE',
            encoding='utf-8',
        )
        config = replace(result_config, adapter='unknown')
        expected = (
            'unsupported test-result adapter'
            if valid_json
            else 'invalid test-result JSON'
        )
        assert validate(config) == [f'report.json: {expected}']


# !SECTION
