# test_u_safety.py
# Deterministic static safety regressions; never install npm dependencies.
"""
:mod:`tests.unit.checks.test_u_safety` module.

Exercise workflow trust boundaries and manifest/lockfile root drift.
"""

import json
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest

from popo.checks.safety import validate
from popo.config.safety import SafetyConfig
from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture(
    params=[
        pytest.param('&workflow\non: EVENT\nloop: *workflow\n', id='mapping-cycle'),
        pytest.param('on: EVENT\nloop: &loop [*loop]\n', id='sequence-cycle'),
    ],
)
def cyclic_workflow(
    request: pytest.FixtureRequest,
) -> str:
    """Supply recursive YAML aliases independent of workflow policy values."""
    return str(request.param)


# !SECTION


# SECTION: TESTS


class TestWorkflowSafety:
    """Test event shapes, dangerous scripts, and bounded exceptions."""

    @pytest.mark.parametrize(
        'source,message',
        [
            ('on: pull_request', ''),
            ('[]', 'workflow must be a mapping'),
            ('on: [push, pull_request_target]', 'needs exception'),
            ('on: {workflow_run: {workflows: [CI]}}', 'needs exception'),
            ('on: pull_request_target', 'needs exception'),
            ('on: pull_request\non: push', 'duplicate'),
            ('on: [', ''),
            ('on: null', 'on must'),
            ('on: [false]', 'event list'),
            (
                'on: push\njobs: {ci: {steps: '
                '[{run: "echo ${{ github.event.issue.title }}"}]}}',
                'interpolated',
            ),
            (
                'on: push\njobs: {ci: {steps: [{run: "echo $TITLE", '
                'env: {TITLE: "${{ github.event.issue.title }}"}}]}}',
                '',
            ),
            (
                'on: workflow_call\njobs: {ci: {steps: '
                '[{run: "${{ inputs.command }}"}]}}',
                '',
            ),
        ],
    )
    def test_workflows(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        source: str,
        message: str,
    ) -> None:
        """Inspect parsed workflows without executing their commands."""
        path = write_file('ci.yml', source)
        original = path.read_bytes()
        failures = validate(SafetyConfig(tmp_path, workflows=('ci.yml',)))
        if source == 'on: [':
            assert 'ci.yml:' in failures[0]
        elif message:
            assert any(message in item for item in failures)
        else:
            assert not failures
        assert path.read_bytes() == original

    @pytest.mark.parametrize(
        'event,expiry,message',
        [
            ('pull_request_target', date(2026, 10, 7), ''),
            ('pull_request_target', date(2026, 10, 6), 'expired'),
            ('push', date(2026, 10, 8), 'unused'),
            ('push', date(2026, 10, 6), 'unused'),
        ],
    )
    def test_exception_lifecycle(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        event: str,
        expiry: date,
        message: str,
    ) -> None:
        """Retire stale exceptions and reject expired reviews."""
        write_file('ci.yml', f'on: {event}')
        config = SafetyConfig(
            tmp_path,
            workflows=('ci.yml',),
            exceptions=(
                ('ci.yml', 'pull_request_target', 'team', 'review', 'owner', expiry),
            ),
        )
        failures = validate(config, today=date(2026, 10, 7))
        assert bool(failures) == bool(message)
        if message:
            assert message in failures[0]

    def test_missing_pattern(
        self,
        tmp_path: Path,
    ) -> None:
        """Fail closed when configured workflow discovery matches nothing."""
        assert validate(SafetyConfig(tmp_path, workflows=('*.yml',))) == [
            'no safety workflows match: *.yml',
        ]

    def test_exception_does_not_allow_head_checkout(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Reject direct untrusted checkout despite a trigger exception."""
        write_file(
            'ci.yml',
            'on: pull_request_target\njobs: {ci: {steps: '
            '[{uses: "actions/checkout@revision", '
            'with: {ref: "${{ github.event.pull_request.head.sha }}"}}]}}',
        )
        config = SafetyConfig(
            tmp_path,
            workflows=('ci.yml',),
            exceptions=(
                (
                    'ci.yml',
                    'pull_request_target',
                    'team',
                    'review',
                    'owner',
                    date(2026, 10, 8),
                ),
            ),
        )
        assert validate(config, today=date(2026, 10, 7)) == [
            'ci.yml: privileged checkout of pull-request head',
        ]

    def test_symlink_escape(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """Reject workflow symlinks that resolve outside the consumer root."""
        outside = write_file('outside.yml', 'on: push')
        root = tmp_path / 'consumer'
        root.mkdir()
        symlink(root / 'ci.yml', outside)
        assert (
            'escapes repository'
            in validate(SafetyConfig(root, workflows=('ci.yml',)))[0]
        )


class TestSafetyFailureIsolation:
    """Keep independent findings when discovery or one npm pair fails."""

    @pytest.mark.parametrize('error', [PermissionError, ValueError])
    def test_discovery_errors_do_not_skip_other_checks(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        monkeypatch: pytest.MonkeyPatch,
        error: type[Exception],
    ) -> None:
        """Retain later findings after errors during glob iteration."""
        write_file('ci.yml', 'on: pull_request_target')
        write_file('package.json', '{"name":"consumer"}')
        write_file(
            'package-lock.json',
            '{"lockfileVersion":3,"packages":{"":{"name":"other"}}}',
        )
        original = Path.glob

        def glob(
            path: Path,
            pattern: str,
        ) -> Iterator[Path]:
            if pattern == 'broken*.yml':
                raise error('PRIVATE DISCOVERY DETAILS')
            yield from original(path, pattern)

        monkeypatch.setattr(Path, 'glob', glob)
        assert validate(
            SafetyConfig(
                tmp_path,
                workflows=('broken*.yml', 'ci.yml'),
                npm_pairs=(('package.json', 'package-lock.json'),),
            ),
        ) == [
            'cannot discover safety workflows: broken*.yml',
            'ci.yml: privileged trigger pull_request_target needs exception',
            'package.json -> package-lock.json: root name differs',
        ]

    @pytest.mark.parametrize(
        'dependencies,message',
        [
            ([], 'dependencies must be an object'),
            ({'lib': 1}, 'dependencies specifications must be strings'),
            ({'lib': ''}, 'dependencies specifications must be strings'),
        ],
    )
    def test_npm_errors_retain_partial_and_later_pair_findings(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        dependencies: object,
        message: str,
    ) -> None:
        """Keep partial drift findings and inspect the next npm pair."""
        write_file('package.json', json.dumps({'dependencies': dependencies}))
        write_file('package-lock.json', '{"lockfileVersion":3,"packages":{"":{}}}')
        write_file('later.json', '{"name":"consumer"}')
        write_file(
            'later-lock.json',
            '{"lockfileVersion":3,"packages":{"":{"name":"other"}}}',
        )
        assert validate(
            SafetyConfig(
                tmp_path,
                npm_pairs=(
                    ('package.json', 'package-lock.json'),
                    ('later.json', 'later-lock.json'),
                ),
            ),
        ) == [
            'package.json -> package-lock.json: root dependencies differs',
            f'package.json -> package-lock.json: {message}',
            'later.json -> later-lock.json: root name differs',
        ]


class TestNpmPairs:
    """Check source manifests even when CI copies them into locked fixtures."""

    def test_invalid_dependency_specification(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Reject malformed specifications even when root metadata matches."""
        write_file('package.json', '{"dependencies":{"lib":123}}')
        write_file(
            'package-lock.json',
            '{"lockfileVersion":3,"packages":{"":{"dependencies":{"lib":123}}}}',
        )
        assert (
            'specifications must be strings'
            in validate(
                SafetyConfig(
                    tmp_path,
                    npm_pairs=(('package.json', 'package-lock.json'),),
                ),
            )[0]
        )

    @pytest.mark.parametrize(
        'content',
        ['[]', '{', '{"lockfileVersion":1}', '{"lockfileVersion":3}'],
    )
    def test_invalid_lock(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
    ) -> None:
        """Report malformed or unsupported lockfiles without running npm."""
        write_file('package.json', '{}')
        write_file('package-lock.json', content)
        assert validate(
            SafetyConfig(tmp_path, npm_pairs=(('package.json', 'package-lock.json'),)),
        )

    @pytest.mark.parametrize(
        'root_version,resolved,message',
        [
            ('2.0.0', '2.0.0', ''),
            ('1.0.0', '2.0.0', 'root dependencies'),
            ('2.0.0', '1.0.0', 'resolved lib'),
        ],
    )
    def test_metadata_drift(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        root_version: str,
        resolved: str,
        message: str,
    ) -> None:
        """Detect both dependency specifications and exact resolved drift."""
        write_file(
            'source/package.json',
            json.dumps({'dependencies': {'lib': '2.0.0'}}),
        )
        write_file(
            'locked/package-lock.json',
            json.dumps(
                {
                    'lockfileVersion': 3,
                    'packages': {
                        '': {'dependencies': {'lib': root_version}},
                        'node_modules/lib': {'version': resolved},
                    },
                },
            ),
        )
        failures = validate(
            SafetyConfig(
                tmp_path,
                npm_pairs=(('source/package.json', 'locked/package-lock.json'),),
            ),
        )
        assert bool(failures) == bool(message)
        if message:
            assert any(message in item for item in failures)


class TestNpmDependencyShapes:
    """
    Validate dependency objects without resolving floating version ranges.
    """

    @pytest.mark.parametrize(
        ('dependencies', 'message'),
        [([], 'dependencies must be an object'), ({'lib': '^2.0'}, '')],
    )
    def test_dependency_shapes(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        dependencies: object,
        message: str,
    ) -> None:
        """Reject non-objects and permit matching non-exact specifications."""
        write_file('package.json', json.dumps({'dependencies': dependencies}))
        write_file(
            'package-lock.json',
            json.dumps(
                {
                    'lockfileVersion': 3,
                    'packages': {'': {'dependencies': dependencies}},
                },
            ),
        )
        failures = validate(
            SafetyConfig(tmp_path, npm_pairs=(('package.json', 'package-lock.json'),)),
        )
        assert bool(failures) == bool(message)
        if message:
            assert message in failures[0]


# !SECTION


class TestWorkflowAliases:
    """Inspect cyclic and shared YAML safely without losing policy findings."""

    @pytest.mark.parametrize('event', ['push', 'pull_request_target'])
    @pytest.mark.parametrize(
        'unsafe',
        [False, True],
        ids=['safe-script', 'unsafe-script'],
    )
    def test_recursive_aliases(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        cyclic_workflow: str,
        event: str,
        unsafe: bool,
    ) -> None:
        """
        Terminate on aliases and still inspect subsequent scripts and
        checkouts.
        """
        script = 'echo ${{ github.event.issue.title }}' if unsafe else 'echo ok'
        source = cyclic_workflow.replace('EVENT', event) + (
            'jobs:\n  check:\n    steps:\n'
            '      - uses: actions/checkout@revision\n'
            '        with: {ref: "${{ github.event.pull_request.head.sha }}"}\n'
            f'      - run: "{script}"\n'
        )
        path = write_file('ci.yml', source)
        expected = []
        if event == 'pull_request_target':
            expected.extend(
                [
                    'ci.yml: privileged trigger pull_request_target needs exception',
                    'ci.yml: privileged checkout of pull-request head',
                ],
            )
        if unsafe:
            expected.append('ci.yml: event data interpolated directly into run')
        assert validate(SafetyConfig(tmp_path, workflows=('ci.yml',))) == expected
        assert path.read_text(encoding='utf-8') == source

    def test_repeated_alias_is_inspected_once(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Avoid duplicate diagnostics for one run mapping reused through aliases.
        """
        write_file(
            'ci.yml',
            (
                'on: push\njobs: {check: {steps: ['
                '&step {run: "echo ${{ github.event.issue.title }}"}, *step]}}'
            ),
        )
        assert validate(SafetyConfig(tmp_path, workflows=('ci.yml',))) == [
            'ci.yml: event data interpolated directly into run',
        ]
