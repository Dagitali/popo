"""Exercise Swift toolchain policy through native CLI selection and reports."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from popo.cli import main
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestSwiftPolicyCommands:
    """
    Keep the explicit Swift policy independent of Python project metadata.
    """

    def test_public_dispatch(
        self,
        swift_policy_consumer: Path,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
        select_check: Callable[[Path, str], tuple[str, ...]],
    ) -> None:
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

    def test_explicit_compiler_observation(
        self,
        swift_policy_consumer: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert (
            main(
                [
                    'check-swift-policy',
                    '--root',
                    str(swift_policy_consumer),
                    '--compiler-version',
                    '6.3.0',
                    '--format',
                    'json',
                ],
            )
            == 1
        )
        report = json.loads(capsys.readouterr().out)
        assert not report['passed']
        assert (
            'compiler version is not supported'
            in report['checks'][0]['diagnostics'][0]['message']
        )

    def test_invalid_configuration_is_identified(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert (
            main(['check-swift-policy', '--root', str(tmp_path), '--format', 'json'])
            == 1
        )
        report = json.loads(capsys.readouterr().out)
        assert report['checks'][0]['diagnostics'][0]['message'].startswith(
            'configuration:',
        )


# !SECTION
