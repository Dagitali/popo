"""
:mod:`tests.support.source_checks` module.

Share independent Python and Swift source-check cases across unit suites.
"""

from collections.abc import Callable

import pytest

from popo.checks import python_source, swift_source
from popo.config.source_checks import SourceCheckConfig

# SECTION: TYPE ALIASES


type SourceCase = tuple[str, str, Callable[[SourceCheckConfig], list[str]]]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(
    name='source_case',
    params=['python', 'swift'],
)
def source_case_fixture(
    request: pytest.FixtureRequest,
) -> SourceCase:
    """
    Select independent language cases sharing discovery and limit rules.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest request carrying the selected fixture parameter.

    Returns
    -------
    SourceCase
        Native source policy/parser helpers for the selected language.
    """
    return (
        ('python-source', 'sample.py', python_source.validate)
        if request.param == 'python'
        else ('swift-source', 'sample.swift', swift_source.validate)
    )


# !SECTION
