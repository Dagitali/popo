"""
:mod:`popo.config.test_results` module.

Load explicit result adapters and consumer-owned acceptance thresholds.
"""

from dataclasses import dataclass
from pathlib import Path

from ._common import ConfigurationError, read_patterns, read_popo, require_table
from .source_checks import SourceCheckConfig

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class TestResultsConfig:
    """
    Store result selection, a named adapter and validated count thresholds.

    Attributes
    ----------
    inputs : SourceCheckConfig
        Root-confined include/exclude discovery; settings are unused.
    adapter : str
        Explicit report format; initially only xcode-summary is supported.
    thresholds : dict[str, int]
        Nonnegative minimum/maximum acceptance counts; never mutated.
    """

    inputs: SourceCheckConfig
    adapter: str
    thresholds: dict[str, int]


# !SECTION


# SECTION: CONSTANTS


THRESHOLDS = {
    'minimum-tests': 1,
    'minimum-passed': 1,
    'maximum-failed': 0,
    'maximum-skipped': 0,
    'maximum-warnings': 0,
}


# !SECTION


# SECTION: FUNCTIONS


def load_test_results_config(
    root: Path,
) -> TestResultsConfig:
    """
    Load a strictly typed, opt-in result acceptance policy.

    Parameters
    ----------
    root : pathlib.Path
        Repository containing standalone or embedded policy.

    Returns
    -------
    TestResultsConfig
        Valid adapter, input patterns and nonnegative integer thresholds.

    Raises
    ------
    ConfigurationError
        Policy is absent, unknown, malformed or contains unsafe patterns.
    OSError, UnicodeError
        Consumer configuration cannot be read or decoded.
    """
    table = require_table(read_popo(root).get('test-results'), name='test-results')
    if table.keys() - THRESHOLDS.keys() - {'adapter', 'include', 'exclude'}:
        raise ConfigurationError('unknown test-results setting')
    if table.get('adapter') != 'xcode-summary':
        raise ConfigurationError('test-results.adapter must be xcode-summary')
    include = read_patterns(table.get('include', []), 'test-results.include')
    exclude = read_patterns(
        table.get('exclude', []),
        'test-results.exclude',
        required=False,
    )
    thresholds = {}
    for key, default in THRESHOLDS.items():
        value = table.get(key, default)
        if type(value) is not int or value < 0:
            raise ConfigurationError(
                f'test-results.{key} requires a nonnegative integer',
            )
        thresholds[key] = value
    return TestResultsConfig(
        SourceCheckConfig(root.resolve(), 'test-results', include, exclude, {}),
        'xcode-summary',
        thresholds,
    )


# !SECTION
