"""Versioned machine-readable output for offline check execution."""

import json
from dataclasses import dataclass

from .support import report

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Keep a stable check identifier with its unchanged validator messages.

    Attributes
    ----------
    check : str
        Public offline command name, or ``configuration`` for selection errors.
    failures : tuple[str, ...]
        Diagnostics returned by the check; no guessed source locations.
    success : str
        Human-readable summary used when the check passes.
    """

    check: str
    failures: tuple[str, ...]
    success: str


# !SECTION


# SECTION: FUNCTIONS


def report_results(
    command: str,
    results: list[CheckResult],
    output_format: str,
) -> int:
    """Print text or schema-versioned JSON and return the aggregate status.

    Parameters
    ----------
    command : str
        Invoked public command.
    results : list[CheckResult]
        Ordered check outcomes, including successful checks.
    output_format : str
        Parser-validated ``text`` or ``json`` output selection.

    Returns
    -------
    int
        One if any result failed, otherwise zero. JSON output contains no text
        reports; existing validator messages remain intact.
    """
    failed = any(result.failures for result in results)
    if output_format == 'json':
        print(
            json.dumps(
                {
                    'schema_version': 1,
                    'command': command,
                    'passed': not failed,
                    'checks': [
                        {
                            'check': result.check,
                            'passed': not result.failures,
                            'diagnostics': [
                                {'severity': 'error', 'message': message}
                                for message in result.failures
                            ],
                            'summary': result.success if not result.failures else '',
                        }
                        for result in results
                    ],
                },
            ),
        )
        return int(failed)
    return report(
        [message for result in results for message in result.failures],
        success=(
            'all configured repository checks passed'
            if command == 'check-all'
            else results[0].success
        ),
    )
