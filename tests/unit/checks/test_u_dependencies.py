"""
:mod:`tests.unit.checks.test_u_dependencies` module.

Test dependency lower bounds, exact matching, and policy failures.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from popo.checks.dependencies import validate
from popo.config import DependencyConfig, DependencyMode
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(
    name='mode',
    params=['exact', 'minimum-constraints'],
)
def comparison_mode_fixture(
    request: pytest.FixtureRequest,
) -> DependencyMode:
    """
    Select each comparison policy with independent temporary inputs.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest request carrying the selected fixture parameter.

    Returns
    -------
    DependencyMode
        Dependency comparison mode selected by the fixture parameter.
    """
    return cast(DependencyMode, request.param)


# !SECTION


# SECTION: TESTS


class TestDependencyPolicy:
    """
    Exercise normalized comparisons and malformed dependency inputs.

    Notes
    -----
    Compare temporary project metadata and constraint fixtures in exact and
    minimum modes. Include malformed inputs and comment/URL-fragment boundaries
    without installing or resolving dependencies.
    """

    def test_commented_directive_retains_line_number(
        self,
        write_file: FileWriter,
        mode: DependencyMode,
    ) -> None:
        """
        Comments must not enable installer directives or hide their location.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        mode : DependencyMode
            Dependency comparison policy selected for the scenario.
        """
        metadata = write_file('pyproject.toml', '[project]\ndependencies = []')
        requirements = write_file(
            'requirements.txt',
            '# heading\n-r other.txt # include\n',
        )
        assert validate(DependencyConfig(metadata, requirements, mode)) == [
            f"{requirements}:2: installer directives are not supported: '-r other.txt'",
        ]

    @pytest.mark.parametrize(
        ('dependencies', 'constraints', 'mode', 'message'),
        [
            (
                '"demo>=2,<4"',
                '# pins\n\ndemo==2',
                'minimum-constraints',
                None,
            ),
            (
                '"demo>=2,<4"',
                'demo==1',
                'minimum-constraints',
                "expected {'demo': '2'}; received {'demo': '1'}",
            ),
            (
                '"demo>=2,<4"',
                'demo==3',
                'minimum-constraints',
                "expected {'demo': '2'}; received {'demo': '3'}",
            ),
            ('"demo==2"', 'demo==2', 'exact', None),
            (
                '"demo==2"',
                'demo==3',
                'exact',
                "expected {'demo': 'demo==2'}; received {'demo': 'demo==3'}",
            ),
            (
                '"demo_pkg>=1,<2", "demo-pkg>=1,<2"',
                'demo-pkg==1',
                'minimum-constraints',
                'duplicate dependency',
            ),
            (
                '"demo>=1,<2"',
                'demo==1\ndemo==1',
                'minimum-constraints',
                'duplicate dependency',
            ),
            (
                '"demo>=1,<2"',
                'demo>=1',
                'minimum-constraints',
                'constraint must use name==version',
            ),
            (
                '"demo>=1,<2"',
                'demo>=1,<2',
                'minimum-constraints',
                'constraint must use name==version',
            ),
            (
                '"demo>=1,<2"',
                'demo @ https://example.com/demo.whl',
                'minimum-constraints',
                'constraint must use name==version',
            ),
            (
                '"demo~=1.0"',
                'demo==1.0',
                'minimum-constraints',
                'dependency must declare',
            ),
            (
                '"demo>=1,<2"',
                '-r other.txt',
                'minimum-constraints',
                'installer directives are not supported',
            ),
            (
                '"demo>=1,<2"',
                'not a requirement!',
                'minimum-constraints',
                'invalid requirement',
            ),
            ('"demo>=1,<2"', '', 'minimum-constraints', 'expected'),
        ],
    )
    def test_comparison(
        self,
        write_file: FileWriter,
        dependencies: str,
        constraints: str,
        mode: DependencyMode,
        message: str | None,
    ) -> None:
        """
        Verify comparison.

        Verify dependency comparisons report the expected result for each
        policy mode.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        dependencies : str
            Project dependency declarations selected for comparison.
        constraints : str
            Requirements or constraint-file text selected for comparison.
        mode : DependencyMode
            Dependency comparison policy selected for the scenario.
        message : str | None
            Expected diagnostic substring; ``None`` selects a successful case.
        """
        metadata = write_file(
            'pyproject.toml',
            f'[project]\ndependencies = [{dependencies}]',
        )
        requirements = write_file('requirements.txt', constraints)
        failures = validate(DependencyConfig(metadata, requirements, mode))
        if message is None:
            assert failures == []
        else:
            assert len(failures) == 1
            assert message in failures[0]

    @pytest.mark.parametrize(
        'names',
        [('Demo_Pkg', 'demo-pkg'), ('demo.pkg', 'Demo__Pkg'), ('DEMO', 'demo')],
    )
    @pytest.mark.parametrize(
        'suffix',
        [
            '==1',
            '[feature]>=1,<2',
            '>=1,<2; python_version < "3.15"',
            ' @ https://example.com/demo.whl#sha256=abc123',
        ],
    )
    def test_exact_comparison_canonicalizes_only_package_names(
        self,
        write_file: FileWriter,
        names: tuple[str, str],
        suffix: str,
    ) -> None:
        """
        Accept equivalent package spelling while preserving other fields.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        names : tuple[str, str]
            Names checked against the selected matching rule.
        suffix : str
            Suffix appended to the version or syntax input.
        """
        expected, actual = (name + suffix for name in names)
        metadata = write_file(
            'pyproject.toml',
            f'[project]\ndependencies = [{json.dumps(expected)}]',
        )
        requirements = write_file('requirements.txt', actual)
        assert validate(DependencyConfig(metadata, requirements, 'exact')) == []

    @pytest.mark.parametrize(
        'suffix',
        [' # minimum', '\t# minimum', '   # note # more'],
    )
    def test_inline_comments(
        self,
        write_file: FileWriter,
        suffix: str,
        mode: DependencyMode,
    ) -> None:
        """
        Accept trailing annotations without changing comparison policy.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        suffix : str
            Trailing requirement text exercising comment or URL-fragment
            handling.
        mode : DependencyMode
            Dependency comparison policy selected for the scenario.
        """
        declaration = 'demo==1' if mode == 'exact' else 'demo>=1,<2'
        metadata = write_file(
            'pyproject.toml',
            f'[project]\ndependencies = ["{declaration}"]',
        )
        requirements = write_file(
            'requirements.txt',
            f'  # heading\n\ndemo==1{suffix}\n',
        )
        assert validate(DependencyConfig(metadata, requirements, mode)) == []

    @pytest.mark.parametrize(
        ('content', 'message'),
        [
            ('[', 'invalid TOML'),
            ('[project]\ndependencies = 42', 'must be a string array'),
            ('[project]\ndependencies = [42]', 'must be a string array'),
        ],
    )
    def test_malformed_metadata(
        self,
        write_file: FileWriter,
        content: str,
        message: str,
        mode: DependencyMode,
    ) -> None:
        """
        Verify invalid dependency metadata produces the expected diagnostic.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        content : str
            Malformed TOML or dependency-array contents to reject.
        message : str
            Expected diagnostic substring for malformed metadata.
        mode : DependencyMode
            Dependency comparison policy selected for the scenario.
        """
        config = DependencyConfig(
            write_file('pyproject.toml', content),
            write_file('requirements.txt', ''),
            mode,
        )
        failures = validate(config)
        assert len(failures) == 1
        assert message in failures[0]

    @pytest.mark.parametrize('project', ['1', '"metadata"', '[]', 'false'])
    def test_malformed_project_table(
        self,
        write_file: FileWriter,
        project: str,
        mode: DependencyMode,
    ) -> None:
        """
        Report malformed project tables instead of crashing during lookup.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        project : str
            Project identity inserted into the header policy.
        mode : DependencyMode
            Dependency comparison mode selected for the scenario.
        """
        metadata = write_file('pyproject.toml', f'project = {project}')
        requirements = write_file('requirements.txt', '')
        assert validate(DependencyConfig(metadata, requirements, mode)) == [
            f'{metadata}: project must be a TOML table',
        ]

    @pytest.mark.parametrize('structural', [False, True])
    def test_metadata_failures_preserve_validation_order(
        self,
        write_file: FileWriter,
        mode: DependencyMode,
        structural: bool,
    ) -> None:
        """
        Keep metadata and installer failure ordering stable.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        mode : DependencyMode
            Dependency comparison mode selected for the scenario.
        structural : bool
            Whether the scenario uses structural declaration syntax.
        """
        metadata = write_file(
            'pyproject.toml',
            '[project]\ndependencies = '
            + ('42' if structural else '["not a requirement"]'),
        )
        requirements = write_file('requirements.txt', '-r other.txt\ninvalid???')
        failures = validate(DependencyConfig(metadata, requirements, mode))
        if structural:
            assert failures == [
                f'{metadata}: project.dependencies must be a string array',
            ]
        else:
            assert len(failures) == 3
            assert failures[0].startswith(f'{metadata}: invalid requirement')
            assert failures[1].startswith(f'{requirements}:1: installer directives')
            assert failures[2].startswith(f'{requirements}: invalid requirement')

    @pytest.mark.parametrize(
        'missing',
        [
            ('pyproject.toml',),
            ('requirements.txt',),
            ('pyproject.toml', 'requirements.txt'),
        ],
        ids=('metadata', 'requirements', 'both'),
    )
    def test_missing_files(
        self,
        tmp_path: Path,
        mode: DependencyMode,
        missing: tuple[str, ...],
    ) -> None:
        """
        Verify missing files.

        Verify absent dependency metadata and constraints each produce a
        diagnostic.

        An undecodable existing partner must not be read before missing-input
        checks finish. Validation preserves all existing input bytes.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        mode : DependencyMode
            Dependency comparison policy selected for the scenario.
        missing : tuple[str, ...]
            Metadata, requirements or both filenames deliberately left absent.
        """
        paths = (tmp_path / 'pyproject.toml', tmp_path / 'requirements.txt')
        for path in paths:
            if path.name not in missing:
                path.write_bytes(b'\xffPRIVATE input')
        before = snapshot_files(tmp_path)
        assert validate(DependencyConfig(*paths, mode)) == [
            f'dependency-policy file does not exist: {path}'
            for path in paths
            if path.name in missing
        ]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'suffix',
        [
            '==2',
            '[other]==1',
            '==1; python_version < "3.15"',
            ' @ https://example.com/demo.whl',
        ],
    )
    def test_name_normalization_keeps_other_exact_differences(
        self,
        write_file: FileWriter,
        suffix: str,
    ) -> None:
        """
        Keep non-name dependency drift visible after normalization.

        Parameters
        ----------
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        suffix : str
            Suffix appended to the version or syntax input.
        """
        metadata = write_file(
            'pyproject.toml',
            '[project]\ndependencies = ["Demo_Pkg==1"]',
        )
        requirements = write_file('requirements.txt', 'demo-pkg' + suffix)
        failures = validate(DependencyConfig(metadata, requirements, 'exact'))
        assert len(failures) == 1
        assert 'expected' in failures[0]

    @pytest.mark.parametrize(
        'suffix',
        ['', ' # artifact'],
    )
    def test_url_fragments_remain_part_of_exact_requirements(
        self,
        write_file: FileWriter,
        suffix: str,
    ) -> None:
        """
        Do not erase a URL hash when stripping a separate inline comment.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        suffix : str
            Trailing requirement text exercising comment or URL-fragment
            handling.
        """
        requirement = 'demo @ https://example.com/demo.whl#sha256=abc123'
        metadata = write_file(
            'pyproject.toml',
            f'[project]\ndependencies = ["{requirement}"]',
        )
        requirements = write_file('requirements.txt', requirement + suffix)
        assert validate(DependencyConfig(metadata, requirements, 'exact')) == []


# !SECTION
