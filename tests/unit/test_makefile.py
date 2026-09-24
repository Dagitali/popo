"""
:mod:`tests.unit.test_makefile` module.

Test Make target discovery, command overrides, and preserved validation boundaries.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

# SECTION: TYPE ALIASES


type Make = Callable[..., subprocess.CompletedProcess[str]]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(name='make')
def make_fixture(
    repository_root: Path,
    tmp_path: Path,
) -> Make:
    """Run Make with bounded execution and no inherited parent-Make overrides."""
    executable = shutil.which('make')
    if executable is None:
        pytest.skip('Make is not available')
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    shutil.copyfile(repository_root / 'Makefile', checkout / 'Makefile')
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {'MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'MAKEOVERRIDES', 'MAKEFILES'}
    }

    def run(
        *args: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [executable, '--no-print-directory', *args],
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    return run


# !SECTION


# SECTION: TESTS


class TestMakefile:
    """Verify Make command contracts and non-destructive environment management."""

    @pytest.mark.parametrize(
        ('alias', 'target'),
        [('fmt', 'format'), ('build', 'dist'), ('check-pre-push', 'check')],
    )
    def test_aliases_preserve_commands(
        self, make: Make, alias: str, target: str
    ) -> None:
        aliased = make('-n', alias)
        direct = make('-n', target)
        assert aliased.returncode == direct.returncode == 0
        assert aliased.stdout == direct.stdout

    def test_default_gate_preserves_existing_checks(
        self,
        make: Make,
    ) -> None:
        result = make('-n', 'PYTHON=custom-python')
        explicit = make('-n', 'check', 'PYTHON=custom-python')
        assert result.returncode == explicit.returncode == 0
        assert result.stdout == explicit.stdout
        for command in ('ruff check .', 'ruff format --check .', 'mypy', 'pytest'):
            assert f'custom-python -m {command}' in result.stdout
        assert 'custom-python -m popo check-all' in result.stdout
        assert ' -m build' not in result.stdout
        assert 'pip install' not in result.stdout

    @pytest.mark.parametrize(
        ('target', 'prefix'),
        [('test-distribution', 'DISTRIBUTION'), ('test-installation', 'INSTALLATION')],
    )
    def test_distribution_paths_and_arguments_are_overridable(
        self,
        make: Make,
        target: str,
        prefix: str,
    ) -> None:
        selected = make(
            '-n',
            target,
            f'{prefix}_TEST_PATH=custom tests/test_check.py',
            'TEST_ARGS=-x',
        )
        assert selected.returncode == 0, selected.stderr
        assert 'pytest -x "custom tests/test_check.py"' in selected.stdout
        replaced = make('-n', target, f'{prefix}_TEST_ARGS=-q alternate.py')
        assert replaced.returncode == 0, replaced.stderr
        assert 'pytest -q alternate.py' in replaced.stdout

    def test_help_lists_public_targets_without_running_checks(
        self,
        make: Make,
    ) -> None:
        result = make('help')
        assert result.returncode == 0, result.stderr
        targets = (
            'check',
            'format-check',
            'docs-markdown',
            'check-release',
            'test-full',
        )
        for target in targets:
            assert target in result.stdout
        assert ' -m pytest' not in result.stdout

    def test_packaging_commands_are_overridable(
        self,
        make: Make,
    ) -> None:
        result = make(
            '-n',
            'dist',
            'DIST_BUILD_COMMAND=build-tool',
            'DIST_CHECK_COMMAND=validate-tool',
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == ['build-tool', 'validate-tool']

    @pytest.mark.parametrize(
        ('target', 'command'),
        [
            ('python-policy', 'check-python-policy'),
            ('dependency-policy', 'check-dependency-boundaries'),
            ('github-actions-pins', 'check-github-actions-pins'),
            ('docs-markdown', 'check-docs'),
            ('self-check', 'check-all'),
        ],
    )
    def test_policy_targets_use_overridable_commands(
        self, make: Make, target: str, command: str
    ) -> None:
        result = make(
            '-n', target, 'PYTHON=custom-python', 'PROJECT_TOOLS_MODULE=tooling'
        )
        assert result.returncode == 0, result.stderr
        assert f'custom-python -m tooling {command}' in result.stdout

    def test_release_changelog_requires_explicit_version(
        self,
        make: Make,
    ) -> None:
        result = make('release-changelog', 'RELEASE_VERSION=', 'PYTHON=must-not-run')
        assert result.returncode != 0
        assert 'RELEASE_VERSION is required' in result.stderr

    def test_release_validation_reuses_configured_artifacts(
        self,
        make: Make,
    ) -> None:
        result = make('-n', 'check-release', 'PYTHON_DIST_DIR=release artifacts')
        assert result.returncode == 0, result.stderr
        assert '--outdir "release artifacts"' in result.stdout
        assert 'check "release artifacts"/*' in result.stdout
        assert '--artifact-dir "release artifacts"' in result.stdout

    @pytest.mark.parametrize(
        'target',
        ['install', 'dev', 'setup'],
    )
    def test_setup_targets_install_only_in_managed_environment(
        self,
        make: Make,
        target: str,
    ) -> None:
        result = make('-n', target, 'VENV_DIR=custom env', 'PYTHON=must-not-install')
        assert result.returncode == 0, result.stderr
        assert 'custom env/' in result.stdout
        assert '-m pip install --disable-pip-version-check -e' in result.stdout
        assert ('[dev]' in result.stdout) is (target != 'install')
        assert 'must-not-install' not in result.stdout

    def test_standalone_distribution_tests_keep_temporary_builds(
        self, make: Make
    ) -> None:
        result = make('-n', 'test-distribution', 'test-installation', 'TEST_ARGS=-x')
        assert result.returncode == 0, result.stderr
        assert 'pytest -x "tests/meta/test_package_artifacts.py"' in result.stdout
        assert (
            'pytest -x "tests/e2e/test_distribution_installation.py"' in result.stdout
        )
        assert '--artifact-dir' not in result.stdout
        assert ' -m build' not in result.stdout

    def test_unsupported_bootstrap_is_rejected_before_creation(
        self, make: Make, tmp_path: Path
    ) -> None:
        environment = tmp_path / 'not-created'
        result = make(
            'venv',
            f'PY={sys.executable}',
            f'VENV_DIR={environment}',
            'MINIMUM_PYTHON_VERSION=99.0',
            'MAXIMUM_PYTHON_VERSION=100.0',
        )
        assert result.returncode != 0
        assert 'is required' in result.stderr
        assert not environment.exists()

    def test_venv_creation_and_safe_reuse(
        self,
        make: Make,
        tmp_path: Path,
    ) -> None:
        environment = tmp_path / 'managed env'
        args = ('venv', f'PY={sys.executable}', f'VENV_DIR={environment}')
        first = make(*args)
        assert first.returncode == 0, first.stderr
        config = environment / 'pyvenv.cfg'
        before = config.read_bytes()
        second = make(*args)
        assert second.returncode == 0, second.stderr
        assert 'Using existing environment' in second.stdout
        assert config.read_bytes() == before

    @pytest.mark.skipif(
        sys.platform == 'win32',
        reason='Uses a POSIX interpreter stub',
    )
    def test_venv_preserves_mismatched_environment(
        self,
        make: Make,
        tmp_path: Path,
    ) -> None:
        environment = tmp_path / 'mismatched'
        executable = environment / 'bin/python'
        executable.parent.mkdir(parents=True)
        (environment / 'pyvenv.cfg').write_text('test fixture', encoding='utf-8')
        executable.write_text('#!/bin/sh\nprintf "0.0\\n"\n', encoding='utf-8')
        executable.chmod(0o755)
        result = make('venv', f'PY={sys.executable}', f'VENV_DIR={environment}')
        assert result.returncode != 0
        assert 'nothing was replaced' in result.stderr
        assert (environment / 'pyvenv.cfg').read_text() == 'test fixture'

    def test_venv_preserves_unusable_existing_directory(
        self,
        make: Make,
        tmp_path: Path,
    ) -> None:
        marker = tmp_path / 'keep.txt'
        marker.write_text('user data', encoding='utf-8')
        result = make('venv', f'PY={sys.executable}', f'VENV_DIR={tmp_path}')
        assert result.returncode != 0
        assert 'not a usable virtual environment' in result.stderr
        assert marker.read_text() == 'user data'

    def test_windows_environment_paths(
        self,
        make: Make,
    ) -> None:
        result = make('show-venv', 'OS=Windows_NT', 'VENV_DIR=custom env')
        assert result.returncode == 0, result.stderr
        assert 'custom env/Scripts/python.exe' in result.stdout


# !SECTION
