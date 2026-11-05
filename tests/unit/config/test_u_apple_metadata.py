"""
:mod:`tests.unit.config.test_u_apple_metadata` module.

Reject malformed Apple metadata policies independently of native file reads.

Reject ambiguous optional expectations, key patterns and discovery selectors.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.config import ConfigurationError
from popo.config.apple_metadata import load_apple_metadata_config
from tests.support.apple_metadata import POLICY
from tests.support.files import FileWriter, snapshot_files

# SECTION: CONSTANTS


RULE = """[[tool.popo.apple-metadata.rules]]
id = "local"
kind = "plist"
path = "Config/Local.plist"
absent = ["Secret"]
"""
COVERAGE = """[[tool.popo.apple-metadata.coverage]]
id = "local-scope"
include = ["Config/Local*.plist"]
rule-ids = ["local"]
"""


# !SECTION


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


class TestAppleMetadataCoverageConfiguration:
    """Reject unsafe discovery selectors and ambiguous coverage references."""

    def test_invalid_coverage_collection_is_rejected(
        self: Self,
        tmp_path: Path,
    ) -> None:
        """
        Reject a table where a coverage array is required.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable consumer root.
        """
        (tmp_path / 'pyproject.toml').write_text(
            '[tool.popo.apple-metadata]\ncoverage = {}\n' + RULE,
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match='coverage must be a list'):
            load_apple_metadata_config(tmp_path)

    @pytest.mark.parametrize(
        ('before', 'after'),
        (
            ('id = "local-scope"', 'id = "local"'),
            ('id = "local-scope"', 'id = 1'),
            ('id = "local-scope"', 'id = "invalid id"'),
            ('rule-ids = ["local"]', 'rule-ids = ["unknown"]'),
            ('rule-ids = ["local"]', 'rule-ids = []'),
            ('include = ["Config/Local*.plist"]', 'include = []'),
            ('include = ["Config/Local*.plist"]', 'include = ["../*.plist"]'),
            ('include = ["Config/Local*.plist"]', 'include = ["/Config/*.plist"]'),
            ('include = ["Config/Local*.plist"]', 'include = ["Config/**/*.plist"]'),
            ('include = ["Config/Local*.plist"]', 'include = ["*/Local.plist"]'),
            ('include = ["Config/Local*.plist"]', 'include = ["Config/./*.plist"]'),
            ('include = ["Config/Local*.plist"]', 'unknown = true'),
        ),
    )
    def test_invalid_file_coverage_is_rejected(
        self: Self,
        tmp_path: Path,
        before: str,
        after: str,
    ) -> None:
        """
        Reject unconfined discovery, unknown references and reused identifiers.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable consumer root.
        before, after : str
            Independent coverage mutation.
        """
        (tmp_path / 'pyproject.toml').write_text(
            RULE + COVERAGE.replace(before, after),
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match='apple-metadata:'):
            load_apple_metadata_config(tmp_path)


class TestAppleMetadataRuleAssertions:
    """Keep new contracts opt-in and reject unsafe or contradictory policy."""

    @pytest.mark.parametrize(
        'extra',
        (
            'optional-expected = []',
            'optional-expected = {Value = inf}',
            'optional-expected = {Secret = "value"}',
            'expected = {Value = "a"}\noptional-expected = {Value = "a"}',
            'required-anywhere = ["Secret"]',
            'required-anywhere = [1]',
            'absent-patterns = ["["]',
            'absent-patterns = [" "]',
            'absent-patterns = ["Value"]\nexpected = {Value = "value"}',
            'absent-patterns = ["Value"]\nrequired-anywhere = ["Value"]',
            'absent-patterns = ["Value"]\noptional-expected = {Value = "v"}',
        ),
    )
    def test_invalid_extensions_are_rejected(
        self: Self,
        tmp_path: Path,
        extra: str,
    ) -> None:
        """
        Reject invalid values, regular expressions and conflicting assertions.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable consumer root.
        extra : str
            Malformed or contradictory rule fields.
        """
        (tmp_path / 'pyproject.toml').write_text(RULE + extra, encoding='utf-8')
        with pytest.raises(ConfigurationError, match='apple-metadata:'):
            load_apple_metadata_config(tmp_path)

    @pytest.mark.parametrize('value', ('false', '0', '[]', '{Enabled = true}'))
    def test_optional_plist_values_remain_typed(
        self: Self,
        tmp_path: Path,
        value: str,
    ) -> None:
        """
        Load typed optional plist expectations without reading metadata.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable consumer root.
        value : str
            Supported native value represented in TOML.
        """
        (tmp_path / 'pyproject.toml').write_text(
            RULE + f'optional-expected = {{Value = {value}}}\n' + COVERAGE,
            encoding='utf-8',
        )
        config = load_apple_metadata_config(tmp_path)
        assert config.rules[0].optional_expected
        assert config.coverage[0].rule_ids == ('local',)


class TestAppleMetadataSelectionConfiguration:
    """Keep all-configuration selection separate from named selectors."""

    @pytest.mark.parametrize(
        'fields',
        (
            'target = "Example"',
            'configurations = ["Debug"]',
            'optional-expected = {Value = false}',
        ),
    )
    def test_invalid_global_selection_is_rejected(
        self: Self,
        tmp_path: Path,
        fields: str,
    ) -> None:
        """
        Keep all-configuration selection independent of named lists.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable consumer root.
        fields : str
            Invalid global selector or non-string setting expectation.
        """
        policy = RULE.replace('kind = "plist"', 'kind = "xcode"')
        (tmp_path / 'pyproject.toml').write_text(
            policy + 'scope = "all-configurations"\n' + fields,
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match='apple-metadata:'):
            load_apple_metadata_config(tmp_path)


# !SECTION
