"""Load optional consumer automation contracts from pyproject.toml."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from popo.config import ConfigurationError

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class AutomationConfig:
    """
    Store consumer roots, discovery globs, and explicit self-reference policy.

    Attributes
    ----------
    root : pathlib.Path
        Resolved consumer root; inspected paths must remain inside it.
    workflow_globs, action_globs, template_globs, yaml_globs : tuple[str, ...]
        Root-relative discovery patterns. Explicit patterns must match files.
    local_repositories : tuple[str, ...]
        Owner/repository aliases resolved against this checkout, not remote refs.
    template_placeholder_refs : tuple[str, ...]
        Exact ref tokens allowed only in templates referencing existing self targets.
    configured : bool
        Whether the consumer opted in through tool.popo.automation.
    """

    root: Path
    workflow_globs: tuple[str, ...] = ('.github/workflows/*.yml',)
    action_globs: tuple[str, ...] = ()
    template_globs: tuple[str, ...] = ()
    yaml_globs: tuple[str, ...] = ()
    local_repositories: tuple[str, ...] = ()
    template_placeholder_refs: tuple[str, ...] = ()
    configured: bool = False


# !SECTION


# SECTION: FUNCTIONS


def load_automation_config(root: Path) -> AutomationConfig:
    """Load and validate automation settings without modifying any files.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root containing optional pyproject.toml.

    Returns
    -------
    AutomationConfig
        Explicit settings or portable workflow-only defaults.

    Raises
    ------
    ConfigurationError
        Invalid TOML, unknown settings, bad types, or unsafe discovery patterns.
    OSError, UnicodeError
        Unreadable or undecodable configuration.
    """
    root = root.resolve()
    path = root / 'pyproject.toml'
    try:
        document = tomllib.loads(path.read_text()) if path.is_file() else {}
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(f'{path}: invalid TOML: {error}') from error
    table: object = document
    for key in ('tool', 'popo'):
        if not isinstance(table, dict):
            raise ConfigurationError(f'{key} parent must be a TOML table')
        table = table.get(key, {})
    if not isinstance(table, dict):
        raise ConfigurationError('tool.popo must be a TOML table')
    configured = 'automation' in table
    table = table.get('automation', {})
    if not isinstance(table, dict):
        raise ConfigurationError('tool.popo.automation must be a TOML table')
    defaults = AutomationConfig(root)
    keys = (
        'workflow-globs',
        'action-globs',
        'template-globs',
        'yaml-globs',
        'local-repositories',
        'template-placeholder-refs',
    )
    if set(table) - set(keys):
        raise ConfigurationError('unknown tool.popo.automation setting')
    values: dict[str, tuple[str, ...]] = {}
    for key in keys:
        value = table.get(key, list(getattr(defaults, key.replace('-', '_'))))
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ConfigurationError(f'{key} must be an array of nonempty strings')
        strings = tuple(cast(list[str], value))
        for item in strings:
            if key.endswith('-globs') and (
                Path(item).is_absolute() or '..' in Path(item).parts
            ):
                raise ConfigurationError(f'{key} must stay inside the repository')
            if key == 'local-repositories' and (
                len(item.split('/')) != 2
                or any(
                    part in ('', '.', '..') or '@' in part for part in item.split('/')
                )
            ):
                raise ConfigurationError('local-repositories must contain owner/repo')
            if key == 'template-placeholder-refs' and any(c in item for c in '@/\n '):
                raise ConfigurationError(
                    'template placeholders must be exact ref tokens',
                )
        values[key] = strings
    return AutomationConfig(
        root,
        values['workflow-globs'],
        values['action-globs'],
        values['template-globs'],
        values['yaml-globs'],
        values['local-repositories'],
        values['template-placeholder-refs'],
        configured,
    )


# !SECTION
