"""
:mod:`tests.unit.config.test_u_logs` module.

Reject malformed named log patterns and multiline literal configuration.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from popo.config import ConfigurationError
from popo.config.source_checks import load_source_check
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestLogConfiguration:
    """Validate log pattern settings independently of checker execution."""

    @pytest.mark.parametrize(
        'patterns',
        (
            pytest.param('{}', id='empty-table'),
            pytest.param('{ bad = "" }', id='empty-literal'),
            pytest.param('{ "bad\\nID" = "x" }', id='multiline-rule-name'),
            *(
                pytest.param(
                    '{warning='
                    + json.dumps(
                        'WARNING' + separator + ('' if trailing else 'PRIVATE'),
                    )
                    + '}',
                    id=f'{label}-{'trailing' if trailing else 'embedded'}',
                )
                for label, separator in (
                    ('lf', '\n'),
                    ('cr', '\r'),
                    ('crlf', '\r\n'),
                    ('vertical-tab', '\v'),
                    ('form-feed', '\f'),
                    ('file-separator', '\x1c'),
                    ('group-separator', '\x1d'),
                    ('record-separator', '\x1e'),
                    ('next-line', '\x85'),
                    ('line-separator', '\u2028'),
                    ('paragraph-separator', '\u2029'),
                )
                for trailing in (False, True)
            ),
        ),
    )
    def test_invalid_patterns(
        self: Self,
        tmp_path: Path,
        write_file: FileWriter,
        patterns: str,
    ) -> None:
        """
        Reject empty literals, empty rule tables and malformed rule names.

        Literals must fit within one scanned log line. Embedded and trailing
        separators are rejected for every supported line-break spelling.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Shared UTF-8 writer creating the consumer policy.
        patterns : str
            Malformed rule tables, names or single-line literal declarations
            encoded as TOML, including embedded and trailing separators.
        """
        write_file(
            'popo.toml',
            '[logs]\ninclude = ["*.log"]\npatterns = ' + patterns,
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(
            ConfigurationError,
            match=r'^logs\.patterns requires named nonempty single-line literals$',
        ):
            load_source_check(tmp_path, 'logs')
        assert snapshot_files(tmp_path) == before


# !SECTION
