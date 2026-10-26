"""
:mod:`tests.unit.checks.test_u_toolchain_policy` module.

Verify scoped workflow observations without cross-job value borrowing.
"""

import pytest

from popo.checks._toolchain_policy import workflow_observations
from tests.support.files import FileWriter

# SECTION: TESTS


class TestWorkflowVersions:
    """
    Resolve only explicit literals, scoped env values and simple matrices.
    """

    @pytest.mark.parametrize('key', ['python-version', 'swift-version'])
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
        source: str,
    ) -> None:
        values, errors = workflow_observations(
            write_file('ci.yml', source),
            'swift-version',
        )
        assert values == ()
        assert errors == ['cannot read a valid workflow version declaration']

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
        value: str,
    ) -> None:
        path = write_file(
            'ci.yml',
            f'jobs: {{ build: {{ with: {{ swift-version: {value} }} }} }}',
        )
        observations, errors = workflow_observations(path, 'swift-version')
        assert observations == ()
        assert errors == [
            'jobs.build.with.swift-version: '
            'unresolved or unsupported version declaration',
        ]

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
        matrix: str,
    ) -> None:
        path = write_file(
            'ci.yml',
            f"""jobs:
  build:
    strategy:
      matrix:
        {matrix}
    with:
      swift-version: ${{{{ matrix.tool }}}}
""",
        )
        observations, errors = workflow_observations(path, 'swift-version')
        assert observations == ()
        assert errors == [
            'jobs.build.with.swift-version: '
            'unresolved or unsupported version declaration',
        ]

    def test_job_scopes_do_not_leak(
        self,
        write_file: FileWriter,
    ) -> None:
        path = write_file(
            'ci.yml',
            """jobs:
  first:
    env: { TOOL: "6.1.2" }
    with: { swift-version: "6.1.2" }
  second:
    with: { swift-version: "${{ env.TOOL }}" }
""",
        )
        values, errors = workflow_observations(path, 'swift-version')
        assert [(item.location, item.value) for item in values] == [
            ('jobs.first.with.swift-version', '6.1.2'),
        ]
        assert errors == [
            'jobs.second.with.swift-version: '
            'unresolved or unsupported version declaration',
        ]


# !SECTION
