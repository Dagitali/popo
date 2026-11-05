"""
:mod:`popo.checks._xcode` module.

Resolve explicit native project configuration references without native tools.
"""

from typing import Any

# SECTION: FUNCTIONS


def configuration_settings(
    project: dict[str, Any],
    target: str,
    configurations: tuple[str, ...],
    *,
    exact: bool = False,
    product_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Select explicit build settings through native object references.

    Parameters
    ----------
    project : dict[str, Any]
        Decoded OpenStep object graph.
    target : str
        Exact native target name; empty selects the root PBXProject.
    configurations : tuple[str, ...]
        Unique selected configuration names in reporting order.
    exact : bool, optional
        Reject additional, unnamed or repeated configuration references.
    product_type : str or None, optional
        Required product type; None leaves the owner type unrestricted.

    Returns
    -------
    list[dict[str, Any]]
        Explicit settings with no inheritance or variable expansion.

    Raises
    ------
    KeyError, TypeError, ValueError
        Owners, configurations or settings are missing, malformed, ambiguous
        or violate exact selection/product requirements.
    """
    objects = mapping(project['objects'])
    if target:
        targets = [
            item
            for item in objects.values()
            if isinstance(item, dict)
            and item.get('isa') == 'PBXNativeTarget'
            and item.get('name') == target
        ]
        if len(targets) != 1:
            raise ValueError('expected one native target')
        owner = targets[0]
    else:
        owner = mapping(objects[project['rootObject']])
        if owner.get('isa') != 'PBXProject':
            raise ValueError('expected the root project')
    if product_type is not None and owner.get('productType') != product_type:
        raise ValueError('unexpected product type')
    listing = mapping(objects[owner['buildConfigurationList']])
    if listing.get('isa') != 'XCConfigurationList':
        raise ValueError('expected a configuration list')
    references = listing['buildConfigurations']
    if not isinstance(references, list) or not all(
        isinstance(key, str) for key in references
    ):
        raise ValueError('expected configuration references')
    configs: dict[str, dict[str, Any] | None] = {}
    for key in references:
        config = mapping(objects[key])
        if isinstance(name := config.get('name'), str):
            configs[name] = None if name in configs else config
    if exact and (
        set(configs) != set(configurations) or len(references) != len(configs)
    ):
        raise ValueError('configuration set differs')
    result = []
    for name in configurations:
        selected = configs.get(name)
        if selected is None or selected.get('isa') != 'XCBuildConfiguration':
            raise ValueError('expected one named build configuration')
        result.append(mapping(selected['buildSettings']))
    return result


def mapping(
    value: object,
) -> dict[str, Any]:
    """
    Require dictionary-shaped native metadata.

    Parameters
    ----------
    value : object
        Decoded property-list value or referenced project object.

    Returns
    -------
    dict[str, Any]
        Validated mapping.

    Raises
    ------
    ValueError
        The supplied value is not a dictionary.
    """
    if not isinstance(value, dict):
        raise ValueError('expected a dictionary')
    return value


# !SECTION
