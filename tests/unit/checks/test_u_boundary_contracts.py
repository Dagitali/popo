"""
:mod:`tests.unit.checks.test_u_boundary_contracts` module.

Check shared language-analyzer ordering, failures and read-only contracts.
"""

from pathlib import Path

import pytest

from popo.checks import python_boundaries, swift_boundaries
from popo.config.source_boundaries import load_boundaries_config
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestBoundaryContracts:
    """Exercise both structural analyzers through their public validators."""

    @pytest.mark.parametrize('language', ('python', 'swift'))
    def test_diagnostic_order_and_read_only_inputs(
        self,
        tmp_path: Path,
        language: str,
    ) -> None:
        """Keep selection failures before imports and deduplicated symbols."""
        domain = f'{language}-boundaries'
        (tmp_path / 'popo.toml').write_text(
            f'[[{domain}.layers]]\nname="core"\n'
            'include=["missing", "source"]\nallowed-imports=[]\n'
            'forbidden-symbols=["Forbidden"]\n',
            encoding='utf-8',
        )
        (tmp_path / 'source').write_text(
            'import Forbidden\nx = Forbidden + Forbidden'
            if language == 'python'
            else 'import Forbidden\nlet x = Forbidden + Forbidden',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        config = load_boundaries_config(tmp_path, domain)
        validator = python_boundaries if language == 'python' else swift_boundaries
        findings = validator.validate(config)
        assert len(findings) == (3 if language == 'python' else 4)
        assert 'missing' in findings[0]
        assert findings[1] == 'source:1: core: forbidden import Forbidden'
        if language == 'swift':
            assert findings[2] == 'source:1: core: forbidden symbol Forbidden'
        assert findings[-1] == 'source:2: core: forbidden symbol Forbidden'
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('language', ('python', 'swift'))
    def test_unreadable_source_fails_without_source_disclosure(
        self,
        tmp_path: Path,
        language: str,
    ) -> None:
        """Return redacted decoding diagnostics for both language front ends."""
        domain = f'{language}-boundaries'
        (tmp_path / 'popo.toml').write_text(
            f'[[{domain}.layers]]\nname="core"\ninclude=["source"]',
            encoding='utf-8',
        )
        (tmp_path / 'source').write_bytes(b'PRIVATE\xff')
        before = snapshot_files(tmp_path)
        validator = python_boundaries if language == 'python' else swift_boundaries
        findings = validator.validate(load_boundaries_config(tmp_path, domain))
        assert findings
        assert 'PRIVATE' not in '\n'.join(findings)
        assert snapshot_files(tmp_path) == before


# !SECTION
