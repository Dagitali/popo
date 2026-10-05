# tests/integration/test_i_actionlint.py
# popo
#
# Responsibilities
# - Exercise actionlint compatibility dispatch and unchanged tool failures.
#
# Maintainer Notes
# - Use a deterministic fake linter; no installations or network requests.

"""Public CLI integration for actionlint's disposable compatibility view."""

import shlex
import sys
from pathlib import Path

import pytest

from popo.cli import main

# SECTION: TESTS


@pytest.mark.parametrize('status', [0, 17])
def test_actionlint_compatibility(
    tmp_path: Path,
    status: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Preserve both streams, validator status, and source self references."""
    action = tmp_path / 'actions/test/action.yml'
    action.parent.mkdir(parents=True)
    action.write_text('name: Test\ndescription: Test\nruns: {using: node24}')
    workflow = tmp_path / '.github/workflows/probe.yml'
    workflow.parent.mkdir(parents=True)
    original = 'jobs: {probe: {steps: [{uses: "$/actions/test"}]}}\n'
    workflow.write_text(original)
    code = (
        'import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
        'text=p.read_text(); assert "$/" not in text; '
        'assert pathlib.Path("actions/test/action.yml").is_file(); '
        'print(p.resolve()); print("stderr", file=sys.stderr); '
        f'sys.exit({status})'
    )
    command = shlex.join([sys.executable, '-c', code])
    assert (
        main(
            [
                'check-actionlint',
                '--root',
                str(tmp_path),
                '--actionlint',
                command,
                str(workflow),
            ],
        )
        == status
    )
    streams = capsys.readouterr()
    assert str(workflow) in streams.out
    assert streams.err == 'stderr\n'
    assert workflow.read_text() == original


@pytest.mark.parametrize(
    'source,expected',
    [
        ('uses: "$/actions/test@main"', 'invalid self-repository'),
        ('uses: "$/actions/missing"', 'missing local'),
        ('uses: "$/../outside"', 'invalid self-repository'),
        ('uses: one\nuses: two', 'duplicate YAML key'),
    ],
)
def test_actionlint_rejects_invalid_source(
    tmp_path: Path,
    source: str,
    expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject unsafe source before launching even a nonexistent executable."""
    workflow = tmp_path / '.github/workflows/probe.yml'
    workflow.parent.mkdir(parents=True)
    workflow.write_text(source)
    assert (
        main(
            [
                'check-actionlint',
                '--root',
                str(tmp_path),
                '--actionlint',
                'nonexistent-actionlint',
            ],
        )
        == 1
    )
    assert expected in capsys.readouterr().out


# !SECTION
