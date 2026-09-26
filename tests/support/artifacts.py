"""
:mod:`tests.support.artifacts` module.

Build distributions once, or select the artifacts provided by CI.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# SECTION: FIXTURES


@pytest.fixture(
    name='artifact',
    scope='module',
    params=['*.whl', '*.tar.gz'],
    ids=['wheel', 'sdist'],
)
def artifact_fixture(
    request: pytest.FixtureRequest,
    artifact_directory: Path,
) -> Path:
    paths = list(artifact_directory.glob(request.param))
    assert len(paths) == 1, f'Expected one {request.param} in {artifact_directory}'
    return paths[0]


@pytest.fixture(
    name='artifact_directory',
    scope='session',
)
def artifact_directory_fixture(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    repository_root: Path,
) -> Path:
    configured = request.config.getoption('--artifact-dir')
    if configured:
        directory = Path(configured).resolve()
    else:
        directory = tmp_path_factory.mktemp('artifacts')
        subprocess.run(
            [sys.executable, '-m', 'build', '--out-dir', str(directory)],
            cwd=repository_root,
            check=True,
            timeout=300,
        )
    subprocess.run(
        [
            sys.executable,
            '-m',
            'twine',
            'check',
            *map(str, sorted(directory.glob('*.whl'))),
            *map(str, sorted(directory.glob('*.tar.gz'))),
        ],
        check=True,
        timeout=60,
    )
    return directory


# !SECTION
