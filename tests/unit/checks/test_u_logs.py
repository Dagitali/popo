"""
:mod:`tests.unit.checks.test_u_logs` module.

Exercise redacted log diagnostics and artifact boundaries.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from popo.checks import logs
from popo.config import ConfigurationError
from popo.config.source_checks import load_source_check
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestRedactedLogs:
    """Keep private lines out of both rule findings and read errors."""

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

    @pytest.mark.parametrize(
        'separator',
        ['\n', '\r', '\r\n', '\v', '\f', '\x85', '\u2028', '\u2029'],
    )
    @pytest.mark.parametrize('trailing', [False, True])
    def test_multiline_literals_are_rejected(
        self: Self,
        tmp_path: Path,
        separator: str,
        trailing: bool,
    ) -> None:
        """Reject literals that cannot occur within a scanned log line."""
        literal = 'WARNING' + separator + ('' if trailing else 'PRIVATE')
        (tmp_path / 'popo.toml').write_text(
            '[logs]\ninclude=["*.log"]\npatterns={warning=' + json.dumps(literal) + '}',
            encoding='utf-8',
        )
        with pytest.raises(ConfigurationError, match='single-line literals'):
            load_source_check(tmp_path, 'logs')

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

    @pytest.mark.parametrize('root_override', [False, True])
    def test_overlapping_rules_preserve_redacted_order(
        self: Self,
        tmp_path: Path,
        root_override: bool,
    ) -> None:
        """Report each matching rule once per line, in declaration order."""
        (tmp_path / 'popo.toml').write_text(
            '[logs]\ninclude=["**/*.log"]\npatterns={warning="WARN", broad="WAR"}',
            encoding='utf-8',
        )
        boundary = tmp_path / 'artifacts' if root_override else tmp_path
        boundary.mkdir(exist_ok=True)
        for filename in ('z.log', 'a.log'):
            (boundary / filename).write_text(
                'WARN WARN PRIVATE\nclean\nWARN PRIVATE',
                encoding='utf-8',
            )
        config = load_source_check(tmp_path, 'logs')
        before = snapshot_files(tmp_path)
        assert logs.validate(config, boundary if root_override else None) == [
            f'{filename}:{line}: {rule}'
            for filename in ('a.log', 'z.log')
            for line in (1, 3)
            for rule in ('warning', 'broad')
        ]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize('error', [OSError, ValueError])
    @pytest.mark.parametrize('root_override', [False, True])
    def test_root_resolution_failures_are_redacted(
        self: Self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        error: type[Exception],
        root_override: bool,
    ) -> None:
        """
        Report inaccessible input roots without exposing exception details.
        """
        (tmp_path / 'popo.toml').write_text(
            '[logs]\ninclude=["*.log"]\npatterns={warning="WARNING"}',
        )
        config = load_source_check(tmp_path, 'logs')

        def fail_resolution(
            path: Path,
        ) -> Path:
            raise error('PRIVATE ROOT')

        monkeypatch.setattr(Path, 'resolve', fail_resolution)
        root = tmp_path / 'artifacts' if root_override else None
        assert logs.validate(config, root) == ['cannot resolve selected input root']


# !SECTION
