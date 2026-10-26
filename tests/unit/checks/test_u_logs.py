"""
:mod:`tests.unit.checks.test_u_logs` module.

Exercise redacted log diagnostics and artifact boundaries.
"""

from pathlib import Path
from typing import Self

import pytest

from popo.checks import logs
from popo.config import ConfigurationError
from popo.config.source_checks import load_source_check

# SECTION: TESTS


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

        def fail_resolution(path: Path) -> Path:
            raise error('PRIVATE ROOT')

        monkeypatch.setattr(Path, 'resolve', fail_resolution)
        root = tmp_path / 'artifacts' if root_override else None
        assert logs.validate(config, root) == ['cannot resolve selected input root']

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


# !SECTION
