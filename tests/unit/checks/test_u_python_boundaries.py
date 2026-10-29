"""
:mod:`tests.unit.checks.test_u_python_boundaries` module.

Exercise offline Python imports, aliases and consumer-selected layers.
"""

from pathlib import Path

import pytest

from popo.checks.python_boundaries import validate
from popo.config.python_boundaries import load_python_boundaries_config
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestPythonBoundaries:
    """Keep module analysis deterministic, confined and non-executing."""

    def test_imports_and_symbols(
        self,
        python_boundary_case: tuple[Path, str | None],
    ) -> None:
        """
        Resolve relative imports and aliases without evaluating source.

        Parameters
        ----------
        python_boundary_case : tuple[Path, str | None]
            Isolated Python consumer and its expected boundary failure.
        """
        root, expected = python_boundary_case
        before = snapshot_files(root)
        findings = validate(load_python_boundaries_config(root))
        if expected:
            assert any(expected in item for item in findings)
        else:
            assert findings == []
        assert snapshot_files(root) == before

    def test_package_relative_import(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Resolve an initializer's relative import within its own package.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        """
        (tmp_path / 'pkg').mkdir()
        (tmp_path / 'pkg/__init__.py').write_text('from . import ui', encoding='utf-8')
        (tmp_path / 'pkg/ui.py').write_text('', encoding='utf-8')
        (tmp_path / 'popo.toml').write_text(
            '[[python-boundaries.layers]]\nname="core"\n'
            'include=["pkg/__init__.py"]\nforbidden-layers=["ui"]\n'
            '[[python-boundaries.layers]]\nname="ui"\ninclude=["pkg/ui.py"]',
            encoding='utf-8',
        )
        assert 'forbidden layer import pkg.ui' in '\n'.join(
            validate(load_python_boundaries_config(tmp_path)),
        )


class TestPythonModuleOwnership:
    """Distinguish a src-layout directory from a module named src.py."""

    @pytest.mark.parametrize(
        'owner',
        ('src.py', 'pkg/module.py', 'src/pkg/module.py'),
    )
    def test_path_based_layer_targets(
        self,
        tmp_path: Path,
        owner: str,
    ) -> None:
        """
        Reject imports from each owned module without executing its code.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        owner : str
            Policy owner or workflow scope selected for the scenario.
        """
        path = tmp_path / owner
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('raise RuntimeError("must not execute")', encoding='utf-8')
        module = 'src' if owner == 'src.py' else 'pkg.module'
        (tmp_path / 'consumer.py').write_text(f'import {module}', encoding='utf-8')
        (tmp_path / 'popo.toml').write_text(
            '[[python-boundaries.layers]]\nname="consumer"\n'
            'include=["consumer.py"]\nforbidden-layers=["owner"]\n'
            '[[python-boundaries.layers]]\nname="owner"\n'
            f'include=["{owner}"]',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        assert validate(load_python_boundaries_config(tmp_path)) == [
            f'consumer.py:1: consumer: forbidden layer import {module}',
        ]
        assert snapshot_files(tmp_path) == before


# !SECTION
