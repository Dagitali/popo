"""
:mod:`tests.integration.conftest` module.

Share report-format and check-selection fixtures across CLI integration cases.
"""

from collections.abc import Callable
from pathlib import Path

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
def cli_format_fixture(
    request: pytest.FixtureRequest,
) -> str | None:
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


@pytest.fixture(
    name='select_check',
    params=['individual', 'explicit', 'profile'],
)
def select_check_fixture(
    request: pytest.FixtureRequest,
) -> Callable[[Path, str], tuple[str, ...]]:
    """
    Select one native check through independent dispatch modes.

    The caller supplies a consumer root with popo.toml to the factory.
    Aggregate modes prepend an explicit check list or a selected profile and
    return CLI arguments. Individual mode preserves the existing policy.
    Consumers and selections remain function-scoped; no command executes here.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest request carrying the selected fixture parameter.

    Returns
    -------
    Callable[[Path, str], tuple[str, ...]]
        Callable returning CLI arguments for the selected execution mode.
    """

    def select(
        root: Path,
        command: str,
    ) -> tuple[str, ...]:
        """
        Select individual, aggregate or profiled execution for the consumer.

        Parameters
        ----------
        root : Path
            Consumer repository root used to resolve and label input paths.
        command : str
            Command selected for invocation in the scenario.

        Returns
        -------
        tuple[str, ...]
            CLI arguments after writing aggregate/profile selection when
            needed.
        """
        if request.param == 'individual':
            return (command,)
        profile = request.param == 'profile'
        prefix = '[profiles.selected]\n' if profile else ''
        path = root / 'popo.toml'
        path.write_text(
            f'{prefix}checks=["{command}"]\n' + path.read_text(encoding='utf-8'),
            encoding='utf-8',
        )
        return ('check-all', '--profile', 'selected') if profile else ('check-all',)

    return select
