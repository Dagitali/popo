"""
:mod:`tests.integration.test_i_guardrails` module.

Verify independent local/CI guardrail scenarios through public CLI output.
"""

import json

import pytest

from popo.cli import main
from popo.config.guardrails import GuardrailsConfig
from tests.support.files import snapshot_files

# SECTION: TESTS


class TestGuardrailCommand:
    """
    Exercise parity dispatch using the same standalone consumer fixture.

    Run the parity check within the exact profile delegated to Make as well as
    through standalone and default-selection commands.
    """

    def test_contract(
        self,
        guardrail_consumer: GuardrailsConfig,
        guardrail_failure: str | None,
        guardrail_arguments: tuple[str, ...],
        capsys: pytest.CaptureFixture[str],
        cli_format: str | None,
        format_arguments: tuple[str, ...],
    ) -> None:
        """Report literal entry-point drift through text and JSON check
        results.

        Self-inspection finishes without executing the declared Make recipe.
        Each command and drift domain receives independent consumer inputs.
        """
        root = guardrail_consumer.root
        before = snapshot_files(root)
        assert main(
            [
                *guardrail_arguments,
                '--root',
                str(root),
                *format_arguments,
            ],
        ) == int(guardrail_failure is not None)
        output = capsys.readouterr()
        assert output.err == ''
        if cli_format == 'json':
            result = json.loads(output.out)
            assert result['passed'] is (guardrail_failure is None)
            checks = result['checks']
            assert [check['check'] for check in checks] == (
                ['check-docs', 'check-guardrail-parity']
                if '--profile' in guardrail_arguments
                else ['check-guardrail-parity']
            )
            assert all(check['passed'] for check in checks[:-1])
            assert checks[-1]['passed'] is (guardrail_failure is None)
            assert checks[-1]['diagnostics'] == (
                []
                if guardrail_failure is None
                else [
                    {
                        'severity': 'error',
                        'message': guardrail_failure,
                    },
                ]
            )
        elif guardrail_failure is None:
            assert output.out.startswith('PASS: ')
        else:
            assert output.out == f'FAIL: {guardrail_failure}\n'
        assert snapshot_files(root) == before


# !SECTION
