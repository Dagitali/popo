"""
:mod:`tests.e2e.test_distribution_installation` module.

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
    """Run an installed CLI or module outside the checkout without import overrides."""

    python: Path
    command: Path
    directory: Path
    environment: dict[str, str]

    def run(
        self,
        *arguments: str,
        module: bool = False,
    ) -> subprocess.CompletedProcess[str]:
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
    """Install each built distribution once, isolated from the editable checkout."""
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
    """Exercise every artifact through independent public CLI scenarios."""

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
        readme = tmp_path / 'README.md'
        readme.write_text(content, encoding='utf-8')
        result = installation.run('check-docs', '--root', str(tmp_path))
        assert result.returncode == status, result.stderr
        assert message in result.stdout
        assert not result.stderr
        assert readme.read_text(encoding='utf-8') == content


# !SECTION
