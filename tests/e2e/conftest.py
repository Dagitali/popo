"""
:mod:`tests.e2e.conftest` module.

Install each distribution for isolated consumer execution tests.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.installation import Installation

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
    Install each selected artifact once per module in its own environment.

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
