"""
:mod:`tests.unit.test_dependencies` module.

Test dependency lower bounds, exact matching, and policy failures.
"""

from pathlib import Path

import pytest

from popo.checks.dependencies import validate
from popo.config import DependencyConfig, DependencyMode
from tests.support.files import FileWriter

# SECTION: TESTS


class TestDependencyPolicy:
    """Exercise normalized comparisons and malformed dependency inputs."""

    @pytest.mark.parametrize(
        ('dependencies', 'constraints', 'mode', 'message'),
        [
            (
                '"packaging>=25.0,<27"',
                '# pins\n\npackaging==25.0',
                'minimum-constraints',
                None,
            ),
            ('"packaging==25.0"', 'packaging==25.0', 'exact', None),
            (
                '"packaging==25.0"',
                'packaging==25.1',
                'exact',
                "'packaging': 'packaging==25.0'",
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
        metadata = write_file(
            'pyproject.toml', f'[project]\ndependencies = [{dependencies}]'
        )
        requirements = write_file('requirements.txt', constraints)
        failures = validate(DependencyConfig(metadata, requirements, mode))
        if message is None:
            assert failures == []
        else:
            assert len(failures) == 1
            assert message in failures[0]

    @pytest.mark.parametrize(
        ('content', 'message'),
        [
            ('[', 'invalid TOML'),
            ('[project]\ndependencies = 42', 'must be a string array'),
            ('[project]\ndependencies = [42]', 'must be a string array'),
        ],
    )
    def test_malformed_metadata(
        self, write_file: FileWriter, content: str, message: str
    ) -> None:
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
        paths = (tmp_path / 'pyproject.toml', tmp_path / 'requirements.txt')
        assert validate(DependencyConfig(*paths, 'exact')) == [
            f'dependency-policy file does not exist: {path}' for path in paths
        ]


# !SECTION
