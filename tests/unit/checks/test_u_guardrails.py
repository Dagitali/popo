"""Inspect local and CI guardrail contracts as inert repository data."""

from pathlib import Path

import pytest

from popo.checks.guardrails import validate
from popo.config.guardrails import GuardrailsConfig
from tests.support.files import snapshot_files

# SECTION: CONSTANTS


NO_FILENAMES = 'pass_filenames: false'


# !SECTION


# SECTION: TESTS


class TestGuardrailParity:
    """
    Collect independent drift without invoking any configured consumer tool.
    """

    def test_matching_contract(
        self,
        guardrail_consumer: GuardrailsConfig,
    ) -> None:
        """Accept the explicit chain and preserve every consumer input byte."""
        root = guardrail_consumer.root
        original = snapshot_files(root)
        assert set(original) == {
            Path('popo.toml'),
            Path('Makefile'),
            Path('.pre-commit-config.yaml'),
            Path('.github/workflows/ci.yml'),
        }
        assert validate(guardrail_consumer) == []
        assert snapshot_files(root) == original

    @pytest.mark.parametrize(
        'recipe',
        [
            'guardrails:\n\t@popo check-all --profile guardrails\n',
            'guardrails:\n# Consumer comment\n\tpopo check-all --profile guardrails\n',
            'guardrails:\n\n\tpopo check-all --profile guardrails\n\nother:\n\tfalse',
        ],
    )
    def test_supported_make_spelling(
        self,
        guardrail_consumer: GuardrailsConfig,
        recipe: str,
    ) -> None:
        """
        Permit Make's silent prefix and whitespace between literal targets.
        """
        guardrail_consumer.makefile.write_text(recipe, encoding='utf-8')
        assert validate(guardrail_consumer) == []

    @pytest.mark.parametrize(
        ('recipe', 'failure'),
        [
            ('other:\n\tpopo check-all --profile guardrails', 'target'),
            ('guardrails:\n\ttrue', 'make'),
            ('guardrails:\n\tpopo check-all --profile guardrails\n\tfalse', 'make'),
            (
                'guardrails:\n\tpopo check-all --profile guardrails\n'
                '# Comment\n\tfalse',
                'make',
            ),
            ('guardrails:\nguardrails:\n', 'target'),
            (
                'guardrails: prerequisite\n\tpopo check-all --profile guardrails',
                'target',
            ),
        ],
    )
    def test_make_drift(
        self,
        guardrail_consumer: GuardrailsConfig,
        guardrail_diagnostics: dict[str, str],
        recipe: str,
        failure: str,
    ) -> None:
        """
        Reject missing, duplicate, indirect or changed invocation recipes.
        """
        guardrail_consumer.makefile.write_text(recipe, encoding='utf-8')
        assert validate(guardrail_consumer) == [guardrail_diagnostics[failure]]

    @pytest.mark.parametrize(
        ('old', 'new', 'failure'),
        [
            ('entry: make guardrails', 'entry: popo check-docs', 'hook'),
            ('language: system', 'language: python', 'hook'),
            (NO_FILENAMES, NO_FILENAMES + '\n        args: false', 'hook'),
            (NO_FILENAMES, NO_FILENAMES + '\n        args: null', 'hook'),
            ('always_run: true', 'always_run: false', 'hook'),
            ('always_run: true', 'always_run: 1', 'hook'),
            (NO_FILENAMES, 'pass_filenames: 0', 'hook'),
            (NO_FILENAMES, 'pass_filenames: true', 'hook'),
            (NO_FILENAMES, 'pass_filenames: "false"', 'hook'),
            ('repo: local', 'repo: https://example.invalid/hooks', 'hook'),
            ('id: popo', 'id: other', 'hook'),
            (NO_FILENAMES, NO_FILENAMES + '\n        args: [extra]', 'hook'),
            (NO_FILENAMES, NO_FILENAMES + '\n      - id: popo', 'hook'),
            ('id: popo', 'id: other', 'workflow'),
            ('run: make guardrails', 'run: popo check-docs', 'workflow'),
            ('run: make guardrails', 'run: []', 'workflow'),
            (
                'run: make guardrails',
                'run: make guardrails\n        uses: ./other',
                'workflow',
            ),
            (
                'run: make guardrails',
                'run: make guardrails\n        working-directory: infra',
                'directory',
            ),
            (
                'runs-on: ubuntu-latest',
                'defaults: {run: {working-directory: infra}}',
                'directory',
            ),
            (
                'name: Guardrails',
                'defaults: {run: {working-directory: infra}}',
                'directory',
            ),
            (
                'run: make guardrails',
                'run: make guardrails\n      - id: popo\n        run: true',
                'workflow',
            ),
            ('  guardrails:', '  other:', 'workflow'),
        ],
    )
    def test_entry_point_drift(
        self,
        guardrail_consumer: GuardrailsConfig,
        guardrail_diagnostics: dict[str, str],
        old: str,
        new: str,
        failure: str,
    ) -> None:
        """
        Check whole-repository hook settings and reject appended arguments.

        Reject drift in the declared workflow step, root or job selection.
        Each mutation runs against an independent consumer fixture.
        """
        path = (
            guardrail_consumer.hooks
            if failure == 'hook'
            else guardrail_consumer.workflow
        )
        content = path.read_text(encoding='utf-8')
        assert old in content, f'Mutation marker missing from {path}'
        path.write_text(content.replace(old, new), encoding='utf-8')
        before = snapshot_files(guardrail_consumer.root)
        assert validate(guardrail_consumer) == [guardrail_diagnostics[failure]]
        assert snapshot_files(guardrail_consumer.root) == before

    @pytest.mark.parametrize(
        ('content', 'parse_error'),
        [
            ('[', 'while parsing'),
            ('jobs: {}\njobs: {}', 'duplicate YAML key: jobs'),
            ('[]', None),
            ('jobs: true', None),
        ],
    )
    def test_malformed_yaml(
        self,
        guardrail_consumer: GuardrailsConfig,
        guardrail_diagnostics: dict[str, str],
        content: str,
        parse_error: str | None,
    ) -> None:
        """
        Unexpected YAML structures produce diagnostics rather than crashes.
        """
        guardrail_consumer.workflow.write_text(content, encoding='utf-8')
        guardrail_consumer.hooks.write_text(content, encoding='utf-8')
        failures = validate(guardrail_consumer)
        if parse_error is None:
            assert failures == [
                guardrail_diagnostics['hook'],
                guardrail_diagnostics['workflow'],
            ]
        else:
            assert len(failures) == 2
            for failure in failures:
                assert failure.startswith('guardrail parity: ')
                assert parse_error in failure

    def test_independent_missing_inputs(
        self,
        guardrail_consumer: GuardrailsConfig,
    ) -> None:
        """Report every missing contract file in one invocation."""
        paths = (
            guardrail_consumer.makefile,
            guardrail_consumer.hooks,
            guardrail_consumer.workflow,
        )
        for path in paths:
            path.unlink()
        failures = validate(guardrail_consumer)
        assert len(failures) == len(paths)
        for path, failure in zip(paths, failures, strict=True):
            assert failure.startswith('guardrail parity: ')
            assert str(path) in failure

    def test_empty_arguments(
        self,
        guardrail_consumer: GuardrailsConfig,
    ) -> None:
        """
        An empty list preserves the canonical Make invocation.

        Permit an explicitly empty argument list without weakening type checks.
        """
        path = guardrail_consumer.hooks
        path.write_text(
            path.read_text(encoding='utf-8') + '        args: []\n',
            encoding='utf-8',
        )
        assert validate(guardrail_consumer) == []


# !SECTION
