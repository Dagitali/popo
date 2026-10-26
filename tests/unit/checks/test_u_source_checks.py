"""
:mod:`tests.unit.checks.test_u_source_checks` module.

Exercise source rules, confined discovery and redacted artifact findings.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.checks import logs, python_source, swift_documentation
from popo.config._common import ConfigurationError
from popo.config.source_checks import load_source_check

# SECTION: TESTS


class TestSourcePolicy:
    """Use fresh synthetic policies; never inspect host financial inputs."""

    @pytest.mark.parametrize(
        'settings',
        (
            'include = []',
            'include = ["../outside.py"]',
            'include = ["/outside.py"]',
            'include = ["*.py"]\nannotations = 1',
            'include = ["*.py"]\nmax-module-lines = 0',
            'include = ["*.py"]\nunknown = true',
        ),
    )
    def test_invalid_configuration(
        self: Self,
        tmp_path: Path,
        settings: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text('[python-source]\n' + settings)
        with pytest.raises(ConfigurationError):
            load_source_check(tmp_path, 'python-source')

    def test_missing_policy_is_explicit(
        self: Self,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(ConfigurationError):
            load_source_check(tmp_path, 'python-source')

    @pytest.mark.parametrize(
        'source,option,diagnostic',
        (
            ('def f(x): pass', 'annotations = true', 'missing signature'),
            ('def f(x: int) -> None: pass', 'parameter-lines = true', 'separate lines'),
            (
                'class C:\n def z(self): pass\n def a(self): pass',
                'alphabetical-methods = true',
                'not alphabetical',
            ),
            ('"""Long documentation"""', 'docstring-width = 10', 'docstring line'),
            ('x = 1\ny = 2', 'max-module-lines = 1', 'module exceeds'),
            ('def broken(', '', 'invalid Python'),
            ('async def f(x): pass', 'annotations = true', 'missing signature'),
            (
                'def f(\n x: int = (\n  1\n ),\n) -> None: pass',
                'parameter-lines = true',
                'separate lines',
            ),
        ),
    )
    def test_python_rules(
        self: Self,
        tmp_path: Path,
        source: str,
        option: str,
        diagnostic: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[python-source]\ninclude = ["*.py"]\n' + option,
        )
        (tmp_path / 'sample.py').write_text(source)
        findings = python_source.validate(load_source_check(tmp_path, 'python-source'))
        assert any(diagnostic in finding for finding in findings)
        assert all(source not in finding for finding in findings)

    def test_annotated_multiline_signatures_and_self_exception(
        self: Self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[python-source]\ninclude = ["*.py"]\nannotations = true\n'
            'parameter-lines = true\nalphabetical-methods = true',
        )
        (tmp_path / 'sample.py').write_text(
            'from typing import Self\nclass C:\n'
            ' def a(self: Self) -> None: pass\n'
            ' async def b(\n  self: Self,\n  x: int = 1,\n'
            '  /,\n  *args: int,\n  y: int = 2,\n  **kwargs: int,\n'
            ' ) -> None: pass\n',
        )
        assert (
            python_source.validate(load_source_check(tmp_path, 'python-source')) == []
        )

    @pytest.mark.parametrize('kind', ('missing', 'escaped', 'excluded', 'undecodable'))
    def test_inputs_fail_closed(
        self: Self,
        tmp_path: Path,
        kind: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[python-source]\ninclude = ["*.py"]\nexclude = ["ignored.py"]',
        )
        if kind == 'escaped':
            (tmp_path / 'sample.py').symlink_to(tmp_path.parent / 'outside.py')
        elif kind == 'excluded':
            (tmp_path / 'ignored.py').write_text('x = 1')
        elif kind == 'undecodable':
            (tmp_path / 'sample.py').write_bytes(b'\xff')
        assert python_source.validate(load_source_check(tmp_path, 'python-source'))


class TestRedactedLogs:
    """Keep private lines out of both rule findings and read errors."""

    @pytest.mark.parametrize('root_override', (False, True))
    def test_named_literal_findings_and_clean_inputs(
        self: Self,
        tmp_path: Path,
        root_override: bool,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[logs]\ninclude = ["**/*.log"]\n'
            '[logs.patterns]\nlayout = "Invalid frame dimension"',
        )
        artifact = tmp_path / 'artifacts' if root_override else tmp_path
        artifact.mkdir(exist_ok=True)
        log = artifact / 'private.log'
        log.write_text('Normal\nInvalid frame dimension: PRIVATE BALANCE\n')
        config = load_source_check(tmp_path, 'logs')
        boundary = artifact if root_override else None
        assert logs.validate(config, boundary) == ['private.log:2: layout']
        log.write_text('Normal\n')
        assert logs.validate(config, boundary) == []
        log.unlink()
        assert logs.validate(config, boundary)

    @pytest.mark.parametrize('patterns', ('{}', '{ bad = "" }', '{ "bad\\nID" = "x" }'))
    def test_invalid_patterns(
        self: Self,
        tmp_path: Path,
        patterns: str,
    ) -> None:
        (tmp_path / 'popo.toml').write_text(
            '[logs]\ninclude = ["*.log"]\npatterns = ' + patterns,
        )
        with pytest.raises(ConfigurationError):
            load_source_check(tmp_path, 'logs')


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
            '[swift-documentation]\ninclude = ["*.swift"]',
        )
        (tmp_path / 'Rule.swift').write_text(source)
        findings = swift_documentation.validate(
            load_source_check(tmp_path, 'swift-documentation'),
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
            '[swift-documentation]\ninclude = ["*.swift"]\nsource-guide = "Guide.md"',
        )
        (tmp_path / 'Rule.swift').write_text(
            '/// File and rule overview.\nstruct Rule {}',
        )
        guide = tmp_path / 'Guide.md'
        guide.write_text('`Other/Rule.swift`')
        config = load_source_check(tmp_path, 'swift-documentation')
        assert 'missing source-guide entry' in '\n'.join(
            swift_documentation.validate(config),
        )
        guide.write_text('`Rule.swift`')
        assert swift_documentation.validate(config) == []


# !SECTION
