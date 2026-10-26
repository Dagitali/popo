"""
:mod:`tests.unit.checks.test_u_swift_source` module.

Exercise Swift source policy and language-specific findings.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.checks import _swift_declarations, swift_source
from popo.checks._swift_declarations import lexical_view
from popo.config.source_checks import load_source_check
from tests.support.files import FileWriter

# SECTION: TESTS


class TestSwiftDocumentation:
    """Check nominal documentation without interpreting strings as code."""

    @pytest.mark.parametrize(
        'source,expected',
        (
            ('struct Rule {}', 'missing file overview'),
            (
                '/// File overview.\nimport Foundation\nstruct Rule {}',
                'missing declaration documentation',
            ),
            (
                '/// File overview.\nimport Foundation\n/// Rule.\nstruct Rule {}',
                'missing blank line',
            ),
            (
                '/// File overview.\nimport Foundation\n\n/// Rule.\n'
                '@MainActor\nstruct Rule {}',
                '',
            ),
            (
                '/// File overview.\nlet text = #"""\nstruct Fake {}\n"""#\n'
                '/* outer /* nested */ struct Fake {} */',
                '',
            ),
        ),
    )
    def test_documentation_rules(
        self: Self,
        tmp_path: Path,
        source: str,
        expected: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[swift-source]\ninclude = ["*.swift"]',
        )
        (tmp_path / 'Rule.swift').write_text(source)
        findings = swift_source.validate(
            load_source_check(tmp_path, 'swift-source'),
        )
        if expected:
            assert any(expected in finding for finding in findings)
        else:
            assert findings == []

    def test_guide_requires_exact_relative_source_entry(
        self: Self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[swift-source]\ninclude = ["*.swift"]\nsource-guide = "Guide.md"',
        )
        (tmp_path / 'Rule.swift').write_text(
            '/// File and rule overview.\nstruct Rule {}',
        )
        guide = tmp_path / 'Guide.md'
        guide.write_text('`Other/Rule.swift`')
        config = load_source_check(tmp_path, 'swift-source')
        assert 'missing source-guide entry' in '\n'.join(
            swift_source.validate(config),
        )
        guide.write_text('`Rule.swift`')
        assert swift_source.validate(config) == []


class TestSwiftLexicalBoundaries:
    """Keep callable bodies, escaped strings and unsupported input bounded."""

    @pytest.mark.parametrize(
        'source',
        [
            'let s = "escaped \\" quote" // ordinary comment',
            'let s = #"escaped \\#" quote"#',
            'let s = "unterminated',
            'let x = 1 /// trailing documentation is not an overview',
        ],
    )
    def test_masked_strings_and_trailing_comments(
        self,
        source: str,
    ) -> None:
        _, documentation = lexical_view(source)
        assert documentation == set()

    def test_members_exclude_callable_and_closure_bodies(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        write_file(
            'popo.toml',
            '[swift-source]\ninclude=["*.swift"]\nmember-docs=true\nraises-docs=true',
        )
        write_file(
            'sample.swift',
            (
                '/// Overview.\nstruct C {\n'
                '\n /// Method.\n func f() -> () throws -> Void {\n'
                '  let local = 1\n  return { throw Error() }\n }\n'
                '\n /// Property.\n var value = {\n'
                '  let local = 1\n  return local\n }()\n}'
            ),
        )
        assert swift_source.validate(load_source_check(tmp_path, 'swift-source')) == []

    @pytest.mark.parametrize(
        'source',
        [
            '/// Overview.\nfunc f(\n _ _: Int,\n) {}',
            '/// Overview.\nfunc f() ->\n Void\n{}',
            '/// Overview.\nfunc f()\nfunc g() {}',
            '/// Overview.\nfunc f(\n values: Dictionary<String, (Int) -> Int>,\n) {}',
        ],
    )
    def test_parameter_layout_subset(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
        source: str,
    ) -> None:
        write_file(
            'popo.toml',
            '[swift-source]\ninclude=["*.swift"]\nparameter-lines=true',
        )
        write_file('sample.swift', source)
        assert swift_source.validate(load_source_check(tmp_path, 'swift-source')) == []

    @pytest.mark.parametrize(
        'text,fragments',
        [
            (
                'value: (Int, Int), other: Int',
                ('value: (Int, Int)', ' other: Int'),
            ),
            (
                'value: Dictionary<String, Int> = [:], other: Int',
                ('value: Dictionary<String, Int> = [:]', ' other: Int'),
            ),
            (
                'value: Int = choose(1, 2), other: Int',
                ('value: Int = choose(1, 2)', ' other: Int'),
            ),
            (
                '\n value: Int,\n other: Int,\n',
                ('\n value: Int', '\n other: Int'),
            ),
        ],
    )
    def test_parameter_syntax_retains_offsets_and_delimiters(
        self: Self,
        text: str,
        fragments: tuple[str, ...],
    ) -> None:
        """
        Retain untrimmed spans while splitting only outer parameter commas.
        """
        parameters = _swift_declarations._parameters(text)
        assert tuple(parameter.text for parameter in parameters) == fragments
        assert tuple(parameter.offset for parameter in parameters) == tuple(
            text.index(fragment) for fragment in fragments
        )


class TestSwiftSource:
    """Check lexical contracts while retaining explicit parser boundaries."""

    @pytest.mark.parametrize(
        'parameter_docs',
        [
            '/// - Parameter values: Inputs.\n/// - Parameter transform: Callback.',
            '/// - Parameters:\n///   - values: Inputs.\n///   - transform: Callback.',
        ],
    )
    def test_complete_multiline_contract(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
        parameter_docs: str,
    ) -> None:
        write_file(
            'popo.toml',
            '[swift-source]\ninclude=["*.swift"]\nmember-docs=true\nparameter-docs=true\nreturn-docs=true\nraises-docs=true\nparameter-lines=true',
        )
        source = (
            '/// File overview.\nimport Foundation\n\n/// Transform inputs.\n'
            + parameter_docs
            + '\n/// - Returns: The result.\n/// - Throws: Invalid input.\n'
            '@MainActor\nfunc transform<T>(\n'
            ' values: Dictionary<String, Array<T>>,\n'
            ' transform: (T, Int) -> T = { value, _ in value },\n'
            ')\n async throws -> [T] { [] }'
        )
        write_file('sample.swift', source)
        assert swift_source.validate(load_source_check(tmp_path, 'swift-source')) == []

    @pytest.mark.parametrize(
        ('source', 'option', 'expected'),
        [
            ('func f(value: Int) {}', 'member-docs', 'missing declaration'),
            ('let value = 1', 'member-docs', 'missing declaration'),
            ('func f(value: Int) {}', 'parameter-docs', 'parameter documentation'),
            ('func f() -> Int { 1 }', 'return-docs', 'return documentation'),
            ('func f() throws {}', 'raises-docs', 'raises documentation'),
            ('func f() rethrows {}', 'raises-docs', 'raises documentation'),
            ('func f(x: Int, y: Int) {}', 'parameter-lines', 'separate lines'),
            (
                'func +(x: Int, y: Int) -> Int { 1 }',
                'return-docs',
                'unsupported callable',
            ),
            ('func broken(x: Int', 'parameter-docs', 'unsupported callable'),
            ('func broken {}', 'parameter-docs', 'unsupported callable'),
            ('func broken(value) {}', 'parameter-docs', 'unsupported callable'),
            ('func broken(: Int) {}', 'parameter-docs', 'unsupported callable'),
            (
                'func f(@Custom(label: 1) value: Int) {}',
                'parameter-docs',
                'unsupported callable',
            ),
        ],
    )
    def test_missing_contracts(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
        source: str,
        option: str,
        expected: str,
    ) -> None:
        write_file(
            'popo.toml',
            f'[swift-source]\ninclude=["*.swift"]\nfile-overviews=false\n{option}=true',
        )
        write_file('sample.swift', source)
        findings = swift_source.validate(load_source_check(tmp_path, 'swift-source'))
        assert len(findings) == 1
        assert expected in findings[0]

    def test_strings_cannot_supply_overviews_or_declarations(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
    ) -> None:
        source = (
            'let text = #"""\n/// Fake overview.\n'
            'func fake(x: Int) throws -> Int {}\n"""#\n'
            '/* outer /* nested */ func fake() {} */'
        )
        code, documentation = lexical_view(source)
        assert 'fake' not in code
        assert documentation == set()
        assert len(source) == len(code)
        write_file(
            'popo.toml',
            '[swift-source]\ninclude=["*.swift"]\nparameter-docs=true\nreturn-docs=true\nraises-docs=true',
        )
        write_file('sample.swift', source)
        assert swift_source.validate(load_source_check(tmp_path, 'swift-source')) == [
            'sample.swift: missing file overview',
        ]

    @pytest.mark.parametrize(
        'result',
        ['Void', '()', 'Swift.Void', 'Never', 'Swift.Never'],
    )
    def test_void_results_need_no_return_documentation(
        self: Self,
        write_file: FileWriter,
        tmp_path: Path,
        result: str,
    ) -> None:
        write_file('popo.toml', '[swift-source]\ninclude=["*.swift"]\nreturn-docs=true')
        write_file('sample.swift', f'/// Overview.\nfunc f() -> {result} {{}}')
        assert swift_source.validate(load_source_check(tmp_path, 'swift-source')) == []


# !SECTION
