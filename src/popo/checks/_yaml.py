"""
:mod:`popo.checks._yaml` module.

Shared safe YAML mapping construction, reading and cycle-safe traversal.
"""

import re
from collections.abc import Hashable, Iterator
from pathlib import Path
from typing import cast

import yaml

# SECTION: PROTECTED CLASSES


class WorkflowLoader(yaml.SafeLoader):
    """
    Load safe YAML with string-only keys and GitHub-compatible booleans.

    Parameters
    ----------
    stream : str, bytes, or file-like object
        YAML input accepted by the inherited SafeLoader constructor.

    Notes
    -----
    Mapping construction rejects duplicate keys and non-string keys. The loader
    uses its own implicit resolvers: only case-insensitive ``true`` and
    ``false`` resolve as booleans, preserving names such as ``on`` and values
    such as ``yes`` as strings. Other safe YAML constructors remain inherited.
    The loader parses data without executing automation or constructing
    arbitrary Python objects.
    """

    def construct_mapping(
        self,
        node: yaml.MappingNode,
        deep: bool = False,
    ) -> dict[Hashable, object]:
        """
        Construct a mapping while enforcing unique string keys.

        Parameters
        ----------
        node : yaml.MappingNode
            YAML mapping node whose key/value pairs are constructed in source
            order.
        deep : bool, optional
            Forwarded to :meth:`yaml.SafeLoader.construct_object` for keys and
            values. Defaults to ``False``.

        Returns
        -------
        dict[collections.abc.Hashable, object]
            Constructed mapping with string keys and safely constructed values.

        Raises
        ------
        ValueError
            If a constructed key is not a string or repeats an earlier key.
        yaml.YAMLError
            If inherited construction cannot process a key or value node.

        Notes
        -----
        Errors propagate to the caller. During file validation, the outer
        validator converts these errors into diagnostics.
        """
        result: dict[Hashable, object] = {}
        for key_node, value_node in node.value:
            key: object = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError('YAML mapping keys must be strings')
            if key in result:
                raise ValueError(f'duplicate YAML key: {key}')
            result[key] = self.construct_object(value_node, deep=deep)
        return result


# !SECTION


# SECTION: PROTECTED VARIABLE


WorkflowLoader.yaml_implicit_resolvers = {
    key: [(tag, regex) for tag, regex in items if tag != 'tag:yaml.org,2002:bool']
    for key, items in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver(
    'tag:yaml.org,2002:bool',
    re.compile(r'^(?:true|false)$', re.I),
    list('tTfF'),
)


# !SECTION


# SECTION: FUNCTIONS


def mapping_nodes(
    value: object,
    seen: set[int] | None = None,
) -> Iterator[dict[str, object]]:
    """
    Yield nested mappings once while avoiding cycles and repeated aliases.

    Parameters
    ----------
    value : object
        Parsed data to traverse; only dictionaries and lists are descended
        into.
    seen : set[int] or None, optional
        Identities already visited. A supplied set is updated in place; when
        omitted, create one shared by the traversal.

    Yields
    ------
    dict[str, object]
        Original dictionaries in depth-first order, visiting a parent before
        its children and preserving dictionary value/list element order.

    Notes
    -----
    Scalars yield nothing. Shared containers and recursive YAML aliases are
    visited only once. Values are not copied or mutated; keys are assumed to
    have been validated by the loader. The visited set is updated as the
    iterator is consumed. An explicit stack avoids the Python recursion limit
    for deeply nested parsed data; YAML parsing has its own limits.
    """
    seen = set() if seen is None else seen
    pending = [value]
    while pending:
        current = pending.pop()
        if not isinstance(current, (dict, list)) or id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, dict):
            mapping = cast(dict[str, object], current)
            yield mapping
            pending.extend(reversed(mapping.values()))
        else:
            pending.extend(reversed(cast(list[object], current)))


def parse_mapping(
    source: str,
    *,
    label: str = 'document',
) -> dict[str, object]:
    """
    Parse a YAML text snapshot using the shared restricted safe loader.

    Parameters
    ----------
    source : str
        YAML text already read by the caller; no files are inspected.
    label : str, optional
        Mapping name used in diagnostics; defaults to ``document``.

    Returns
    -------
    dict[str, object]
        Mapping with unique string keys and GitHub-compatible booleans.

    Raises
    ------
    yaml.YAMLError
        If YAML parsing or safe construction fails.
    ValueError
        If the document is not a mapping, including empty input, or contains
        duplicate or non-string keys.

    Notes
    -----
    Share the same shape and key validation as file-based reading. Parsing
    performs no file I/O and does not execute automation or arbitrary objects.
    """
    # PyYAML's dynamic return value is narrowed at this boundary.
    value: object = yaml.load(source, Loader=WorkflowLoader)
    return require_mapping(value, label)


def read_mapping(
    path: Path,
    *,
    label: str = 'document',
) -> dict[str, object]:
    """
    Read a UTF-8 YAML file and require a mapping document.

    Parameters
    ----------
    path : pathlib.Path
        File to read; repository containment is checked separately by callers.
    label : str, optional
        Mapping name used in diagnostics; defaults to ``document``.

    Returns
    -------
    dict[str, object]
        Parsed document using the restricted safe loader.

    Raises
    ------
    OSError, UnicodeError
        If the file cannot be read or decoded as UTF-8.
    yaml.YAMLError
        If YAML parsing or safe construction fails.
    ValueError
        If the document is not a mapping or contains duplicate/non-string keys.

    Notes
    -----
    Empty YAML resolves to ``None`` and fails the mapping requirement. Read
    without modifying the file or executing referenced automation.
    :func:`~popo.checks.automation.validate` converts these errors into
    per-file diagnostics. Safety and actionlint callers handle errors
    separately.
    """
    return parse_mapping(path.read_text(encoding='utf-8'), label=label)


def require_mapping(
    value: object,
    label: str,
) -> dict[str, object]:
    """
    Require a dictionary and narrow its type without copying its contents.

    Parameters
    ----------
    value : object
        Candidate mapping; only dict instances are accepted.
    label : str
        Description used in a failure diagnostic.

    Returns
    -------
    dict[str, object]
        The original dictionary, with its type narrowed for callers.

    Raises
    ------
    ValueError
        If value is not a dict instance.

    Notes
    -----
    Do not validate key or value types or mutate the dictionary. String-key
    validation for YAML occurs in the loader.
    """
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be a mapping')
    return cast(dict[str, object], value)


# !SECTION
