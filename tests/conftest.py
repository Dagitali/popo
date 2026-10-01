"""
:mod:`tests.conftest` module.

Classify tests by architectural layer and register shared artifact fixtures.
"""

from pathlib import Path

import pytest

from tests.support.files import FileWriter

# SECTION: CONSTANTS


TESTS_ROOT = Path(__file__).parent
TEST_LAYERS = frozenset({'unit', 'integration', 'meta', 'e2e'})
pytest_plugins = ('tests.support.artifacts',)


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(
    name='repository_root',
    scope='session',
)
def repository_root_fixture() -> Path:
    """
    Return the repository root for tests of project-level contracts.

    Returns
    -------
    pathlib.Path
        Resolved absolute path containing the repository metadata and source.
    """
    return TESTS_ROOT.parent.resolve()


@pytest.fixture(name='write_file')
def write_file_fixture(
    tmp_path: Path,
) -> FileWriter:
    """
    Provide a writer for files in a test's temporary repository.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory supplied by pytest.

    Returns
    -------
    FileWriter
        Callable accepting a relative path and text, creating parent
        directories, writing UTF-8 content, and returning the resulting Path.
        Existing files are overwritten; filesystem errors propagate when the
        writer is called.

    Notes
    -----
    Callers must supply trusted paths within tmp_path. The helper joins paths
    but does not enforce containment or reject absolute paths and parent
    traversal.
    """

    def write(relative_path: str, content: str) -> Path:
        """
        Create a UTF-8 fixture file and return its path.

        Parameters
        ----------
        relative_path : str
            Path joined to the enclosing test's tmp_path. The caller is
            responsible for supplying a trusted path; containment is not
            enforced.
        content : str
            Text written to the file, replacing any existing contents.

        Returns
        -------
        pathlib.Path
            Written file path after creating its parent directories.

        Raises
        ------
        OSError, UnicodeError
            If directory creation or UTF-8 writing fails.
        """
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    return write


# !SECTION


# SECTION: HOOKS


def pytest_addoption(
    parser: pytest.Parser,
) -> None:
    """
    Register options shared by artifact-oriented test layers.

    Parameters
    ----------
    parser : pytest.Parser
        Parser receiving --artifact-dir for an existing wheel/sdist directory.
        Artifact fixtures interpret the option; registering it does not build
        or inspect distributions.
    """
    parser.addoption(
        '--artifact-dir',
        help='Directory containing a wheel and sdist',
    )


def pytest_collection_modifyitems(
    items: list[pytest.Item],
) -> None:
    """
    Apply each test directory's architectural-layer marker during collection.

    Parameters
    ----------
    items : list[pytest.Item]
        Collected items, marked in place using the first tests-relative path
        component. This hook classifies items; it does not select test paths.

    Raises
    ------
    pytest.UsageError
        If an item lies outside the tests directory or a recognized test layer.
    """
    for item in items:
        try:
            layer = item.path.relative_to(TESTS_ROOT).parts[0]
        except ValueError as error:
            raise pytest.UsageError(
                f'{item.path} is outside the tests directory',
            ) from error
        if layer not in TEST_LAYERS:
            raise pytest.UsageError(f'{item.path} is outside a test layer')
        item.add_marker(getattr(pytest.mark, layer))


# !SECTION
