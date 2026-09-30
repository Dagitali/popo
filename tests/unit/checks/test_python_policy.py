"""
:mod:`tests.unit.checks.test_python_policy` module.

Test Python-version consistency and workflow matrix resolution.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from popo.checks.python_policy import validate
from popo.config import PythonPolicyConfig
from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture(name='policy')
def policy_fixture(
    tmp_path: Path,
    write_file: FileWriter,
) -> PythonPolicyConfig:
    """Create one consistent policy; individual cases vary only their relevant input."""
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


class TestPythonPolicy:
    """Validate policy consistency and supported workflow version declarations."""

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
        """Resolve every block-list item, including quoted values with comments."""
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
        write_file(path, content)
        assert any(
            message in failure for failure in validate(policy, running_version='3.13')
        )

    def test_invalid_specifier(
        self,
        policy: PythonPolicyConfig,
    ) -> None:
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
        path = write_file(
            '.github/workflows/ci.yml',
            f'uses: actions/setup-python@{'a' * 40}\n{declaration}',
        )
        assert validate(policy, running_version='3.13') == [
            f'{path}: setup-python requires an explicit version',
        ]

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
        write_file(
            '.github/workflows/ci.yml',
            f'uses: actions/setup-python@{'a' * 40}\n{declaration}\n',
        )
        assert validate(policy, running_version='3.13') == []

    def test_unsupported_runtime(
        self,
        policy: PythonPolicyConfig,
    ) -> None:
        assert 'checker runtime' in validate(policy, running_version='3.12')[0]

    @pytest.mark.parametrize('version', ['3.12', 'banana'])
    def test_unsupported_workflow_version(
        self,
        policy: PythonPolicyConfig,
        write_file: FileWriter,
        version: str,
    ) -> None:
        path = write_file('.github/workflows/ci.yml', f'python-version: "{version}"\n')
        assert validate(policy, running_version='3.13') == [
            f'{path}: unsupported Python version {version!r}',
        ]
