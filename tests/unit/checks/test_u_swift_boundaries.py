"""
:mod:`tests.unit.checks.test_u_swift_boundaries` module.

Exercise consumer layouts, lexical masking and directional boundary policy.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Self
from unittest.mock import Mock

import pytest

from popo.checks import swift_boundaries
from popo.checks.swift_boundaries import validate
from popo.config.swift_boundaries import load_swift_boundaries_config
from tests.support.files import snapshot_files

# SECTION: FIXTURES


@pytest.fixture(
    name='boundary_project',
    params=(('Core', 'Data', 'UI'), ('Engine', 'Adapters', 'Screens')),
)
def boundary_project_fixture(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> tuple[Path, tuple[str, str, str]]:
    """
    Build two unrelated layouts with the same consumer-selected graph.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Disposable consumer root.
    request : pytest.FixtureRequest
        Independent folder-name layout.

    Returns
    -------
    tuple[pathlib.Path, tuple[str, str, str]]
        Consumer root and core/storage/presentation directory names.
    """
    core, data, ui = request.param
    (tmp_path / 'popo.toml').write_text(
        '[swift-boundaries]\n'
        '[[swift-boundaries.layers]]\nname="core"\n'
        f'include=["{core}/**/*.swift"]\nallowed-imports=["Foundation"]\n'
        'forbidden-layers=["data","ui"]\nforbidden-symbols=["UserDefaults"]\n'
        '[[swift-boundaries.layers]]\nname="data"\n'
        f'include=["{data}/**/*.swift"]\nforbidden-layers=["ui"]\n'
        '[[swift-boundaries.layers]]\nname="ui"\n'
        f'include=["{ui}/**/*.swift"]\n',
    )
    for folder, text in (
        (core, 'import Foundation\nstruct Rule {}'),
        (data, 'struct Store { let rule: Rule }'),
        (ui, 'struct Screen {}'),
    ):
        path = tmp_path / folder / 'Source.swift'
        path.parent.mkdir()
        path.write_text(text)
    return tmp_path, request.param


# !SECTION


# SECTION: TESTS


class TestSwiftBoundaries:
    """Report only configured metadata, not arbitrary source contents."""

    def test_class_methods_do_not_declare_a_type_named_func(
        self: Self,
        boundary_project: tuple[Path, tuple[str, str, str]],
    ) -> None:
        """
        Do not confuse class func with a nominal type declaration.

        Parameters
        ----------
        boundary_project : tuple[Path, tuple[str, str, str]]
            Disposable repository and its core/storage/presentation directory
            names.
        """
        root, (core, data, _) = boundary_project
        (root / data / 'Source.swift').write_text(
            'class Host {\n class func helper() {}\n}',
        )
        (root / core / 'Source.swift').write_text('func allowed() {}')
        assert validate(load_swift_boundaries_config(root)) == []

    @pytest.mark.parametrize(
        'text',
        (
            '// Store UserDefaults\n',
            '/* Store /* UserDefaults */ Screen */\n',
            'let text = "Store UserDefaults Screen"\n',
            'let text = #"""\nStore UserDefaults Screen\n"""#\n',
        ),
    )
    def test_comments_and_strings_are_masked(
        self: Self,
        boundary_project: tuple[Path, tuple[str, str, str]],
        text: str,
    ) -> None:
        """
        Reuse the existing Swift masker instead of a second comment regex.

        Parameters
        ----------
        boundary_project : tuple[Path, tuple[str, str, str]]
            Disposable repository and its core/storage/presentation directory
            names.
        text : str
            Swift comment or string content that lexical masking must ignore.
        """
        root, (core, _, _) = boundary_project
        with (root / core / 'Source.swift').open('a') as stream:
            stream.write('\n' + text)
        assert validate(load_swift_boundaries_config(root)) == []

    @pytest.mark.parametrize(
        'source,rule',
        (
            ('import SwiftUI\nstruct Rule {}', 'forbidden import SwiftUI'),
            (
                '@preconcurrency import struct SwiftUI.View\nstruct Rule {}',
                'forbidden import SwiftUI',
            ),
            ('let value: Store', 'forbidden symbol Store'),
            ('let value: Screen', 'forbidden symbol Screen'),
            ('let value: UserDefaults', 'forbidden symbol UserDefaults'),
        ),
    )
    def test_forbidden_dependencies(
        self: Self,
        boundary_project: tuple[Path, tuple[str, str, str]],
        source: str,
        rule: str,
    ) -> None:
        """
        Keep architecture choices independent of branded directory names.

        Parameters
        ----------
        boundary_project : tuple[Path, tuple[str, str, str]]
            Disposable repository and its core/storage/presentation directory
            names.
        source : str
            Synthetic Swift source introducing the configured dependency.
        rule : str
            Expected fixed import or symbol diagnostic fragment.
        """
        root, (core, _, _) = boundary_project
        (root / core / 'Source.swift').write_text(source)
        findings = validate(load_swift_boundaries_config(root))
        assert len(findings) == 1
        assert rule in findings[0]

    @pytest.mark.parametrize('case', ('deleted', 'undecodable', 'escaped'))
    def test_missing_or_unreadable_layers_cannot_pass(
        self: Self,
        boundary_project: tuple[Path, tuple[str, str, str]],
        symlink: Callable[[Path, Path], None],
        case: str,
    ) -> None:
        """
        Incomplete source inventories cannot establish architecture safety.

        Parameters
        ----------
        boundary_project : tuple[Path, tuple[str, str, str]]
            Disposable repository and its core/storage/presentation directory
            names.
        symlink : collections.abc.Callable[[pathlib.Path, pathlib.Path], None]
            Platform-aware link creator; unavailable link operations skip.
        case : str
            Independent missing, malformed, unreadable or escaping input
            scenario.
        """
        root, (_, data, _) = boundary_project
        path = root / data / 'Source.swift'
        if case == 'undecodable':
            path.write_bytes(b'\xff')
        else:
            path.unlink()
            if case == 'escaped':
                outside = root.parent / 'outside.swift'
                outside.write_bytes(b'\xffPRIVATE outside source')
                symlink(path, outside)
        before = snapshot_files(root)
        expected = {
            'deleted': [f'data: no inputs match: {data}/**/*.swift'],
            'undecodable': [f'{data}/Source.swift: cannot read UTF-8 input'],
            'escaped': [
                f'data: {data}/Source.swift: input escapes selected root',
                f'data: no inputs match: {data}/**/*.swift',
            ],
        }
        assert validate(load_swift_boundaries_config(root)) == expected[case]
        assert snapshot_files(root) == before

    @pytest.mark.parametrize(
        'declaration',
        (
            'struct Store {}',
            'class Store {}',
            'enum Store {}',
            'actor Store {}',
            'protocol Store {}',
            'typealias Store = Int',
        ),
    )
    def test_nominal_and_alias_names_are_collected(
        self: Self,
        boundary_project: tuple[Path, tuple[str, str, str]],
        declaration: str,
    ) -> None:
        """
        Include the declaration categories supported by the boundary guard.

        Parameters
        ----------
        boundary_project : tuple[Path, tuple[str, str, str]]
            Disposable repository and its core/storage/presentation directory
            names.
        declaration : str
            Nominal or typealias syntax supplying a forbidden type name.
        """
        root, (core, data, _) = boundary_project
        (root / data / 'Source.swift').write_text(declaration)
        (root / core / 'Source.swift').write_text('let dependency: Store')
        assert any(
            'forbidden symbol Store' in item
            for item in validate(load_swift_boundaries_config(root))
        )

    @pytest.mark.parametrize('allowed', (None, (), ('Foundation',)))
    def test_optional_import_policy_keeps_symbol_checks(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        allowed: tuple[str, ...] | None,
    ) -> None:
        """
        Skip absent import policy without suppressing import-token symbols.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        allowed : tuple[str, ...] | None
            Permitted imports, or None to disable the allowlist.
        """
        policy = (
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["source.swift"]\n'
            'forbidden-symbols=["Foundation"]\n'
        )
        if allowed is not None:
            policy += f'allowed-imports={list(allowed)!r}\n'
        (tmp_path / 'popo.toml').write_text(policy, encoding='utf-8')
        (tmp_path / 'source.swift').write_text('import Foundation\n', encoding='utf-8')
        imports = Mock(wraps=swift_boundaries._imports)
        monkeypatch.setattr(swift_boundaries, '_imports', imports)
        assert validate(load_swift_boundaries_config(tmp_path)) == [
            *(
                ['source.swift:1: core: forbidden import Foundation']
                if allowed == ()
                else []
            ),
            'source.swift:1: core: forbidden symbol Foundation',
        ]
        assert imports.call_count == int(allowed is not None)


# !SECTION
