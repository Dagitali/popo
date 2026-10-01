"""
:mod:`popo.checks.automation` module.

Validate configured automation contracts without execution or network access.
"""

import json
import re
from collections.abc import Hashable, Iterator
from pathlib import Path
from typing import cast

import yaml

from ..config.automation import AutomationConfig
from .actions import is_pinned

# SECTION: PROTECTED CLASSES


class _Loader(yaml.SafeLoader):
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
            Forwarded to the inherited object constructor for keys and values.
            Defaults to False.

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


_Loader.yaml_implicit_resolvers = {
    key: [(tag, regex) for tag, regex in items if tag != 'tag:yaml.org,2002:bool']
    for key, items in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(
    'tag:yaml.org,2002:bool',
    re.compile(r'^(?:true|false)$', re.I),
    list('tTfF'),
)


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _call(
    node: dict[str, object],
    target: dict[str, object],
    workflow: bool,
) -> None:
    """
    Validate supplied inputs against a local action or workflow contract.

    Parameters
    ----------
    node : dict[str, object]
        Caller mapping with optional ``with`` inputs.
    target : dict[str, object]
        Action document or workflow_call mapping with optional ``inputs``.
    workflow : bool
        Whether declarations require workflow input types and supplied values
        must match string, boolean, or number types.

    Raises
    ------
    ValueError
        If input tables or declarations are not mappings, supplied names are
        unknown, required inputs lack values and defaults, or workflow input
        types or supplied values are invalid.

    Notes
    -----
    Validate without mutating either mapping. Strings containing ``${{`` skip
    supplied-value type checks; expressions are not evaluated. Action inputs
    receive name/required checks without workflow type enforcement. A required
    input with a declared default may be omitted. Errors propagate here and
    become per-file diagnostics in validate.
    """
    declared = _mapping(target.get('inputs', {}), 'inputs')
    supplied = _mapping(node.get('with', {}), 'with')
    if unknown := set(supplied) - set(declared):
        raise ValueError(f'unknown inputs: {sorted(unknown)}')
    for name, declaration in declared.items():
        spec = _mapping(declaration, f'input {name}')
        if (
            spec.get('required') is True
            and 'default' not in spec
            and name not in supplied
        ):
            raise ValueError(f'missing required input: {name}')
        if workflow and spec.get('type') not in ('string', 'boolean', 'number'):
            raise ValueError(f'invalid workflow input type: {name}')
    for name, value in supplied.items():
        if isinstance(value, str) and '${{' in value:
            continue
        spec = _mapping(declared[name], f'input {name}')
        kind = spec.get('type') if workflow else None
        valid = (
            kind is None
            or (kind == 'string' and isinstance(value, str))
            or (kind == 'boolean' and type(value) is bool)
            or (kind == 'number' and type(value) in (int, float))
        )
        if not valid:
            raise ValueError(f'wrong type for input: {name}')


def _composite(
    data: dict[str, object],
) -> None:
    """
    Validate action metadata and the supported composite-step structure.

    Parameters
    ----------
    data : dict[str, object]
        Parsed action document containing name, description, and runs settings.

    Raises
    ------
    ValueError
        If name or description is not a nonempty string, runs is not a mapping,
        composite steps are not a nonempty list of mappings, a step does not
        contain exactly one of run/uses, or a run step lacks a nonempty shell.

    Notes
    -----
    Non-composite runtimes return after validating name, description, and the
    runs mapping. This helper does not validate the complete action schema or
    execute steps. It does not mutate data; validate converts its errors into
    per-file diagnostics.
    """
    for key in ('name', 'description'):
        if not isinstance(data.get(key), str) or not data[key]:
            raise ValueError(f'action needs {key}')
    runs = _mapping(data.get('runs'), 'runs')
    if runs.get('using') != 'composite':
        # Other action runtimes are outside composite structural validation.
        return
    steps = runs.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('composite steps must be a nonempty list')
    for item in steps:
        step = _mapping(item, 'step')
        if ('run' in step) == ('uses' in step):
            raise ValueError('composite step needs exactly one of run/uses')
        if 'run' in step and (
            not isinstance(step.get('shell'), str) or not step['shell']
        ):
            raise ValueError('composite run step needs shell')


def _inside(
    root: Path,
    path: Path,
) -> Path:
    """
    Resolve a path and require it to remain within the resolved root.

    Parameters
    ----------
    root : pathlib.Path
        Repository boundary, resolved before comparison.
    path : pathlib.Path
        Path to resolve, including any symlinks. Relative paths are based on
        the process working directory, not implicitly joined to root.

    Returns
    -------
    pathlib.Path
        Resolved absolute path equal to root or below it.

    Raises
    ------
    ValueError
        If the resolved path lies outside the resolved root.
    OSError
        If path resolution fails, including a symlink loop.

    Notes
    -----
    Resolution does not require the target to exist. This containment check
    does not establish file type, readability, or a general filesystem sandbox.
    """
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'path escapes repository: {path}')
    return resolved


def _mapping(
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


def _metadata(
    root: Path,
    path: Path,
) -> None:
    """
    Validate the JSON companion of an automation template.

    Parameters
    ----------
    root : pathlib.Path
        Repository boundary for the companion file.
    path : pathlib.Path
        Template path whose final suffix is replaced with .properties.json.

    Raises
    ------
    ValueError
        If the companion escapes root, is not a mapping, lacks nonempty string
        name/description fields, or has invalid categories/filePatterns arrays.
    json.JSONDecodeError
        If the companion contains invalid JSON.
    OSError, UnicodeError
        If path resolution, reading, or decoding fails. Reading uses the
        default text encoding of the execution environment.
    re.PatternError
        If a filePatterns entry is not a valid regular expression.

    Notes
    -----
    Missing optional arrays default to empty lists. Compile patterns without
    matching files, evaluating automation, or changing either file. These
    errors propagate here and are converted into diagnostics by validate.
    """
    metadata = _inside(root, path.with_suffix('.properties.json'))
    doc = _mapping(json.loads(metadata.read_text()), 'template metadata')
    for key in ('name', 'description'):
        if not isinstance(doc.get(key), str) or not doc[key]:
            raise ValueError(f'template metadata needs {key}')
    for key in ('filePatterns', 'categories'):
        values = doc.get(key, [])
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError(f'{key} must be an array of strings')
        if key == 'filePatterns':
            for pattern in values:
                re.compile(pattern)


def _nodes(
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
        omitted, create one shared by the recursive traversal.

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
    iterator is consumed. Traversal remains recursive and can exceed Python's
    recursion limit for sufficiently deep input.
    """
    seen = set() if seen is None else seen
    if not isinstance(value, (dict, list)) or id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        yield mapping
        children = list(mapping.values())
    else:
        children = cast(list[object], value)
    for child in children:
        yield from _nodes(child, seen)


def _read(
    path: Path,
) -> dict[str, object]:
    # PyYAML's dynamic return value is narrowed at this boundary.
    """
    Read a UTF-8 YAML file and require a mapping document.

    Parameters
    ----------
    path : pathlib.Path
        File to read; repository containment is checked separately by callers.

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
    Empty YAML resolves to None and fails the mapping requirement. Read without
    modifying the file or executing referenced automation. validate converts
    these errors into per-file diagnostics.
    """
    value: object = yaml.load(path.read_text(encoding='utf-8'), Loader=_Loader)
    return _mapping(value, 'document')


def _target(
    config: AutomationConfig,
    reference: str,
) -> Path | None:
    """
    Resolve a local or configured self-aliased automation reference.

    Parameters
    ----------
    config : AutomationConfig
        Consumer root and owner/repository aliases for this checkout.
    reference : str
        A ./ path, an aliased owner/repository/path@revision reference, or a
        reference outside the configured local forms.

    Returns
    -------
    pathlib.Path or None
        Resolved in-root YAML file, or None for a reference that is neither a
        ./ path nor a configured alias. Directory targets select exactly one
        action.yml or action.yaml file.

    Raises
    ------
    ValueError
        If an aliased reference lacks a single nonempty revision, the resolved
        path escapes root, a directory lacks exactly one action file, or the
        final target is missing or does not have a .yml/.yaml suffix.
    OSError
        If filesystem inspection or path resolution fails.

    Notes
    -----
    Resolve aliases in configuration order against the current checkout.
    Revision text is parsed but not fetched or verified, and pin/placeholder
    policy is checked separately. Do not parse the target's contents or execute
    it. validate converts these errors into per-file diagnostics.
    """
    relative: str | None = None
    if reference.startswith('./'):
        relative = reference[2:]
    else:
        for alias in config.local_repositories:
            if reference.startswith(alias + '/'):
                location, separator, revision = reference.removeprefix(
                    alias + '/',
                ).partition('@')
                if not separator or not revision or '@' in revision:
                    raise ValueError(f'invalid aliased reference: {reference}')
                relative = location
                break
    if relative is None:
        return None
    path = _inside(config.root, config.root / relative)
    if path.is_dir():
        candidates = [path / 'action.yml', path / 'action.yaml']
        existing = [p for p in candidates if p.is_file()]
        if len(existing) != 1:
            raise ValueError(f'expected one action.yml/action.yaml: {reference}')
        path = _inside(config.root, existing[0])
    if not path.is_file() or path.suffix not in ('.yml', '.yaml'):
        raise ValueError(f'missing local automation target: {reference}')
    return path


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: AutomationConfig,
    *,
    pins_only: bool = False,
) -> list[str]:
    """Report automation contract and reference-pin failures for a consumer.

    Parameters
    ----------
    config : AutomationConfig
        Consumer-owned discovery patterns, self aliases, and template
        exceptions.
    pins_only : bool, optional
        Check parsed uses values and narrowly scoped template placeholders
        only.

    Returns
    -------
    list[str]
        Per-file diagnostics for malformed YAML/JSON, missing or escaping
        targets, input mismatches, composite structure, template metadata, and
        unsafe pins. Read/decode errors become diagnostics; validation
        continues across files.

    Notes
    -----
    Never execute commands, mutate files, or query remote references. Aliased
    refs describe the current checkout, not the historical commit named by a
    caller. Expressions are not evaluated. This is not a full GitHub schema
    validator. Generic pin rules are shared with check-github-actions-pins.
    Placeholder refs are exempt only in templates with configured self aliases
    and existing targets.
    """
    failures: list[str] = []
    paths: dict[Path, str] = {}
    for kind, patterns in (
        ('workflow', config.workflow_globs),
        ('action', config.action_globs),
        ('template', config.template_globs),
        ('yaml', config.yaml_globs),
    ):
        for pattern in patterns:
            matches = sorted(p for p in config.root.glob(pattern) if p.is_file())
            if not matches:
                failures.append(f'no automation files match: {pattern}')
            for path in matches:
                if path in paths and paths[path] != kind:
                    failures.append(f'{path}: conflicting automation categories')
                else:
                    paths[path] = kind
    for path, kind in paths.items():
        try:
            _inside(config.root, path)
            data = _read(path)
            if not pins_only:
                if kind == 'action':
                    _composite(data)
                if kind == 'template':
                    _metadata(config.root, path)
            if kind == 'yaml':
                continue
            for node in _nodes(data):
                if 'uses' not in node:
                    continue
                reference = node['uses']
                if not isinstance(reference, str):
                    raise ValueError('uses must be a string')
                target = _target(config, reference)
                placeholder = (
                    kind == 'template'
                    and target is not None
                    and any(
                        reference.startswith(alias + '/')
                        for alias in config.local_repositories
                    )
                    and reference.rpartition('@')[2] in config.template_placeholder_refs
                )
                if not placeholder and not is_pinned(reference):
                    raise ValueError(
                        f'remote action must use a full commit SHA: {reference}',
                    )
                if target is not None and not pins_only:
                    doc = _read(target)
                    workflow = target.name not in ('action.yml', 'action.yaml')
                    if workflow:
                        events = _mapping(doc.get('on'), 'workflow on')
                        if 'workflow_call' not in events:
                            raise ValueError(f'target lacks workflow_call: {reference}')
                        event = events['workflow_call']
                        doc = _mapping({} if event is None else event, 'workflow_call')
                    _call(node, doc, workflow)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError, re.error) as error:
            failures.append(f'{path}: {error}')
    if not pins_only:
        for parent in sorted(
            {p.parent for p, kind in paths.items() if kind == 'template'},
        ):
            for metadata in sorted(parent.glob('*.properties.json')):
                stem = metadata.name.removesuffix('.properties.json')
                if not any(
                    (parent / (stem + ext)).is_file() for ext in ('.yml', '.yaml')
                ):
                    failures.append(f'{metadata}: orphan template metadata')
    return failures


# !SECTION
