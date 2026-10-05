# src/popo/checks/actionlint.py
# popo
#
# Responsibilities
# - Run actionlint against a disposable same-repository compatibility view.
#
# Maintainer Notes
# - Never execute workflow commands or change consumer source files.
# - Preserve validator diagnostics and exit statuses, including tool failures.

"""Adapt self-repository references for actionlint without hiding errors."""

import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from ..config.automation import AutomationConfig, load_automation_config
from .automation import _inside, _nodes, _read, _target

# SECTION: PROTECTED FUNCTIONS


def _normalize(
    source: str,
    config: AutomationConfig,
) -> str:
    """
    Rewrite self uses values, retaining other source and duplicate keys.

    YAML node marks identify real mapping values, not text inside run scripts.
    Targets are resolved through native contract validation; errors propagate.
    """
    pending = [yaml.compose(source, Loader=yaml.SafeLoader)]
    seen: set[int] = set()
    changes: dict[tuple[int, int], str] = {}
    while pending:
        node = pending.pop()
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                if (
                    isinstance(key, yaml.ScalarNode)
                    and key.value == 'uses'
                    and isinstance(value, yaml.ScalarNode)
                    and value.value.startswith('$/')
                ):
                    target = _target(config, value.value)
                    assert target is not None
                    location = (
                        target.parent
                        if target.name
                        in (
                            'action.yml',
                            'action.yaml',
                        )
                        else target
                    )
                    replacement = './' + location.relative_to(config.root).as_posix()
                    start, end = value.start_mark.index, value.end_mark.index
                    # Aliases share their defining node; retain its anchor.
                    anchor = re.match(r'&[^\s]+\s+', source[start:end])
                    fragment = source[start:end]
                    # Preserve consumed block-scalar line breaks and locations.
                    padding = (
                        '\n' * fragment.count('\n') if fragment.endswith('\n') else ''
                    )
                    changes[start, end] = (
                        (anchor[0] if anchor else '')
                        + json.dumps(replacement)
                        + padding
                    )
                pending.extend((key, value))
        elif isinstance(node, yaml.SequenceNode):
            pending.extend(node.value)
    for (start, end), replacement in sorted(changes.items(), reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


# !SECTION


# SECTION: FUNCTIONS


def run(
    root: Path,
    paths: list[str],
    command: str = 'actionlint',
) -> int:
    """
    Run actionlint in a disposable normalized automation tree.

    Parameters
    ----------
    root : pathlib.Path
        Consumer repository; selected files and local targets must stay inside.
    paths : list[str]
        Workflow paths relative to root, or absolute paths inside root. Empty
        selects configured workflow and template globs.
    command : str, optional
        Maintainer-selected actionlint executable and options, shell-split
        without executing a shell. Tools are never installed automatically.

    Returns
    -------
    int
        Exact validator exit status. Both streams retain diagnostics with
        temporary paths mapped back to source locations.

    Raises
    ------
    ValueError
        Empty command, missing files, unsafe references, or duplicate keys.
    OSError, UnicodeError, yaml.YAMLError
        Source reads, temporary-file operations, process launch, or YAML fail.

    Notes
    -----
    Copy only selected automation and local targets, never environments or
    arbitrary repository files. Cleanup occurs on success and failure. This
    Run the linter, not workflow code or a substitute contract checker.
    """
    root = root.resolve()
    config = load_automation_config(root)
    selected = (
        [root / path for path in paths]
        if paths
        else [
            path
            for pattern in (*config.workflow_globs, *config.template_globs)
            for path in sorted(root.glob(pattern))
            if path.is_file()
        ]
    )
    if not selected:
        raise ValueError('no workflows selected for actionlint')
    selected = [_inside(root, path) for path in selected]
    command_parts = shlex.split(command)
    if not command_parts:
        raise ValueError('actionlint command must not be empty')
    if '/' in command_parts[0]:
        # Keep venv symlinks intact when making executable paths absolute.
        command_parts[0] = str(Path(command_parts[0]).absolute())
    sources: dict[Path, str] = {}
    # Retain implicit consumer runner-label and ignore configuration.
    for name in ('actionlint.yaml', 'actionlint.yml'):
        path = root / '.github' / name
        if path.is_file():
            path = _inside(root, path)
            sources[path] = path.read_text(encoding='utf-8')
    pending = list(selected)
    while pending:
        path = pending.pop()
        if path in sources:
            continue
        data = _read(path)
        sources[path] = _normalize(path.read_text(encoding='utf-8'), config)
        for node in _nodes(data):
            reference = node.get('uses')
            if isinstance(reference, str):
                target = _target(config, reference)
                if target is not None:
                    pending.append(target)
    with tempfile.TemporaryDirectory(prefix='popo-actionlint-') as directory:
        mirror = Path(directory)
        for path, source in sources.items():
            destination = mirror / path.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(source, encoding='utf-8')
        result: subprocess.CompletedProcess[str] = subprocess.run(
            command_parts + [str(path.relative_to(root)) for path in selected],
            cwd=mirror,
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout.replace(str(mirror), str(root)), end='')
        print(result.stderr.replace(str(mirror), str(root)), end='', file=sys.stderr)
        return result.returncode


# !SECTION
