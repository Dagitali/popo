"""Audit GitHub settings through GET requests, never policy-file inference.

Maintainer Notes
----------------
Do not expose tokens, raw API payloads, or mutate hosted configuration.
Keep inaccessible evidence distinct from confirmed policy drift.
"""

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from urllib.parse import quote

from ..config.hosted import HostedConfig, RepositoryPolicy, expected_checks

# SECTION: DATA CLASSES


Status = Literal['verified', 'missing', 'inaccessible', 'excepted']


@dataclass(frozen=True)
class Finding:
    """Record a narrow observation and its evidence endpoint."""

    repository: str
    check: str
    status: Status
    detail: str
    evidence: str


@dataclass(frozen=True)
class Response:
    """Represent a parsed API response without retaining credentials."""

    data: Any = None
    error: str = ''
    status: int | None = None


@dataclass(frozen=True)
class Audit:
    """Record a timestamped audit, not an enforcement or delivery guarantee."""

    observed_at: str
    findings: tuple[Finding, ...]

    @property
    def failed(self) -> bool:
        """Return whether confirmed drift or unavailable evidence remains."""
        return any(item.status in {'missing', 'inaccessible'} for item in self.findings)

    def to_json(self) -> str:
        """Serialize only the sanitized report, never full API responses."""
        return json.dumps(asdict(self), indent=2)


Fetcher = Callable[[str, bool], Response]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _repository(
    policy: RepositoryPolicy,
    get: Fetcher,
) -> list[Finding]:
    """Compare explicit expectations with authenticated hosted observations."""
    base = f'repos/{policy.name}'
    findings: list[Finding] = []

    def add(check: str, state: bool | None, detail: str, endpoint: str) -> None:
        findings.append(
            Finding(
                policy.name,
                check,
                'inaccessible' if state is None else 'verified' if state else 'missing',
                detail,
                f'https://api.github.com/{endpoint}',
            ),
        )

    metadata = get(base, False)
    if metadata.error or not isinstance(metadata.data, dict):
        for check in sorted(expected_checks(policy)):
            add(check, None, metadata.error or 'unexpected repository response', base)
        return findings
    for setting, expected in policy.settings.items():
        endpoint = base
        if setting == 'private-vulnerability-reporting':
            endpoint += '/private-vulnerability-reporting'
            response = get(endpoint, False)
            observed = (
                response.data.get('enabled')
                if isinstance(response.data, dict)
                else None
            )
            error = response.error
        else:
            security = metadata.data.get('security_and_analysis', {})
            key = setting.replace('-', '_')
            feature = security.get(key, {}) if isinstance(security, dict) else {}
            value = feature.get('status') if isinstance(feature, dict) else None
            observed = (
                {'enabled': True, 'disabled': False}.get(value)
                if isinstance(value, str)
                else None
            )
            error = ''
        state = observed == expected if type(observed) is bool and not error else None
        add(
            setting,
            state,
            error or f'expected={expected}; observed={observed}',
            endpoint,
        )
    if policy.labels:
        endpoint = base + '/labels?per_page=100'
        labels = get(endpoint, True)
        valid = (
            not labels.error
            and isinstance(labels.data, list)
            and all(
                isinstance(item, dict) and isinstance(item.get('name'), str)
                for item in labels.data
            )
        )
        names = {item['name'] for item in labels.data} if valid else set()
        for label in policy.labels:
            add(
                f'label:{label}',
                label in names if valid else None,
                labels.error
                or (
                    'unexpected labels response'
                    if not valid
                    else 'label present'
                    if label in names
                    else 'label absent'
                ),
                endpoint,
            )
    if policy.codeowners:
        ref = metadata.data.get('default_branch')
        endpoint = base + '/git/trees/' + quote(str(ref), safe='') + '?recursive=1'
        tree = get(endpoint, False)
        valid = (
            isinstance(ref, str)
            and not tree.error
            and isinstance(tree.data, dict)
            and tree.data.get('truncated') is False
            and isinstance(tree.data.get('tree'), list)
            and all(
                isinstance(item, dict)
                and isinstance(item.get('path'), str)
                and isinstance(item.get('type'), str)
                for item in tree.data['tree']
            )
        )
        paths = (
            {item['path'] for item in tree.data['tree'] if item['type'] == 'blob'}
            if valid
            else set()
        )
        if not valid:
            add(
                'codeowners',
                None,
                tree.error or 'unavailable or truncated tree',
                endpoint,
            )
        elif not paths.intersection(
            {'.github/CODEOWNERS', 'CODEOWNERS', 'docs/CODEOWNERS'},
        ):
            add('codeowners', False, 'no CODEOWNERS file on default branch', endpoint)
        else:
            endpoint = base + '/codeowners/errors?ref=' + quote(str(ref), safe='')
            errors = get(endpoint, False)
            values = (
                errors.data.get('errors') if isinstance(errors.data, dict) else None
            )
            valid = not errors.error and isinstance(values, list)
            add(
                'codeowners',
                not values if valid else None,
                errors.error
                or (
                    f'{len(values or [])} hosted validation errors'
                    if valid
                    else 'unexpected errors response'
                ),
                endpoint,
            )
    for branch, checks in policy.branches.items():
        endpoint = base + '/branches/' + quote(branch, safe='')
        info = get(endpoint, False)
        protected = info.data.get('protected') if isinstance(info.data, dict) else None
        if info.error or type(protected) is not bool:
            for check in [
                f'branch:{branch}:protected',
                *(f'branch:{branch}:check:{name}' for name in checks),
            ]:
                add(check, None, info.error or 'unexpected branch response', endpoint)
            continue
        add(f'branch:{branch}:protected', protected, f'protected={protected}', endpoint)
        if not checks:
            continue
        rules_endpoint = (
            base + '/rules/branches/' + quote(branch, safe='') + '?per_page=100'
        )
        rules = get(rules_endpoint, True)
        legacy = (
            get(endpoint + '/protection', False) if protected else Response(data={})
        )
        if legacy.status == 404 and legacy.data == 'Branch not protected':
            legacy = Response(data={})
        try:
            if rules.error or not isinstance(rules.data, list):
                raise ValueError('effective rules unavailable')
            contexts: set[str] = set()
            for rule in rules.data:
                if not isinstance(rule, dict) or not isinstance(rule.get('type'), str):
                    raise ValueError('unexpected effective rule')
                if rule['type'] == 'required_status_checks':
                    required_rules = rule['parameters']['required_status_checks']
                    if not isinstance(required_rules, list):
                        raise ValueError('unexpected rules check array')
                    contexts.update(item['context'] for item in required_rules)
            legacy_known = not legacy.error and isinstance(legacy.data, dict)
            if legacy_known:
                required = legacy.data.get('required_status_checks') or {}
                legacy_contexts = required.get('contexts', [])
                legacy_checks = required.get('checks', [])
                if not isinstance(legacy_contexts, list) or not isinstance(
                    legacy_checks,
                    list,
                ):
                    raise ValueError('unexpected legacy check array')
                contexts.update(legacy_contexts)
                contexts.update(item['context'] for item in legacy_checks)
            if any(not isinstance(name, str) for name in contexts):
                raise ValueError('unexpected check context')
            for check in checks:
                state = True if check in contexts else False if legacy_known else None
                add(
                    f'branch:{branch}:check:{check}',
                    state,
                    'required context present'
                    if state
                    else legacy.error or 'required context absent',
                    rules_endpoint,
                )
        except (KeyError, TypeError, ValueError, AttributeError):
            for check in checks:
                add(
                    f'branch:{branch}:check:{check}',
                    None,
                    rules.error or 'incomplete or malformed branch-check evidence',
                    rules_endpoint,
                )
    return findings


# !SECTION


def _github_get(
    endpoint: str,
    paginate: bool = False,
) -> Response:
    """
    Fetch one GitHub endpoint using the authenticated GitHub CLI.

    Parameters
    ----------
    endpoint : str
        Internally constructed repository API path, not an arbitrary URL.
    paginate : bool, optional
        Fetch all pages and combine array responses.

    Returns
    -------
    Response
        Parsed data or a sanitized failure. Authentication, launch, timeout,
        API, and malformed JSON errors remain unavailable evidence.

    Notes
    -----
    Explicitly uses GET and github.com. Credentials are managed by ``gh``;
    no token is read or printed by Popo. Subprocesses have a bounded timeout.
    """
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
        endpoint,
    ]
    if paginate:
        command.extend(['--paginate', '--slurp'])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return Response(error='GitHub CLI unavailable, timed out, or undecodable')
    if result.returncode:
        match = re.search(r'\(HTTP (\d{3})\)', result.stderr)
        status = int(match[1]) if match else None
        # Retain only a recognized absence message, never arbitrary API text.
        try:
            body = json.loads(result.stdout)
        except (ValueError, TypeError):
            body = None
        message = (
            'Branch not protected'
            if isinstance(body, dict) and body.get('message') == 'Branch not protected'
            else None
        )
        return Response(
            data=message,
            error=f'GitHub GET failed (HTTP {status or 'unknown'})',
            status=status,
        )
    try:
        data = json.loads(result.stdout)
        if paginate:
            if not isinstance(data, list) or any(
                not isinstance(page, list) for page in data
            ):
                return Response(error='unexpected paginated response')
            data = [item for page in data for item in page]
        return Response(data=data)
    except ValueError:
        return Response(error='invalid JSON response')


# SECTION: FUNCTIONS


def audit(
    config: HostedConfig,
    get: Fetcher = _github_get,
    *,
    today: date | None = None,
) -> Audit:
    """
    Collect narrow hosted findings and apply approved exceptions.

    Parameters
    ----------
    config : HostedConfig
        Validated expectations, supplied by the consuming repository.
    get : callable, optional
        Read-only API adapter; deterministic tests supply an in-memory fake.
    today : datetime.date or None, optional
        UTC date for exception expiry; defaults to the current UTC date.

    Returns
    -------
    Audit
        Timestamped findings. Only confirmed drift can be excepted; missing
        access remains inaccessible. Expired exceptions are failures even if
        the original setting has subsequently been corrected.

    Notes
    -----
    Approval URLs are recorded attestations, not independently authenticated
    approvals. This audit does not prove notification delivery, check-source
    identity, bypass restrictions, or successful caller execution.
    """
    now = datetime.now(UTC)
    day = today or now.date()
    findings = [item for repo in config.repositories for item in _repository(repo, get)]
    for exception in config.exceptions:
        if exception.expires < day:
            findings.append(
                Finding(
                    exception.repository,
                    f'exception:{exception.check}',
                    'missing',
                    f'exception expired {exception.expires}; owner={exception.owner}',
                    exception.approval,
                ),
            )
            continue
        for index, item in enumerate(findings):
            if (item.repository, item.check, item.status) == (
                exception.repository,
                exception.check,
                'missing',
            ):
                findings[index] = Finding(
                    item.repository,
                    item.check,
                    'excepted',
                    f'{item.detail}; owner={exception.owner}; '
                    f'approved-by={exception.approved_by}; '
                    f'expires={exception.expires}; '
                    f'reason={exception.reason}; approval={exception.approval}',
                    item.evidence,
                )
    return Audit(now.isoformat(), tuple(findings))


# !SECTION
