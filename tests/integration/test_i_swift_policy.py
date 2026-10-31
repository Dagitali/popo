"""
:mod:`tests.integration.test_i_swift_policy` module.

Exercise Swift toolchain policy through native CLI selection and reports.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from popo.cli import main
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestSwiftPolicyCommands:
    """
    Cover swift policy commands.

    Keep the explicit Swift policy independent of Python project metadata.
    """

    @pytest.mark.parametrize(
        ('observed', 'message'),
        (
            pytest.param('6.2.0', None, id='supported'),
            pytest.param(
                '6.3.0',
                'compiler version is not supported by policy',
                id='unsupported',
            ),
            pytest.param(
                '6.1-SNAPSHOT',
                'invalid stable Swift version',
                id='malformed',
            ),
        ),
    )
    def test_explicit_compiler_observation(
        self,
        swift_policy_consumer: Path,
        capsys: pytest.CaptureFixture[str],
        observed: str,
        message: str | None,
    ) -> None:
        """
        Report explicit compiler observations without changing declarations.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        observed : str
            Supported, unsupported or malformed explicit compiler observation.
        message : str | None
            Exact diagnostic detail, or None for a supported observation.
        """
        before = snapshot_files(swift_policy_consumer)
        failed = message is not None
        assert main(
            [
                'check-swift-policy',
                '--root',
                str(swift_policy_consumer),
                '--compiler-version',
                observed,
                '--format',
                'json',
            ],
        ) == int(failed)
        output = capsys.readouterr()
        assert output.err == ''
        assert json.loads(output.out) == {
            'schema_version': 1,
            'command': 'check-swift-policy',
            'passed': not failed,
            'checks': [
                {
                    'check': 'check-swift-policy',
                    'passed': not failed,
                    'diagnostics': (
                        []
                        if message is None
                        else [
                            {
                                'severity': 'error',
                                'message': f'--compiler-version: {message}',
                            },
                        ]
                    ),
                    'summary': ''
                    if failed
                    else 'Swift toolchain declarations are consistent',
                },
            ],
        }
        assert snapshot_files(swift_policy_consumer) == before

    def test_invalid_configuration_is_identified(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Verify invalid configuration is identified.

        Parameters
        ----------
        tmp_path : Path
            Per-test temporary directory supplied by pytest.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        """
        assert (
            main(['check-swift-policy', '--root', str(tmp_path), '--format', 'json'])
            == 1
        )
        report = json.loads(capsys.readouterr().out)
        assert report['checks'][0]['diagnostics'][0]['message'].startswith(
            'configuration:',
        )

    def test_public_dispatch(
        self,
        swift_policy_consumer: Path,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
        select_check: Callable[[Path, str], tuple[str, ...]],
    ) -> None:
        """
        Verify public dispatch.

        Parameters
        ----------
        swift_policy_consumer : Path
            Isolated Swift consumer with explicit compiler policy.
        capsys : pytest.CaptureFixture[str]
            Pytest fixture capturing standard output and error streams.
        cli_format : str | None
            Requested CLI output format, or None for its default.
        format_arguments : tuple[str, ...]
            CLI arguments selecting text or JSON output.
        select_check : Callable[[Path, str], tuple[str, ...]]
            Fixture selecting individual, aggregate or profiled execution.
        """
        root = swift_policy_consumer
        arguments = select_check(root, 'check-swift-policy')
        before = snapshot_files(root)
        assert main([*arguments, '--root', str(root), *format_arguments]) == 0
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            report = json.loads(output.out)
            assert report['passed']
            assert [item['check'] for item in report['checks']] == [
                'check-swift-policy',
            ]
        else:
            assert output.out.startswith('PASS:')
        assert snapshot_files(root) == before
        assert not (root / 'pyproject.toml').exists()


# !SECTION
