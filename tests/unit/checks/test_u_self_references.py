# tests/unit/checks/test_u_self_references.py
# popo
#
# Responsibilities
# - Verify native self-reference syntax, target safety, and input contracts.
#
# Maintainer Notes
# - Keep consumer trees isolated; do not fetch or execute referenced actions.

"""Regression coverage for native same-repository automation references."""

from pathlib import Path

import pytest

from popo.checks.actions import is_pinned
from popo.checks.automation import validate
from popo.config.automation import AutomationConfig

# SECTION: TESTS


@pytest.mark.parametrize(
    'reference,inputs,message',
    [
        ('$/actions/test', 'required: value', ''),
        ('$/actions/test@main', 'required: value', 'invalid self'),
        ('$/../outside', 'required: value', 'invalid self'),
        ('$/actions/missing', 'required: value', 'missing local'),
        ('$/actions/test', 'unknown: value', 'unknown inputs'),
        ('$/actions/test', '', 'missing required input'),
        ('$/actions/escape', 'required: value', 'escapes repository'),
        ('$/', '', 'invalid self'),
    ],
)
def test_native_self_contracts(
    tmp_path: Path,
    reference: str,
    inputs: str,
    message: str,
) -> None:
    """
    Validate syntax, containment, targets, and supplied action inputs.

    Each case writes only within pytest's temporary tree. A symlink targets
    the tree's parent but never writes there. Validation leaves source intact.
    """
    action = tmp_path / 'actions/test/action.yml'
    action.parent.mkdir(parents=True)
    action.write_text(
        'name: Test\ndescription: Test\ninputs:\n'
        '  required: {required: true}\nruns:\n'
        '  using: composite\n  steps: [{run: echo ok, shell: bash}]\n',
    )
    if reference == '$/actions/escape':
        try:
            (tmp_path / 'actions/escape').symlink_to(
                tmp_path.parent,
                target_is_directory=True,
            )
        except OSError as error:
            if getattr(error, 'winerror', None) in (5, 1314):
                pytest.skip('Windows policy prevents creating test symlinks')
            raise
    workflow = tmp_path / '.github/workflows/probe.yml'
    workflow.parent.mkdir(parents=True)
    original = (
        f'jobs:\n  probe:\n    steps: [{{uses: "{reference}", with: {{{inputs}}}}}]'
    )
    workflow.write_text(original)
    failures = validate(AutomationConfig(tmp_path))
    assert bool(failures) == bool(message), failures
    if message:
        assert message in failures[0]
    assert workflow.read_text() == original


@pytest.mark.parametrize(
    'reference',
    ['$/action', '$/.github/workflows/test.yml'],
)
def test_self_references_are_same_revision_pins(
    reference: str,
) -> None:
    """Accept revision-free self paths without weakening remote pin policy."""
    assert is_pinned(reference)
    assert not is_pinned(reference + '@main')
    assert not is_pinned('upstream/action@main')


# !SECTION
