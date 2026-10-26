"""Exercise Swift declaration drift without launching tools or manifests."""

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
    """Keep package minimums, preferred compilers and observed versions distinct."""

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

    @pytest.mark.parametrize('observed', ['6.3.0', '6.1-SNAPSHOT'])
    def test_bad_observed_compiler(
        self,
        swift_policy_consumer: Path,
        observed: str,
    ) -> None:
        failures = validate(
            load_swift_policy_config(swift_policy_consumer),
            compiler_version=observed,
        )
        assert len(failures) == 1
        assert failures[0].startswith('--compiler-version:')

    def test_preferred_ci_membership_is_configurable(
        self,
        swift_policy_consumer: Path,
    ) -> None:
        root = swift_policy_consumer
        workflow = root / '.github/workflows/ci.yml'
        workflow.write_text(
            workflow.read_text().replace('["6.1.2", "6.2.0"]', '["6.2.0"]'),
            encoding='utf-8',
        )
        config = load_swift_policy_config(root)
        assert validate(config) == [
            'Swift CI declarations do not include the preferred compiler',
        ]
        assert validate(replace(config, require_preferred_in_ci=False)) == []

    @pytest.mark.parametrize('ci_version', ['6.2.0', '6.3.0'])
    def test_explicit_compiler_cannot_supply_missing_ci_preference(
        self,
        swift_policy_consumer: Path,
        ci_version: str,
    ) -> None:
        """Keep caller observations distinct from actual workflow declarations."""
        workflow = swift_policy_consumer / '.github/workflows/ci.yml'
        workflow.write_text(
            workflow.read_text().replace('["6.1.2", "6.2.0"]', f'["{ci_version}"]'),
            encoding='utf-8',
        )
        failures = validate(
            load_swift_policy_config(swift_policy_consumer),
            compiler_version='6.1.2',
        )
        assert failures[-1] == (
            'Swift CI declarations do not include the preferred compiler'
        )
        assert len(failures) == (2 if ci_version == '6.3.0' else 1)

    @pytest.mark.parametrize(
        'path',
        ['.swift-version', 'Package.swift', '.github/workflows/ci.yml'],
    )
    def test_missing_and_unreadable_inputs(
        self,
        swift_policy_consumer: Path,
        path: str,
    ) -> None:
        root = swift_policy_consumer
        (root / path).unlink()
        assert validate(load_swift_policy_config(root))

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

    def test_root_and_workflow_inspection_errors_are_redacted(
        self,
        swift_policy_consumer: Path,
    ) -> None:
        config = load_swift_policy_config(swift_policy_consumer)
        with patch.object(Path, 'resolve', side_effect=ValueError('PRIVATE')):
            findings = validate(config)
        assert findings
        assert 'PRIVATE' not in '\n'.join(findings)
        with patch.object(Path, 'glob', side_effect=OSError('PRIVATE')):
            findings = validate(config)
        assert 'cannot discover Swift policy workflows' in findings


# !SECTION
