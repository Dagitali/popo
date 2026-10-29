"""
:mod:`tests.unit.checks.test_u_python_policy` module.

Test Python-version consistency and workflow matrix resolution.
"""

from dataclasses import replace
from pathlib import Path
from typing import Literal
from unittest.mock import patch

import pytest

from popo.checks.python_policy import _workflow_observations, validate
from popo.config import PythonPolicyConfig
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture
def policy(
    tmp_path: Path,
    write_file: FileWriter,
) -> PythonPolicyConfig:
    """
    Prepare consistent Python-policy inputs for an isolated test.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Consumer root for temporary metadata, version file, and workflow.
    write_file : tests.support.files.FileWriter
        Helper creating the UTF-8 policy input files.

    Returns
    -------
    PythonPolicyConfig
        Python >=3.13,<3.15 policy with preferred version 3.13, Ruff target
        py313, and mypy version 3.13, pointing to the prepared input files.

    Raises
    ------
    OSError, UnicodeError
        If writing a fixture file fails.

    Notes
    -----
    Individual scenarios modify only the relevant input or replace a model
    field. Creating the fixture does not run the policy validator or contact
    services.
    """
    metadata = write_file(
        'pyproject.toml',
        '[project]\nrequires-python = ">=3.13,<3.15"\n'
        '[tool.mypy]\npython_version = "3.13"\n'
        '[tool.ruff]\ntarget-version = "py313"\n',
    )
    version = write_file('.python-version', '3.13\n')
    workflow = write_file('.github/workflows/ci.yml', 'python-version: "3.13"\n')
    return PythonPolicyConfig(
        metadata,
        '>=3.13,<3.15',
        '3.13',
        version,
        metadata,
        'py313',
        '3.13',
        workflow.parent,
    )


@pytest.fixture(params=['${{ env.MISSING }}', '${{ matrix.missing }}'])
def unresolved_reference(
    request: pytest.FixtureRequest,
) -> str:
    """
    Supply recognized version references with no matching declaration.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest request carrying the selected fixture parameter.

    Returns
    -------
    str
        Workflow expression selected for the unresolved-reference scenario.
    """
    return str(request.param)


# !SECTION


# SECTION: TESTS


class TestPythonPolicy:
    """
    Validate policy consistency and supported workflow version declarations.

    Notes
    -----
    Start from consistent temporary policy files, then vary one declaration or
    configuration field. Supply explicit checker-runtime versions to keep
    results independent of the interpreter executing the tests.
    """

    @pytest.mark.parametrize(
        'dimension',
        ['python-version', 'python'],
    )
    @pytest.mark.parametrize(
        'version',
        ['3.14', '3.12', 'banana'],
    )
    def test_block_matrix_versions(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        dimension: str,
        version: str,
    ) -> None:
        """
        Resolve every block-list item, including quoted values with comments.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        dimension : str
            Workflow matrix key used to resolve the setup-python version
            expression.
        version : str
            Candidate interpreter or workflow version selected for policy
            validation.
        """
        path = write_file(
            '.github/workflows/ci.yml',
            'jobs:\n  check:\n    strategy:\n      matrix:\n'
            f'        {dimension}:\n'
            '          - "3.13" # minimum\n'
            f"          - '{version}' # candidate\n"
            '    steps:\n'
            f'      - uses: actions/setup-python@{'a' * 40}\n'
            '        with:\n'
            f'          python-version: ${{{{ matrix.{dimension} }}}}\n',
        )
        assert validate(policy, running_version='3.13') == (
            []
            if version == '3.14'
            else [f'{path}: unsupported Python version {version!r}']
        )

    @pytest.mark.parametrize(
        'version,supported',
        [
            ('3.12', False),
            ('3.13', True),
            ('3.14', True),
            ('3.15', False),
            ('4.0', False),
        ],
    )
    def test_checker_runtime_policy(
        self,
        policy: PythonPolicyConfig,
        version: str,
        supported: bool,
    ) -> None:
        """
        Accept supported runtimes and report exact out-of-policy diagnostics.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        version : str
            Explicit runtime at, within or outside the configured bounds.
        supported : bool
            Whether this runtime belongs to the declared supported range.
        """
        before = snapshot_files(policy.metadata.parent)
        assert validate(policy, running_version=version) == (
            []
            if supported
            else [
                f'checker runtime: Python {policy.requires_python} is required; '
                f'received {version}',
            ]
        )
        assert snapshot_files(policy.metadata.parent) == before

    @pytest.mark.parametrize(
        ('path', 'content', 'message'),
        [
            ('pyproject.toml', '[', 'invalid TOML'),
            ('pyproject.toml', 'project = []\ntool = []', 'project.requires-python'),
            ('.python-version', '3.12', "expected '3.13'"),
        ],
    )
    def test_inconsistent_files(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        path: str,
        content: str,
        message: str,
    ) -> None:
        """
        Verify inconsistent files.

        Verify changed policy inputs produce the expected inconsistency
        diagnostic.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        path : str
            Repository-relative path whose contents are prepared for the
            scenario.
        content : str
            Replacement contents introducing a policy inconsistency or
            malformed configuration.
        message : str
            Expected substring in at least one reported policy diagnostic.
        """
        write_file(path, content)
        assert any(
            message in failure for failure in validate(policy, running_version='3.13')
        )

    def test_invalid_specifier(
        self,
        policy: PythonPolicyConfig,
    ) -> None:
        """
        Verify invalid specifier.

        Verify an invalid configured Python requirement becomes a policy
        diagnostic.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        """
        assert (
            'invalid requires-python policy'
            in validate(replace(policy, requires_python='invalid'))[0]
        )

    @pytest.mark.parametrize(
        'field',
        ['metadata', 'ruff_config', 'python_version_file', 'workflow_directory'],
    )
    def test_missing_inputs(
        self,
        policy: PythonPolicyConfig,
        tmp_path: Path,
        field: str,
    ) -> None:
        """
        Verify each missing Python-policy input is reported.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        field : str
            Configuration path field replaced with a missing input.
        """
        config = replace(policy, **{field: tmp_path / 'missing'})
        assert any(
            'does not exist' in f for f in validate(config, running_version='3.13')
        )

    @pytest.mark.parametrize(
        ('target', 'valid'),
        [('py313', True), ('py312', False)],
    )
    def test_separate_ruff_configuration(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        target: str,
        valid: bool,
    ) -> None:
        """
        Verify separate ruff configuration.

        Verify top-level settings in a separate Ruff file match the policy
        target.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        target : str
            Ruff target-version text written to the separate configuration
            file.
        valid : bool
            Whether the candidate Ruff target should satisfy the configured
            policy.
        """
        path = write_file('ruff.toml', f'target-version = "{target}"')
        failures = validate(replace(policy, ruff_config=path), running_version='3.13')
        assert (failures == []) is valid
        if not valid:
            assert 'Ruff target-version' in failures[0]

    @pytest.mark.parametrize(
        'declaration',
        [
            '',
            'python-version: ${{ env.MISSING }}',
            'python-version: ${{ matrix.missing }}',
        ],
        ids=['absent', 'unknown-environment', 'unknown-matrix'],
    )
    def test_setup_requires_resolvable_version(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        declaration: str,
    ) -> None:
        """
        Verify setup-python requires a resolvable explicit version declaration.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        declaration : str
            Workflow version declaration or expression selected for resolution.
        """
        path = write_file(
            '.github/workflows/ci.yml',
            f'uses: actions/setup-python@{'a' * 40}\n{declaration}',
        )
        reference = declaration.removeprefix('python-version: ')
        message = (
            f'unsupported Python version {reference!r}'
            if declaration
            else 'setup-python requires an explicit version'
        )
        assert validate(policy, running_version='3.13') == [f'{path}: {message}']

    @pytest.mark.parametrize(
        'declaration',
        [
            pytest.param('python-version: "3.13"', id='literal'),
            pytest.param("python-version: '3.14' # supported", id='comment'),
            pytest.param(
                'env:\n  PYTHON_VERSION: "3.13"\n'
                'python-version: ${{ env.PYTHON_VERSION }}',
                id='environment',
            ),
            pytest.param(
                "python-version: ['3.13', '3.14']\n"
                'python-version: ${{ matrix.python-version }}',
                id='matrix',
            ),
        ],
    )
    def test_supported_declarations(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        declaration: str,
    ) -> None:
        """
        Verify supported literal, environment, and matrix declarations.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        declaration : str
            Workflow version declaration or expression selected for resolution.
        """
        write_file(
            '.github/workflows/ci.yml',
            f'uses: actions/setup-python@{'a' * 40}\n{declaration}\n',
        )
        assert validate(policy, running_version='3.13') == []

    @pytest.mark.parametrize('version', ['3.12', 'banana'])
    def test_unsupported_workflow_version(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        version: str,
    ) -> None:
        """
        Verify unsupported workflow version.

        Verify invalid or unsupported workflow versions produce an exact
        diagnostic.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consistent policy inputs, isolated from the real checkout.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        version : str
            Candidate interpreter or workflow version selected for policy
            validation.
        """
        path = write_file('.github/workflows/ci.yml', f'python-version: "{version}"\n')
        assert validate(policy, running_version='3.13') == [
            f'{path}: unsupported Python version {version!r}',
        ]


class TestPythonPolicyInputBoundaries:
    """Validate each declaration and inspect shared metadata consistently."""

    @pytest.mark.parametrize('parser', ['text', 'scoped'])
    def test_diagnostic_stage_and_workflow_order(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        parser: Literal['text', 'scoped'],
    ) -> None:
        """
        Preserve runtime, local and per-workflow diagnostic order.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consumer-owned expectations used by the operation.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        parser : Literal['text', 'scoped']
            Parser implementation or workflow reader mode under test.
        """
        policy.python_version_file.write_text('3.12', encoding='utf-8')
        first = write_file(
            '.github/workflows/a.yml',
            'jobs:\n  build:\n    steps:\n      - with:\n'
            '          python-version: "3.12"\n',
        )
        middle = write_file(
            '.github/workflows/ci.yml',
            'name: actions/setup-python@fixture\njobs: {}\n',
        )
        last = write_file(
            '.github/workflows/z.yml',
            'jobs:\n  build:\n    steps:\n      - with:\n'
            '          python-version: "banana"\n',
        )
        config = replace(policy, workflow_parser=parser)
        before = snapshot_files(policy.metadata.parent)
        assert validate(config, running_version='3.12') == [
            'checker runtime: Python >=3.13,<3.15 is required; received 3.12',
            f"{policy.python_version_file}: expected '3.13'",
            f"{first}: unsupported Python version '3.12'",
            f'{middle}: '
            + (
                'setup-python requires an explicit version'
                if parser == 'text'
                else 'no explicit python-version declarations'
            ),
            f"{last}: unsupported Python version 'banana'",
        ]
        assert snapshot_files(policy.metadata.parent) == before

    @pytest.mark.parametrize('missing', [False, True], ids=['malformed', 'missing'])
    def test_shared_metadata_failure_is_reported_once(
        self,
        policy: PythonPolicyConfig,
        missing: bool,
    ) -> None:
        """
        Avoid duplicate diagnostics for one package/Ruff metadata input.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consumer-owned expectations used by the operation.
        missing : bool
            Whether the selected input or policy field is absent.
        """
        if missing:
            policy.metadata.unlink()
        else:
            policy.metadata.write_text('[', encoding='utf-8')
        failures = validate(policy, running_version='3.13')
        assert len(failures) == 1
        assert ('does not exist' if missing else 'invalid TOML') in failures[0]

    def test_shared_metadata_is_read_once(
        self,
        policy: PythonPolicyConfig,
    ) -> None:
        """
        Use one observation for package, mypy and embedded Ruff settings.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consumer-owned expectations used by the operation.
        """
        with patch.object(
            Path,
            'read_text',
            autospec=True,
            side_effect=Path.read_text,
        ) as reads:
            assert validate(policy, running_version='3.13') == []
        assert (
            sum(call.args[0] == policy.metadata for call in reads.call_args_list) == 1
        )

    @pytest.mark.parametrize(
        'unresolved_first',
        [False, True],
        ids=['after-valid', 'before-valid'],
    )
    def test_unresolved_reference_cannot_hide_behind_valid_version(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        unresolved_reference: str,
        unresolved_first: bool,
    ) -> None:
        """
        Reject unresolved declarations even when another version is supported.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consumer-owned expectations used by the operation.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        unresolved_reference : str
            Unresolved workflow expression supplied by the fixture.
        unresolved_first : bool
            Whether an unresolved version precedes a valid declaration.
        """
        declarations = [
            'python-version: "3.13"',
            f'python-version: {unresolved_reference}',
        ]
        if unresolved_first:
            declarations.reverse()
        path = write_file(
            '.github/workflows/ci.yml',
            (f'uses: actions/setup-python@{'a' * 40}\n' + '\n'.join(declarations)),
        )
        assert validate(policy, running_version='3.13') == [
            f'{path}: unsupported Python version {unresolved_reference!r}',
        ]


class TestScopedPythonPolicy:
    """Opt into scoped observations without changing legacy text defaults."""

    @pytest.mark.parametrize(
        'scenario,message',
        [
            ('matrix', None),
            ('missing-declarations', 'no explicit python-version declarations'),
            ('missing-workflow', 'no Python policy workflows found'),
        ],
    )
    def test_scoped_workflow_declarations(
        self,
        policy: PythonPolicyConfig,
        tmp_path: Path,
        scenario: str,
        message: str | None,
    ) -> None:
        """
        Validate each scoped observation case with independent inputs.

        Parameters
        ----------
        policy : PythonPolicyConfig
            Consumer-owned expectations used by the operation.
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        scenario : str
            Selected parameterized behavior or input variant.
        message : str | None
            Expected error message or scenario diagnostic.
        """
        workflow = policy.workflow_directory / 'ci.yml'
        if scenario == 'missing-workflow':
            workflow.unlink()
        else:
            source = (
                """jobs:
  build:
    strategy:
      matrix:
        python: ["3.13", "3.14"]
    steps:
      - with:
          python-version: ${{ matrix.python }}
"""
                if scenario == 'matrix'
                else 'jobs: {}'
            )
            workflow.write_text(source, encoding='utf-8')
        expected = []
        if message is not None:
            expected = [
                f'{workflow}: {message}'
                if scenario == 'missing-declarations'
                else message,
            ]
        before = snapshot_files(tmp_path)
        assert (
            validate(replace(policy, workflow_parser='scoped'), running_version='3.13')
            == expected
        )
        assert snapshot_files(tmp_path) == before


class TestWorkflowObservationProvenance:
    """Keep observation provenance independent of Python policy comparison."""

    @pytest.mark.parametrize('parser', ('text', 'scoped'))
    def test_reader_modes_retain_runtime_observations(
        self,
        tmp_path: Path,
        parser: Literal['text', 'scoped'],
    ) -> None:
        """
        Retain source and native selector without executing a workflow.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        parser : Literal['text', 'scoped']
            Parser implementation or workflow reader mode under test.
        """
        path = tmp_path / 'ci.yml'
        path.write_text(
            'jobs:\n  build:\n    steps:\n      - with:\n'
            '          python-version: "3.13"\n',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        observations, failures = _workflow_observations(path, parser)
        assert failures == []
        assert len(observations) == 1
        observation = observations[0]
        assert observation.source == path
        assert observation.value == '3.13'
        assert observation.kind == 'runtime'
        assert observation.location == (
            'python-version'
            if parser == 'text'
            else 'jobs.build.steps[0].with.python-version'
        )
        assert snapshot_files(tmp_path) == before

    def test_unresolved_legacy_reference_retains_its_value(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Leave unsupported textual values visible to membership checking.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        path = tmp_path / 'ci.yml'
        value = '${{ env.MISSING }}'
        path.write_text(f'python-version: {value}\n', encoding='utf-8')
        observations, failures = _workflow_observations(path, 'text')
        assert failures == []
        assert tuple(item.value for item in observations) == (value,)


# !SECTION
