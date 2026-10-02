"""
:mod:`tests.unit.checks.test_u_dependencies` module.

Test dependency lower bounds, exact matching, and policy failures.
"""

from pathlib import Path

import pytest

from popo.checks.dependencies import validate
from popo.config import DependencyConfig, DependencyMode
from tests.support.files import FileWriter

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
    ) -> None:
        """
        Comments must not enable installer directives or hide their location.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
        metadata = write_file('pyproject.toml', '[project]\ndependencies = []')
        requirements = write_file(
            'requirements.txt',
            '# heading\n-r other.txt # include\n',
        )
        assert validate(DependencyConfig(metadata, requirements, 'exact')) == [
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
            Expected diagnostic substring; an empty string selects a successful
            case.
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
        'suffix',
        [' # minimum', '\t# minimum', '   # note # more'],
    )
    @pytest.mark.parametrize(
        'mode',
        ['exact', 'minimum-constraints'],
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
    ) -> None:
        """
        Verify invalid dependency metadata produces the expected diagnostic.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        message : str
            Expected diagnostic substring; an empty string selects a successful
            case.
        """
        config = DependencyConfig(
            write_file('pyproject.toml', content),
            write_file('requirements.txt', ''),
            'exact',
        )
        assert message in validate(config)[0]

    def test_missing_files(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify absent dependency metadata and constraints each produce a
        diagnostic.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
        paths = (tmp_path / 'pyproject.toml', tmp_path / 'requirements.txt')
        assert validate(DependencyConfig(*paths, 'exact')) == [
            f'dependency-policy file does not exist: {path}' for path in paths
        ]

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
