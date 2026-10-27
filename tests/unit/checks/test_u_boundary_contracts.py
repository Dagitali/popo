"""
:mod:`tests.unit.checks.test_u_boundary_contracts` module.

Check shared language-analyzer ordering, failures and read-only contracts.
"""

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, cast
from unittest.mock import Mock

import pytest

from popo.checks import python_boundaries, swift_boundaries
from popo.config.source_boundaries import BoundaryConfig, load_boundaries_config
from tests.support.files import snapshot_files

# SECTION: NAMED TUPLES


class BoundaryCase(NamedTuple):
    """
    Keep native syntax and expected lexical differences beside a validator.
    """

    domain: str
    validate: Callable[[BoundaryConfig], list[str]]
    reference: str
    symbol_lines: tuple[int, ...]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(
    name='boundary_case',
    params=(
        pytest.param(
            BoundaryCase(
                'python-boundaries',
                python_boundaries.validate,
                'x = Forbidden + Forbidden',
                (2,),
            ),
            id='python',
        ),
        pytest.param(
            BoundaryCase(
                'swift-boundaries',
                swift_boundaries.validate,
                'let x = Forbidden + Forbidden',
                (1, 2),
            ),
            id='swift',
        ),
    ),
)
def boundary_case_fixture(
    request: pytest.FixtureRequest,
) -> BoundaryCase:
    """
    Supply one native boundary implementation and its diagnostic expectations.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Selected Python or Swift case; each scenario runs for both languages.

    Returns
    -------
    BoundaryCase
        Policy domain, public validator, native reference and symbol locations.
        Swift includes import-line tokens; Python inspects AST references.
    """
    return cast(BoundaryCase, request.param)


# !SECTION


# SECTION: TESTS


class TestBoundaryContracts:
    """Exercise both structural analyzers through their public validators."""

    def test_diagnostic_order_and_read_only_inputs(
        self,
        tmp_path: Path,
        boundary_case: BoundaryCase,
    ) -> None:
        """Keep selection failures before imports and deduplicated symbols."""
        domain = boundary_case.domain
        (tmp_path / 'popo.toml').write_text(
            f'[[{domain}.layers]]\nname="core"\n'
            'include=["missing", "source"]\nallowed-imports=[]\n'
            'forbidden-symbols=["Forbidden"]\n',
            encoding='utf-8',
        )
        (tmp_path / 'source').write_text(
            f'import Forbidden\n{boundary_case.reference}',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        config = load_boundaries_config(tmp_path, domain)
        findings = boundary_case.validate(config)
        assert findings == [
            'core: no inputs match: missing',
            'source:1: core: forbidden import Forbidden',
            *(
                f'source:{line}: core: forbidden symbol Forbidden'
                for line in boundary_case.symbol_lines
            ),
        ]
        assert snapshot_files(tmp_path) == before

    def test_unreadable_source_fails_without_source_disclosure(
        self,
        tmp_path: Path,
        boundary_case: BoundaryCase,
    ) -> None:
        """
        Return redacted decoding diagnostics for both language front ends.
        """
        domain = boundary_case.domain
        (tmp_path / 'popo.toml').write_text(
            f'[[{domain}.layers]]\nname="core"\ninclude=["source"]',
            encoding='utf-8',
        )
        (tmp_path / 'source').write_bytes(b'PRIVATE\xff')
        before = snapshot_files(tmp_path)
        findings = boundary_case.validate(load_boundaries_config(tmp_path, domain))
        assert findings
        assert 'PRIVATE' not in '\n'.join(findings)
        assert snapshot_files(tmp_path) == before


class TestOverlappingBoundaryLayers:
    """Retain layer-specific evaluation while preparing each input once."""

    def test_overlapping_selections_parse_once(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        boundary_case: BoundaryCase,
    ) -> None:
        """Apply both layers' restrictions to one shared parsed source."""
        analyzer = (
            python_boundaries._PythonBoundaryAnalyzer
            if boundary_case.domain == 'python-boundaries'
            else swift_boundaries._SwiftBoundaryAnalyzer
        )
        parse = Mock(wraps=analyzer.parse)
        monkeypatch.setattr(analyzer, 'parse', staticmethod(parse))
        domain = boundary_case.domain
        (tmp_path / 'popo.toml').write_text(
            ''.join(
                f'[[{domain}.layers]]\nname="{name}"\n'
                'include=["source"]\nallowed-imports=[]\n'
                for name in ('first', 'second')
            ),
            encoding='utf-8',
        )
        (tmp_path / 'source').write_text('import Blocked', encoding='utf-8')
        before = snapshot_files(tmp_path)
        assert boundary_case.validate(load_boundaries_config(tmp_path, domain)) == [
            f'source:1: {name}: forbidden import Blocked'
            for name in ('first', 'second')
        ]
        parse.assert_called_once()
        assert snapshot_files(tmp_path) == before


# !SECTION
