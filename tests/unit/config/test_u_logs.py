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

    @pytest.mark.parametrize('patterns', ('{}', '{ bad = "" }', '{ "bad\\nID" = "x" }'))
    def test_invalid_patterns(
        self: Self,
        tmp_path: Path,
        write_file: FileWriter,
        patterns: str,
    ) -> None:
        """
        Reject empty literals, empty rule tables and malformed rule names.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Shared UTF-8 writer creating the consumer policy.
        patterns : str
            Pattern declarations encoded in the scenario configuration.
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

    @pytest.mark.parametrize(
        'separator',
        [
            pytest.param('\n', id='lf'),
            pytest.param('\r', id='cr'),
            pytest.param('\r\n', id='crlf'),
            pytest.param('\v', id='vertical-tab'),
            pytest.param('\f', id='form-feed'),
            pytest.param('\x1c', id='file-separator'),
            pytest.param('\x1d', id='group-separator'),
            pytest.param('\x1e', id='record-separator'),
            pytest.param('\x85', id='next-line'),
            pytest.param('\u2028', id='line-separator'),
            pytest.param('\u2029', id='paragraph-separator'),
        ],
    )
    @pytest.mark.parametrize('trailing', [False, True])
    def test_multiline_literals_are_rejected(
        self: Self,
        tmp_path: Path,
        write_file: FileWriter,
        separator: str,
        trailing: bool,
    ) -> None:
        """
        Reject literals that cannot occur within a scanned log line.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        write_file : FileWriter
            Shared UTF-8 writer creating the consumer policy.
        separator : str
            Separator spelling used by the scenario.
        trailing : bool
            Whether the input includes a trailing separator.
        """
        literal = 'WARNING' + separator + ('' if trailing else 'PRIVATE')
        write_file(
            'popo.toml',
            '[logs]\ninclude=["*.log"]\npatterns={warning=' + json.dumps(literal) + '}',
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match='single-line literals'):
            load_source_check(tmp_path, 'logs')
        assert snapshot_files(tmp_path) == before


# !SECTION
