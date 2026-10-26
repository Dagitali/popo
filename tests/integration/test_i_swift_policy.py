"""Exercise Swift toolchain policy through native CLI selection and reports."""

import json
from pathlib import Path

import pytest

from popo.cli import main
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestSwiftPolicyCommands:
    """Keep the explicit Swift policy independent of Python project metadata."""

    @pytest.mark.parametrize('selection', ['individual', 'explicit', 'profile'])
    def test_public_dispatch(
        self,
        swift_policy_consumer: Path,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
        selection: str,
    ) -> None:
        root = swift_policy_consumer
        path = root / 'popo.toml'
        if selection == 'explicit':
            path.write_text(
                'checks=["check-swift-policy"]\n' + path.read_text(),
                encoding='utf-8',
            )
        elif selection == 'profile':
            path.write_text(
                '[profiles.swift]\nchecks=["check-swift-policy"]\n' + path.read_text(),
                encoding='utf-8',
            )
        arguments = (
            ['check-swift-policy']
            if selection == 'individual'
            else ['check-all']
            if selection == 'explicit'
            else ['check-all', '--profile', 'swift']
        )
        before = snapshot_files(root)
        assert main([*arguments, '--root', str(root), *format_arguments]) == 0
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            report = json.loads(output.out)
            assert report['passed']
            assert report['checks'][0]['check'] == 'check-swift-policy'
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
        report = json.loads(capsys.readouterr().out)
        assert report['checks'][0]['diagnostics'][0]['message'].startswith(
            'configuration:',
        )


# !SECTION
