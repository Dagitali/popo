"""
:mod:`tests.unit.checks.test_u_toolchain_policy` module.

Verify scoped workflow observations without cross-job value borrowing.
"""

import pytest

from popo.checks._toolchain_policy import workflow_observations
from tests.support.files import FileWriter

# SECTION: TESTS


@pytest.mark.parametrize('key', ('python-version', 'swift-version'))
class TestWorkflowVersions:
    """
    Cover workflow versions.

    Resolve only explicit literals, scoped env values and simple matrices.
    """

    @pytest.mark.parametrize(
        'workflow_env,job_env,step_env,expected',
        [
            ('{TOOL: "3.13"}', '{}', '{}', ('3.13',)),
            ('{TOOL: "3.13"}', '{TOOL: "3.14"}', '{}', ('3.14',)),
            ('{TOOL: "3.13"}', '{TOOL: "3.14"}', '{TOOL: "3.15"}', ('3.15',)),
            ('{TOOL: "3.13"}', '{}', '{TOOL: null}', ()),
            ('{TOOL: "3.13"}', '{}', '{TOOL: ""}', ()),
            ('{TOOL: "3.13"}', '{}', '{TOOL: false}', ()),
            ('[]', '{}', '{TOOL: "3.15"}', ()),
            ('{}', '[]', '{TOOL: "3.15"}', ()),
        ],
    )
    def test_environment_precedence(
        self,
        write_file: FileWriter,
        key: str,
        workflow_env: str,
        job_env: str,
        step_env: str,
        expected: tuple[str, ...],
    ) -> None:
        """
        Validate every scope and preserve invalid higher-scope overrides.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        workflow_env : str
            Workflow-scoped environment declarations for version resolution.
        job_env : str
            Job-scoped environment declarations used for version resolution.
        step_env : str
            Step-scoped environment declarations used for version resolution.
        expected : tuple[str, ...]
            Expected result for the selected parameterized scenario.
        """
        source = f"""env: {workflow_env}
jobs:
  build:
    env: {job_env}
    steps:
      - env: {step_env}
        with:
          {key}: ${{{{ env.TOOL }}}}
"""
        path = write_file('ci.yml', source)
        observations, errors = workflow_observations(path, key)
        assert tuple(item.value for item in observations) == expected
        assert errors == (
            []
            if expected
            else [
                f'jobs.build.steps[0].with.{key}: '
                'unresolved or unsupported version declaration',
            ]
        )
        assert path.read_text(encoding='utf-8') == source

    def test_job_scopes_do_not_leak(
        self,
        write_file: FileWriter,
        key: str,
    ) -> None:
        """
        Verify job scopes do not leak.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        """
        path = write_file(
            'ci.yml',
            f"""jobs:
  first:
    env: {{ TOOL: "6.1.2" }}
    with: {{ {key}: "6.1.2" }}
  second:
    with: {{ {key}: "${{{{ env.TOOL }}}}" }}
""",
        )
        values, errors = workflow_observations(path, key)
        assert [(item.location, item.value) for item in values] == [
            (f'jobs.first.with.{key}', '6.1.2'),
        ]
        assert errors == [
            f'jobs.second.with.{key}: unresolved or unsupported version declaration',
        ]

    @pytest.mark.parametrize(
        'source',
        [
            '[]',
            'jobs: []',
            'jobs: { bad: [] }',
            'jobs: { bad: {steps: false} }',
            'jobs: { bad: {steps: [false]} }',
            'jobs: { "bad id": {} }',
            'jobs: { bad: {with: []} }',
            'jobs: {}\njobs: {}',
        ],
    )
    def test_malformed_documents(
        self,
        write_file: FileWriter,
        key: str,
        source: str,
    ) -> None:
        """
        Verify malformed documents.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        source : str
            Decoded input text to inspect without executing it.
        """
        values, errors = workflow_observations(
            write_file('ci.yml', source),
            key,
        )
        assert values == ()
        assert errors == ['cannot read a valid workflow version declaration']

    @pytest.mark.parametrize(
        'expression,expected',
        [
            ('"6.1.2"', ('6.1.2',)),
            ('"${{ env.TOOL }}"', ('6.1.2',)),
            ('"${{ matrix.tool }}"', ('6.1.2', '6.2.0')),
        ],
    )
    def test_supported_declarations(
        self,
        write_file: FileWriter,
        key: str,
        expression: str,
        expected: tuple[str, ...],
    ) -> None:
        """
        Verify supported declarations.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        expression : str
            Workflow version expression under test.
        expected : tuple[str, ...]
            Expected result for the selected parameterized scenario.
        """
        path = write_file(
            'ci.yml',
            f"""env: {{ TOOL: "6.0.0" }}
jobs:
  build:
    env: {{ TOOL: "6.1.0" }}
    strategy:
      matrix:
        tool: ["6.1.2", "6.2.0"]
    steps:
      - env: {{ TOOL: "6.1.2" }}
        with:
          {key}: {expression}
""",
        )
        observations, errors = workflow_observations(path, key)
        assert errors == []
        assert tuple(item.value for item in observations) == expected
        assert all(
            item.source == path and item.location == f'jobs.build.steps[0].with.{key}'
            for item in observations
        )

    @pytest.mark.parametrize(
        'matrix',
        [
            'include: [{tool: "6.1.2"}]',
            'exclude: [{tool: "6.1.2"}]',
            'tool: []',
            'tool: "6.1.2"',
            'tool: [6.1]',
        ],
    )
    def test_unsupported_matrix_forms(
        self,
        write_file: FileWriter,
        key: str,
        matrix: str,
    ) -> None:
        """
        Verify unsupported matrix forms.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        matrix : str
            Workflow matrix declarations used for version resolution.
        """
        path = write_file(
            'ci.yml',
            f"""jobs:
  build:
    strategy:
      matrix:
        {matrix}
    with:
      {key}: ${{{{ matrix.tool }}}}
""",
        )
        observations, errors = workflow_observations(path, key)
        assert observations == ()
        assert errors == [
            f'jobs.build.with.{key}: unresolved or unsupported version declaration',
        ]

    @pytest.mark.parametrize(
        'value',
        [
            '6.1',
            '""',
            '"${{ inputs.tool }}"',
            '"${{ env.MISSING }}"',
            '"${{ matrix.missing }}"',
        ],
    )
    def test_unsupported_or_unresolved_values(
        self,
        write_file: FileWriter,
        key: str,
        value: str,
    ) -> None:
        """
        Verify unsupported or unresolved values.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        value : str
            Unvalidated value supplied to the operation.
        """
        path = write_file(
            'ci.yml',
            f'jobs: {{ build: {{ with: {{ {key}: {value} }} }} }}',
        )
        observations, errors = workflow_observations(path, key)
        assert observations == ()
        assert errors == [
            f'jobs.build.with.{key}: unresolved or unsupported version declaration',
        ]


class TestObservationInterpretation:
    """
    Cover observation interpretation.

    Keep observation roles explicit and independent of action input names.
    """

    @pytest.mark.parametrize('kind', ('runtime', 'compiler'))
    @pytest.mark.parametrize('key', ('python-version', 'swift-version'))
    def test_caller_selects_role(
        self,
        write_file: FileWriter,
        key: str,
        kind: str,
    ) -> None:
        """
        Record caller semantics without guessing from the workflow key.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        key : str
            Policy key whose value is inspected.
        kind : str
            Native syntax kind or policy variant under test.
        """
        path = write_file('ci.yml', f'jobs:\n  build:\n    with: {{ {key}: "3.13" }}')
        observations, errors = workflow_observations(path, key, kind=kind)
        assert errors == []
        assert len(observations) == 1
        assert observations[0].kind == kind
        assert observations[0].value == '3.13'


# !SECTION
