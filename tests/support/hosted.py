"""
:mod:`tests.support.hosted` module.

Function-scoped hosted-policy and API evidence fixtures shared across layers.

Maintainer Notes
----------------
Keep each consumer's mutable observations isolated; never contact GitHub.
"""

import pytest

from popo.checks.hosted import Response
from popo.config.hosted import RepositoryPolicy

# SECTION: FIXTURES


@pytest.fixture(name='hosted_policy')
def hosted_policy_fixture() -> RepositoryPolicy:
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


@pytest.fixture(name='github_responses')
def github_responses_fixture() -> dict[str, Response]:
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


@pytest.fixture(name='hosted_exception_config')
def hosted_exception_config_fixture() -> str:
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


# !SECTION
