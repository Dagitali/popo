"""
:mod:`tests.unit.test_docs` module.

Test local Markdown targets, heading anchors, and ignored build output.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from popo.checks import docs
from popo.checks.docs import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestMarkdownLinks:
    """Cover local link resolution without accessing external sites."""

    def test_anchor_cache_is_shared_within_but_not_between_checks(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Reuse resolved targets during a run, then reread them after edits."""
        readme = write_file(
            'README.md',
            '[One](guide.md#intro)\n[Two](./guide.md#intro)\n',
        )
        guide = write_file('guide.md', '# Intro\n')
        with patch.object(docs, '_anchors', wraps=docs._anchors) as anchors:
            assert validate(tmp_path) == []
            anchors.assert_called_once_with(guide.resolve())
            write_file('guide.md', '# Renamed\n')
            assert validate(tmp_path) == [
                f'{readme}:1: anchor does not exist: guide.md#intro',
                f'{readme}:2: anchor does not exist: ./guide.md#intro',
            ]
            assert anchors.call_count == 2

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

    @pytest.mark.parametrize(
        ('target', 'message'),
        [
            ('missing.md', 'local target does not exist'),
            ('#missing', 'anchor does not exist'),
        ],
    )
    def test_broken_reference_definitions(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        target: str,
        message: str,
    ) -> None:
        """Check even unused definitions and retain their source line numbers."""
        readme = write_file('README.md', f'# Project\n\n[unused]: {target}\n')
        assert validate(tmp_path) == [f'{readme}:3: {message}: {target}']

    def test_checks_github_but_ignores_generated_files(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        for directory in (
            '.github',
            'dist',
            '.venv',
            'docs/build',
            'node_modules',
            'frontend/node_modules/vendor',
        ):
            write_file(f'{directory}/README.md', '[Missing](missing.md)\n')
        path = tmp_path / '.github/README.md'
        assert validate(tmp_path) == [
            f'{path}:1: local target does not exist: missing.md',
        ]

    @pytest.mark.parametrize(
        'link',
        ['[templates](templates/)', '[templates]: templates/'],
    )
    def test_directory_links_without_a_readme(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        link: str,
    ) -> None:
        write_file('templates/bug.yml', 'name: Bug\n')
        write_file('README.md', link)
        assert validate(tmp_path) == []

    @pytest.mark.parametrize(
        'name',
        ['docs/building.md', 'docs/build-guide/README.md', 'node_modules-guide.md'],
    )
    def test_exclusions_match_path_components_not_substrings(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        name: str,
    ) -> None:
        """Keep maintained documentation whose name resembles build output."""
        source = write_file(name, '[Missing](missing.md)\n')
        assert validate(tmp_path) == [
            f'{source}:1: local target does not exist: missing.md',
        ]

    @pytest.mark.parametrize(
        'anchor',
        ['<a id="legacy"></a>', "<a name='legacy'></a>"],
    )
    def test_explicit_anchors(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        anchor: str,
    ) -> None:
        write_file('README.md', f'{anchor}\n[Old](#legacy)\n[old]: #legacy\n')
        assert validate(tmp_path) == []

    def test_fenced_explicit_anchors_are_not_targets(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        readme = write_file(
            'README.md',
            '```html\n<a id="hidden"></a>\n```\n[x]: #hidden\n',
        )
        assert validate(tmp_path) == [f'{readme}:4: anchor does not exist: #hidden']

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

    def test_fenced_reference_definitions_are_examples(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        write_file('README.md', '```markdown\n[example]: missing.md\n```\n')
        assert validate(tmp_path) == []

    def test_linked_targets_in_excluded_directories(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Discovery exclusions do not disable validation of explicit links."""
        write_file('node_modules/demo/README.md', '# Package\n')
        source = write_file(
            'README.md',
            '[Package](node_modules/demo/README.md#missing)\n',
        )
        assert validate(tmp_path) == [
            f'{source}:1: anchor does not exist: node_modules/demo/README.md#missing',
        ]

    @pytest.mark.parametrize(
        ('link', 'target', 'content'),
        [
            ('docs/guide.md#getting-started', 'docs/guide.md', '# Getting Started\n'),
            ('my%20guide.md#intro-1', 'my guide.md', '# Intro\n# Intro\n'),
            ('docs', 'docs/README.md', '# Guide'),
            ('docs/#guide', 'docs/README.md', '# Guide'),
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
        'filename',
        ['manual.pdf', 'page.html', 'image.png'],
    )
    def test_non_markdown_fragments_do_not_decode_targets(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        filename: str,
    ) -> None:
        """Check existence without treating arbitrary file formats as Markdown."""
        (tmp_path / filename).write_bytes(b'\xff\xfe\x00')
        write_file('README.md', f'[Target]({filename}#section)\n')
        assert validate(tmp_path) == []

    def test_non_markdown_fragments_still_require_existing_files(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        readme = write_file('README.md', '[Manual](missing.pdf#page=2)\n')
        assert validate(tmp_path) == [
            f'{readme}:1: local target does not exist: missing.pdf#page=2',
        ]

    @pytest.mark.parametrize(
        'destination',
        ['guide.md#intro', '<guide.md#intro>', 'guide.md#intro "Guide title"'],
    )
    def test_reference_destinations(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        destination: str,
    ) -> None:
        """Validate definitions and optional titles without a network request."""
        write_file(
            'README.md',
            f'[Guide]\n\n[Guide]: {destination}\n[web]: HTTPS://example.com',
        )
        write_file('guide.md', '# Intro\n')
        assert validate(tmp_path) == []

    def test_reference_destination_with_spaces(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        write_file('README.md', '[guide]: <my guide.md#intro> "Title"\n')
        write_file('my guide.md', '# Intro\n')
        assert validate(tmp_path) == []

    @pytest.mark.parametrize(
        'target',
        ['../outside.md', '%2e%2e/outside.md', '../absent.md'],
    )
    @pytest.mark.parametrize(
        'reference',
        [False, True],
    )
    def test_rejects_repository_escapes(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        target: str,
        reference: bool,
    ) -> None:
        """Reject traversal before checking existence or reading target anchors."""
        write_file('outside.md', '# Outside\n')
        link = f'[outside]: {target}' if reference else f'[Outside]({target})'
        source = write_file('repo/README.md', link)
        assert validate(tmp_path / 'repo') == [
            f'{source}:1: link escapes repository: {target}',
        ]

    @pytest.mark.parametrize(
        'target',
        ['external#secret', 'directory/', 'docs/#secret'],
    )
    def test_rejects_symlinked_targets_outside_root(
        self,
        write_file: FileWriter,
        target: str,
    ) -> None:
        """Resolve links and directory README targets before anchor inspection."""
        outside = write_file('outside/private.md', '# Secret\n')
        source = write_file('repo/README.md', f'[Outside]({target})\n')
        root = source.parent
        (root / 'docs').mkdir()
        try:
            (root / 'external').symlink_to(outside)
            (root / 'directory').symlink_to(outside.parent, target_is_directory=True)
            (root / 'docs/README.md').symlink_to(outside)
        except OSError as error:
            pytest.skip(f'Symlinks are unavailable: {error}')
        with patch.object(docs, '_anchors') as anchors:
            assert validate(root) == [
                f'{source}:1: link escapes repository: {target}',
            ]
            anchors.assert_not_called()

    def test_relative_root_allows_parent_links_within_repository(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Reject escapes rather than every use of a parent-directory component."""
        write_file('repo/README.md', '# Home\n')
        write_file('repo/docs/guide.md', '[Home](../README.md#home)\n')
        monkeypatch.chdir(tmp_path)
        assert validate(Path('repo')) == []

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

    def test_uppercase_markdown_extension_keeps_fragment_validation(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        readme = write_file('README.md', '[Guide](guide.MD#missing)\n')
        write_file('guide.MD', '# Intro\n')
        assert validate(tmp_path) == [
            f'{readme}:1: anchor does not exist: guide.MD#missing',
        ]
