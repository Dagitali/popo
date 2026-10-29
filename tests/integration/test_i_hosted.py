"""
:mod:`tests.integration.test_i_hosted` module.

Verify hosted CLI dispatch and reporting using in-memory evidence.
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.checks.hosted import Response, audit
from popo.cli import main
from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture(name='audit_arguments')
def audit_arguments_fixture(
    tmp_path: Path,
    format_arguments: tuple[str, ...],
) -> list[str]:
    """
    Build the selected format's public CLI arguments for a fresh consumer.

    Parameters
    ----------
    tmp_path : Path
        Per-test temporary directory supplied by pytest.
    format_arguments : tuple[str, ...]
        CLI arguments selecting text or JSON output.

    Returns
    -------
    list[str]
        CLI arguments pointing to the temporary hosted policy.
    """
    return ['audit-github-settings', '--root', str(tmp_path), *format_arguments]


# !SECTION


# SECTION: TESTS


class TestHostedCommandLine:
    """Verify hosted CLI dispatch and reporting using in-memory evidence."""

    def test_invalid_configuration(
        self,
        audit_arguments: list[str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
    ) -> None:
        """
        Report malformed configuration before invoking the audit adapter.

        Parameters
        ----------
        audit_arguments : list[str]
            CLI arguments selecting the hosted policy under test.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        cli_format : str | None
            Requested CLI output format, or None for its default.
        """
        observer = Mock(side_effect=AssertionError('must not audit invalid policy'))
        monkeypatch.setattr('popo.cli.hosted.audit', observer)
        assert main(audit_arguments) == 1
        observer.assert_not_called()
        streams = capsys.readouterr()
        assert streams.err == ''
        if cli_format == 'json':
            assert json.loads(streams.out)['error'].startswith('configuration: ')
        else:
            assert streams.out.startswith('FAIL: configuration: ')

    @pytest.mark.parametrize(
        'denied',
        [False, True],
        ids=['verified', 'inaccessible'],
    )
    def test_policy_reporting(
        self,
        audit_arguments: list[str],
        write_file: FileWriter,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        hosted_exception_config: str,
        github_responses: dict[str, Response],
        cli_format: str | None,
        denied: bool,
    ) -> None:
        """
        Preserve CLI drift exits and JSON/text reporting with loaded policy.

        Parse actual consumer configuration before collecting deterministic API
        observations. Freeze the exception review day so expiry cannot change
        this dispatch test's outcome. No credentials or GitHub calls are used.

        Parameters
        ----------
        audit_arguments : list[str]
            CLI arguments selecting the hosted policy under test.
        write_file : FileWriter
            Fixture writing UTF-8 files beneath the temporary consumer root.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        hosted_exception_config : str
            Valid hosted policy and explicit approval TOML.
        github_responses : dict[str, Response]
            Isolated endpoint-to-response mapping; no network is used.
        cli_format : str | None
            Requested CLI output format, or None for its default.
        denied : bool
            Whether access is denied in the simulated response.
        """
        write_file('pyproject.toml', hosted_exception_config)
        monkeypatch.setattr(
            'popo.cli.hosted.audit',
            lambda config: audit(
                config,
                lambda path, pages: (
                    Response(error='denied') if denied else github_responses[path]
                ),
                today=date(2026, 10, 5),
            ),
        )
        assert main(audit_arguments) == int(denied)
        streams = capsys.readouterr()
        assert streams.err == ''
        expected = 'inaccessible' if denied else 'verified'
        if cli_format == 'json':
            findings = json.loads(streams.out)['findings']
            assert [item['status'] for item in findings] == [expected]
            assert findings[0]['repository'] == 'example/library'
            assert findings[0]['check'] == 'label:bug'
        else:
            assert streams.out.startswith('GitHub settings audit: ')
            assert f'{expected}: example/library label:bug:' in streams.out


# !SECTION
