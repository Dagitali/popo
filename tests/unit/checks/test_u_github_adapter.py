"""
:mod:`tests.unit.checks.test_u_github_adapter` module.

Verify sanitized GitHub CLI GET responses without network access.
"""

import subprocess
from collections.abc import Callable
from unittest.mock import Mock

import pytest

from popo.checks import hosted
from popo.checks.hosted import _github_get

# SECTION: TESTS


class TestGitHubReadAdapter:
    """Verify sanitized GitHub CLI GET responses without network access."""

    @pytest.mark.parametrize(
        ('stdout', 'returncode', 'stderr', 'paginate', 'expected', 'failed', 'status'),
        [
            ('{}', 0, '', False, {}, False, None),
            (
                '[[{"name":"first"}],[{"name":"last"}]]',
                0,
                '',
                True,
                [{'name': 'first'}, {'name': 'last'}],
                False,
                None,
            ),
            ('{}', 0, '', True, None, True, None),
            ('[[1],{}]', 0, '', True, None, True, None),
            ('null', 0, '', False, None, False, None),
            ('not json', 0, '', False, None, True, None),
            ('', 1, 'sensitive-value (HTTP 403)', False, None, True, 403),
            ('', 1, 'sensitive-value', False, None, True, None),
            (
                '{"message":"Branch not protected"}',
                1,
                'sensitive-value (HTTP 404)',
                False,
                'Branch not protected',
                True,
                404,
            ),
        ],
    )
    def test_adapter(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stdout: str,
        returncode: int,
        stderr: str,
        paginate: bool,
        expected: object,
        failed: bool,
        status: int | None,
    ) -> None:
        """Preserve GET boundaries and sanitize parsed or failed responses."""
        runner = Mock(
            return_value=subprocess.CompletedProcess([], returncode, stdout, stderr),
        )
        monkeypatch.setattr(subprocess, 'run', runner)
        result = _github_get('repos/example/library', paginate)
        assert result.data == expected
        assert bool(result.error) is failed
        assert result.status == status
        runner.assert_called_once()
        assert runner.call_args.kwargs['timeout'] == 60
        assert 'sensitive-value' not in result.error
        command = runner.call_args.args[0]
        assert command[command.index('--method') + 1] == 'GET'
        assert command[command.index('--hostname') + 1] == 'github.com'
        assert ('--paginate' in command) == paginate
        assert ('--slurp' in command) == paginate

    @pytest.mark.parametrize(
        'error_factory',
        [
            pytest.param(FileNotFoundError, id='missing-gh'),
            pytest.param(lambda: subprocess.TimeoutExpired('gh', 60), id='timeout'),
            pytest.param(
                lambda: UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid'),
                id='decode',
            ),
        ],
    )
    def test_adapter_launch_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        error_factory: Callable[[], Exception],
    ) -> None:
        """Return unavailable evidence when the CLI cannot launch or finish."""
        monkeypatch.setattr(subprocess, 'run', Mock(side_effect=error_factory()))
        assert _github_get('repos/example/library').error

    @pytest.mark.parametrize('returncode', (0, 1))
    def test_parser_depth_failure_remains_sanitized(
        self,
        monkeypatch: pytest.MonkeyPatch,
        returncode: int,
    ) -> None:
        """Handle parser-depth failures on successful and failed HTTP paths."""
        monkeypatch.setattr(
            subprocess,
            'run',
            Mock(
                return_value=subprocess.CompletedProcess(
                    [],
                    returncode,
                    'sensitive-value',
                    'sensitive-value (HTTP 503)',
                ),
            ),
        )
        monkeypatch.setattr(
            hosted.json,
            'loads',
            Mock(side_effect=RecursionError('sensitive-value')),
        )
        result = _github_get('repos/example/library')
        assert result.data is None
        assert result.error == (
            'GitHub GET failed (HTTP 503)' if returncode else 'invalid JSON response'
        )
        assert result.status == (503 if returncode else None)
        assert 'sensitive-value' not in result.error


# !SECTION
