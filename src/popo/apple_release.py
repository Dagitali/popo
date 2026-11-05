"""
:mod:`popo.apple_release` module.

Read selected Apple release identity without exposing other project settings.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checks._openstep import parse_project
from .checks._xcode import configuration_settings, mapping
from .config.apple_release import AppleReleaseConfig, load_apple_release_config

# SECTION: DATA CLASS


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    """
    Retain only the validated release fields permitted in public reports.

    Attributes
    ----------
    version : str
        Agreed numeric version normalized to three components.
    build : int
        Agreed positive build number normalized to an integer.
    """

    version: str
    build: int


# !SECTION


# SECTION: FUNCTIONS


def identity(
    project: dict[str, Any],
    config: AppleReleaseConfig,
    tag: str | None = None,
) -> ReleaseIdentity:
    """
    Validate an exact native configuration set and its release identity.

    Parameters
    ----------
    project : dict[str, Any]
        Decoded native object graph, without build-settings evaluation.
    config : AppleReleaseConfig
        Exact consumer target/configuration selection and tag convention.
    tag : str or None, optional
        Explicit tag to compare after normalization; None omits tag checking.

    Returns
    -------
    ReleaseIdentity
        Two- or three-part numeric version normalized to three parts and a
        positive integer build. Literal spellings must agree before conversion.

    Raises
    ------
    KeyError, TypeError, ValueError
        Native references or explicit values are missing, inconsistent,
        malformed or ambiguous, or the tag differs. No values enter errors.
    """
    settings = configuration_settings(
        project,
        config.target,
        config.configurations,
        exact=True,
        product_type=config.product_type,
    )
    identities: set[tuple[str, str]] = set()
    for item in settings:
        version = item.get('MARKETING_VERSION')
        build = item.get('CURRENT_PROJECT_VERSION')
        if not isinstance(version, str) or not re.fullmatch(
            r'[0-9]+\.[0-9]+(?:\.[0-9]+)?',
            version,
        ):
            raise ValueError('invalid marketing version')
        if (
            not isinstance(build, str)
            or not re.fullmatch(r'[0-9]+', build)
            or int(build) <= 0
        ):
            raise ValueError('invalid build number')
        identities.add((version, build))
    if len(identities) != 1:
        raise ValueError('inconsistent release identity')
    version, build = identities.pop()
    normalized = version + '.0' if version.count('.') == 1 else version
    if tag is not None and tag != config.tag_prefix + normalized:
        raise ValueError('release tag mismatch')
    return ReleaseIdentity(normalized, int(build))


def read_identity(
    root: Path,
    tag: str | None = None,
) -> ReleaseIdentity:
    """
    Read one confined project and expose only its agreed release fields.

    Parameters
    ----------
    root : pathlib.Path
        Consumer policy and input root.
    tag : str or None, optional
        Explicit expected tag; never inferred from Git or the environment.

    Returns
    -------
    ReleaseIdentity
        Validated version/build from the explicitly selected target.

    Raises
    ------
    OSError, UnicodeError
        Policy, input or symlink target cannot be read or decoded.
    ValueError, KeyError, TypeError, RecursionError
        Policy, source structure, release values or tag violate the contract.
        The CLI converts these failures into value-redacted diagnostics.
    """
    config = load_apple_release_config(root)
    path = root / config.project
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('project escapes root')
    project = mapping(parse_project(path.read_text(encoding='utf-8')))
    return identity(project, config, tag)


# !SECTION
