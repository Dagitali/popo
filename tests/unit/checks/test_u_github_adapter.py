"""
:mod:`tests.unit.checks.test_u_github_adapter` module.

Verify sanitized GitHub CLI GET responses without network access.
"""

import subprocess
from collections.abc import Callable
from unittest.mock import Mock

import pytest

from popo.checks import hosted
from popo.checks.hosted import Response, _github_get

# SECTION: FIXTURES


@pytest.fixture(name='runner')
def runner_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> Mock:
    """
    Isolate each adapter invocation from real processes and network access.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Restore the subprocess runner after each independent scenario.

    Returns
    -------
    unittest.mock.Mock
        Fresh process runner configured by the requesting test.
    """
    runner = Mock()
    monkeypatch.setattr(subprocess, 'run', runner)
    return runner


# !SECTION


# SECTION: TESTS


class TestGitHubReadAdapter:
    """Verify sanitized GitHub CLI GET responses without network access."""

    @pytest.mark.parametrize(
        ('stdout', 'returncode', 'stderr', 'paginate', 'expected'),
        [
            ('{}', 0, '', False, Response(data={})),
            (
                '[[{"name":"first"}],[{"name":"last"}]]',
                0,
                '',
                True,
                Response(data=[{'name': 'first'}, {'name': 'last'}]),
            ),
            ('[]', 0, '', True, Response(data=[])),
            ('{}', 0, '', True, Response(error='unexpected paginated response')),
            ('[[1],{}]', 0, '', True, Response(error='unexpected paginated response')),
            ('null', 0, '', False, Response()),
            ('not json', 0, '', False, Response(error='invalid JSON response')),
            (
                '',
                1,
                'sensitive-value (HTTP 403)',
                False,
                Response(error='GitHub GET failed (HTTP 403)', status=403),
            ),
            (
                '',
                1,
                'sensitive-value',
                False,
                Response(error='GitHub GET failed (HTTP unknown)'),
            ),
            (
                '{"message":"Branch not protected"}',
                1,
                'sensitive-value (HTTP 404)',
                False,
                Response(
                    data='Branch not protected',
                    error='GitHub GET failed (HTTP 404)',
                    status=404,
                ),
            ),
            (
                '{"message":"sensitive-value"}',
                1,
                'sensitive-value (HTTP 404)',
                True,
                Response(error='GitHub GET failed (HTTP 404)', status=404),
            ),
        ],
    )
    def test_adapter(
        self,
        runner: Mock,
        stdout: str,
        returncode: int,
        stderr: str,
        paginate: bool,
        expected: Response,
    ) -> None:
        """
        Preserve GET boundaries and sanitize parsed or failed responses.

        Parameters
        ----------
        runner : unittest.mock.Mock
            Fresh process runner preventing real subprocess execution.
        stdout : str
            Standard output supplied by the simulated process.
        returncode : int
            Exit status returned by the simulated process.
        stderr : str
            Standard error supplied by the simulated process.
        paginate : bool
            Whether the fetcher requests paginated array evidence.
        expected : Response
            Complete parsed data, sanitized error and HTTP status contract.
        """
        runner.return_value = subprocess.CompletedProcess(
            [],
            returncode,
            stdout,
            stderr,
        )
        result = _github_get('repos/example/library', paginate)
        assert result == expected
        assert 'sensitive-value' not in result.error
        command = [
            'gh',
            'api',
            '--hostname',
            'github.com',
            '--method',
            'GET',
            '-H',
            'Accept: application/vnd.github+json',
            '-H',
            'X-GitHub-Api-Version: 2026-03-10',
            'repos/example/library',
        ]
        if paginate:
            command.extend(['--paginate', '--slurp'])
        runner.assert_called_once_with(
            command,
            capture_output=True,
            text=True,
            timeout=60,
        )

    @pytest.mark.parametrize(
        'error_factory',
        [
            pytest.param(lambda: FileNotFoundError('sensitive-value'), id='missing-gh'),
            pytest.param(
                lambda: subprocess.TimeoutExpired(
                    'sensitive-value',
                    60,
                    output='sensitive-value',
                    stderr='sensitive-value',
                ),
                id='timeout',
            ),
            pytest.param(
                lambda: UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'sensitive-value'),
                id='decode',
            ),
        ],
    )
    @pytest.mark.parametrize('paginate', (False, True))
    def test_adapter_launch_error(
        self,
        runner: Mock,
        error_factory: Callable[[], Exception],
        paginate: bool,
    ) -> None:
        """
        Return sanitized unavailable evidence without exception contents.

        Parameters
        ----------
        runner : unittest.mock.Mock
            Fresh process runner preventing real subprocess execution.
        error_factory : Callable[[], Exception]
            Factory producing a fresh exception for each invocation.
        paginate : bool
            Exercise launch failure with or without pagination flags.
        """
        runner.side_effect = error_factory()
        assert _github_get('repos/example/library', paginate) == Response(
            error='GitHub CLI unavailable, timed out, or undecodable',
        )
        runner.assert_called_once()

    @pytest.mark.parametrize('returncode', (0, 1))
    def test_parser_depth_failure_remains_sanitized(
        self,
        monkeypatch: pytest.MonkeyPatch,
        returncode: int,
        runner: Mock,
    ) -> None:
        """
        Handle parser-depth failures on successful and failed HTTP paths.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        returncode : int
            Exit status returned by the simulated process.
        runner : unittest.mock.Mock
            Fresh process runner preventing real subprocess execution.
        """
        runner.return_value = subprocess.CompletedProcess(
            [],
            returncode,
            'sensitive-value',
            'sensitive-value (HTTP 503)',
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
        runner.assert_called_once()


# !SECTION
