"""
:mod:`tests.unit.test_u_apple_release` module.

Validate exact native release selection, numeric formats and literal agreement.
"""

from copy import deepcopy
from dataclasses import replace
from typing import Any, Self

import pytest

from popo.apple_release import ReleaseIdentity, identity
from popo.checks._openstep import parse_project
from popo.checks._xcode import mapping
from popo.config.apple_release import AppleReleaseConfig
from tests.support.apple_release import PROJECT

# SECTION: FIXTURES


@pytest.fixture(name='release_project')
def release_project_fixture() -> dict[str, Any]:
    """
    Decode a fresh independent native project graph for each mutation.

    Returns
    -------
    dict[str, Any]
        Application target with two explicit release configurations.
    """
    return mapping(parse_project(PROJECT))


@pytest.fixture(name='release_config')
def release_config_fixture() -> AppleReleaseConfig:
    """
    Supply one application target and its exact configuration set.

    Returns
    -------
    AppleReleaseConfig
        Consumer selector with the conventional explicit tag prefix.
    """
    return AppleReleaseConfig(
        'Example.xcodeproj/project.pbxproj',
        'Example',
        ('Debug', 'Release'),
        'com.apple.product-type.application',
        'v',
    )


# !SECTION


# SECTION: TESTS


class TestAppleReleaseIdentity:
    """Keep release-specific format and agreement matrices in Popo."""

    @pytest.mark.parametrize(
        'case',
        (
            'extra',
            'missing',
            'repeated-reference',
            'duplicate-name',
            'unnamed',
            'ambiguous-target',
            'wrong-product',
        ),
    )
    def test_exact_owner_and_configuration_set(
        self: Self,
        release_project: dict[str, Any],
        release_config: AppleReleaseConfig,
        case: str,
    ) -> None:
        """
        Reject non-exact selections even when all release values agree.

        Parameters
        ----------
        release_project : dict[str, Any]
            Independent native project graph.
        release_config : AppleReleaseConfig
            Expected target and complete configuration names.
        case : str
            Structural mutation violating the release selection contract.
        """
        objects = release_project['objects']
        references = objects['L']['buildConfigurations']
        if case == 'missing':
            references.pop()
        elif case == 'repeated-reference':
            references.append('D')
        elif case in ('extra', 'duplicate-name'):
            objects['X'] = deepcopy(objects['D'])
            if case == 'extra':
                objects['X']['name'] = 'Unexpected'
            references.append('X')
        elif case == 'unnamed':
            del objects['R']['name']
        elif case == 'ambiguous-target':
            objects['X'] = deepcopy(objects['T'])
        else:
            objects['T']['productType'] = 'com.apple.product-type.bundle.unit-test'
        with pytest.raises(ValueError):
            identity(release_project, release_config)

    @pytest.mark.parametrize(
        'field,value',
        (
            ('MARKETING_VERSION', None),
            ('MARKETING_VERSION', 1),
            ('MARKETING_VERSION', '1'),
            ('MARKETING_VERSION', '1.2.3.4'),
            ('MARKETING_VERSION', '1.2.0-beta'),
            ('MARKETING_VERSION', ' 1.2'),
            ('MARKETING_VERSION', '١.٢'),
            ('MARKETING_VERSION', '$(VERSION)'),
            ('CURRENT_PROJECT_VERSION', None),
            ('CURRENT_PROJECT_VERSION', True),
            ('CURRENT_PROJECT_VERSION', 7),
            ('CURRENT_PROJECT_VERSION', '0'),
            ('CURRENT_PROJECT_VERSION', '-1'),
            ('CURRENT_PROJECT_VERSION', '1.2'),
            ('CURRENT_PROJECT_VERSION', '7 '),
            ('CURRENT_PROJECT_VERSION', '$(BUILD)'),
        ),
    )
    def test_formats_require_explicit_numeric_strings(
        self: Self,
        release_project: dict[str, Any],
        release_config: AppleReleaseConfig,
        field: str,
        value: object,
    ) -> None:
        """
        Reject missing, nonliteral, non-ASCII and incorrectly typed fields.

        Parameters
        ----------
        release_project : dict[str, Any]
            Fresh application configuration graph.
        release_config : AppleReleaseConfig
            Explicit application selector.
        field : str
            Version or build setting independently mutated.
        value : object
            Invalid native setting value.
        """
        release_project['objects']['D']['buildSettings'][field] = value
        with pytest.raises(ValueError):
            identity(release_project, release_config)

    def test_other_targets_do_not_contribute_identity(
        self: Self,
        release_project: dict[str, Any],
        release_config: AppleReleaseConfig,
    ) -> None:
        """
        Ignore independent test-target versions and unrelated metadata.

        Parameters
        ----------
        release_project : dict[str, Any]
            Independent app graph extended with another native target.
        release_config : AppleReleaseConfig
            Exact application-only release scope.
        """
        objects = release_project['objects']
        objects['Other'] = {
            'isa': 'PBXNativeTarget',
            'name': 'Tests',
            'buildConfigurationList': 'OtherList',
        }
        objects['OtherList'] = {
            'isa': 'XCConfigurationList',
            'buildConfigurations': ['OtherConfig'],
        }
        objects['OtherConfig'] = {
            'isa': 'XCBuildConfiguration',
            'name': 'Debug',
            'buildSettings': {
                'MARKETING_VERSION': '99.0',
                'CURRENT_PROJECT_VERSION': '999',
            },
        }
        assert identity(release_project, release_config) == ReleaseIdentity('1.2.0', 7)

    @pytest.mark.parametrize(
        'field,value',
        (
            ('MARKETING_VERSION', '1.2'),
            ('CURRENT_PROJECT_VERSION', '07'),
            ('MARKETING_VERSION', '9.0.0'),
            ('CURRENT_PROJECT_VERSION', '9'),
        ),
    )
    def test_raw_spelling_agrees_before_normalization(
        self: Self,
        release_project: dict[str, Any],
        release_config: AppleReleaseConfig,
        field: str,
        value: str,
    ) -> None:
        """
        Fail disagreement even when converted version/build values coincide.

        Parameters
        ----------
        release_project : dict[str, Any]
            Fresh native graph with one changed configuration.
        release_config : AppleReleaseConfig
            Exact configuration selection.
        field : str
            Setting whose literal spelling must agree.
        value : str
            Individually valid but inconsistent literal.
        """
        release_project['objects']['D']['buildSettings'][field] = value
        with pytest.raises(ValueError, match='inconsistent release identity'):
            identity(release_project, release_config)

    @pytest.mark.parametrize(
        'prefix,tag,accepted',
        (
            ('v', 'v1.2.0', True),
            ('', '1.2.0', True),
            ('release/', 'release/1.2.0', True),
            ('v', 'v1.2', False),
            ('v', '1.2.0', False),
            ('v', 'v1.2.0-rc.1', False),
            ('v', ' v1.2.0', False),
            ('v', 'v1.2.0/extra', False),
        ),
    )
    def test_tag_matching_is_explicit_and_exact(
        self: Self,
        release_project: dict[str, Any],
        release_config: AppleReleaseConfig,
        prefix: str,
        tag: str,
        accepted: bool,
    ) -> None:
        """
        Apply the consumer prefix only when a tag is supplied.

        Parameters
        ----------
        release_project : dict[str, Any]
            Valid native application project.
        release_config : AppleReleaseConfig
            Configuration copied with an explicit prefix.
        prefix : str
            Consumer-owned literal tag prefix, including the empty prefix.
        tag : str
            Explicit release tag supplied by the caller.
        accepted : bool
            Whether it exactly matches prefix plus normalized version.
        """
        config = replace(release_config, tag_prefix=prefix)
        if accepted:
            assert identity(release_project, config, tag).version == '1.2.0'
        else:
            with pytest.raises(ValueError, match='release tag mismatch'):
                identity(release_project, config, tag)

    @pytest.mark.parametrize(
        'version,build,normalized,number',
        (
            ('1.2', '7', '1.2.0', 7),
            ('1.2.3', '8', '1.2.3', 8),
            ('01.02', '007', '01.02.0', 7),
            ('0.0.0', '1', '0.0.0', 1),
        ),
    )
    def test_valid_identity_normalizes_after_agreement(
        self: Self,
        release_project: dict[str, Any],
        release_config: AppleReleaseConfig,
        version: str,
        build: str,
        normalized: str,
        number: int,
    ) -> None:
        """
        Preserve compatible numeric formats without a second version source.

        Parameters
        ----------
        release_project : dict[str, Any]
            Native graph whose selected settings receive identical values.
        release_config : AppleReleaseConfig
            Explicit exact target selector.
        version, build : str
            Agreed source version/build literals.
        normalized : str
            Expected three-part version.
        number : int
            Expected positive integer build.
        """
        for key in ('D', 'R'):
            release_project['objects'][key]['buildSettings'].update(
                MARKETING_VERSION=version,
                CURRENT_PROJECT_VERSION=build,
            )
        assert identity(release_project, release_config) == ReleaseIdentity(
            normalized,
            number,
        )


# !SECTION
