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
    """Return the checkout root for project-level tests."""
    return TESTS_ROOT.parent.resolve()


@pytest.fixture(name='write_file')
def write_file_fixture(
    tmp_path: Path,
) -> FileWriter:
    """Write UTF-8 fixture content, creating parents inside a temporary repository."""

    def write(relative_path: str, content: str) -> Path:
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
    """Add command-line options for pytest."""
    parser.addoption(
        '--artifact-dir',
        help='Directory containing a wheel and sdist',
    )


def pytest_collection_modifyitems(
    items: list[pytest.Item],
) -> None:
    """Assign layer markers and reject tests outside the recognized layout."""
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
