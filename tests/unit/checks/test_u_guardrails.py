"""Inspect local and CI guardrail contracts as inert repository data."""

import pytest

from popo.checks.guardrails import validate
from popo.config.guardrails import GuardrailsConfig

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
        original = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
        assert validate(guardrail_consumer) == []
        assert {p: p.read_bytes() for p in root.rglob('*') if p.is_file()} == original

    @pytest.mark.parametrize(
        'recipe',
        [
            'guardrails:\n\t@popo check-all --profile guardrails\n',
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
        'recipe',
        [
            'other:\n\tpopo check-all --profile guardrails',
            'guardrails:\n\ttrue',
            'guardrails:\n\tpopo check-all --profile guardrails\n\tfalse',
            'guardrails:\nguardrails:\n',
            'guardrails: prerequisite\n\tpopo check-all --profile guardrails',
        ],
    )
    def test_make_drift(
        self,
        guardrail_consumer: GuardrailsConfig,
        recipe: str,
    ) -> None:
        """
        Reject missing, duplicate, indirect or changed invocation recipes.
        """
        guardrail_consumer.makefile.write_text(recipe, encoding='utf-8')
        assert len(validate(guardrail_consumer)) == 1

    @pytest.mark.parametrize(
        'old,new',
        [
            ('entry: make guardrails', 'entry: popo check-docs'),
            ('language: system', 'language: python'),
            ('pass_filenames: false', 'pass_filenames: false\n        args: false'),
            ('pass_filenames: false', 'pass_filenames: false\n        args: null'),
            ('always_run: true', 'always_run: false'),
            ('pass_filenames: false', 'pass_filenames: true'),
            ('pass_filenames: false', 'pass_filenames: "false"'),
            ('repo: local', 'repo: https://example.invalid/hooks'),
            ('id: popo', 'id: other'),
            ('pass_filenames: false', 'pass_filenames: false\n        args: [extra]'),
            ('pass_filenames: false', 'pass_filenames: false\n      - id: popo'),
        ],
    )
    def test_hook_drift(
        self,
        guardrail_consumer: GuardrailsConfig,
        old: str,
        new: str,
    ) -> None:
        """
        Check whole-repository hook settings and reject appended arguments.
        """
        path = guardrail_consumer.hooks
        path.write_text(path.read_text().replace(old, new), encoding='utf-8')
        assert len(validate(guardrail_consumer)) == 1

    @pytest.mark.parametrize(
        'old,new',
        [
            ('id: popo', 'id: other'),
            ('run: make guardrails', 'run: popo check-docs'),
            ('run: make guardrails', 'run: []'),
            ('run: make guardrails', 'run: make guardrails\n        uses: ./other'),
            (
                'run: make guardrails',
                'run: make guardrails\n        working-directory: infra',
            ),
            ('runs-on: ubuntu-latest', 'defaults: {run: {working-directory: infra}}'),
            ('name: Guardrails', 'defaults: {run: {working-directory: infra}}'),
            (
                'run: make guardrails',
                'run: make guardrails\n      - id: popo\n        run: true',
            ),
            ('  guardrails:', '  other:'),
        ],
    )
    def test_workflow_drift(
        self,
        guardrail_consumer: GuardrailsConfig,
        old: str,
        new: str,
    ) -> None:
        """Reject drift in the declared step, root or job selection."""
        path = guardrail_consumer.workflow
        path.write_text(path.read_text().replace(old, new), encoding='utf-8')
        assert len(validate(guardrail_consumer)) == 1

    @pytest.mark.parametrize('content', ['[', 'jobs: {}\njobs: {}', '[]', 'jobs: true'])
    def test_malformed_yaml(
        self,
        guardrail_consumer: GuardrailsConfig,
        content: str,
    ) -> None:
        """
        Unexpected YAML structures produce diagnostics rather than crashes.
        """
        guardrail_consumer.workflow.write_text(content, encoding='utf-8')
        guardrail_consumer.hooks.write_text(content, encoding='utf-8')
        assert len(validate(guardrail_consumer)) == 2

    def test_independent_missing_inputs(
        self,
        guardrail_consumer: GuardrailsConfig,
    ) -> None:
        """Report every missing contract file in one invocation."""
        for path in (
            guardrail_consumer.makefile,
            guardrail_consumer.hooks,
            guardrail_consumer.workflow,
        ):
            path.unlink()
        assert len(validate(guardrail_consumer)) == 3


class TestOptionalHookArguments:
    """Permit an explicitly empty argument list without weakening type checks."""

    def test_empty_arguments(
        self,
        guardrail_consumer: GuardrailsConfig,
    ) -> None:
        """An empty list preserves the canonical Make invocation."""
        path = guardrail_consumer.hooks
        path.write_text(path.read_text() + '        args: []\n', encoding='utf-8')
        assert validate(guardrail_consumer) == []


# !SECTION
