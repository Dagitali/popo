"""
:mod:`popo.config.automation` module.

Load optional consumer automation contracts from the selected policy file.
"""

from dataclasses import dataclass
from pathlib import Path

from ._common import ConfigurationError, read_popo, read_strings, require_table

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
        Owner/repository aliases resolved against this checkout, not remote
        refs.
    template_placeholder_refs : tuple[str, ...]
        Exact ref tokens without whitespace, @ or /, allowed only in templates
        referencing existing self targets.
    configured : bool
        Whether the selected policy source contains an automation table.
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


def load_automation_config(
    root: Path,
) -> AutomationConfig:
    """Load and validate automation settings without modifying any files.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root containing optional standalone (e.g., popo.toml) or
        Python-based (i.e., pyproject.toml) policy.

    Returns
    -------
    AutomationConfig
        Explicit settings or portable workflow-only defaults.

    Raises
    ------
    ConfigurationError
        Invalid TOML, unknown settings, bad types, or unsafe discovery
        patterns.
    OSError, UnicodeError
        Unreadable or undecodable configuration.
    """
    root = root.resolve()
    popo = read_popo(root)
    configured = 'automation' in popo
    table = require_table(popo.get('automation', {}), name='tool.popo.automation')
    defaults = AutomationConfig(root)
    keys = (
        'workflow-globs',
        'action-globs',
        'template-globs',
        'yaml-globs',
        'local-repositories',
        'template-placeholder-refs',
    )
    if table.keys() - set(keys):
        raise ConfigurationError('unknown tool.popo.automation setting')
    values: dict[str, tuple[str, ...]] = {}
    for key in keys:
        value = table.get(key, list(getattr(defaults, key.replace('-', '_'))))
        strings = read_strings(value, key, unique=False)
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
            if key == 'template-placeholder-refs' and any(
                character in '@/' or character.isspace() for character in item
            ):
                raise ConfigurationError(
                    'template placeholders must be exact ref tokens',
                )
        values[key] = strings
    return AutomationConfig(
        root=root,
        workflow_globs=values['workflow-globs'],
        action_globs=values['action-globs'],
        template_globs=values['template-globs'],
        yaml_globs=values['yaml-globs'],
        local_repositories=values['local-repositories'],
        template_placeholder_refs=values['template-placeholder-refs'],
        configured=configured,
    )


# !SECTION
