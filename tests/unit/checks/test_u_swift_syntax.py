"""
:mod:`tests.unit.checks.test_u_swift_syntax` module.

Verify concrete Swift syntax, UTF-8 positions and bounded recovery contracts.
"""

from pathlib import Path

import pytest

from popo.checks import _swift_declarations, _swift_syntax, swift_boundaries
from popo.config.source_boundaries import load_boundaries_config
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestSwiftSyntax:
    """
    Keep native syntax inspection offline and preserve original locations.
    """

    def test_comment_locations_and_unicode_offsets(
        self,
    ) -> None:
        """Map UTF-8 node columns to character spans after non-ASCII text."""
        source = (
            '/// Overview\r\n/* outer /* inner */ comment */\nlet é = "😀"; struct Ω {}'
        )
        syntax = _swift_syntax.parse(source)
        assert not syntax.root.has_error
        nominal = next(
            n for n in _swift_syntax.nodes(syntax.root) if n.type == 'class_declaration'
        )
        assert syntax.offset(nominal) == source.index('struct')
        assert syntax.documentation == frozenset({1})
        assert 'outer' not in syntax.code
        assert '😀' not in syntax.code
        assert len(source) == len(syntax.code)

    @pytest.mark.parametrize(
        'source,expected',
        [
            ('', (0, 1)),
            ('abc', (0, 4)),
            ('\n', (0, 1, 2)),
            ('\n\n', (0, 1, 2, 3)),
            ('é😀\r\nabc', (0, 4, 8)),
            ('é😀\r\n', (0, 4, 5)),
            ('a\rb\u2028c', (0, 6)),
        ],
    )
    def test_line_offsets_preserve_original_character_positions(
        self,
        source: str,
        expected: tuple[int, ...],
    ) -> None:
        """Count LF boundaries without changing Unicode or the end sentinel."""
        assert _swift_syntax.parse(source).line_offsets == expected

    @pytest.mark.parametrize(
        'literal',
        (
            '"struct Ghost {}"',
            '"""\nstruct Ghost {}\n"""',
            '#"struct Ghost {}"#',
            '/struct Ghost {}/',
            '#/struct Ghost {}/#',
            '"é😀 \\(Ghost())"',
        ),
    )
    def test_literals_do_not_supply_declarations(
        self,
        literal: str,
    ) -> None:
        """
        Mask ordinary/raw/regex literals and their interpolation contents.
        """
        source = f'let text = {literal}\nstruct Real {{}}'
        syntax = _swift_syntax.parse(source)
        assert len(syntax.code) == len(source)
        assert [i for i, c in enumerate(source) if c == '\n'] == [
            i for i, c in enumerate(syntax.code) if c == '\n'
        ]
        assert 'Ghost' not in syntax.code
        assert syntax.documentation == frozenset()
        assert [
            d.facts.kind for d in _swift_declarations.parse(source).declarations
        ] == [
            'let',
            'struct',
        ]

    @pytest.mark.parametrize('indent', ('  ', '\t', '\u00a0'))
    @pytest.mark.parametrize(
        'suffix,continues',
        [
            ('async', True),
            ('throws', True),
            ('rethrows', True),
            ('-> Int', True),
            ('where T: P', True),
            ('struct Next', False),
        ],
    )
    def test_multiline_signature_continuation_boundaries(
        self,
        indent: str,
        suffix: str,
        continues: bool,
    ) -> None:
        """Retain whitespace and keyword boundaries without copying suffixes."""
        code = f' f()\n{indent}{suffix} {{}}'
        signature = _swift_declarations._signature(code, 0)
        assert signature.parameter_names == ()
        assert signature.end == (code.index('{') if continues else code.index('\n'))
        assert signature.tail == (f'\n{indent}{suffix} ' if continues else '')

    @pytest.mark.parametrize('opening', ('/* unfinished', '/* outer /* inner */'))
    def test_unterminated_comments_cannot_supply_facts(
        self,
        opening: str,
    ) -> None:
        """Do not let grammar recovery turn an open block comment into code."""
        source = (
            f'let prefix = 1\n{opening}\n/// Fake\nimport Blocked\nstruct Ghost {{}}'
        )
        syntax = _swift_syntax.parse(source)
        assert syntax.documentation == frozenset()
        assert 'Ghost' not in syntax.code
        assert swift_boundaries._imports(syntax) == []
        assert [
            d.facts.kind for d in _swift_declarations.parse(source).declarations
        ] == [
            'let',
        ]
        assert len(source) == len(syntax.code)

    def test_same_line_members_do_not_borrow_parent_documentation(
        self,
    ) -> None:
        """
        Discover same-line types/members but attach docs only to their owner.
        """
        facts = _swift_declarations.parse(
            '/// Overview\nstruct A { func f(x: Int) {} }; struct B {}',
        )
        assert [d.facts.kind for d in facts.declarations] == [
            'struct',
            'func',
            'struct',
        ]
        assert [d.facts.documentation for d in facts.declarations] == [
            ' Overview',
            '',
            '',
        ]
        assert facts.declarations[1].facts.parameter_names == ('x',)

    def test_recovery_retains_unsupported_callable_diagnostics(
        self,
    ) -> None:
        """
        Preserve bounded contracts when the grammar recovers malformed code.
        """
        source = (
            '/// Overview\n@MainActor\nstruct C {\n let value: Int\n'
            ' func +(x: Int) -> Int { x }\n}\n???'
        )
        assert _swift_syntax.parse(source).root.has_error
        declarations = _swift_declarations.parse(source).declarations
        assert [d.facts.kind for d in declarations] == ['struct', 'let', 'func']
        assert declarations[0].facts.documentation == ' Overview'
        assert declarations[-1].facts.parameter_names is None


class TestSwiftBoundarySyntax:
    """Collect structural imports and types without executing Swift tools."""

    @pytest.mark.parametrize(
        'owner',
        (
            'struct First {}; struct Target {}',
            'typealias Target = Int',
            'protocol Target {}',
            'actor Target {}',
            'enum Target { case value }',
            'class Host { class func helper() {} }; struct Target {}',
        ),
    )
    def test_structural_type_ownership(
        self,
        tmp_path: Path,
        owner: str,
    ) -> None:
        """
        Recognize native nominal/typealias names including same-line types.
        """
        (tmp_path / 'owner.swift').write_text(owner, encoding='utf-8')
        (tmp_path / 'core.swift').write_text('let value: Target', encoding='utf-8')
        (tmp_path / 'popo.toml').write_text(
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["core.swift"]\n'
            'forbidden-layers=["owner"]\n'
            '[[swift-boundaries.layers]]\nname="owner"\ninclude=["owner.swift"]',
            encoding='utf-8',
        )
        before = snapshot_files(tmp_path)
        assert swift_boundaries.validate(
            load_boundaries_config(
                tmp_path,
                'swift-boundaries',
            ),
        ) == ['core.swift:1: core: forbidden symbol Target']
        assert snapshot_files(tmp_path) == before

    def test_native_imports_and_regex_masking(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Inspect same-line attributed imports but ignore literal fake code.
        """
        (tmp_path / 'source.swift').write_text(
            'import Foundation; @preconcurrency import struct SwiftUI.View\n'
            'let regex = /Target/\nlet text = #"import Blocked"#',
            encoding='utf-8',
        )
        (tmp_path / 'popo.toml').write_text(
            '[[swift-boundaries.layers]]\nname="core"\ninclude=["*.swift"]\n'
            'allowed-imports=["Foundation"]\nforbidden-symbols=["Target"]',
            encoding='utf-8',
        )
        assert swift_boundaries.validate(
            load_boundaries_config(
                tmp_path,
                'swift-boundaries',
            ),
        ) == ['source.swift:1: core: forbidden import SwiftUI']


class TestSwiftDeclarationClassification:
    """Distinguish syntax node identities from keywords in other constructs."""

    @pytest.mark.parametrize(
        'kind',
        (
            'struct',
            'class',
            'enum',
            'protocol',
            'typealias',
            'func',
            'let',
            'var',
        ),
    )
    def test_selective_imports_do_not_supply_declarations(
        self,
        kind: str,
    ) -> None:
        """
        Ignore imported declaration keywords while retaining actual types.
        """
        source = f'import {kind} Package.Member\nstruct Actual {{}}'
        syntax = _swift_syntax.parse(source)
        assert not syntax.root.has_error
        facts = _swift_declarations.parse(source)
        assert [(d.facts.kind, d.facts.line) for d in facts.declarations] == [
            ('struct', 2),
        ]


class TestSwiftDocumentationLocations:
    """Keep native documentation selection independent of traversal order."""

    @pytest.mark.parametrize('reverse', (False, True))
    def test_documentation_lines_are_sorted_unique_and_standalone(
        self,
        reverse: bool,
    ) -> None:
        """
        Ignore literal text and trailing comments while retaining real docs.
        """
        syntax = _swift_syntax.parse(
            '/// Overview 😀.\nlet text = "/// not documentation"\n'
            '  /// Details.\nstruct Ω {}\nlet value = 1 /// trailing\n'
            '/* /// block comments do not supply DocC lines */',
        )
        owners = tuple(_swift_syntax.nodes(syntax.root)) * 2
        assert _swift_syntax.documentation_lines(
            reversed(owners) if reverse else owners,
            syntax.source,
        ) == (1, 3)
        assert syntax.documentation == frozenset({1, 3})


# !SECTION
