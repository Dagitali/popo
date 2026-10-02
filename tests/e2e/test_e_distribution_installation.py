"""
:mod:`tests.e2e.test_e_distribution_installation` module.

Exercise installed commands outside the checkout in clean environments.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from packaging.version import Version

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class Installation:
    """
    Represent an isolated artifact installation for public CLI tests.

    Attributes
    ----------
    python : pathlib.Path
        Interpreter in the temporary installation's virtual environment.
    command : pathlib.Path
        Installed popo console-script executable.
    directory : pathlib.Path
        Subprocess working directory outside the source checkout.
    environment : dict[str, str]
        Environment passed to subprocesses, with PYTHONPATH/PYTHONHOME removed
        by the installation fixture.

    Notes
    -----
    The dataclass is frozen and slotted; it does not create the environment or
    validate paths. Freezing prevents attribute rebinding but does not make the
    environment dictionary immutable.
    """

    python: Path
    command: Path
    directory: Path
    environment: dict[str, str]

    def run(
        self,
        *arguments: str,
        module: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run the installed console script or module and capture its result.

        Parameters
        ----------
        *arguments : str
            CLI arguments appended to the chosen entry point.
        module : bool, optional
            Use the installation's Python interpreter with -m popo when
            ``True``; otherwise invoke its console script. Defaults to
            ``False``.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Exit status and captured text output, including unsuccessful CLI
            exits.

        Raises
        ------
        subprocess.TimeoutExpired
            If the process exceeds 30 seconds.
        OSError, UnicodeError
            If startup fails or captured output cannot be decoded.

        Notes
        -----
        Use :attr:`Installation.directory` and
        :attr:`Installation.environment`. Nonzero statuses are returned for
        scenario assertions instead of raising
        :exc:`~subprocess.CalledProcessError`.
        """
        prefix = [str(self.python), '-m', 'popo'] if module else [str(self.command)]
        return subprocess.run(
            [*prefix, *arguments],
            cwd=self.directory,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(
    name='installation',
    scope='module',
)
def installation_fixture(
    artifact: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Installation:
    """
    Install a built artifact once per module in a separate virtual environment.

    Parameters
    ----------
    artifact : pathlib.Path
        Wheel or sdist selected by the shared parameterized artifact fixture.
    tmp_path_factory : pytest.TempPathFactory
        Factory creating the temporary directory for this installation.

    Returns
    -------
    Installation
        Interpreter, console script, working directory, and sanitized
        environment after virtual-environment creation, pip installation, and
        pip check.

    Raises
    ------
    subprocess.CalledProcessError
        If environment creation, artifact installation, or dependency checking
        exits unsuccessfully.
    subprocess.TimeoutExpired
        If creation/checking exceeds 60 seconds or installation exceeds 300.
    OSError
        If directory creation or subprocess startup fails.

    Notes
    -----
    Remove PYTHONPATH and PYTHONHOME from the inherited environment to avoid
    source-import overrides. :mod:`pip` may download runtime or build
    requirements. All installed-CLI scenarios in the module share this fixture
    for each artifact; their consumer repositories remain independent.
    """
    directory = tmp_path_factory.mktemp('installed')
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {'PYTHONPATH', 'PYTHONHOME'}
    }
    venv = directory / 'venv'
    bin_dir = venv / ('Scripts' if os.name == 'nt' else 'bin')
    python = bin_dir / ('python.exe' if os.name == 'nt' else 'python')
    for command, timeout in (
        ([sys.executable, '-m', 'venv', str(venv)], 60),
        ([str(python), '-m', 'pip', 'install', str(artifact)], 300),
        ([str(python), '-m', 'pip', 'check'], 60),
    ):
        subprocess.run(
            command,
            cwd=directory,
            env=environment,
            check=True,
            timeout=timeout,
        )
    return Installation(
        python,
        bin_dir / ('popo.exe' if os.name == 'nt' else 'popo'),
        directory,
        environment,
    )


# !SECTION


# SECTION: TESTS


class TestInstalledCLI:
    """
    Exercise every artifact through independent public CLI scenarios.

    Notes
    -----
    Each artifact has a module-scoped installation, while consumer inputs use
    per-test temporary directories. Exercise both console and module entry
    points, exit statuses, output channels, and read-only checker behavior.
    """

    @pytest.mark.parametrize(
        'module',
        [False, True],
    )
    @pytest.mark.parametrize(
        ('reference', 'status'),
        [('upstream/action@main', 1), ('upstream/action@' + 'a' * 40, 0)],
        ids=['mutable', 'pinned'],
    )
    def test_automation_contracts(
        self,
        installation: Installation,
        tmp_path: Path,
        module: bool,
        reference: str,
        status: int,
    ) -> None:
        """
        Verify installed automation checking reports pins without rewriting
        inputs.

        Parameters
        ----------
        installation : Installation
            Installed artifact isolated from checkout imports.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        reference : str
            Remote reference selected for the pin-validation scenario.
        status : int
            Expected installed CLI exit status.
        module : bool
            Whether to invoke python -m popo rather than the console-script
            entry point.
        """
        (tmp_path / 'pyproject.toml').write_text(
            '[tool.popo.automation]\nworkflow-globs = ["ci.yml"]',
            encoding='utf-8',
        )
        workflow = tmp_path / 'ci.yml'
        source = f'jobs: {{test: {{steps: [{{uses: {reference}}}]}}}}'
        workflow.write_text(source, encoding='utf-8')
        result = installation.run(
            'check-automation-contracts',
            '--root',
            str(tmp_path),
            module=module,
        )
        assert result.returncode == status, result.stdout + result.stderr
        assert not result.stderr
        assert workflow.read_text(encoding='utf-8') == source

    @pytest.mark.parametrize(
        'argument',
        ['--help', '--version'],
    )
    @pytest.mark.parametrize(
        'module',
        [False, True],
        ids=['console', 'module'],
    )
    def test_information_commands(
        self,
        installation: Installation,
        argument: str,
        module: bool,
    ) -> None:
        """
        Verify help and version output through console and module entry points.

        Parameters
        ----------
        installation : Installation
            Installed artifact isolated from checkout imports.
        argument : str
            Information option to exercise, either --help or --version.
        module : bool
            Whether to invoke python -m popo rather than the console-script
            entry point.
        """
        result = installation.run(argument, module=module)
        assert result.returncode == 0, result.stderr
        if argument == '--help':
            assert 'check-all' in result.stdout
        else:
            assert Version(result.stdout.split()[-1]).release
        assert not result.stderr

    @pytest.mark.parametrize(
        ('content', 'status', 'message'),
        [
            ('# Consumer\n', 0, 'PASS:'),
            ('[missing](missing.md)\n', 1, 'FAIL:'),
        ],
        ids=['valid-project', 'broken-link'],
    )
    def test_checks_consumer(
        self,
        installation: Installation,
        tmp_path: Path,
        content: str,
        status: int,
        message: str,
    ) -> None:
        """
        Verify installed Markdown checks report status and preserve consumer
        files.

        Parameters
        ----------
        installation : Installation
            Installed artifact isolated from checkout imports.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        status : int
            Expected process or CLI exit status.
        message : str
            Expected diagnostic substring; an empty string selects a successful
            case.
        """
        readme = tmp_path / 'README.md'
        readme.write_text(content, encoding='utf-8')
        result = installation.run('check-docs', '--root', str(tmp_path))
        assert result.returncode == status, result.stderr
        assert message in result.stdout
        assert not result.stderr
        assert readme.read_text(encoding='utf-8') == content


# !SECTION
