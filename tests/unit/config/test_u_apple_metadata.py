"""
:mod:`tests.unit.config.test_u_apple_metadata` module.

Reject malformed Apple metadata policies independently of native file reads.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.config import ConfigurationError
from popo.config.apple_metadata import load_apple_metadata_config
from tests.support.apple_metadata import POLICY
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestAppleMetadataConfiguration:
    """
    Validate explicit selectors, typed expectations and rule requirements.
    """

    @pytest.mark.parametrize(
        ('content', 'message'),
        (
            pytest.param(
                '[tool.popo.apple-metadata]\nrules=[]',
                'apple-metadata: requires nonempty rules',
                id='empty-rules',
            ),
            pytest.param(
                '[[tool.popo.apple-metadata.rules]]\n'
                'id="empty"\nkind="plist"\npath="Info.plist"',
                'apple-metadata: empty rule requirements',
                id='empty-requirements',
            ),
        ),
    )
    def test_empty_rules_or_requirements_are_rejected(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
        message: str,
    ) -> None:
        """
        Reject policies with no rules or rules with no assertions to perform.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root without native metadata files.
        write_file : FileWriter
            UTF-8 writer creating only the malformed policy.
        content : str
            Explicit empty rule collection or otherwise valid empty plist rule.
        message : str
            Exact loader diagnostic identifying the missing requirements.
        """
        write_file('pyproject.toml', content)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_apple_metadata_config(tmp_path)
        assert str(raised.value) == message
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'before,after',
        (
            ('kind = "plist"', 'kind = "json"'),
            ('id = "privacy"', 'id = "invalid id"'),
            ('id = "identity"', 'id = "privacy"'),
            ('path = "Info.plist"', 'path = "../Info.plist"'),
            ('path = "Info.plist"', 'path = "/Info.plist"'),
            ('path = "Info.plist"', 'path = "./Info.plist"'),
            ('path = "Info.plist"', 'path = ""'),
            ('path = "Info.plist"', 'path = 1'),
            ('absent = ["PrivateKey"]', 'unknown = true'),
            ('absent = ["PrivateKey"]', 'absent = [1]'),
            ('absent = ["PrivateKey"]', 'absent = ["a", "a"]'),
            ('absent = ["PrivateKey"]', 'absent = ["ITSAppUsesNonExemptEncryption"]'),
            ('absent = ["PrivateKey"]', 'target = "not-allowed"'),
            ('target = "Example"', 'scope = "invalid"'),
            ('target = "Example"', 'scope = "project"\ntarget = "Example"'),
            ('target = "Example"', 'target = 1'),
            ('target = "Example"', 'target = ""'),
            (
                'target = "Example"\nconfigurations = ["Debug", "Release"]',
                'target = "Example"\nconfigurations = []',
            ),
            ('PRODUCT_BUNDLE_IDENTIFIER = "com.example.app"', 'S = false'),
            ('ITSAppUsesNonExemptEncryption = false', 'Value = inf'),
            ('ITSAppUsesNonExemptEncryption = false', 'Value = 2026-11-03'),
        ),
    )
    def test_invalid_policy_is_rejected(
        self: Self,
        tmp_path: Path,
        before: str,
        after: str,
    ) -> None:
        """
        Reject unsafe selectors, contradictory keys and unsupported values.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable policy root.
        before, after : str
            Literal mutation isolating one invalid policy field.
        """
        assert POLICY.count(before) == 1
        (tmp_path / 'pyproject.toml').write_text(
            POLICY.replace(before, after, 1),
            encoding='utf-8',
        )
        original = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError):
            load_apple_metadata_config(tmp_path)
        assert snapshot_files(tmp_path) == original


# !SECTION
