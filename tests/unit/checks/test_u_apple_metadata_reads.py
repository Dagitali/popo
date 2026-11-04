"""
:mod:`tests.unit.checks.test_u_apple_metadata_reads` module.

Verify per-run Apple metadata read caching without hiding independent rules.
"""

import plistlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import call, patch

import pytest

from popo.checks.apple_metadata import validate
from popo.config.apple_metadata import AppleRule
from tests.support.apple_metadata import PROJECT
from tests.support.files import snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='rule', params=('plist', 'xcode'))
def rule_fixture(
    request: pytest.FixtureRequest,
) -> AppleRule:
    """
    Select a valid metadata rule without creating or reading native files.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Property-list or Xcode adapter selected for this independent case.

    Returns
    -------
    AppleRule
        Rule requiring one private key to remain absent in native metadata.
    """
    kind = str(request.param)
    return AppleRule(
        'first',
        'metadata',
        kind,
        {},
        ('PrivateMissing',),
        'Example' if kind == 'xcode' else '',
        ('Debug',) if kind == 'xcode' else (),
        (),
    )


# !SECTION


# SECTION: TESTS


class TestAppleMetadataReads:
    """Observe each path/adapter once while retaining rule-local findings."""

    @pytest.mark.parametrize('failure', ('missing', 'malformed', 'nonobject'))
    def test_failed_documents_are_cached_and_later_runs_refresh(
        self,
        tmp_path: Path,
        rule: AppleRule,
        failure: str,
    ) -> None:
        """
        Reuse read/parse failures and inspect repairs on the next run.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing at most one native input.
        rule : AppleRule
            Valid plist or Xcode selection supplied by the adapter fixture.
        failure : str
            Missing input, malformed serialization or non-dictionary root.
        """
        path = tmp_path / rule.path
        if failure == 'malformed':
            path.write_bytes(b'PRIVATE {} {}')
        elif failure == 'nonobject':
            path.write_bytes(plistlib.dumps([]) if rule.kind == 'plist' else b'()')
        rules = tuple(
            replace(rule, identity=name) for name in ('first', 'second', 'third')
        )
        before = snapshot_files(tmp_path)
        with patch.object(
            Path,
            'read_bytes',
            autospec=True,
            side_effect=Path.read_bytes,
        ) as read:
            assert validate(tmp_path, rules) == [
                f'{item.identity}: metadata missing, invalid or violates policy'
                for item in rules
            ]
            read.assert_called_once_with(path)
        assert snapshot_files(tmp_path) == before
        path.write_bytes(
            plistlib.dumps({}) if rule.kind == 'plist' else PROJECT.encode(),
        )
        repaired = snapshot_files(tmp_path)
        with patch.object(
            Path,
            'read_bytes',
            autospec=True,
            side_effect=Path.read_bytes,
        ) as read:
            assert validate(tmp_path, rules) == []
            read.assert_called_once_with(path)
        assert snapshot_files(tmp_path) == repaired

    def test_policy_failure_does_not_poison_the_document_cache(
        self,
        tmp_path: Path,
        rule: AppleRule,
    ) -> None:
        """
        Preserve later successful rules after a mismatch in shared metadata.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing valid native metadata.
        rule : AppleRule
            Rule with an absent-key requirement that the document satisfies.
        """
        path = tmp_path / rule.path
        path.write_bytes(
            plistlib.dumps({}) if rule.kind == 'plist' else PROJECT.encode(),
        )
        rules = (
            replace(rule, expected={'MissingSetting': True}),
            replace(rule, identity='second'),
        )
        before = snapshot_files(tmp_path)
        with patch.object(
            Path,
            'read_bytes',
            autospec=True,
            side_effect=Path.read_bytes,
        ) as read:
            assert validate(tmp_path, rules) == [
                'first: metadata missing, invalid or violates policy',
            ]
        assert read.call_args_list == [call(path)]
        assert snapshot_files(tmp_path) == before


# !SECTION
