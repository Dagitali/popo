"""
:mod:`tests.unit.checks.test_u_github_adapter` module.

Verify sanitized GitHub CLI GET responses without network access.
"""

import subprocess
from unittest.mock import Mock

import pytest

from popo.checks.hosted import _github_get

# SECTION: TESTS


class TestGitHubReadAdapter:
    """Verify sanitized GitHub CLI GET responses without network access."""

    @pytest.mark.parametrize(
        ('stdout', 'returncode', 'stderr', 'paginate', 'expected'),
        [
            ('{}', 0, '', False, {}),
            (
                '[[{"name":"first"}],[{"name":"last"}]]',
                0,
                '',
                True,
                [{'name': 'first'}, {'name': 'last'}],
            ),
            ('{}', 0, '', True, None),
            ('not json', 0, '', False, None),
            ('', 1, 'sensitive-value (HTTP 403)', False, None),
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
    ) -> None:
        """Preserve GET boundaries and sanitize parsed or failed responses."""
        runner = Mock(
            return_value=subprocess.CompletedProcess([], returncode, stdout, stderr),
        )
        monkeypatch.setattr(subprocess, 'run', runner)
        result = _github_get('repos/example/library', paginate)
        assert result.data == expected
        assert bool(result.error) == (expected is None)
        assert result.status == (403 if returncode else None)
        runner.assert_called_once()
        assert runner.call_args.kwargs['timeout'] == 60
        assert 'sensitive-value' not in result.error
        command = runner.call_args.args[0]
        assert command[command.index('--method') + 1] == 'GET'
        assert command[command.index('--hostname') + 1] == 'github.com'
        assert ('--paginate' in command) == paginate
        assert ('--slurp' in command) == paginate

    @pytest.mark.parametrize(
        'error',
        [FileNotFoundError(), subprocess.TimeoutExpired('gh', 60)],
    )
    def test_adapter_launch_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        error: Exception,
    ) -> None:
        """Return unavailable evidence when the CLI cannot launch or finish."""
        monkeypatch.setattr(subprocess, 'run', Mock(side_effect=error))
        assert _github_get('repos/example/library').error


# !SECTION
