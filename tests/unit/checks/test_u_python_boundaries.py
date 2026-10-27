"""
:mod:`tests.unit.checks.test_u_python_boundaries` module.

Exercise offline Python imports, aliases and consumer-selected layers.
"""

from pathlib import Path

import pytest

from popo.checks.python_boundaries import validate
from popo.cli import main
from popo.config.python_boundaries import load_python_boundaries_config
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestPythonBoundaries:
    """Keep module analysis deterministic, confined and non-executing."""

    @pytest.mark.parametrize(
        'source,expected',
        (
            ('import pkg.ui', 'forbidden layer import pkg.ui'),
            ('from .ui import Screen', 'forbidden layer import pkg.ui.Screen'),
            ('from . import ui', 'forbidden layer import pkg.ui'),
            ('from ..ui import Screen', 'unresolved relative import'),
            ('import os', 'forbidden import os'),
            (
                'import pathlib.Path\nx = pathlib.Path()',
                'forbidden symbol pathlib.Path',
            ),
            ('from pathlib import Path as P\nx = P()', 'forbidden symbol pathlib.Path'),
            ('import pathlib as p\nx = p.Path()', 'forbidden symbol pathlib.Path'),
            ('def broken(', 'invalid Python source'),
            ('# import pkg.ui\nx = "pkg.ui"', None),
            ('raise RuntimeError("must not execute")', None),
            ('from pathlib import PurePath', None),
        ),
    )
    def test_imports_and_symbols(
        self,
        tmp_path: Path,
        source: str,
        expected: str | None,
    ) -> None:
        """Resolve relative imports and aliases without evaluating source."""
        folder = tmp_path / 'src/pkg'
        folder.mkdir(parents=True)
        (folder / 'core.py').write_text(source, encoding='utf-8')
        (folder / 'ui.py').write_text('class Screen: pass', encoding='utf-8')
        (tmp_path / 'popo.toml').write_text(
            'checks=["check-python-boundaries"]\n'
            '[[python-boundaries.layers]]\nname="core"\n'
            'include=["src/pkg/core.py"]\nallowed-imports=["pathlib"]\n'
            'forbidden-layers=["ui"]\nforbidden-symbols=["pathlib.Path"]\n'
            '[[python-boundaries.layers]]\nname="ui"\n'
            'include=["src/pkg/ui.py"]\n',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        findings = validate(load_python_boundaries_config(tmp_path))
        if expected:
            assert any(expected in item for item in findings)
        else:
            assert findings == []
        assert main(['check-all', '--root', str(tmp_path)]) == bool(expected)
        assert snapshot_files(tmp_path) == before

    def test_package_relative_import(
        self,
        tmp_path: Path,
    ) -> None:
        """Resolve an initializer's relative import within its own package."""
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


class TestBoundaryConfigurationParity:
    """Apply common policy contracts independently of language syntax."""

    @pytest.mark.parametrize('language', ('python', 'swift'))
    @pytest.mark.parametrize(
        'settings',
        (
            '',
            'layers=[]',
            'unknown=true',
            '[[DOMAIN.layers]]\nname="core"\ninclude=["*.SOURCE"]\n'
            'forbidden-layers=["core"]',
        ),
    )
    def test_invalid_policy(
        self,
        tmp_path: Path,
        language: str,
        settings: str,
    ) -> None:
        """Reject empty, unknown and self-referencing layer policies."""
        from popo.config._common import ConfigurationError
        from popo.config.source_boundaries import load_boundaries_config

        domain = f'{language}-boundaries'
        settings = settings.replace('DOMAIN', domain).replace('SOURCE', language)
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\n{settings}',
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError):
            load_boundaries_config(tmp_path, domain)

    @pytest.mark.parametrize('language', ('python', 'swift'))
    def test_overlapping_layers_read_once(
        self,
        tmp_path: Path,
        language: str,
    ) -> None:
        """Check overlapping selections without repeating source reads."""
        from popo.checks._source_boundaries import boundary_sources
        from popo.config.source_boundaries import load_boundaries_config

        domain = f'{language}-boundaries'
        (tmp_path / 'source').write_text('', encoding='utf-8')
        (tmp_path / 'popo.toml').write_text(
            ''.join(
                f'[[{domain}.layers]]\nname="{name}"\ninclude=["source"]\n'
                for name in ('one', 'two')
            ),
            encoding='utf-8',
        )
        paths, sources, failures = boundary_sources(
            load_boundaries_config(tmp_path, domain),
        )
        assert len(paths) == 2
        assert len(sources) == 1
        assert failures == []


# !SECTION
