# tests/unit/checks/test_u_self_references.py
# popo
#
# Responsibilities
# - Verify native self-reference syntax, target safety, and input contracts.
#
# Maintainer Notes
# - Keep consumer trees isolated; do not fetch or execute referenced actions.

"""
:mod:`tests.unit.checks.test_u_self_references` module.

Regression coverage for native same-repository automation references.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.checks.actions import is_pinned
from popo.checks.automation import validate
from popo.config.automation import AutomationConfig
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestSelfReferences:
    """Group isolated regression scenarios for self references."""

    @pytest.mark.parametrize(
        ('reference', 'inputs', 'message'),
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
        self,
        tmp_path: Path,
        write_file: FileWriter,
        symlink: Callable[[Path, Path], None],
        reference: str,
        inputs: str,
        message: str,
    ) -> None:
        """
        Validate syntax, containment, targets, and supplied action inputs.

        Each case writes only within pytest's temporary tree. A symlink targets
        the tree's parent but never writes there. Validation leaves source
        intact.
        """
        write_file(
            'actions/test/action.yml',
            'name: Test\ndescription: Test\ninputs:\n'
            '  required: {required: true}\nruns:\n'
            '  using: composite\n  steps: [{run: echo ok, shell: bash}]\n',
        )
        if reference == '$/actions/escape':
            symlink(tmp_path / 'actions/escape', tmp_path.parent)
        original = (
            f'jobs:\n  probe:\n    steps: [{{uses: "{reference}", with: {{{inputs}}}}}]'
        )
        write_file('.github/workflows/probe.yml', original)
        before = snapshot_files(tmp_path)
        failures = validate(AutomationConfig(tmp_path))
        assert bool(failures) == bool(message), failures
        if message:
            assert message in failures[0]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'reference',
        ['$/action', '$/.github/workflows/test.yml'],
    )
    def test_self_references_are_same_revision_pins(
        self,
        reference: str,
    ) -> None:
        """
        Accept revision-free self paths without weakening remote pin policy.
        """
        assert is_pinned(reference)
        assert not is_pinned(reference + '@main')
        assert not is_pinned('upstream/action@main')


# !SECTION
