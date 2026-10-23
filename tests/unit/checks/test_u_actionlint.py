# tests/unit/checks/test_u_actionlint.py
# popo
#
# Responsibilities
# - Verify parsed-value normalization preserves scripts and YAML anchors.
#
# Maintainer Notes
# - Keep adaptation independent of tool installation and hosted execution.

"""Unit coverage for the temporary actionlint source view."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from popo.checks.actionlint import _normalize, run
from popo.config.automation import AutomationConfig

# SECTION: FIXTURES


@pytest.fixture(params=['actionlint.yml', 'actionlint.yaml'])
def linter_repository(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """
    Provide both supported implicit config names with duplicate input paths.
    """
    config = tmp_path / '.github' / str(request.param)
    config.parent.mkdir()
    config.write_text('self-hosted-runner: [custom]', encoding='utf-8')
    workflow = tmp_path / 'ci.yml'
    workflow.write_text(
        'jobs: {check: {steps: [{uses: null}, {uses: "docker://alpine:3"}]}}',
        encoding='utf-8',
    )
    return config


# !SECTION


# SECTION: TESTS


class TestActionlintNormalization:
    """Group isolated regression scenarios for actionlint."""

    @pytest.mark.parametrize(
        'source',
        [
            'uses: "$/actions/test"\n',
            'ref: &self $/actions/test\nuses: *self\n',
            'uses: >-\n  $/actions/test\n',
        ],
    )
    def test_normalization_uses_yaml_values(
        self,
        tmp_path: Path,
        source: str,
    ) -> None:
        """
        Normalize quoted, aliased, and block values without rewriting scripts.
        """
        action = tmp_path / 'actions/test/action.yml'
        action.parent.mkdir(parents=True)
        action.write_text('name: Test')
        script = 'run: |\n  uses: $/actions/test\n'
        normalized = _normalize(source + script, AutomationConfig(tmp_path))
        data = yaml.safe_load(normalized)
        assert data['uses'] == './actions/test'
        assert data['run'] == 'uses: $/actions/test\n'
        assert script in normalized


class TestActionlintFailures:
    """Reject invalid invocations before launching any external validator."""

    @pytest.mark.parametrize(
        ('paths', 'command', 'message'),
        [([], 'actionlint', 'no workflows'), (['ci.yml'], '', 'must not be empty')],
    )
    def test_invalid_selection(
        self,
        tmp_path: Path,
        paths: list[str],
        command: str,
        message: str,
    ) -> None:
        """Return precise selection and command errors without execution."""
        (tmp_path / 'ci.yml').write_text('on: push', encoding='utf-8')
        with pytest.raises(ValueError, match=message):
            run(tmp_path, paths, command)


class TestActionlintSourceView:
    """Verify source selection and implicit config handling without a tool."""

    def test_implicit_configuration_and_duplicate_paths(
        self,
        linter_repository: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Copy implicit configuration once and clean the temporary view."""
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, '', ''))
        monkeypatch.setattr(subprocess, 'run', runner)
        assert run(tmp_path, ['ci.yml', 'ci.yml'], 'actionlint') == 0
        mirror = Path(runner.call_args.kwargs['cwd'])
        assert not mirror.exists()
        assert (
            linter_repository.read_text(encoding='utf-8')
            == 'self-hosted-runner: [custom]'
        )


# !SECTION
