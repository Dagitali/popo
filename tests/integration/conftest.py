"""Share report-format selection across independent CLI integration cases."""

import pytest

# SECTION: FIXTURES


@pytest.fixture(
    name='cli_format',
    params=[
        pytest.param(None, id='default-text'),
        pytest.param('text', id='explicit-text'),
        pytest.param('json', id='json'),
    ],
)
def cli_format_fixture(request: pytest.FixtureRequest) -> str | None:
    """
    Exercise default and explicit formats with independent consumers.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Selected default-text, explicit-text or JSON parameter.

    Returns
    -------
    str or None
        Explicit format, or ``None`` to exercise the public CLI default.
        Mutable consumer inputs remain function-scoped and isolated.
    """
    return None if request.param is None else str(request.param)


@pytest.fixture(name='format_arguments')
def format_arguments_fixture(
    cli_format: str | None,
) -> tuple[str, ...]:
    """
    Build only the selected format switches, leaving command choice local.

    Parameters
    ----------
    cli_format : str or None
        Default text, explicit text or JSON selected by the shared fixture.

    Returns
    -------
    tuple[str, ...]
        Immutable argument suffix; empty when testing the default format.
    """
    return () if cli_format is None else ('--format', cli_format)
