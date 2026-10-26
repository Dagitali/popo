"""
:mod:`tests.integration.test_i_selection` module.

Exercise language-neutral CLI plans and versioned offline JSON reports.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from popo.cli import main
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='profile_consumer')
def profile_consumer_fixture(
    write_file: FileWriter,
    tmp_path: Path,
) -> Path:
    """
    Provide independent profile/explanation cases with invalid default policy.

    Parameters
    ----------
    write_file : FileWriter
        Writer for the temporary consumer policy.
    tmp_path : pathlib.Path
        Fresh root for each command and output-format scenario.

    Returns
    -------
    pathlib.Path
        Consumer selecting an unconfigured file check by default and only docs
        through its named profile. Tests choose their own Markdown contents.
    """
    write_file(
        'popo.toml',
        'checks=["check-required-files"]\n[profiles.docs]\nchecks=["check-docs"]',
    )
    return tmp_path


# !SECTION


# SECTION: TESTS


class TestSelectedChecks:
    """Run native checks through the same CLI used locally and in CI."""

    def test_explain(
        self,
        profile_consumer: Path,
        write_file: FileWriter,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        cli_format: str | None,
        format_arguments: tuple[str, ...],
    ) -> None:
        """Explain does not execute validators, and profiles control execution.

        Broken Markdown would fail the selected check if explanation invoked
        it; an observer also fails immediately if that validator is called.
        Keep this consumer independent of profile execution scenarios.
        """
        validator = Mock(side_effect=AssertionError('explain must not run checks'))
        monkeypatch.setattr('popo.checks.docs.validate', validator)
        write_file('README.md', '[missing](absent)')
        before = snapshot_files(profile_consumer)
        assert (
            main(
                [
                    'explain',
                    '--root',
                    str(profile_consumer),
                    '--profile',
                    'docs',
                    *format_arguments,
                ],
            )
            == 0
        )
        validator.assert_not_called()
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            plan = json.loads(output.out)
            assert plan['checks'] == ['check-docs']
            assert plan['selection'] == 'profile: docs'
            assert plan['configuration_exists'] is True
            assert plan['configuration'] == str(profile_consumer / 'popo.toml')
        else:
            assert 'profile: docs' in output.out
            assert 'check-docs' in output.out
        assert snapshot_files(profile_consumer) == before

    def test_independent_configuration_failures(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
    ) -> None:
        """
        One domain's bad settings do not hide later selected check failures.
        """
        write_file('popo.toml', 'checks=["check-required-files","check-docs"]\nfiles=1')
        write_file('README.md', '[missing](absent)')
        assert main(['check-all', '--root', str(tmp_path), *format_arguments]) == 1
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            result = json.loads(output.out)
            assert [check['check'] for check in result['checks']] == [
                'check-required-files',
                'check-docs',
            ]
            assert all(not check['passed'] for check in result['checks'])
        else:
            assert 'configuration: tool.popo.files must be a TOML table' in output.out
            assert 'local target does not exist: absent' in output.out

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

    @pytest.mark.parametrize('command', ['check-all', 'explain'])
    def test_invalid_plan(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        command: str,
        cli_format: str | None,
        format_arguments: tuple[str, ...],
    ) -> None:
        """
        Bad selection produces one configuration result in the chosen format.
        """
        write_file('popo.toml', 'checks=[]')
        assert main([command, '--root', str(tmp_path), *format_arguments]) == 1
        output = capsys.readouterr()
        assert not output.err
        if cli_format == 'json':
            result = json.loads(output.out)
            assert result['passed'] is False
            assert result['checks'][0]['check'] == 'configuration'
        else:
            assert 'checks must select at least one check' in output.out

    @pytest.mark.parametrize('profile', ['docs', None], ids=['named', 'default'])
    def test_profile_execution(
        self,
        profile_consumer: Path,
        write_file: FileWriter,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
        profile: str | None,
    ) -> None:
        """
        A selected profile replaces the independently failing default checks.
        """
        write_file('README.md', '# Consumer')
        profile_arguments = [] if profile is None else ['--profile', profile]
        assert main(
            [
                'check-all',
                '--root',
                str(profile_consumer),
                *profile_arguments,
                *format_arguments,
            ],
        ) == int(profile is None)
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            result = json.loads(output.out)
            assert result['passed'] is (profile is not None)
            assert [check['check'] for check in result['checks']] == [
                'check-required-files' if profile is None else 'check-docs',
            ]
        else:
            assert (
                'requires tool.popo.files' if profile is None else 'PASS:'
            ) in output.out

    @pytest.mark.parametrize('valid', [True, False], ids=['passing', 'failing'])
    def test_swift_consumer(
        self,
        write_file: FileWriter,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
        valid: bool,
    ) -> None:
        """A Swift repository can select docs/files without Python metadata."""
        write_file(
            'popo.toml',
            'checks=["check-docs","check-required-files"]\n[files]\nrequired=["Package.swift"]',
        )
        write_file('Package.swift', '// swift-tools-version: 6.0\n')
        write_file('README.md', '# Consumer\n' if valid else '[missing](absent)')
        before = snapshot_files(tmp_path)
        assert main(
            ['check-all', '--root', str(tmp_path), *format_arguments],
        ) == int(not valid)
        output = capsys.readouterr()
        assert not output.err
        if cli_format == 'json':
            result = json.loads(output.out)
            assert result['schema_version'] == 1
            assert result['passed'] is valid
            assert [check['check'] for check in result['checks']] == [
                'check-docs',
                'check-required-files',
            ]
            assert result['checks'][1]['passed'] is True
            if not valid:
                assert result['checks'][0]['diagnostics'] == [
                    {
                        'severity': 'error',
                        'message': (
                            f'{tmp_path / 'README.md'}:1: '
                            'local target does not exist: absent'
                        ),
                    },
                ]
                assert result['checks'][0]['summary'] == ''
        else:
            assert ('PASS:' if valid else 'FAIL:') in output.out
        assert snapshot_files(tmp_path) == before


# !SECTION
