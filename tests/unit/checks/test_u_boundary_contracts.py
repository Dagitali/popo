"""
:mod:`tests.unit.checks.test_u_boundary_contracts` module.

Check shared language-analyzer ordering, failures and read-only contracts.
"""

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, cast
from unittest.mock import Mock

import pytest

from popo.checks import _source_boundaries, python_boundaries, swift_boundaries
from popo.config.source_boundaries import (
    BoundaryConfig,
    BoundaryLayer,
    load_boundaries_config,
)
from popo.config.source_checks import SourceCheckConfig
from tests.support.files import snapshot_files

# SECTION: NAMED TUPLES


class BoundaryCase(NamedTuple):
    """
    Cover boundary case.

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
        """
        Keep selection failures before imports and deduplicated symbols.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        boundary_case : BoundaryCase
            Language-specific boundary policy and source-writing helpers.
        """
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

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        boundary_case : BoundaryCase
            Language-specific boundary policy and source-writing helpers.
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


class TestImportMatching:
    """Preserve exact names, dot boundaries and native descendant policies."""

    @pytest.mark.parametrize('descendants', (False, True))
    @pytest.mark.parametrize(
        'target,exact,descendant',
        [
            ('Allowed', '', ''),
            ('Allowed.child', 'forbidden import', ''),
            ('AllowedExtra', 'forbidden import', 'forbidden import'),
            ('allowed', 'forbidden import', 'forbidden import'),
            ('Blocked', 'forbidden layer import', 'forbidden layer import'),
            ('Blocked.child', 'forbidden import', 'forbidden layer import'),
        ],
    )
    def test_exact_and_descendant_matching(
        self,
        tmp_path: Path,
        descendants: bool,
        target: str,
        exact: str,
        descendant: str,
    ) -> None:
        """
        Keep forbidden ownership ahead of an overlapping allowlist.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        descendants : bool
            Whether dotted descendant matching is enabled.
        target : str
            Import target tested against the configured matching rule.
        exact : str
            Exact name tested against boundary matching.
        descendant : str
            Dotted descendant name tested against the boundary rule.
        """
        layer = BoundaryLayer(
            'core',
            SourceCheckConfig(tmp_path, 'python-source', (), (), {}),
            ('Allowed', 'Blocked'),
            (),
            (),
        )
        expected = descendant if descendants else exact
        references = iter((_source_boundaries.ImportReference(3, target),))
        assert _source_boundaries.import_findings(
            references,
            layer,
            'source',
            forbidden_targets={'Blocked'},
            allow_descendants=descendants,
        ) == ([f'source:3: core: {expected} {target}'] if expected else [])
        assert list(references) == []


class TestOverlappingBoundaryLayers:
    """Retain layer-specific evaluation while preparing each input once."""

    def test_overlapping_layers_read_once(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        boundary_case: BoundaryCase,
    ) -> None:
        """
        Check overlapping selections without repeating source reads.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        boundary_case : BoundaryCase
            Language-specific boundary policy and source-writing helpers.
        """
        read = Mock(wraps=_source_boundaries.read_source)
        monkeypatch.setattr(_source_boundaries, 'read_source', read)

        domain = boundary_case.domain
        (tmp_path / 'source').write_text('', encoding='utf-8')
        (tmp_path / 'popo.toml').write_text(
            ''.join(
                f'[[{domain}.layers]]\nname="{name}"\ninclude=["source"]\n'
                for name in ('one', 'two')
            ),
            encoding='utf-8',
        )
        paths, sources, failures = _source_boundaries.boundary_sources(
            load_boundaries_config(tmp_path, domain),
        )
        assert len(paths) == 2
        assert sources == {tmp_path / 'source': ''}
        read.assert_called_once_with(tmp_path / 'source', tmp_path)
        assert failures == []

    @pytest.mark.parametrize('readable', (False, True))
    def test_overlapping_selections_prepare_once(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        boundary_case: BoundaryCase,
        readable: bool,
    ) -> None:
        """
        Prepare each input once and preserve independent layer findings.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        boundary_case : BoundaryCase
            Language-specific boundary policy and source-writing helpers.
        readable : bool
            Whether the selected input can be read.
        """
        analyzer = (
            python_boundaries._PythonBoundaryAnalyzer
            if boundary_case.domain == 'python-boundaries'
            else swift_boundaries._SwiftBoundaryAnalyzer
        )
        parse = Mock(wraps=analyzer.parse)
        monkeypatch.setattr(analyzer, 'parse', staticmethod(parse))
        targets = Mock(wraps=analyzer.targets)
        monkeypatch.setattr(analyzer, 'targets', staticmethod(targets))
        domain = boundary_case.domain
        (tmp_path / 'popo.toml').write_text(
            ''.join(
                f'[[{domain}.layers]]\nname="{name}"\n'
                'include=["source"]\nallowed-imports=[]\n'
                for name in ('first', 'second')
            ),
            encoding='utf-8',
        )
        path = tmp_path / 'source'
        if readable:
            text = 'import Blocked\n' + (
                'class Owned:\n pass'
                if domain == 'python-boundaries'
                else 'struct Owned {}'
            )
            path.write_text(text, encoding='utf-8')
        else:
            path.write_bytes(b'PRIVATE\xff')
        before = snapshot_files(tmp_path)
        assert boundary_case.validate(load_boundaries_config(tmp_path, domain)) == (
            [
                f'source:1: {name}: forbidden import Blocked'
                for name in ('first', 'second')
            ]
            if readable
            else ['source: cannot read UTF-8 input']
        )
        if readable:
            parse.assert_called_once()
        else:
            parse.assert_not_called()
        targets.assert_called_once()
        assert targets.call_args.args[:2] == (path, tmp_path)
        assert (targets.call_args.args[2] is None) is (not readable)
        assert snapshot_files(tmp_path) == before


class TestSymbolReporting:
    """
    Cover symbol reporting.

    Share exact matching, deduplication and order across native collectors.
    """

    @pytest.mark.parametrize('forbidden', [(), ('Blocked', 'Other')])
    def test_native_candidates_are_filtered_once_in_location_order(
        self,
        forbidden: tuple[str, ...],
    ) -> None:
        """
        Skip unused candidates or consume once with unique ordered findings.

        Parameters
        ----------
        forbidden : tuple[str, ...]
            Names explicitly forbidden by the boundary policy.
        """
        reference = _source_boundaries.SymbolReference
        observations = (
            reference(3, 'Other'),
            reference(2, 'Other'),
            reference(2, 'Blocked'),
            reference(2, 'Blocked'),
            reference(1, 'blocked'),
            reference(1, 'Allowed'),
        )
        candidates = iter(observations)
        assert _source_boundaries.symbol_findings(
            candidates,
            forbidden,
            'source',
            'Core',
        ) == (
            [
                'source:2: Core: forbidden symbol Blocked',
                'source:2: Core: forbidden symbol Other',
                'source:3: Core: forbidden symbol Other',
            ]
            if forbidden
            else []
        )
        assert list(candidates) == ([] if forbidden else list(observations))


# !SECTION
