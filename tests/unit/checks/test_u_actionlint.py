# tests/unit/checks/test_u_actionlint.py
# popo
#
# Responsibilities
# - Verify parsed-value normalization preserves scripts and YAML anchors.
#
# Maintainer Notes
# - Keep adaptation independent of tool installation and hosted execution.

"""Unit coverage for the temporary actionlint source view."""

from pathlib import Path

import pytest
import yaml

from popo.checks.actionlint import _normalize
from popo.config.automation import AutomationConfig

# SECTION: TESTS


@pytest.mark.parametrize(
    'source',
    [
        'uses: "$/actions/test"\n',
        'ref: &self $/actions/test\nuses: *self\n',
        'uses: >-\n  $/actions/test\n',
    ],
)
def test_normalization_uses_yaml_values(
    tmp_path: Path,
    source: str,
) -> None:
    """Normalize quoted, aliased, and block values without rewriting scripts."""
    action = tmp_path / 'actions/test/action.yml'
    action.parent.mkdir(parents=True)
    action.write_text('name: Test')
    script = 'run: |\n  uses: $/actions/test\n'
    normalized = _normalize(source + script, AutomationConfig(tmp_path))
    data = yaml.safe_load(normalized)
    assert data['uses'] == './actions/test'
    assert data['run'] == 'uses: $/actions/test\n'
    assert script in normalized


# !SECTION
