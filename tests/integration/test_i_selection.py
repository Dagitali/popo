"""Exercise language-neutral CLI plans and versioned offline JSON reports."""

import json
from pathlib import Path

import pytest

from popo.cli import main
from popo.config.guardrails import GuardrailsConfig
from tests.support.files import FileWriter

# SECTION: TESTS


class TestSelectedChecks:
    """Run native checks through the same CLI used locally and in CI."""

    @pytest.mark.parametrize('output_format', ['text', 'json'])
    @pytest.mark.parametrize('valid', [True, False])
    def test_swift_consumer(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        output_format: str,
        valid: bool,
    ) -> None:
        """A Swift repository can select docs/files without Python metadata."""
        config = write_file(
            'popo.toml',
            'checks=["check-docs","check-required-files"]\n[files]\nrequired=["Package.swift"]',
        )
        write_file('Package.swift', '// swift-tools-version: 6.0\n')
        readme = write_file(
            'README.md',
            '# Consumer\n' if valid else '[missing](absent)',
        )
        before = {p: p.read_bytes() for p in tmp_path.iterdir()}
        assert main(
            ['check-all', '--root', str(tmp_path), '--format', output_format],
        ) == int(not valid)
        output = capsys.readouterr()
        assert not output.err
        if output_format == 'json':
            result = json.loads(output.out)
            assert result['schema_version'] == 1
            assert result['passed'] is valid
            assert [r['check'] for r in result['checks']] == [
                'check-docs',
                'check-required-files',
            ]
            assert result['checks'][1]['passed'] is True
            if not valid:
                assert result['checks'][0]['diagnostics'][0]['severity'] == 'error'
                assert result['checks'][0]['summary'] == ''
        else:
            assert ('PASS:' if valid else 'FAIL:') in output.out
        assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before
        assert config.exists() and readme.exists()

    @pytest.mark.parametrize('output_format', ['text', 'json'])
    def test_profile_and_explain(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        output_format: str,
    ) -> None:
        """
        Explain does not execute validators, and profiles control execution.
        """
        write_file(
            'popo.toml',
            'checks=["check-required-files"]\n[profiles.docs]\nchecks=["check-docs"]',
        )
        args = ['--root', str(tmp_path), '--profile', 'docs', '--format', output_format]
        assert main(['explain', *args]) == 0
        output = capsys.readouterr().out
        if output_format == 'json':
            plan = json.loads(output)
            assert plan['checks'] == ['check-docs']
            assert plan['selection'] == 'profile: docs'
            assert plan['configuration_exists'] is True
            assert plan['configuration'] == str(tmp_path / 'popo.toml')
        else:
            assert 'profile: docs' in output
        assert main(['check-all', *args]) == 0
        capsys.readouterr()
        assert main(['check-all', '--root', str(tmp_path)]) == 1
        assert 'requires tool.popo.files' in capsys.readouterr().out

    @pytest.mark.parametrize('command', ['check-all', 'explain'])
    @pytest.mark.parametrize('output_format', ['text', 'json'])
    def test_invalid_plan(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        command: str,
        output_format: str,
    ) -> None:
        """
        Bad selection produces one configuration result in the chosen format.
        """
        write_file('popo.toml', 'checks=[]')
        assert main([command, '--root', str(tmp_path), '--format', output_format]) == 1
        output = capsys.readouterr()
        assert not output.err
        if output_format == 'json':
            result = json.loads(output.out)
            assert result['passed'] is False
            assert result['checks'][0]['check'] == 'configuration'
        else:
            assert 'checks must select at least one check' in output.out

    def test_independent_configuration_failures(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        One domain's bad settings do not hide later selected check failures.
        """
        write_file('popo.toml', 'checks=["check-required-files","check-docs"]\nfiles=1')
        write_file('README.md', '[missing](absent)')
        assert main(['check-all', '--root', str(tmp_path), '--format', 'json']) == 1
        result = json.loads(capsys.readouterr().out)
        assert len(result['checks']) == 2
        assert all(not check['passed'] for check in result['checks'])

    def test_individual_json(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Individual native commands share the offline result schema."""
        write_file('README.md', '# Consumer')
        assert main(['check-docs', '--root', str(tmp_path), '--format', 'json']) == 0
        result = json.loads(capsys.readouterr().out)
        assert result['command'] == 'check-docs'
        assert result['checks'][0]['diagnostics'] == []


class TestGuardrailCommand:
    """Exercise parity dispatch using the same standalone consumer fixture."""

    @pytest.mark.parametrize('command', ['check-guardrail-parity', 'check-all'])
    @pytest.mark.parametrize('valid', [True, False])
    def test_contract(
        self,
        guardrail_consumer: GuardrailsConfig,
        capsys: pytest.CaptureFixture[str],
        command: str,
        valid: bool,
    ) -> None:
        """
        Report literal entry-point drift through text and JSON check results.
        """
        if not valid:
            guardrail_consumer.makefile.write_text(
                'guardrails:\n\tfalse',
                encoding='utf-8',
            )
        assert main(
            [command, '--root', str(guardrail_consumer.root), '--format', 'json'],
        ) == int(not valid)
        result = json.loads(capsys.readouterr().out)
        assert result['checks'][0]['check'] == 'check-guardrail-parity'
        assert result['passed'] is valid


class TestSelfInspectingProfile:
    """Run the parity check within the exact profile delegated to Make."""

    def test_profile(
        self,
        guardrail_consumer: GuardrailsConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Self-inspection finishes without executing the declared Make recipe."""
        assert (
            main(
                [
                    'check-all',
                    '--root',
                    str(guardrail_consumer.root),
                    '--profile',
                    'guardrails',
                    '--format',
                    'json',
                ],
            )
            == 0
        )
        result = json.loads(capsys.readouterr().out)
        assert [check['check'] for check in result['checks']] == [
            'check-docs',
            'check-guardrail-parity',
        ]
        assert all(check['passed'] for check in result['checks'])


# !SECTION
