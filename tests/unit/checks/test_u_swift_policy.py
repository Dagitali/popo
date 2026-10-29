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
    Cover swift policy.

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
        """
        Verify bad observed compiler.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        observed : str
            Observed version or evidence value supplied by the scenario.
        message : str
            Expected error message or scenario diagnostic.
        """
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

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        require_preferred : bool
            Whether the preferred tool selection must be declared.
        ci_version : str
            Compiler or runtime version declared by CI.
        observed : str | None
            Observed version or evidence value supplied by the scenario.
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
        """
        Verify consistent declarations.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        observed : str | None
            Observed version or evidence value supplied by the scenario.
        """
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
            (
                '.swift-version',
                '6.2.0',
                'local declaration: preferred version differs from policy',
            ),
            (
                '.swift-version',
                'PRIVATE SECRET',
                'local declaration: invalid stable Swift version',
            ),
            (
                'Package.swift',
                '// swift-tools-version: 6.0\n',
                'local declaration: tools version differs from policy',
            ),
            ('Package.swift', '', 'missing literal first-line tools version'),
            (
                'Package.swift',
                '// comment\n// swift-tools-version: 5.9',
                'missing literal first-line tools version',
            ),
            (
                '.github/workflows/ci.yml',
                'jobs: {}',
                'no explicit swift-version declarations',
            ),
            (
                '.github/workflows/ci.yml',
                '[',
                'cannot read a valid workflow version declaration',
            ),
        ],
    )
    def test_drift(
        self,
        swift_policy_consumer: Path,
        filename: str,
        content: str,
        message: str,
    ) -> None:
        """
        Report exactly one located drift finding without changing inputs.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        filename : str
            Input filename used in the scenario.
        content : str
            Text written to the scenario input.
        message : str
            Expected error message or scenario diagnostic.
        """
        (swift_policy_consumer / filename).write_text(content, encoding='utf-8')
        before = snapshot_files(swift_policy_consumer)
        failures = validate(load_swift_policy_config(swift_policy_consumer))
        assert failures == [f'{filename}: {message}']
        assert 'PRIVATE SECRET' not in '\n'.join(failures)
        assert snapshot_files(swift_policy_consumer) == before

    @pytest.mark.parametrize(
        'path,message',
        [
            ('.swift-version', 'Swift policy input escapes repository root'),
            ('Package.swift', 'Swift policy input escapes repository root'),
            ('.github/workflows/ci.yml', 'workflow escapes repository root'),
        ],
    )
    def test_escaping_links(
        self,
        swift_policy_consumer: Path,
        symlink: Callable[[Path, Path], None],
        path: str,
        message: str,
    ) -> None:
        """
        Reject escapes before decoding and preserve inside/outside bytes.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        symlink : Callable[[Path, Path], None]
            Platform-aware fixture creating a symbolic link or skipping
            support.
        path : str
            Input path inspected by the operation.
        message : str
            Expected error message or scenario diagnostic.
        """
        root = swift_policy_consumer
        outside = root.parent / 'outside-toolchain-input'
        outside.write_bytes(b'\xffPRIVATE')
        target = root / path
        target.unlink()
        symlink(target, outside)
        before = snapshot_files(root)
        assert validate(load_swift_policy_config(root)) == [f'{path}: {message}']
        assert snapshot_files(root) == before
        assert outside.read_bytes() == b'\xffPRIVATE'

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

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture restoring patched attributes and environment values.
        path : str
            Input path inspected by the operation.
        state : str
            Observed audit state or scenario condition.
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
                """
                Inject the selected permission failure.

                Read unaffected inputs and inject a private permission failure
                for the target.

                Parameters
                ----------
                selected : Path
                    Selected input path or paths to inspect.
                encoding : str | None
                    Explicit text encoding, or None to use the reader default.
                errors : str | None
                    Text decoding error policy, or None for the reader default.

                Returns
                -------
                str
                    Original decoded contents for an unaffected input.

                Raises
                ------
                PermissionError
                    If the selected target is read; unaffected reads retain
                    native errors.
                """
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
        """
        Isolate discovery failures and suppress raw exception details.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        operation : str
            Filesystem or adapter operation selected for failure injection.
        error : type[Exception]
            Error value or exception class injected by the scenario.
        """
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
