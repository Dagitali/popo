"""
:mod:`tests.unit.checks.test_u_test_results` module.

Exercise strict report schema, configurable acceptance and private diagnostics.
"""

import json
from dataclasses import replace
from pathlib import Path
from typing import Self
from unittest.mock import Mock

import pytest

from popo.checks.test_results import validate, xcode_summary
from popo.config.test_results import THRESHOLDS, load_test_results_config
from popo.config.test_results import TestResultsConfig as ResultConfig

# SECTION: FIXTURES


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


@pytest.fixture(name='passing')
def passing_fixture() -> dict[str, object]:
    """
    Supply one accepted Xcode-summary record per scenario.

    Returns
    -------
    dict[str, object]
        Independent native counts with no failures, skips or warnings.
    """
    return dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0)


# !SECTION


# SECTION: TESTS


class TestResultAdapter:
    """Validate the named report schema without echoing native payloads."""

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

    def test_inconsistent_totals_are_not_threshold_overrides(
        self: Self,
        passing: dict[str, object],
    ) -> None:
        """
        Always require internally consistent counts even with relaxed limits.

        Parameters
        ----------
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        """
        passing['totalTestCount'] = 2
        assert xcode_summary(passing, THRESHOLDS) == [
            'native test counts disagree with total',
        ]

    @pytest.mark.parametrize(
        'changes,threshold',
        (
            ({'totalTestCount': 0, 'passedTests': 0}, 'minimum-tests'),
            ({'passedTests': 0, 'failedTests': 1}, 'minimum-passed'),
            ({'totalTestCount': 2, 'failedTests': 1}, 'maximum-failed'),
            ({'totalTestCount': 2, 'skippedTests': 1}, 'maximum-skipped'),
            ({'runtimeWarnings': [{'message': 'PRIVATE BALANCE'}]}, 'maximum-warnings'),
        ),
    )
    def test_acceptance_is_consumer_configurable(
        self: Self,
        passing: dict[str, object],
        changes: dict[str, object],
        threshold: str,
    ) -> None:
        """
        Reject each threshold violation and permit an explicit relaxed policy.

        Parameters
        ----------
        passing : dict[str, object]
            Fresh accepted native-summary mapping, isolated per scenario.
        changes : dict[str, object]
            Count or warning replacements introducing one acceptance violation.
        threshold : str
            Consumer acceptance setting expected to reject the modified report.
        """
        report = passing | changes
        findings = xcode_summary(report, THRESHOLDS)
        assert any(threshold in finding for finding in findings)
        assert 'PRIVATE BALANCE' not in str(findings)
        relaxed = THRESHOLDS | {
            'minimum-tests': 0,
            'minimum-passed': 0,
            'maximum-failed': 1,
            'maximum-skipped': 1,
            'maximum-warnings': 1,
        }
        assert xcode_summary(report, relaxed) == []

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

    @pytest.mark.parametrize(
        'case',
        ('missing', 'invalid-json', 'invalid-utf8', 'escaped'),
    )
    def test_unusable_evidence_fails_closed(
        self: Self,
        tmp_path: Path,
        result_config: ResultConfig,
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
            path.symlink_to(tmp_path.parent / 'outside.json')
        findings = validate(result_config)
        assert findings
        assert 'PRIVATE' not in str(findings)

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


class TestDirectResultConfiguration:
    """Fail safely when direct callers bypass loader and CLI guarantees."""

    @pytest.mark.parametrize('valid_json', (False, True))
    def test_unsupported_adapter_preserves_json_error_precedence(
        self,
        tmp_path: Path,
        result_config: ResultConfig,
        valid_json: bool,
    ) -> None:
        """Reject unknown adapters without hiding malformed JSON evidence."""
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

    def test_conflicting_overrides_fail_before_discovery(
        self,
        tmp_path: Path,
        result_config: ResultConfig,
    ) -> None:
        """
        Do not inspect artifacts when root and summary overrides conflict.
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
        """Report unusable artifact roots without disclosing exception text."""
        monkeypatch.setattr(Path, 'resolve', Mock(side_effect=error_type('PRIVATE')))
        assert validate(result_config) == ['cannot resolve selected result root']


# !SECTION
