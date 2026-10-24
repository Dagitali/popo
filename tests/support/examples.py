"""Copy maintained consumers without changing their source examples."""

import shutil
from pathlib import Path

import pytest

# SECTION: FIXTURES


@pytest.fixture(
    name='example_name',
    scope='module',
    params=['swift', 'python', 'cdk'],
)
def example_name_fixture(
    request: pytest.FixtureRequest,
) -> str:
    """Select a self-contained Swift, Python, or Python CDK consumer."""
    return str(request.param)


@pytest.fixture(name='example_checks')
def example_checks_fixture(
    example_name: str,
) -> tuple[str, ...]:
    """Describe the shared checks and intentional Python-specific additions."""
    python_checks = (
        ('check-dependency-boundaries', 'check-python-policy')
        if example_name != 'swift'
        else ()
    )
    return (
        'check-docs',
        'check-required-files',
        'check-github-actions-pins',
        *python_checks,
        'check-guardrail-parity',
    )


@pytest.fixture(name='example_consumer')
def example_consumer_fixture(
    repository_root: Path,
    tmp_path: Path,
    example_name: str,
) -> Path:
    """
    Provide an independent copy of every example input, including dot-files.

    Parameters
    ----------
    repository_root : pathlib.Path
        Checkout containing the maintained example.
    tmp_path : pathlib.Path
        Per-test temporary directory outside the example.
    example_name : str
        Consumer type selected independently for each example.

    Returns
    -------
    pathlib.Path
        Consumer root with no inherited Git metadata or generated environments.

    Raises
    ------
    OSError
        If copying the example fails.
    """
    source = repository_root / 'examples' / example_name
    # Exclude local Git, Python and application state when copying the example.
    return Path(
        shutil.copytree(
            source,
            tmp_path / 'consumer',
            ignore=shutil.ignore_patterns(
                '.git',
                '.venv',
                '.build',
                '.swiftpm',
                '__pycache__',
                '*.egg-info',
                'build',
                'dist',
                'cdk.out',
            ),
        ),
    )


@pytest.fixture(
    name='example_drift',
    params=[
        (
            'Makefile',
            '\tpopo check-all --profile guardrails',
            '\tpopo check-all --profile guardrails\n\t@echo unexpected',
            'guardrails recipe must be exactly',
        ),
        (
            '.pre-commit-config.yaml',
            '        entry: make guardrails',
            '        entry: make guardrails\n        args: [unexpected]',
            'popo must be one local system hook',
        ),
        (
            '.github/workflows/ci.yml',
            'run: make guardrails',
            'run: make another-target',
            'must run make guardrails',
        ),
        (
            '.github/workflows/ci.yml',
            '    runs-on: ubuntu-latest',
            '    runs-on: ubuntu-latest\n    defaults:\n'
            '      run:\n        working-directory: Sources',
            'guardrail invocation must use the repository root',
        ),
    ],
    ids=['make-recipe', 'hook-arguments', 'ci-command', 'working-directory'],
)
def example_drift_fixture(
    request: pytest.FixtureRequest,
    example_consumer: Path,
) -> str:
    """
    Change one real entry point and supply its expected failure text.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Input filename, original text, replacement, and expected diagnostic.
    example_consumer : pathlib.Path
        Independent copy of the maintained consumer example.

    Returns
    -------
    str
        Diagnostic substring expected from the parity checker.

    Raises
    ------
    AssertionError
        If the maintained example no longer has exactly one mutation target.
    OSError, UnicodeError
        If reading or writing the disposable input fails.

    Notes
    -----
    Mutations are independent from validation. Both deterministic integration
    tests and installed tool execution use these isolated consumer scenarios.
    """
    filename, before, after, diagnostic = request.param
    path = example_consumer / filename
    source = path.read_text(encoding='utf-8')
    assert source.count(before) == 1
    path.write_text(source.replace(before, after), encoding='utf-8')
    return str(diagnostic)


# !SECTION
