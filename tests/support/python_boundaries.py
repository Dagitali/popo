"""
:mod:`tests.support.python_boundaries` module.

Share inert Python boundary consumers across checker and CLI test layers.
"""

from pathlib import Path

import pytest

# SECTION: FIXTURES


@pytest.fixture(
    name='python_boundary_case',
    params=(
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
        ('from pathlib import Path\nx = Path', 'forbidden symbol pathlib.Path'),
        ('import pathlib.Path as P\nx = P', 'forbidden symbol pathlib.Path'),
        ('import pathlib as Π\nx = Π.Path', 'forbidden symbol pathlib.Path'),
        ('import pathlib as p\nx = pExtra.Path', None),
        ('def broken(', 'invalid Python source'),
        ('# import pkg.ui\nx = "pkg.ui"', None),
        ('raise RuntimeError("must not execute")', None),
        ('from pathlib import PurePath', None),
    ),
)
def python_boundary_case_fixture(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> tuple[Path, str | None]:
    """
    Create an independent source/import graph without executing consumer code.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Disposable consumer repository owned by the requesting test.
    request : pytest.FixtureRequest
        Native source and expected diagnostic substring from the case table.

    Returns
    -------
    tuple[pathlib.Path, str or None]
        Consumer root and expected diagnostic, or None for accepted inputs.
        Each case selects only the Python boundary checker for aggregate runs.
    """
    source, expected = request.param
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
    return tmp_path, expected


# !SECTION
