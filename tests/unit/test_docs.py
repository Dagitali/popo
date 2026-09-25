"""
:mod:`tests.unit.test_docs` module.

Test local Markdown targets, heading anchors, and ignored build output.
"""

from pathlib import Path

import pytest

from popo.checks.docs import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestMarkdownLinks:
    """Cover local link resolution without accessing external sites."""

    @pytest.mark.parametrize(
        ('link', 'message'),
        [
            ('missing.md', 'local target does not exist'),
            ('#absent', 'anchor does not exist'),
        ],
    )
    def test_broken_links(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        link: str,
        message: str,
    ) -> None:
        readme = write_file('README.md', f'[Missing]({link})\n')
        assert validate(tmp_path) == [f'{readme}:1: {message}: {link}']

    def test_checks_github_but_ignores_generated_files(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        for directory in ('.github', 'dist', '.venv', 'docs/build'):
            write_file(f'{directory}/README.md', '[Missing](missing.md)\n')
        path = tmp_path / '.github/README.md'
        assert validate(tmp_path) == [
            f'{path}:1: local target does not exist: missing.md',
        ]

    def test_fenced_headings_do_not_create_or_number_anchors(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Use the same fence rules for link scanning and heading discovery."""
        readme = write_file(
            'README.md',
            '[Public](guide.md#public)\n[Hidden](guide.md#hidden)\n',
        )
        write_file(
            'guide.md',
            '````markdown\n~~~\n```\n# Hidden\n# Public\n````\n# Public\n',
        )
        assert validate(tmp_path) == [
            f'{readme}:2: anchor does not exist: guide.md#hidden',
        ]

    @pytest.mark.parametrize(
        ('link', 'target', 'content'),
        [
            ('docs/guide.md#getting-started', 'docs/guide.md', '# Getting Started\n'),
            ('my%20guide.md#intro-1', 'my guide.md', '# Intro\n# Intro\n'),
            ('docs', 'docs/README.md', '# Guide'),
            ('<guide.md>', 'guide.md', '# Guide'),
            ('guide.md "Guide title"', 'guide.md', '# Guide'),
            (
                'guide.md#public',
                'guide.md',
                '```\n# Hidden\n```\n~~~\n# Hidden\n~~~\n# Public',
            ),
        ],
    )
    def test_local_targets(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        link: str,
        target: str,
        content: str,
    ) -> None:
        write_file('README.md', f'[Guide]({link})\n[External](HTTPS://example.com)')
        write_file(target, content)
        assert validate(tmp_path) == []

    def test_missing_root(
        self,
        tmp_path: Path,
    ) -> None:
        root = tmp_path / 'missing'
        assert validate(root) == [f'repository root does not exist: {root}']

    @pytest.mark.parametrize(
        'block',
        [
            '```markdown\n[Example](missing.md)\n```',
            '~~~markdown\n[Example](missing.md)\n~~~',
            '```\n~~~\n[Example](missing.md)\n```',
            '````\n```\n[Example](missing.md)\n````',
            '```\n```python\n[Example](missing.md)\n```',
            '   ```markdown\n[Example](missing.md)\n  ````  ',
        ],
        ids=['backticks', 'tildes', 'mixed', 'shorter', 'info-string', 'indented'],
    )
    def test_skips_code_examples_and_preserves_line_numbers(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        block: str,
    ) -> None:
        """Only a matching, sufficiently long closing fence ends an example."""
        readme = write_file('README.md', f'{block}\n[Real](missing.md)\n')
        line = len(block.splitlines()) + 1
        assert validate(tmp_path) == [
            f'{readme}:{line}: local target does not exist: missing.md',
        ]

    @pytest.mark.parametrize('fence', ['```', '~~~'])
    def test_unclosed_fence_extends_to_end_of_file(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        fence: str,
    ) -> None:
        """Do not interpret unfinished code examples as active links."""
        write_file('README.md', f'{fence}\n[Example](missing.md)\n')
        assert validate(tmp_path) == []
