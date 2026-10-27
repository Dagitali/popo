"""
:mod:`tests.unit.checks.test_u_swift_policy` module.

Exercise Swift declaration drift without launching tools or manifests.
"""

import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from popo.checks.swift_policy import validate
from popo.config.swift_policy import load_swift_policy_config
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestSwiftPolicy:
    """
    Keep package minimums, preferred compilers and observed versions distinct.
    """

    @pytest.mark.parametrize(
        'observed,message',
        [
            ('6.3.0', 'compiler version is not supported by policy'),
            ('6.1-SNAPSHOT', 'invalid stable Swift version'),
        ],
    )
    def test_bad_observed_compiler(
        self,
        swift_policy_consumer: Path,
        observed: str,
        message: str,
    ) -> None:
        failures = validate(
            load_swift_policy_config(swift_policy_consumer),
            compiler_version=observed,
        )
        assert failures == [f'--compiler-version: {message}']

    @pytest.mark.parametrize('require_preferred', [False, True])
    @pytest.mark.parametrize('ci_version', ['6.2.0', '6.3.0'])
    @pytest.mark.parametrize('observed', [None, '6.1.2'])
    def test_ci_policy_is_independent_of_caller_observations(
        self,
        swift_policy_consumer: Path,
        require_preferred: bool,
        ci_version: str,
        observed: str | None,
    ) -> None:
        """
        Keep caller observations distinct from actual workflow declarations.
        """
        root = swift_policy_consumer
        workflow = root / '.github/workflows/ci.yml'
        source = workflow.read_text(encoding='utf-8')
        marker = '["6.1.2", "6.2.0"]'
        assert marker in source
        workflow.write_text(
            source.replace(marker, f'["{ci_version}"]'),
            encoding='utf-8',
        )
        config = replace(
            load_swift_policy_config(root),
            require_preferred_in_ci=require_preferred,
        )
        expected = []
        if ci_version == '6.3.0':
            expected.append(
                '.github/workflows/ci.yml: jobs.swift.steps[0].with.swift-version: '
                'compiler version is not supported by policy',
            )
        if require_preferred:
            expected.append(
                'Swift CI declarations do not include the preferred compiler',
            )
        before = snapshot_files(root)
        assert validate(config, compiler_version=observed) == expected
        assert snapshot_files(root) == before

    @pytest.mark.parametrize('observed', [None, '6.1.2', '6.2.0'])
    def test_consistent_declarations(
        self,
        swift_policy_consumer: Path,
        monkeypatch: pytest.MonkeyPatch,
        observed: str | None,
    ) -> None:
        root = swift_policy_consumer
        before = snapshot_files(root)
        runner = Mock(side_effect=AssertionError('no tools may execute'))
        monkeypatch.setattr(subprocess, 'run', runner)
        assert validate(load_swift_policy_config(root), compiler_version=observed) == []
        assert snapshot_files(root) == before
        assert not (root / 'pyproject.toml').exists()
        runner.assert_not_called()

    @pytest.mark.parametrize(
        'filename,content,message',
        [
            ('.swift-version', '6.2.0', 'preferred version differs'),
            ('.swift-version', 'PRIVATE SECRET', 'invalid stable Swift version'),
            ('Package.swift', '// swift-tools-version: 6.0\n', 'tools version differs'),
            ('Package.swift', '', 'missing literal first-line'),
            (
                'Package.swift',
                '// comment\n// swift-tools-version: 5.9',
                'missing literal first-line',
            ),
            ('.github/workflows/ci.yml', 'jobs: {}', 'no explicit swift-version'),
            ('.github/workflows/ci.yml', '[', 'cannot read a valid workflow'),
        ],
    )
    def test_drift(
        self,
        swift_policy_consumer: Path,
        filename: str,
        content: str,
        message: str,
    ) -> None:
        (swift_policy_consumer / filename).write_text(content, encoding='utf-8')
        failures = validate(load_swift_policy_config(swift_policy_consumer))
        assert any(message in item for item in failures)
        assert 'PRIVATE SECRET' not in '\n'.join(failures)

    @pytest.mark.parametrize(
        'path',
        ['.swift-version', 'Package.swift', '.github/workflows/ci.yml'],
    )
    def test_escaping_links(
        self,
        swift_policy_consumer: Path,
        symlink: Callable[[Path, Path], None],
        path: str,
    ) -> None:
        root = swift_policy_consumer
        outside = root.parent / 'outside-toolchain-input'
        outside.write_text('PRIVATE', encoding='utf-8')
        target = root / path
        target.unlink()
        symlink(target, outside)
        assert any(
            'escapes repository' in f for f in validate(load_swift_policy_config(root))
        )

    @pytest.mark.parametrize(
        'path',
        ['.swift-version', 'Package.swift', '.github/workflows/ci.yml'],
    )
    @pytest.mark.parametrize('state', ['missing', 'decode', 'permission'])
    def test_missing_and_unreadable_inputs(
        self,
        swift_policy_consumer: Path,
        monkeypatch: pytest.MonkeyPatch,
        path: str,
        state: str,
    ) -> None:
        """
        Reject each inaccessible declaration without revealing private data.
        """
        root = swift_policy_consumer
        config = load_swift_policy_config(root)
        target = root / path
        if state == 'missing':
            target.unlink()
        elif state == 'decode':
            target.write_bytes(b'PRIVATE\xff')
        else:
            original = Path.read_text

            def read(
                selected: Path,
                encoding: str | None = None,
                errors: str | None = None,
            ) -> str:
                if selected == target:
                    raise PermissionError('PRIVATE PERMISSION DETAILS')
                return original(selected, encoding=encoding, errors=errors)

            monkeypatch.setattr(Path, 'read_text', read)
        if path.startswith('.github/'):
            expected = (
                'no Swift policy workflows match: .github/workflows/ci.yml'
                if state == 'missing'
                else '.github/workflows/ci.yml: '
                'cannot read a valid workflow version declaration'
            )
        else:
            expected = f'{path}: cannot read Swift policy input'
        before = snapshot_files(root)
        assert validate(config) == [expected]
        assert snapshot_files(root) == before

    @pytest.mark.parametrize('operation', ['resolve', 'glob'])
    @pytest.mark.parametrize('error', [OSError, ValueError])
    def test_root_and_workflow_inspection_errors_are_redacted(
        self,
        swift_policy_consumer: Path,
        operation: str,
        error: type[Exception],
    ) -> None:
        """Isolate discovery failures and suppress raw exception details."""
        root = swift_policy_consumer
        config = load_swift_policy_config(root)
        before = snapshot_files(root)
        with patch.object(Path, operation, side_effect=error('PRIVATE')):
            findings = validate(config)
        assert findings == (
            [
                '.swift-version: cannot read Swift policy input',
                'Package.swift: cannot read Swift policy input',
                'cannot resolve Swift policy workflow',
            ]
            if operation == 'resolve'
            else ['cannot discover Swift policy workflows']
        )
        assert snapshot_files(root) == before


# !SECTION
