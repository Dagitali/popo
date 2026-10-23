"""Test hosted observations without network access or credentials.

Maintainer Notes
----------------
Exercise unavailable evidence separately from confirmed missing settings.
"""

from datetime import date

import pytest

from popo.checks.hosted import Response, audit
from popo.config.hosted import ExceptionPolicy, HostedConfig, RepositoryPolicy

# SECTION: FUNCTIONS


def audit_statuses(
    hosted_policy: RepositoryPolicy,
    github_responses: dict[str, Response],
    exceptions: tuple[ExceptionPolicy, ...] = (),
) -> dict[str, str]:
    """Return check statuses from deterministic API fixtures."""
    result = audit(
        HostedConfig((hosted_policy,), exceptions),
        lambda endpoint, paginate: github_responses[endpoint],
        today=date(2026, 10, 5),
    )
    checks = [item.check for item in result.findings]
    assert len(checks) == len(set(checks)), 'duplicate audit findings'
    return {item.check: item.status for item in result.findings}


# !SECTION


# SECTION: TESTS


class TestHostedObservations:
    """Group isolated regression scenarios for hosted."""

    @pytest.mark.parametrize(
        'http_status',
        [401, 403, 404, 429, 500, None],
    )
    def test_access_failure(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
        http_status: int | None,
    ) -> None:
        github_responses['repos/example/library/private-vulnerability-reporting'] = (
            Response(
                error='GET failed',
                status=http_status,
            )
        )
        assert (
            audit_statuses(hosted_policy, github_responses)[
                'private-vulnerability-reporting'
            ]
            == 'inaccessible'
        )

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
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
        enabled: bool,
        error: str,
        expires: date,
        expected: str,
    ) -> None:
        github_responses['repos/example/library/private-vulnerability-reporting'] = (
            Response(
                {'enabled': enabled},
                error,
            )
        )
        exception = ExceptionPolicy(
            hosted_policy.name,
            'private-vulnerability-reporting',
            'owner',
            'migration',
            'reviewer',
            'https://example.com/approval',
            expires,
        )
        statuses = audit_statuses(hosted_policy, github_responses, (exception,))
        assert statuses['private-vulnerability-reporting'] == expected
        if expires < date(2026, 10, 5):
            assert statuses['exception:private-vulnerability-reporting'] == 'missing'

    def test_malformed_check_array(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
    ) -> None:
        github_responses['repos/example/library/branches/main/protection'] = Response(
            {
                'required_status_checks': {'contexts': 'quality'},
            },
        )
        assert (
            audit_statuses(hosted_policy, github_responses)['branch:main:check:quality']
            == 'inaccessible'
        )

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
            (
                '/branches/main',
                {'protected': False},
                'branch:main:protected',
                'missing',
            ),
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
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
        suffix: str,
        data: object,
        check: str,
        status: str,
    ) -> None:
        github_responses['repos/example/library' + suffix] = Response(data)
        assert audit_statuses(hosted_policy, github_responses)[check] == status

    def test_omitted_security(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
    ) -> None:
        github_responses['repos/example/library'] = Response({'default_branch': 'main'})
        assert (
            audit_statuses(hosted_policy, github_responses)['secret-scanning']
            == 'inaccessible'
        )

    def test_repository_inaccessible(
        self,
        hosted_policy: RepositoryPolicy,
    ) -> None:
        result = audit(
            HostedConfig((hosted_policy,), ()),
            lambda path, pages: Response(error='404'),
        )
        assert result.failed
        assert {item.status for item in result.findings} == {'inaccessible'}

    def test_rules_and_legacy_union(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
    ) -> None:
        github_responses['repos/example/library/branches/main/protection'] = Response(
            'Branch not protected',
            '404',
            404,
        )
        github_responses['repos/example/library/rules/branches/main?per_page=100'] = (
            Response(
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
        )
        assert (
            audit_statuses(hosted_policy, github_responses)['branch:main:check:quality']
            == 'verified'
        )

    def test_unknown_legacy_absence(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
    ) -> None:
        github_responses['repos/example/library/branches/main/protection'] = Response(
            error='404',
            status=404,
        )
        assert (
            audit_statuses(hosted_policy, github_responses)['branch:main:check:quality']
            == 'inaccessible'
        )

    def test_verified(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
    ) -> None:
        assert set(audit_statuses(hosted_policy, github_responses).values()) == {
            'verified',
        }


class TestHostedEvidenceBoundaries:
    """
    Exercise malformed evidence and optional inventory without credentials.
    """

    @pytest.mark.parametrize(
        'data',
        [None, {}, {'protected': 'true'}],
    )
    def test_unavailable_branch(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
        data: object,
    ) -> None:
        """
        Require a boolean observation before classifying branch protection.
        """
        github_responses['repos/example/library/branches/main'] = Response(data)
        statuses = audit_statuses(hosted_policy, github_responses)
        assert statuses['branch:main:protected'] == 'inaccessible'
        assert statuses['branch:main:check:quality'] == 'inaccessible'

    @pytest.mark.parametrize(
        'data',
        [
            None,
            {},
            {
                'type': 'required_status_checks',
                'parameters': {'required_status_checks': 'bad'},
            },
        ],
    )
    def test_malformed_rules(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
        data: object,
    ) -> None:
        """
        Keep incomplete rule evidence distinct from a confirmed missing check.
        """
        github_responses['repos/example/library/rules/branches/main?per_page=100'] = (
            Response(
                [data],
            )
        )
        assert (
            audit_statuses(hosted_policy, github_responses)['branch:main:check:quality']
            == 'inaccessible'
        )

    def test_optional_expectations(self) -> None:
        """Audit a bare branch expectation without fetching unused evidence."""
        hosted_policy = RepositoryPolicy('example/library', {}, (), False, {'main': ()})
        github_responses = {
            'repos/example/library': Response({}),
            'repos/example/library/branches/main': Response({'protected': True}),
        }
        assert audit_statuses(hosted_policy, github_responses) == {
            'branch:main:protected': 'verified',
        }


class TestHostedCheckEvidence:
    """Check effective-rule availability and nonstring legacy contexts."""

    @pytest.mark.parametrize(
        ('rules', 'legacy', 'expected'),
        [
            (None, {}, 'inaccessible'),
            ([], {'contexts': [1]}, 'inaccessible'),
            (
                [{'type': 'pull_request'}],
                {'checks': [{'context': 'quality'}]},
                'verified',
            ),
        ],
    )
    def test_context_evidence(
        self,
        hosted_policy: RepositoryPolicy,
        github_responses: dict[str, Response],
        rules: object,
        legacy: dict[str, object],
        expected: str,
    ) -> None:
        """
        Accept valid legacy checks while rejecting incomplete typed evidence.
        """
        github_responses['repos/example/library/rules/branches/main?per_page=100'] = (
            Response(
                rules,
            )
        )
        github_responses['repos/example/library/branches/main/protection'] = Response(
            {'required_status_checks': legacy},
        )
        assert (
            audit_statuses(hosted_policy, github_responses)['branch:main:check:quality']
            == expected
        )


# !SECTION
