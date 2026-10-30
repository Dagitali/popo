"""
:mod:`tests.unit.test_u_reporting` module.

Protect single-pass text reporting, JSON contracts and aggregate exit status.
"""

import json
from collections.abc import Iterator

import pytest

from popo.reporting import CheckResult, report_results
from popo.support import report

# SECTION: TESTS


class TestCheckReporting:
    """Preserve command identity, schemas and empty-result behavior."""

    @pytest.mark.parametrize('command', ('check-docs', 'check-all'))
    @pytest.mark.parametrize('output_format', ('text', 'json'))
    @pytest.mark.parametrize(
        'failure_states',
        (
            pytest.param((False, False), id='all-pass'),
            pytest.param((True, False), id='first-fails'),
            pytest.param((False, True), id='last-fails'),
            pytest.param((True, True), id='both-fail'),
        ),
    )
    def test_check_order_messages_and_exit_status(
        self,
        capsys: pytest.CaptureFixture[str],
        command: str,
        output_format: str,
        failure_states: tuple[bool, bool],
    ) -> None:
        """
        Preserve check order, duplicate/blank findings and summary selection.

        Parameters
        ----------
        capsys : pytest.CaptureFixture[str]
            Captured public output and error streams.
        command : str
            Individual or aggregate command whose reporting rules apply.
        output_format : str
            Text or versioned JSON output selection.
        failure_states : tuple[bool, bool]
            Independent failure flags for the first and second check.
        """
        first_failed, second_failed = failure_states
        failed = any(failure_states)
        first_failures = ('earlier',) if first_failed else ()
        failures = ('first', 'first', '') if second_failed else ()
        results = [
            CheckResult('check-docs', first_failures, 'docs passed'),
            CheckResult('check-python-policy', failures, 'python passed'),
        ]
        before = list(results)
        assert report_results(command, results, output_format) == int(failed)
        assert results == before
        output = capsys.readouterr()
        assert output.err == ''
        if output_format == 'json':
            assert json.loads(output.out) == {
                'schema_version': 1,
                'command': command,
                'passed': not failed,
                'checks': [
                    {
                        'check': 'check-docs',
                        'passed': not first_failed,
                        'diagnostics': [
                            {'severity': 'error', 'message': message}
                            for message in first_failures
                        ],
                        'summary': '' if first_failed else 'docs passed',
                    },
                    {
                        'check': 'check-python-policy',
                        'passed': not second_failed,
                        'diagnostics': [
                            {'severity': 'error', 'message': message}
                            for message in failures
                        ],
                        'summary': '' if second_failed else 'python passed',
                    },
                ],
            }
        elif failed:
            assert output.out == (
                ('FAIL: earlier\n' if first_failed else '')
                + ('FAIL: first\nFAIL: first\nFAIL: \n' if second_failed else '')
            )
        else:
            assert output.out == (
                'PASS: all configured repository checks passed\n'
                if command == 'check-all'
                else 'PASS: docs passed\n'
            )

    @pytest.mark.parametrize(
        'command,output_format',
        [('check-all', 'text'), ('check-all', 'json'), ('check-docs', 'json')],
    )
    def test_empty_aggregate_or_json_results_pass(
        self,
        capsys: pytest.CaptureFixture[str],
        command: str,
        output_format: str,
    ) -> None:
        """
        Preserve empty aggregate success and empty versioned result arrays.

        Parameters
        ----------
        capsys : pytest.CaptureFixture[str]
            Captured standard output and error.
        command : str
            Individual or aggregate reporting command.
        output_format : str
            Supported output format permitting empty results.
        """
        assert report_results(command, [], output_format) == 0
        output = capsys.readouterr()
        assert output.err == ''
        if output_format == 'json':
            assert json.loads(output.out) == {
                'schema_version': 1,
                'command': command,
                'passed': True,
                'checks': [],
            }
        else:
            assert output.out == 'PASS: all configured repository checks passed\n'

    def test_empty_individual_text_results_raise(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Require an individual text result before emitting any report output.

        Parameters
        ----------
        capsys : pytest.CaptureFixture[str]
            Captured streams that must remain empty on contract failure.
        """
        with pytest.raises(IndexError):
            report_results('check-docs', [], 'text')
        assert capsys.readouterr() == ('', '')


class TestTextReporting:
    """Consume failure iterables once without depending on their truthiness."""

    def test_iteration_failure_propagates_after_partial_output(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Propagate iterator errors without printing a misleading success line.

        Parameters
        ----------
        capsys : pytest.CaptureFixture[str]
            Captured partial output and error streams.
        """
        error = RuntimeError('failure iteration stopped')

        def failures() -> Iterator[str]:
            """
            Yield one diagnostic before failing to produce later observations.

            Yields
            ------
            str
                First failure message, emitted before the injected exception.

            Raises
            ------
            RuntimeError
                Always raise the enclosing scenario's exception after yielding.
            """
            yield 'first'
            raise error

        with pytest.raises(
            RuntimeError,
            match='failure iteration stopped',
            check=lambda raised: raised is error,
        ):
            report(failures(), success='done')
        assert capsys.readouterr() == ('FAIL: first\n', '')

    @pytest.mark.parametrize('iterator', (False, True))
    @pytest.mark.parametrize(
        'failures,expected,status',
        [
            ((), 'PASS: done\n', 0),
            (('one',), 'FAIL: one\n', 1),
            (('same', 'same'), 'FAIL: same\nFAIL: same\n', 1),
            (('',), 'FAIL: \n', 1),
            (('é😀',), 'FAIL: é😀\n', 1),
            (('first\nsecond',), 'FAIL: first\nsecond\n', 1),
        ],
        ids=('empty', 'single', 'duplicates', 'blank-message', 'unicode', 'multiline'),
    )
    def test_order_content_and_status(
        self,
        capsys: pytest.CaptureFixture[str],
        iterator: bool,
        failures: tuple[str, ...],
        expected: str,
        status: int,
    ) -> None:
        """
        Report sequences and one-shot iterators with identical public output.

        Parameters
        ----------
        capsys : pytest.CaptureFixture[str]
            Captured output and error streams.
        iterator : bool
            Whether to supply a one-shot iterator rather than its tuple.
        failures : tuple[str, ...]
            Ordered diagnostic contents, including intentionally blank strings.
        expected : str
            Complete standard output, including prefixes and final newlines.
        status : int
            Exit status determined by the presence of failure observations.
        """
        values = iter(failures) if iterator else failures
        assert report(values, success='done') == status
        assert capsys.readouterr() == (expected, '')
        if iterator:
            assert list(values) == []


# !SECTION
