"""Test hosted observations without network access or credentials.

Maintainer Notes
----------------
Exercise unavailable evidence separately from confirmed missing settings.
"""

import json
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.checks.hosted import Response, _github_get, audit
from popo.cli import main
from popo.config import ConfigurationError
from popo.config.hosted import (
    ExceptionPolicy,
    HostedConfig,
    RepositoryPolicy,
    load_hosted_config,
)

# SECTION: FIXTURES


@pytest.fixture(name='policy')
def policy_fixture() -> RepositoryPolicy:
    """Return a representative consumer-owned inventory."""
    return RepositoryPolicy(
        'example/library',
        {
            'private-vulnerability-reporting': True,
            'secret-scanning': True,
            'secret-scanning-push-protection': True,
        },
        ('bug',),
        True,
        {'main': ('quality',)},
    )


@pytest.fixture(name='responses')
def responses_fixture() -> dict[str, Response]:
    """Return complete, successful API evidence for the policy."""
    base = 'repos/example/library'
    return {
        base: Response(
            {
                'default_branch': 'main',
                'security_and_analysis': {
                    'secret_scanning': {'status': 'enabled'},
                    'secret_scanning_push_protection': {'status': 'enabled'},
                },
            },
        ),
        base + '/private-vulnerability-reporting': Response({'enabled': True}),
        base + '/labels?per_page=100': Response([{'name': 'bug'}]),
        base + '/git/trees/main?recursive=1': Response(
            {
                'truncated': False,
                'tree': [{'path': '.github/CODEOWNERS', 'type': 'blob'}],
            },
        ),
        base + '/codeowners/errors?ref=main': Response({'errors': []}),
        base + '/branches/main': Response({'protected': True}),
        base + '/branches/main/protection': Response(
            {
                'required_status_checks': {'contexts': ['quality'], 'checks': []},
            },
        ),
        base + '/rules/branches/main?per_page=100': Response([]),
    }


# !SECTION


# SECTION: FUNCTIONS


def run(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
    exceptions: tuple[ExceptionPolicy, ...] = (),
) -> dict[str, str]:
    """Return check statuses from deterministic API fixtures."""
    result = audit(
        HostedConfig((policy,), exceptions),
        lambda endpoint, paginate: responses[endpoint],
        today=date(2026, 10, 5),
    )
    return {item.check: item.status for item in result.findings}


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(name='exception_config')
def exception_config_fixture() -> str:
    """Return an explicit valid policy and approval attestation."""
    return """
[[tool.popo.hosted.repositories]]
name = "example/library"
labels = ["bug"]
[[tool.popo.hosted.exceptions]]
repository = "example/library"
check = "label:bug"
owner = "owner"
reason = "Migration"
approved-by = "reviewer"
approval = "https://example.com/review"
expires = "2026-10-31"
"""


# SECTION: TESTS


@pytest.mark.parametrize(
    'http_status',
    [401, 403, 404, 429, 500, None],
)
def test_access_failure(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
    http_status: int | None,
) -> None:
    responses['repos/example/library/private-vulnerability-reporting'] = Response(
        error='GET failed',
        status=http_status,
    )
    assert run(policy, responses)['private-vulnerability-reporting'] == 'inaccessible'


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
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    returncode: int,
    stderr: str,
    paginate: bool,
    expected: object,
) -> None:
    runner = Mock(
        return_value=subprocess.CompletedProcess([], returncode, stdout, stderr),
    )
    monkeypatch.setattr(subprocess, 'run', runner)
    result = _github_get('repos/example/library', paginate)
    assert result.data == expected
    assert 'sensitive-value' not in result.error
    command = runner.call_args.args[0]
    assert command[command.index('--method') + 1] == 'GET'
    assert '--hostname' in command
    assert '--paginate' in command if paginate else '--paginate' not in command


@pytest.mark.parametrize(
    'error',
    [FileNotFoundError(), subprocess.TimeoutExpired('gh', 60)],
)
def test_adapter_launch_error(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    monkeypatch.setattr(subprocess, 'run', Mock(side_effect=error))
    assert _github_get('repos/example/library').error


def test_cli_drift_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exception_config: str,
    policy: RepositoryPolicy,
) -> None:
    (tmp_path / 'pyproject.toml').write_text(exception_config)
    result = audit(
        HostedConfig((policy,), ()),
        lambda path, pages: Response(error='denied'),
    )
    monkeypatch.setattr('popo.cli.hosted.audit', lambda config: result)
    assert main(['audit-github-settings', '--root', str(tmp_path)]) == 1
    assert 'inaccessible:' in capsys.readouterr().out


def test_cli_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    policy: RepositoryPolicy,
    responses: dict[str, Response],
) -> None:
    (tmp_path / 'pyproject.toml').write_text(
        '[[tool.popo.hosted.repositories]]\nname="example/library"\n'
        'settings={private-vulnerability-reporting=true}\n',
    )
    result = audit(HostedConfig((policy,), ()), lambda path, pages: responses[path])
    monkeypatch.setattr('popo.cli.hosted.audit', lambda config: result)
    assert (
        main(['audit-github-settings', '--root', str(tmp_path), '--format', 'json'])
        == 0
    )
    assert json.loads(capsys.readouterr().out)['findings'][0]['status'] == 'verified'
    (tmp_path / 'pyproject.toml').write_text('')
    assert (
        main(['audit-github-settings', '--root', str(tmp_path), '--format', 'json'])
        == 1
    )
    assert 'error' in json.loads(capsys.readouterr().out)


@pytest.mark.parametrize(
    'section',
    ['repositories', 'exceptions'],
)
def test_duplicate_scopes(
    tmp_path: Path,
    exception_config: str,
    section: str,
) -> None:
    if section == 'repositories':
        extra = (
            '\n[[tool.popo.hosted.repositories]]\n'
            'name="example/library"\nlabels=["bug"]'
        )
    else:
        extra = (
            '\n[[tool.popo.hosted.exceptions]]'
            + exception_config.split('[[tool.popo.hosted.exceptions]]', 1)[1]
        )
    (tmp_path / 'pyproject.toml').write_text(exception_config + extra)
    with pytest.raises(ConfigurationError):
        load_hosted_config(tmp_path)


@pytest.mark.parametrize(
    ('enabled', 'error', 'expires', 'expected'),
    [
        (False, '', date(2026, 10, 5), 'excepted'),
        (False, '', date(2026, 10, 4), 'missing'),
        (True, '', date(2026, 10, 6), 'verified'),
        (False, 'denied', date(2026, 10, 6), 'inaccessible'),
    ],
)
def test_exceptions(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
    enabled: bool,
    error: str,
    expires: date,
    expected: str,
) -> None:
    responses['repos/example/library/private-vulnerability-reporting'] = Response(
        {'enabled': enabled},
        error,
    )
    exception = ExceptionPolicy(
        policy.name,
        'private-vulnerability-reporting',
        'owner',
        'migration',
        'reviewer',
        'https://example.com/approval',
        expires,
    )
    statuses = run(policy, responses, (exception,))
    assert statuses['private-vulnerability-reporting'] == expected
    if expires < date(2026, 10, 5):
        assert statuses['exception:private-vulnerability-reporting'] == 'missing'


@pytest.mark.parametrize(
    'config',
    [
        '',
        '[[tool.popo.hosted.repositories]]\nname="owner/repo"',
        '[tool.popo.hosted]\nrepositories=[]',
        '[[tool.popo.hosted.repositories]]\nname="bad"',
        '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nlabels=["bug","bug"]',
        '[[tool.popo.hosted.repositories]]\nname="owner/repo"\ncodeowners="yes"',
        '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nsettings={unknown=true}',
        '[[tool.popo.hosted.repositories]]\nname="owner/repo"\nsettings={secret-scanning=1}',
    ],
)
def test_invalid_config(
    tmp_path: Path,
    config: str,
) -> None:
    (tmp_path / 'pyproject.toml').write_text(config)
    with pytest.raises(ConfigurationError):
        load_hosted_config(tmp_path)


@pytest.mark.parametrize(
    ('original', 'replacement'),
    [
        ('owner = "owner"', 'owner = ""'),
        ('reason = "Migration"', ''),
        ('approved-by = "reviewer"', 'approved-by = false'),
        ('check = "label:bug"', 'check = "label:other"'),
        ('repository = "example/library"', 'repository = "other/repository"'),
        ('expires = "2026-10-31"', 'expires = "20261031"'),
        ('expires = "2026-10-31"', 'expires = "2026-02-31"'),
        ('expires = "2026-10-31"', 'expires = 2026-10-31'),
        ('https://example.com/review', 'http://example.com/review'),
        ('https://example.com/review', 'https://'),
        ('https://example.com/review', 'https://user:secret@example.com/review'),
    ],
)
def test_invalid_exception(
    tmp_path: Path,
    exception_config: str,
    original: str,
    replacement: str,
) -> None:
    (tmp_path / 'pyproject.toml').write_text(
        exception_config.replace(original, replacement),
    )
    with pytest.raises(ConfigurationError):
        load_hosted_config(tmp_path)


def test_malformed_check_array(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
) -> None:
    responses['repos/example/library/branches/main/protection'] = Response(
        {
            'required_status_checks': {'contexts': 'quality'},
        },
    )
    assert run(policy, responses)['branch:main:check:quality'] == 'inaccessible'


@pytest.mark.parametrize(
    ('suffix', 'data', 'check', 'status'),
    [
        (
            '/private-vulnerability-reporting',
            {'enabled': False},
            'private-vulnerability-reporting',
            'missing',
        ),
        (
            '/private-vulnerability-reporting',
            {},
            'private-vulnerability-reporting',
            'inaccessible',
        ),
        (
            '/private-vulnerability-reporting',
            {'enabled': 1},
            'private-vulnerability-reporting',
            'inaccessible',
        ),
        ('/labels?per_page=100', [], 'label:bug', 'missing'),
        ('/labels?per_page=100', [{}], 'label:bug', 'inaccessible'),
        (
            '/git/trees/main?recursive=1',
            {'truncated': False, 'tree': []},
            'codeowners',
            'missing',
        ),
        (
            '/git/trees/main?recursive=1',
            {'truncated': True, 'tree': []},
            'codeowners',
            'inaccessible',
        ),
        ('/codeowners/errors?ref=main', {'errors': [{}]}, 'codeowners', 'missing'),
        ('/codeowners/errors?ref=main', {}, 'codeowners', 'inaccessible'),
        ('/branches/main', {'protected': False}, 'branch:main:protected', 'missing'),
        ('/branches/main/protection', {}, 'branch:main:check:quality', 'missing'),
        (
            '/rules/branches/main?per_page=100',
            [{}],
            'branch:main:check:quality',
            'inaccessible',
        ),
    ],
)
def test_observations(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
    suffix: str,
    data: object,
    check: str,
    status: str,
) -> None:
    responses['repos/example/library' + suffix] = Response(data)
    assert run(policy, responses)[check] == status


def test_omitted_security(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
) -> None:
    responses['repos/example/library'] = Response({'default_branch': 'main'})
    assert run(policy, responses)['secret-scanning'] == 'inaccessible'


def test_repository_inaccessible(
    policy: RepositoryPolicy,
) -> None:
    result = audit(
        HostedConfig((policy,), ()),
        lambda path, pages: Response(error='404'),
    )
    assert result.failed
    assert {item.status for item in result.findings} == {'inaccessible'}


def test_rules_and_legacy_union(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
) -> None:
    responses['repos/example/library/branches/main/protection'] = Response(
        'Branch not protected',
        '404',
        404,
    )
    responses['repos/example/library/rules/branches/main?per_page=100'] = Response(
        [
            {
                'type': 'required_status_checks',
                'parameters': {
                    'required_status_checks': [
                        {'context': 'quality', 'integration_id': 123},
                    ],
                },
            },
        ],
    )
    assert run(policy, responses)['branch:main:check:quality'] == 'verified'


def test_unknown_legacy_absence(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
) -> None:
    responses['repos/example/library/branches/main/protection'] = Response(
        error='404',
        status=404,
    )
    assert run(policy, responses)['branch:main:check:quality'] == 'inaccessible'


def test_valid_exception(
    tmp_path: Path,
    exception_config: str,
) -> None:
    (tmp_path / 'pyproject.toml').write_text(exception_config)
    config = load_hosted_config(tmp_path)
    assert config.exceptions[0].expires == date(2026, 10, 31)
    assert config.repositories[0].labels == ('bug',)


def test_verified(
    policy: RepositoryPolicy,
    responses: dict[str, Response],
) -> None:
    assert set(run(policy, responses).values()) == {'verified'}
