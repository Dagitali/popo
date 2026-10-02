"""
:mod:`tests.unit.test_u_makefile` module.

Test Make target discovery, command overrides, and preserved validation
boundaries.
"""

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

# SECTION: TYPE ALIASES


type MakeRunner = Callable[..., subprocess.CompletedProcess[str]]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(name='make')
def make_fixture(
    repository_root: Path,
    tmp_path: Path,
) -> MakeRunner:
    """
    Provide a bounded Make runner using a temporary copy of the checkout
    Makefile.

    Parameters
    ----------
    repository_root : pathlib.Path
        Checkout containing the canonical Makefile to copy.
    tmp_path : pathlib.Path
        Per-test directory containing the temporary checkout.

    Returns
    -------
    MakeRunner
        Callable accepting Make arguments and returning captured text results.

    Raises
    ------
    OSError
        If directory creation or copying the Makefile fails.

    Notes
    -----
    Skip the test if Make is unavailable. Remove inherited Make control
    variables and configurable Makefile variables from each subprocess
    environment. The returned runner permits nonzero exits for assertions and
    bounds each call to 60 seconds. Scenario commands may create files and
    environments only in their fixtures.
    """
    executable = shutil.which('make')
    if executable is None:
        pytest.skip('Make is not available')
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    shutil.copyfile(repository_root / 'Makefile', checkout / 'Makefile')
    override_names = {
        'MAKEFLAGS',
        'MFLAGS',
        'MAKELEVEL',
        'MAKEOVERRIDES',
        'MAKEFILES',
        'VIRTUAL_ENV',
    } | set(
        re.findall(
            r'^([A-Z][A-Z0-9_]*)\s*\?=',
            (checkout / 'Makefile').read_text(encoding='utf-8'),
            re.MULTILINE,
        ),
    )

    def run(
        *args: str,
    ) -> subprocess.CompletedProcess[str]:
        """
        Invoke Make in the copied checkout with a controlled environment.

        Parameters
        ----------
        *args : str
            Targets, options, and variable assignments passed to Make.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Captured stdout/stderr and exit status, including unsuccessful
            commands.

        Raises
        ------
        subprocess.TimeoutExpired
            If Make exceeds 60 seconds.
        OSError, UnicodeError
            If process startup or captured-output decoding fails.

        Notes
        -----
        Use --no-print-directory and the enclosing fixture's copied checkout
        and sanitized environment. Nonzero exits are returned rather than
        raised.
        """
        return subprocess.run(
            [executable, '--no-print-directory', *args],
            cwd=checkout,
            env={
                key: value
                for key, value in os.environ.items()
                if key not in override_names
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    return run


# !SECTION


# SECTION: TESTS


class TestMakefile:
    """
    Verify Make command contracts and non-destructive environment management.

    Notes
    -----
    Run Make against a copied Makefile with inherited overrides removed. Most
    command-contract scenarios use dry runs; environment-management scenarios
    exercise temporary directories and verify existing state is preserved.
    """

    def test_checks_use_checkout_source_path(
        self,
        make: MakeRunner,
        tmp_path: Path,
    ) -> None:
        """
        Verify Make supplies the checkout source path to test subprocesses.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
        result = make('-s', 'test', 'PYTEST=printf \'%s\' "$$PYTHONPATH"')
        assert result.returncode == 0, result.stderr
        assert result.stdout.split(os.pathsep)[0] == str(tmp_path / 'checkout/src')

    def test_inherited_overrides_do_not_leak(
        self,
        make: MakeRunner,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Keep nested Make assertions independent of caller overrides.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        monkeypatch : pytest.MonkeyPatch
            Restore environment, attributes, and working directory.
        """
        monkeypatch.setenv('TEST_ARGS', '--must-not-leak')
        monkeypatch.setenv('PYTHON', 'must-not-run')
        result = make('-n', 'test')
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == 'python3 -m pytest'

    @pytest.mark.parametrize(
        ('managed', 'overrides', 'expected'),
        [
            (False, (), 'python3'),
            (True, (), '".venv/bin/python"'),
            (True, ('VIRTUAL_ENV=active-env',), 'python3'),
            (True, ('PYTHON=custom-python',), 'custom-python'),
            (True, ('VENV_DIR=custom env',), '"custom env/bin/python"'),
            (True, ('OS=Windows_NT',), '".venv/Scripts/python.exe"'),
        ],
        ids=['path', 'managed', 'active', 'explicit', 'spaces', 'windows'],
    )
    def test_interpreter_selection(
        self,
        make: MakeRunner,
        tmp_path: Path,
        managed: bool,
        overrides: tuple[str, ...],
        expected: str,
    ) -> None:
        """
        Verify Make selects managed, active, or explicitly overridden Python.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        managed : bool
            Whether the temporary checkout includes a managed interpreter stub.
        overrides : tuple[str, ...]
            Make variable assignments controlling interpreter selection.
        expected : str
            Exact interpreter command expected in Make dry-run output.
        """
        if managed:
            interpreter = tmp_path / 'checkout' / expected.strip('"')
            if expected in {'python3', 'custom-python'}:
                interpreter = tmp_path / 'checkout/.venv/bin/python'
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text('', encoding='utf-8')
            interpreter.chmod(0o755)
        result = make('-n', 'test', *overrides)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == f'{expected} -m pytest'

    @pytest.mark.parametrize(
        ('alias', 'target'),
        [('fmt', 'format'), ('build', 'dist'), ('check-pre-push', 'check')],
    )
    def test_aliases_preserve_commands(
        self,
        make: MakeRunner,
        alias: str,
        target: str,
    ) -> None:
        """
        Verify aliases and canonical Make targets emit identical commands.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        alias : str
            Contributor convenience target compared with its canonical target.
        target : str
            Canonical Make target whose dry-run commands must match the alias.
        """
        aliased = make('-n', alias)
        direct = make('-n', target)
        assert aliased.returncode == direct.returncode == 0
        assert aliased.stdout == direct.stdout

    def test_default_gate_preserves_existing_checks(
        self,
        make: MakeRunner,
    ) -> None:
        """
        Verify default Make checks include source gates without building or
        installing.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
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
        make: MakeRunner,
        target: str,
        prefix: str,
    ) -> None:
        """
        Verify independent overrides for artifact test paths and arguments.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        target : str
            Artifact test target whose path and arguments are overridden.
        prefix : str
            Make variable prefix selecting distribution or installation test
            overrides.
        """
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
        make: MakeRunner,
    ) -> None:
        """
        Verify Make help lists contributor targets without executing the
        quality gate.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
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
        make: MakeRunner,
    ) -> None:
        """
        Verify distribution build and metadata-check commands accept overrides.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
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
        self,
        make: MakeRunner,
        target: str,
        command: str,
    ) -> None:
        """
        Verify policy targets honor Python and tooling-module overrides.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        target : str
            Make policy target to inspect without executing its checker.
        command : str
            Expected Popo subcommand emitted by the Make policy target.
        """
        result = make(
            '-n',
            target,
            'PYTHON=custom-python',
            'PROJECT_TOOLS_MODULE=tooling',
        )
        assert result.returncode == 0, result.stderr
        assert f'custom-python -m tooling {command}' in result.stdout

    def test_release_changelog_requires_explicit_version(
        self,
        make: MakeRunner,
    ) -> None:
        """
        Verify release-changelog fails before invocation when its version is
        absent.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
        result = make('release-changelog', 'RELEASE_VERSION=', 'PYTHON=must-not-run')
        assert result.returncode != 0
        assert 'RELEASE_VERSION is required' in result.stderr

    def test_release_validation_reuses_configured_artifacts(
        self,
        make: MakeRunner,
    ) -> None:
        """
        Verify release checks share the configured artifact directory.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
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
        make: MakeRunner,
        target: str,
    ) -> None:
        """
        Verify setup uses managed Python and selects development extras.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        target : str
            Installation target selecting runtime-only or development
            dependencies.
        """
        result = make('-n', target, 'VENV_DIR=custom env', 'PYTHON=must-not-install')
        assert result.returncode == 0, result.stderr
        assert 'custom env/' in result.stdout
        assert '-m pip install --disable-pip-version-check -e' in result.stdout
        assert ('[dev]' in result.stdout) is (target != 'install')
        assert 'must-not-install' not in result.stdout

    def test_standalone_distribution_tests_keep_temporary_builds(
        self,
        make: MakeRunner,
    ) -> None:
        """
        Verify standalone artifact targets leave build-on-demand selection to
        fixtures.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
        result = make('-n', 'test-distribution', 'test-installation', 'TEST_ARGS=-x')
        assert result.returncode == 0, result.stderr
        assert 'pytest -x "tests/meta/test_m_package_artifacts.py"' in result.stdout
        assert (
            'pytest -x "tests/e2e/test_e_distribution_installation.py"' in result.stdout
        )
        assert '--artifact-dir' not in result.stdout
        assert ' -m build' not in result.stdout

    def test_unsupported_bootstrap_is_rejected_before_creation(
        self,
        make: MakeRunner,
        tmp_path: Path,
    ) -> None:
        """
        Verify unsupported bootstrap Python fails before creating an
        environment.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
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
        make: MakeRunner,
        tmp_path: Path,
    ) -> None:
        """
        Verify managed environment creation and compatible reuse preserve its
        metadata.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
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
        make: MakeRunner,
        tmp_path: Path,
    ) -> None:
        """
        Verify an incompatible existing environment fails without replacement.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
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
        make: MakeRunner,
        tmp_path: Path,
    ) -> None:
        """
        Verify an unusable existing environment directory is preserved on
        failure.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
        marker = tmp_path / 'keep.txt'
        marker.write_text('user data', encoding='utf-8')
        result = make('venv', f'PY={sys.executable}', f'VENV_DIR={tmp_path}')
        assert result.returncode != 0
        assert 'not a usable virtual environment' in result.stderr
        assert marker.read_text() == 'user data'

    def test_windows_environment_paths(
        self,
        make: MakeRunner,
    ) -> None:
        """
        Verify Windows setup commands select Scripts and python.exe paths.

        Parameters
        ----------
        make : MakeRunner
            Runner for the isolated copied Makefile.
        """
        result = make('show-venv', 'OS=Windows_NT', 'VENV_DIR=custom env')
        assert result.returncode == 0, result.stderr
        assert 'custom env/Scripts/python.exe' in result.stdout


# !SECTION
