"""
:mod:`tests.e2e.test_e_distribution_installation` module.

Exercise installed commands outside the checkout in clean environments.
"""

import json
from pathlib import Path

import pytest
from packaging.utils import parse_sdist_filename, parse_wheel_filename
from packaging.version import Version

from popo.config.guardrails import GuardrailsConfig
from tests.support.files import snapshot_files
from tests.support.installation import Installation
from tests.support.inventory import repository

# SECTION: FIXTURES


@pytest.fixture(
    name='use_module',
    params=[False, True],
    ids=['console', 'module'],
)
def use_module_fixture(
    request: pytest.FixtureRequest,
) -> bool:
    """Exercise both installed entry points with independent inputs."""
    return bool(request.param)


@pytest.fixture(
    name='artifact_version',
    scope='module',
)
def artifact_version_fixture(
    artifact: Path,
) -> Version:
    """Read the expected version from a validated wheel or sdist filename."""
    if artifact.suffix == '.whl':
        return parse_wheel_filename(artifact.name)[1]
    return parse_sdist_filename(artifact.name)[1]


# !SECTION


# SECTION: TESTS


class TestInstalledCLI:
    """
    Exercise every artifact through independent public CLI scenarios.

    Notes
    -----
    Each artifact has a module-scoped installation, while consumer inputs use
    per-test temporary directories. Exercise both console and module entry
    points, exit statuses, output channels, and read-only checker behavior.
    """

    @pytest.mark.parametrize('format_', ['json', 'spdx'])
    def test_source_inventory(
        self,
        installation: Installation,
        tmp_path: Path,
        use_module: bool,
        format_: str,
    ) -> None:
        """
        Inventory committed bytes through installed console and module commands.

        Parameters
        ----------
        installation : Installation
            Isolated wheel or sdist installation outside the checkout.
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        use_module : bool
            Whether to invoke the module instead of the console executable.
        format_ : str
            Selected plain JSON or source-only SPDX representation.
        """
        commit = repository(tmp_path)
        before = snapshot_files(tmp_path)
        result = installation.run(
            'source-inventory',
            '--root',
            str(tmp_path),
            '--revision',
            'fixture-tag',
            '--name',
            'Consumer',
            '--format',
            format_,
            module=use_module,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert len(report['files']) == 2
        assert (
            report.get('revision') == commit
            if format_ == 'json'
            else report['spdxVersion'] == 'SPDX-2.3'
        )
        assert result.stderr == ''
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        ('reference', 'status'),
        [('upstream/action@main', 1), ('upstream/action@' + 'a' * 40, 0)],
        ids=['mutable', 'pinned'],
    )
    def test_automation_contracts(
        self,
        installation: Installation,
        tmp_path: Path,
        use_module: bool,
        reference: str,
        status: int,
    ) -> None:
        """
        Verify installed automation checking reports pins without rewriting
        inputs.

        Parameters
        ----------
        installation : Installation
            Installed artifact isolated from checkout imports.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        reference : str
            Remote reference selected for the pin-validation scenario.
        status : int
            Expected installed CLI exit status.
        use_module : bool
            Whether to invoke python -m popo rather than the console-script
            entry point.
        """
        (tmp_path / 'pyproject.toml').write_text(
            '[tool.popo.automation]\nworkflow-globs = ["ci.yml"]',
            encoding='utf-8',
        )
        workflow = tmp_path / 'ci.yml'
        source = f'jobs: {{test: {{steps: [{{uses: {reference}}}]}}}}'
        workflow.write_text(source, encoding='utf-8')
        result = installation.run(
            'check-automation-contracts',
            '--root',
            str(tmp_path),
            module=use_module,
        )
        assert result.returncode == status, result.stdout + result.stderr
        assert not result.stderr
        assert workflow.read_text(encoding='utf-8') == source

    @pytest.mark.parametrize(
        'argument',
        ['--help', '--version'],
    )
    def test_information_commands(
        self,
        installation: Installation,
        artifact_version: Version,
        argument: str,
        use_module: bool,
    ) -> None:
        """
        Verify help and version output through console and module entry points.

        Parameters
        ----------
        installation : Installation
            Installed artifact isolated from checkout imports.
        artifact_version : packaging.version.Version
            Expected artifact version, independent of source-import fallbacks.
        argument : str
            Information option to exercise, either --help or --version.
        use_module : bool
            Whether to invoke python -m popo rather than the console-script
            entry point.
        """
        result = installation.run(argument, module=use_module)
        assert result.returncode == 0, result.stderr
        if argument == '--help':
            assert 'check-all' in result.stdout
        else:
            assert Version(result.stdout.split()[-1]) == artifact_version
        assert not result.stderr

    @pytest.mark.parametrize(
        ('content', 'status', 'message'),
        [
            ('# Consumer\n', 0, 'PASS:'),
            ('[missing](missing.md)\n', 1, 'FAIL:'),
            ('[Text][missing]\n', 1, 'undefined reference:'),
            ('![Image](missing.png)\n', 1, 'local target does not exist:'),
        ],
        ids=['valid-project', 'broken-link', 'undefined-reference', 'missing-image'],
    )
    def test_checks_consumer(
        self,
        installation: Installation,
        tmp_path: Path,
        use_module: bool,
        content: str,
        status: int,
        message: str,
    ) -> None:
        """
        Verify installed Markdown checks report status and preserve consumer
        files.

        Parameters
        ----------
        installation : Installation
            Installed artifact isolated from checkout imports.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        use_module : bool
            Select the installed module instead of the console script.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        status : int
            Expected process or CLI exit status.
        message : str
            Expected standard-output substring for the supplied exit status.
        """
        readme = tmp_path / 'README.md'
        readme.write_text(content, encoding='utf-8')
        result = installation.run(
            'check-docs',
            '--root',
            str(tmp_path),
            module=use_module,
        )
        assert result.returncode == status, result.stderr
        assert message in result.stdout
        assert not result.stderr
        assert readme.read_text(encoding='utf-8') == content

    @pytest.mark.parametrize('valid', [True, False], ids=['passing', 'failing'])
    @pytest.mark.parametrize(
        'command',
        ['check-required-files', 'check-file-headers'],
    )
    def test_installed_file_policies(
        self,
        installation: Installation,
        tmp_path: Path,
        command: str,
        use_module: bool,
        valid: bool,
    ) -> None:
        """
        Verify opt-in file commands through installed package entry points.

        Parameters
        ----------
        installation : Installation
            Wheel or sdist installed outside the source checkout.
        tmp_path : pathlib.Path
            Disposable consumer with one passing or failing policy scenario.
        command : str
            Public file-policy subcommand to exercise.
        use_module : bool
            Select the installed module instead of the console script.
        valid : bool
            Whether this consumer satisfies the selected file-policy check.
        """
        metadata = tmp_path / 'pyproject.toml'
        metadata.write_text(
            """[tool.popo.files]
required = ["required.txt"]
[tool.popo.headers]
project = "Sample"
notice = "Copyright"
[[tool.popo.headers.rules]]
patterns = ["*"]
format = "raw"
prefix = "HEADER"
purpose-required = false
[[tool.popo.headers.exceptions]]
patterns = ["pyproject.toml"]
reason = "Synthetic policy fixture"
""",
            encoding='utf-8',
        )
        source = tmp_path / 'required.txt'
        if valid or command == 'check-file-headers':
            source.write_text('HEADER' if valid else 'INVALID', encoding='utf-8')
        original = snapshot_files(tmp_path)
        result = installation.run(command, '--root', str(tmp_path), module=use_module)
        assert result.returncode == (0 if valid else 1), result.stdout + result.stderr
        assert ('PASS:' if valid else 'FAIL:') in result.stdout
        assert result.stderr == ''
        assert snapshot_files(tmp_path) == original


class TestInstalledSelection:
    """
    Verify language-neutral plans through isolated installed entry points.
    """

    @pytest.mark.parametrize('valid', [True, False], ids=['passing', 'failing'])
    def test_standalone_profile(
        self,
        installation: Installation,
        tmp_path: Path,
        use_module: bool,
        valid: bool,
    ) -> None:
        """
        Select docs without Python metadata and preserve the consumer bytes.
        """
        policy = tmp_path / 'popo.toml'
        policy.write_text('[profiles.docs]\nchecks=["check-docs"]\n', encoding='utf-8')
        readme = tmp_path / 'README.md'
        readme.write_text(
            '# Consumer' if valid else '[missing](absent)',
            encoding='utf-8',
        )
        original = snapshot_files(tmp_path)
        arguments = ['--root', str(tmp_path), '--profile', 'docs', '--format', 'json']
        explanation = installation.run('explain', *arguments, module=use_module)
        assert explanation.returncode == 0, explanation.stdout + explanation.stderr
        assert explanation.stderr == ''
        assert json.loads(explanation.stdout)['checks'] == ['check-docs']
        result = installation.run('check-all', *arguments, module=use_module)
        assert result.returncode == int(not valid), result.stdout + result.stderr
        assert result.stderr == ''
        report = json.loads(result.stdout)
        assert report['schema_version'] == 1
        assert report['passed'] is valid
        assert report['checks'][0]['check'] == 'check-docs'
        assert snapshot_files(tmp_path) == original

    def test_guardrail_contract(
        self,
        installation: Installation,
        guardrail_consumer: GuardrailsConfig,
        guardrail_failure: str | None,
        guardrail_arguments: tuple[str, ...],
        use_module: bool,
    ) -> None:
        """Inspect profile wiring from installed packages without running Make.

        Each command and matching/Make/hook/workflow scenario owns a fresh
        consumer, including the exact profile delegated to Make. Preserve all
        consumer bytes and assert the specific diagnostic from each artifact.
        """
        root = guardrail_consumer.root
        original = snapshot_files(root)
        result = installation.run(
            *guardrail_arguments,
            '--root',
            str(root),
            '--format',
            'json',
            module=use_module,
        )
        assert result.returncode == int(guardrail_failure is not None), (
            result.stdout + result.stderr
        )
        assert result.stderr == ''
        report = json.loads(result.stdout)
        assert report['passed'] is (guardrail_failure is None)
        checks = report['checks']
        assert [check['check'] for check in checks] == (
            ['check-docs', 'check-guardrail-parity']
            if '--profile' in guardrail_arguments
            else ['check-guardrail-parity']
        )
        assert all(check['passed'] for check in checks[:-1])
        assert checks[-1]['passed'] is (guardrail_failure is None)
        assert checks[-1]['diagnostics'] == (
            []
            if guardrail_failure is None
            else [
                {
                    'severity': 'error',
                    'message': guardrail_failure,
                },
            ]
        )
        assert snapshot_files(root) == original


# !SECTION
