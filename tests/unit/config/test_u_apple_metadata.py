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
    """Check explicit selectors, typed expectations and rule requirements."""

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
        ('before', 'after', 'message'),
        (
            *(
                pytest.param(before, after, message, id=label)
                for label, before, after, message in (
                    (
                        'invalid-kind',
                        'kind = "plist"',
                        'kind = "json"',
                        'kind must be plist or xcode',
                    ),
                    (
                        'invalid-id',
                        'id = "privacy"',
                        'id = "invalid id"',
                        'invalid rule id',
                    ),
                    (
                        'duplicate-id',
                        'id = "identity"',
                        'id = "privacy"',
                        'duplicate rule id',
                    ),
                    (
                        'parent-path',
                        'path = "Info.plist"',
                        'path = "../Info.plist"',
                        'requires a confined literal path',
                    ),
                    (
                        'absolute-path',
                        'path = "Info.plist"',
                        'path = "/Info.plist"',
                        'requires a confined literal path',
                    ),
                    (
                        'dot-path',
                        'path = "Info.plist"',
                        'path = "./Info.plist"',
                        'requires a confined literal path',
                    ),
                    (
                        'empty-path',
                        'path = "Info.plist"',
                        'path = ""',
                        'requires a confined literal path',
                    ),
                    (
                        'nonstring-path',
                        'path = "Info.plist"',
                        'path = 1',
                        'requires a confined literal path',
                    ),
                    (
                        'unknown-setting',
                        'absent = ["PrivateKey"]',
                        'unknown = true',
                        'unknown rule setting',
                    ),
                    (
                        'nonstring-list-member',
                        'absent = ["PrivateKey"]',
                        'absent = [1]',
                        'expected a list of nonblank strings',
                    ),
                    (
                        'duplicate-list-member',
                        'absent = ["PrivateKey"]',
                        'absent = ["a", "a"]',
                        'duplicate list entry',
                    ),
                    (
                        'contradictory-keys',
                        'absent = ["PrivateKey"]',
                        'absent = ["ITSAppUsesNonExemptEncryption"]',
                        'contradictory key requirements',
                    ),
                    (
                        'plist-target',
                        'absent = ["PrivateKey"]',
                        'target = "not-allowed"',
                        'plist rules cannot select targets',
                    ),
                    (
                        'invalid-scope',
                        'target = "Example"',
                        'scope = "invalid"',
                        'invalid xcode scope',
                    ),
                    (
                        'project-scope-target',
                        'target = "Example"',
                        'scope = "project"\ntarget = "Example"',
                        'xcode needs target, configurations and string values',
                    ),
                    (
                        'nonstring-target',
                        'target = "Example"',
                        'target = 1',
                        'target must be a string',
                    ),
                    (
                        'empty-target',
                        'target = "Example"',
                        'target = ""',
                        'xcode needs target, configurations and string values',
                    ),
                    (
                        'empty-configurations',
                        'target = "Example"\nconfigurations = ["Debug", "Release"]',
                        'target = "Example"\nconfigurations = []',
                        'xcode needs target, configurations and string values',
                    ),
                    (
                        'nonstring-xcode-value',
                        'PRODUCT_BUNDLE_IDENTIFIER = "com.example.app"',
                        'S = false',
                        'xcode needs target, configurations and string values',
                    ),
                    (
                        'nonfinite-value',
                        'ITSAppUsesNonExemptEncryption = false',
                        'Value = inf',
                        'unsupported expected values',
                    ),
                    (
                        'date-value',
                        'ITSAppUsesNonExemptEncryption = false',
                        'Value = 2026-11-03',
                        'unsupported expected values',
                    ),
                )
            ),
        ),
    )
    def test_invalid_policy_is_rejected(
        self: Self,
        tmp_path: Path,
        before: str,
        after: str,
        message: str,
    ) -> None:
        """
        Reject unsafe selectors, contradictory keys and unsupported values.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable policy root.
        before, after : str
            Literal mutation isolating one invalid policy field.
        message : str
            Exact diagnostic detail following the Apple-metadata prefix.
        """
        assert POLICY.count(before) == 1
        (tmp_path / 'pyproject.toml').write_text(
            POLICY.replace(before, after, 1),
            encoding='utf-8',
        )
        original = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError) as raised:
            load_apple_metadata_config(tmp_path)
        assert str(raised.value) == f'apple-metadata: {message}'
        assert snapshot_files(tmp_path) == original


# !SECTION
