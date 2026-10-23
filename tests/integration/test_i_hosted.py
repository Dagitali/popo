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


@pytest.fixture(
    params=[
        pytest.param(None, id='default-text'),
        pytest.param('text', id='explicit-text'),
        pytest.param('json', id='json'),
    ],
)
def audit_format(request: pytest.FixtureRequest) -> str | None:
    """
    Exercise default and explicit report formats with independent consumers.
    """
    return None if request.param is None else str(request.param)


@pytest.fixture
def audit_arguments(
    tmp_path: Path,
    audit_format: str | None,
) -> list[str]:
    """
    Build the selected format's public CLI arguments for a fresh consumer.
    """
    arguments = ['audit-github-settings', '--root', str(tmp_path)]
    if audit_format is not None:
        arguments.extend(['--format', audit_format])
    return arguments


# !SECTION


# SECTION: TESTS


class TestHostedCommandLine:
    """Verify hosted CLI dispatch and reporting using in-memory evidence."""

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
        audit_format: str | None,
        denied: bool,
    ) -> None:
        """
        Preserve CLI drift exits and JSON/text reporting with loaded policy.

        Parse actual consumer configuration before collecting deterministic API
        observations. Freeze the exception review day so expiry cannot change
        this dispatch test's outcome. No credentials or GitHub calls are used.
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
        if audit_format == 'json':
            findings = json.loads(streams.out)['findings']
            assert [item['status'] for item in findings] == [expected]
            assert findings[0]['repository'] == 'example/library'
            assert findings[0]['check'] == 'label:bug'
        else:
            assert streams.out.startswith('GitHub settings audit: ')
            assert f'{expected}: example/library label:bug:' in streams.out

    def test_invalid_configuration(
        self,
        audit_arguments: list[str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        audit_format: str | None,
    ) -> None:
        """Report malformed configuration before invoking the audit adapter."""
        observer = Mock(side_effect=AssertionError('must not audit invalid policy'))
        monkeypatch.setattr('popo.cli.hosted.audit', observer)
        assert main(audit_arguments) == 1
        observer.assert_not_called()
        streams = capsys.readouterr()
        assert streams.err == ''
        if audit_format == 'json':
            assert json.loads(streams.out)['error'].startswith('configuration: ')
        else:
            assert streams.out.startswith('FAIL: configuration: ')


# !SECTION
