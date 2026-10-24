"""Exercise example consumers through installed Make, Git-hook and CI paths.

Use the same example with both wheel and source installations. Execute only
trusted example commands in disposable repositories; never dispatch a workflow.
"""

import os
import shlex
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: MARKS


# The example documents a POSIX shell; Windows retains the native CLI suites.
pytestmark = pytest.mark.skipif(os.name == 'nt', reason='POSIX consumer examples')


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(
    name='guardrail_tools',
    scope='module',
)
def guardrail_tools_fixture(
    installation: Installation,
    repository_root: Path,
    example_name: str,
) -> Installation:
    """
    Install the pinned hook runner alongside the artifact under test.

    Parameters
    ----------
    installation : Installation
        Wheel or sdist installed in a separate virtual environment.
    repository_root : pathlib.Path
        Checkout supplying the example's explicit pre-commit dependency pin.
    example_name : str
        Consumer whose own pinned hook runner is used.

    Returns
    -------
    Installation
        Installed tools with a controlled PATH and external hook cache.

    Raises
    ------
    AssertionError
        If installation, dependency checking, or tool discovery fails.
    OSError, UnicodeError, subprocess.TimeoutExpired
        If reading inputs or executing installation commands fails.

    Notes
    -----
    Network-dependent installation stays in the opt-in artifact layer. The
    example's Popo Git pin is replaced by the installed wheel or sdist; no
    editable checkout or Python source-path override supplies the command.
    Clear caller-controlled Make, Git and hook overrides before execution.
    """
    requirements = (
        repository_root / 'examples' / example_name / 'requirements-guardrails.txt'
    ).read_text(encoding='utf-8')
    hook_pin = next(
        line for line in requirements.splitlines() if line.startswith('pre-commit==')
    )
    result = installation.execute(
        str(installation.python),
        '-m',
        'pip',
        'install',
        hook_pin,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = installation.execute(str(installation.python), '-m', 'pip', 'check')
    assert result.returncode == 0, result.stdout + result.stderr
    environment = {
        key: value
        for key, value in installation.environment.items()
        if not key.startswith(('GIT_', 'PRE_COMMIT_'))
        and key
        not in {
            'MAKEFLAGS',
            'MFLAGS',
            'MAKELEVEL',
            'MAKEOVERRIDES',
            'MAKEFILES',
            'BASH_ENV',
            'ENV',
            'SKIP',
        }
    }
    environment.update(
        PATH=str(installation.python.parent) + os.pathsep + environment.get('PATH', ''),
        VIRTUAL_ENV=str(installation.python.parent.parent),
        PRE_COMMIT_HOME=str(installation.directory / 'hook-cache'),
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM='1',
        GIT_TERMINAL_PROMPT='0',
    )
    assert shutil.which('make', path=environment['PATH']), 'Make is required'
    assert shutil.which('git', path=environment['PATH']), 'Git is required'
    return replace(installation, environment=environment)


@pytest.fixture(
    name='entry_point',
    params=['make', 'pre-commit', 'ci'],
)
def entry_point_fixture(request: pytest.FixtureRequest) -> str:
    """
    Give each actual caller its own consumer, commands and outcome.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Selected Make, pre-commit, or CI-command scenario.

    Returns
    -------
    str
        Caller identifier used to select a trusted execution path.
    """
    return str(request.param)


# !SECTIONS


# SECTION: PROTECTED FUNCTIONS


def _run_consumer(
    tools: Installation,
    root: Path,
    entry_point: str,
) -> subprocess.CompletedProcess[str]:
    """Run the example's Make command, installed hook, or declared CI step.

    Git writes only disposable metadata. CI execution runs the checked-in
    step's literal command locally; it does not simulate GitHub's scheduler,
    token permissions, setup actions, or hosted branch protections.
    """
    if entry_point == 'make':
        return tools.execute('make', 'guardrails', directory=root)
    if entry_point == 'ci':
        workflow = yaml.safe_load(
            (root / '.github/workflows/ci.yml').read_text(encoding='utf-8'),
        )
        steps = workflow['jobs']['guardrails']['steps']
        step = next(step for step in steps if step.get('id') == 'popo')
        return tools.execute(*shlex.split(step['run']), directory=root)
    for arguments in (
        ('git', '-c', 'init.templateDir=', 'init', '--quiet'),
        ('git', 'config', 'core.autocrlf', 'false'),
        (str(tools.python), '-m', 'pre_commit', 'install'),
        ('git', 'add', '--all'),
    ):
        result = tools.execute(*arguments, directory=root, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
    assert (root / '.git/hooks/pre-commit').is_file()
    return tools.execute(
        'git',
        '-c',
        'user.name=Popo Test',
        '-c',
        'user.email=popo@example.invalid',
        '-c',
        'commit.gpgsign=false',
        'commit',
        '-m',
        'test: exercise guardrails',
        directory=root,
        timeout=60,
    )


def _consumer_sources(root: Path) -> dict[Path, bytes]:
    """
    Compare consumer source bytes separately from disposable Git metadata.
    """
    return {
        path: value
        for path, value in snapshot_files(root).items()
        if '.git' not in path.parts
    }


# !SECTION


# SECTION: TESTS


class TestExampleAdoption:
    """
    Prove shared policy executes and reports drift without rewriting files.
    """

    def test_entry_points(
        self,
        guardrail_tools: Installation,
        example_consumer: Path,
        entry_point: str,
    ) -> None:
        """
        Run the same profile from Make, an installed hook and the CI step.
        """
        original = snapshot_files(example_consumer)
        result = _run_consumer(guardrail_tools, example_consumer, entry_point)
        assert result.returncode == 0, result.stdout + result.stderr
        output = result.stdout + result.stderr
        assert 'PASS: all configured repository checks passed' in output
        assert _consumer_sources(example_consumer) == original

    def test_policy_failure(
        self,
        guardrail_tools: Installation,
        example_consumer: Path,
        entry_point: str,
    ) -> None:
        """A real documentation failure must fail every caller's execution."""
        readme = example_consumer / 'README.md'
        readme.write_text(
            readme.read_text(encoding='utf-8') + '\n[Missing](absent.md)\n',
            encoding='utf-8',
        )
        original = snapshot_files(example_consumer)
        result = _run_consumer(guardrail_tools, example_consumer, entry_point)
        assert result.returncode != 0, result.stdout + result.stderr
        assert 'local target does not exist: absent.md' in result.stdout + result.stderr
        assert _consumer_sources(example_consumer) == original

    @pytest.mark.parametrize('entry_point', ['make', 'pre-commit'])
    def test_detect_drift(
        self,
        guardrail_tools: Installation,
        example_consumer: Path,
        entry_point: str,
        example_drift: str,
    ) -> None:
        """
        Inspect one entry-point mismatch through independent real callers.
        """
        original = snapshot_files(example_consumer)
        result = _run_consumer(guardrail_tools, example_consumer, entry_point)
        assert result.returncode != 0, result.stdout + result.stderr
        assert example_drift in result.stdout + result.stderr
        assert _consumer_sources(example_consumer) == original


# !SECTION
