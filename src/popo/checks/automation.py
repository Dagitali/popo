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
    """Reject duplicate/non-string keys and retain GitHub's on key."""

    def construct_mapping(
        self,
        node: yaml.MappingNode,
        deep: bool = False,
    ) -> dict[Hashable, object]:
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
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'path escapes repository: {path}')
    return resolved


def _mapping(
    value: object,
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be a mapping')
    return cast(dict[str, object], value)


def _metadata(
    root: Path,
    path: Path,
) -> None:
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
    value: object = yaml.load(path.read_text(encoding='utf-8'), Loader=_Loader)
    return _mapping(value, 'document')


def _target(
    config: AutomationConfig,
    reference: str,
) -> Path | None:
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
