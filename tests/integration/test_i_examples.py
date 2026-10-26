"""
:mod:`tests.integration.test_i_examples` module.

Validate the maintained consumer examples without tools, credentials or
network.
"""

import json
from pathlib import Path

import pytest

from popo.cli import main
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestConsumerExamples:
    """Keep the executable example aligned with the public policy contract."""

    def test_shared_profile(
        self,
        example_consumer: Path,
        capsys: pytest.CaptureFixture[str],
        example_checks: tuple[str, ...],
    ) -> None:
        """
        Run each example's shared checks and its language-specific additions.
        """
        original = snapshot_files(example_consumer)
        status = main(
            [
                'check-all',
                '--root',
                str(example_consumer),
                '--profile',
                'guardrails',
                '--format',
                'json',
            ],
        )
        output = capsys.readouterr()
        assert status == 0, output.out + output.err
        assert output.err == ''
        report = json.loads(output.out)
        assert report['passed'] is True
        assert tuple(check['check'] for check in report['checks']) == example_checks
        assert snapshot_files(example_consumer) == original

    def test_specific_drift(
        self,
        example_consumer: Path,
        example_drift: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Give each declared entry-point mismatch a specific JSON diagnostic.
        """
        original = snapshot_files(example_consumer)
        status = main(
            [
                'check-all',
                '--root',
                str(example_consumer),
                '--profile',
                'guardrails',
                '--format',
                'json',
            ],
        )
        output = capsys.readouterr()
        assert status == 1, output.out + output.err
        assert output.err == ''
        report = json.loads(output.out)
        assert report['passed'] is False
        parity = report['checks'][-1]
        assert parity['check'] == 'check-guardrail-parity'
        assert len(parity['diagnostics']) == 1
        assert example_drift in parity['diagnostics'][0]['message']
        assert snapshot_files(example_consumer) == original


class TestPythonConsumerPolicies:
    """
    Preserve Python-specific policy differences in Python and CDK examples.
    """

    @pytest.mark.parametrize('example_name', ['python', 'cdk'], indirect=True)
    @pytest.mark.parametrize('domain', ['dependencies', 'python-policy'])
    def test_declared_policy_drift(
        self,
        example_consumer: Path,
        example_name: str,
        domain: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Fail a changed language policy while the shared wiring still passes.
        """
        if domain == 'python-policy':
            (example_consumer / '.python-version').write_text(
                '3.12\n',
                encoding='utf-8',
            )
            check = 'check-python-policy'
            diagnostic = "expected '3.13'"
        else:
            relative = (
                'requirements/lowest.txt'
                if example_name == 'python'
                else 'requirements.txt'
            )
            (example_consumer / relative).write_text(
                'packaging==0.0.1\n',
                encoding='utf-8',
            )
            check = 'check-dependency-boundaries'
            diagnostic = 'received'
        original = snapshot_files(example_consumer)
        status = main(
            [
                'check-all',
                '--root',
                str(example_consumer),
                '--profile',
                'guardrails',
                '--format',
                'json',
            ],
        )
        output = capsys.readouterr()
        assert status == 1, output.out + output.err
        assert output.err == ''
        report = json.loads(output.out)
        results = {item['check']: item for item in report['checks']}
        assert results[check]['passed'] is False
        assert diagnostic in results[check]['diagnostics'][0]['message']
        assert results['check-guardrail-parity']['passed'] is True
        assert snapshot_files(example_consumer) == original


# !SECTION
