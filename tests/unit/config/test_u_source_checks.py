"""
:mod:`tests.unit.config.test_u_source_checks` module.

Verify shared selection validation across source and log policy domains.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from popo.config._common import ConfigurationError
from popo.config.source_checks import load_source_check
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='write_policy')
def write_policy_fixture(
    domain: str,
    write_file: FileWriter,
) -> Callable[[dict[str, object]], Path]:
    """
    Write valid domain defaults with caller-supplied selection overrides.

    Parameters
    ----------
    domain : str
        Native source or log domain selected for the scenario.
    write_file : FileWriter
        UTF-8 writer creating the isolated consumer policy.

    Returns
    -------
    collections.abc.Callable[[dict[str, object]], pathlib.Path]
        Writer accepting include/exclude overrides without mutating them.
        Log cases receive a valid named literal so selection errors remain
        independent of domain-specific rule validation.
    """

    def write(
        overrides: dict[str, object],
    ) -> Path:
        """
        Serialize selection values with TOML-compatible JSON escaping.

        Parameters
        ----------
        overrides : dict[str, object]
            Scalar or array selection values to replace ordered defaults.

        Returns
        -------
        pathlib.Path
            Written standalone policy; no configuration is loaded here.
        """
        settings = {'include': ('second/*', 'first/*')} | overrides
        body = f'[{domain}]\n' + '\n'.join(
            f'{key}={json.dumps(value)}' for key, value in settings.items()
        )
        if domain == 'logs':
            body += '\npatterns={diagnostic="warning"}'
        return write_file('popo.toml', body)

    return write


# !SECTION


# SECTION: TESTS


@pytest.mark.parametrize('domain', ('python-source', 'swift-source', 'logs'))
class TestSourceSelectionPolicy:
    """Apply common pattern contracts without coupling consumer languages."""

    @pytest.mark.parametrize('setting', ('include', 'exclude'))
    @pytest.mark.parametrize(
        'pattern',
        ('../outside', 'absolute', 'nested/../outside'),
    )
    def test_escaping_patterns_identify_the_setting(
        self,
        tmp_path: Path,
        domain: str,
        write_policy: Callable[[dict[str, object]], Path],
        setting: str,
        pattern: str,
    ) -> None:
        """
        Reject unsafe includes and excludes with specific setting names.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        domain : str
            Native check domain selected for the scenario.
        write_policy : collections.abc.Callable
            Shared policy writer preserving domain-specific valid defaults.
        setting : str
            Configuration setting selected for mutation.
        pattern : str
            Glob or literal selection passed to the operation.
        """
        selected = (
            str(tmp_path.parent / 'outside') if pattern == 'absolute' else pattern
        )
        policy = {'include': ['*.py'], 'exclude': []} | {setting: [selected]}
        write_policy(policy)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=rf'{domain}\.{setting} must stay'):
            load_source_check(tmp_path, domain)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('setting', ('include', 'exclude'))
    @pytest.mark.parametrize(
        'value,message',
        (
            pytest.param(False, 'must be an array of nonempty strings', id='boolean'),
            pytest.param(1, 'must be an array of nonempty strings', id='integer'),
            pytest.param('*.py', 'must be an array of nonempty strings', id='scalar'),
            pytest.param((1,), 'must be an array of nonempty strings', id='nonstring'),
            pytest.param(('',), 'must be an array of nonempty strings', id='empty'),
            pytest.param((' ',), 'must be an array of nonempty strings', id='blank'),
            pytest.param(('same', 'same'), 'contains duplicates', id='duplicate'),
        ),
    )
    def test_malformed_patterns_identify_the_setting(
        self,
        tmp_path: Path,
        domain: str,
        write_policy: Callable[[dict[str, object]], Path],
        setting: str,
        value: object,
        message: str,
    ) -> None:
        """
        Reject malformed arrays consistently before domain-specific rules.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated root containing the selected consumer policy.
        domain : str
            Python, Swift or log policy domain under test.
        write_policy : collections.abc.Callable
            Shared policy writer supplying valid unrelated defaults.
        setting : str
            Include or exclude setting receiving the malformed value.
        value : object
            Invalid scalar or immutable array fixture serialized as TOML.
        message : str
            Exact shared-parser diagnostic after the setting identifier.
        """
        write_policy({setting: value})
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_source_check(tmp_path, domain)
        assert str(raised.value) == f'{domain}.{setting} {message}'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'exclusions',
        [
            pytest.param(None, id='omitted'),
            pytest.param((), id='explicit-empty'),
            pytest.param(('second/*', 'first/*'), id='ordered-patterns'),
        ],
    )
    def test_optional_exclusions_preserve_order(
        self,
        tmp_path: Path,
        domain: str,
        write_policy: Callable[[dict[str, object]], Path],
        exclusions: tuple[str, ...] | None,
    ) -> None:
        """
        Preserve pattern order with omitted, empty or explicit exclusions.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        domain : str
            Native check domain selected for the scenario.
        write_policy : collections.abc.Callable
            Shared policy writer preserving domain-specific valid defaults.
        exclusions : tuple[str, ...] | None
            Excluded input patterns, or None to use policy defaults.
        """
        write_policy({} if exclusions is None else {'exclude': exclusions})
        before = snapshot_files(tmp_path)
        config = load_source_check(tmp_path, domain)
        assert config.include == ('second/*', 'first/*')
        assert config.exclude == (exclusions or ())
        assert snapshot_files(tmp_path) == before


# !SECTION
