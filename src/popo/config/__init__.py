"""
:mod:`popo.config` package.

Configuration models and loaders, exported from their policy modules.
"""

from ._common import ConfigurationError
from .automation import AutomationConfig, load_automation_config
from .dependencies import DependencyConfig, DependencyMode
from .project import ProjectConfig, load_config
from .python_policy import PythonPolicyConfig

# SECTION: EXPORTS / PACKAGE API


__all__ = [
    # Data Classes
    'AutomationConfig',
    'DependencyConfig',
    'ProjectConfig',
    'PythonPolicyConfig',
    # Errors
    'ConfigurationError',
    # Functions
    'load_automation_config',
    'load_config',
    # Type Aliases
    'DependencyMode',
]


# !SECTION
