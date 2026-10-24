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
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(
    name='linter_repository',
    params=['actionlint.yml', 'actionlint.yaml'],
)
def linter_repository_fixture(
    request: pytest.FixtureRequest,
    write_file: FileWriter,
) -> Path:
    """
    Provide both supported implicit config names with duplicate input paths.
    """
    config = write_file(f'.github/{request.param}', 'self-hosted-runner: [custom]')
    write_file(
        'ci.yml',
        'jobs: {check: {steps: [{uses: null}, {uses: "docker://alpine:3"}]}}',
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
        write_file: FileWriter,
        source: str,
    ) -> None:
        """
        Normalize quoted, aliased, and block values without rewriting scripts.
        """
        write_file('actions/test/action.yml', 'name: Test')
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
        write_file: FileWriter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Return precise selection and command errors without execution."""
        write_file('ci.yml', 'on: push')
        runner = Mock(
            side_effect=AssertionError('Invalid input must not launch a tool'),
        )
        monkeypatch.setattr(subprocess, 'run', runner)
        with pytest.raises(ValueError, match=message):
            run(tmp_path, paths, command)
        runner.assert_not_called()


class TestActionlintSourceView:
    """Verify source selection and implicit config handling without a tool."""

    @pytest.mark.parametrize('status', [0, 17], ids=['success', 'tool-failure'])
    def test_implicit_configuration_and_duplicate_paths(
        self,
        linter_repository: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        status: int,
    ) -> None:
        """Copy implicit configuration once and clean the temporary view."""
        before = snapshot_files(tmp_path)
        # Unrelated consumer files must never enter the compatibility view.
        (tmp_path / 'private.txt').write_text('consumer data', encoding='utf-8')

        def inspect_view(
            arguments: list[str],
            **options: object,
        ) -> subprocess.CompletedProcess[str]:
            """Inspect the live mirror before returning the tool's status."""
            mirror = Path(str(options['cwd']))
            assert mirror != tmp_path
            assert snapshot_files(mirror) == before
            assert (mirror / linter_repository.relative_to(tmp_path)).is_file()
            assert arguments == ['actionlint', 'ci.yml', 'ci.yml']
            return subprocess.CompletedProcess(arguments, status, '', '')

        original = snapshot_files(tmp_path)
        runner = Mock(side_effect=inspect_view)
        monkeypatch.setattr(subprocess, 'run', runner)
        assert run(tmp_path, ['ci.yml', 'ci.yml'], 'actionlint') == status
        runner.assert_called_once()
        assert not Path(runner.call_args.kwargs['cwd']).exists()
        assert snapshot_files(tmp_path) == original

    def test_launch_failure_cleans_view(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Clean the temporary view when process startup raises an error."""
        before = snapshot_files(tmp_path)
        error = OSError('fixture launch failure')
        runner = Mock(side_effect=error)
        monkeypatch.setattr(subprocess, 'run', runner)
        with pytest.raises(OSError, match='fixture launch failure') as raised:
            run(tmp_path, ['ci.yml'], 'actionlint')
        assert raised.value is error
        runner.assert_called_once()
        assert not Path(runner.call_args.kwargs['cwd']).exists()
        assert snapshot_files(tmp_path) == before


# !SECTION
