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
    """
    Select the sole artifact of the parameterized distribution type.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Active request whose parameter is ``*.whl`` or ``*.tar.gz``.
    artifact_directory : pathlib.Path
        Directory prepared and checked by the session-scoped artifact fixture.

    Returns
    -------
    pathlib.Path
        Matching wheel or sdist, prevalidated by ``artifact_directory``.

    Raises
    ------
    StopIteration
        If an artifact is removed after the directory fixture validates it.
    """
    return next(artifact_directory.glob(request.param))


@pytest.fixture(
    name='artifact_directory',
    scope='session',
)
def artifact_directory_fixture(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    repository_root: Path,
) -> Path:
    """
    Build or select distributions and validate their metadata once per session.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Request used to read the optional --artifact-dir command-line value.
    tmp_path_factory : pytest.TempPathFactory
        Factory allocating an isolated output directory when building
        artifacts.
    repository_root : pathlib.Path
        Project checkout used as the build command's working directory.

    Returns
    -------
    pathlib.Path
        Resolved prebuilt directory, or temporary build output directory, after
        Twine checks all matching wheel and source-distribution paths.

    Raises
    ------
    AssertionError
        If the directory lacks exactly one wheel and one source distribution.
    subprocess.CalledProcessError
        If the build or Twine validation command exits unsuccessfully.
    subprocess.TimeoutExpired
        If building exceeds 300 seconds or Twine checking exceeds 60 seconds.
    OSError
        If directory creation, path resolution, or process startup fails.

    Notes
    -----
    A nonempty --artifact-dir selects existing output relative to the process
    working directory; otherwise python -m build creates both distributions
    with its default isolated build environment. Build dependencies may be
    downloaded. Both paths run Twine through the current interpreter; neither
    publishes artifacts or installs them for smoke testing. Exact artifact
    counts are checked before Twine runs.
    """
    configured = request.config.getoption('--artifact-dir')
    if configured:
        directory = Path(configured).resolve()
    else:
        directory = tmp_path_factory.mktemp('artifacts')
        subprocess.run(
            [sys.executable, '-m', 'build', '--outdir', str(directory)],
            cwd=repository_root,
            check=True,
            timeout=300,
        )
    artifacts = []
    for pattern in ('*.whl', '*.tar.gz'):
        matches = sorted(directory.glob(pattern))
        assert len(matches) == 1, f'Expected one {pattern} in {directory}'
        artifacts.extend(matches)
    subprocess.run(
        [
            sys.executable,
            '-m',
            'twine',
            'check',
            *map(str, artifacts),
        ],
        check=True,
        timeout=60,
    )
    return directory


# !SECTION
