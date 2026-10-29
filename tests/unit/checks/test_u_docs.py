"""
:mod:`tests.unit.checks.test_u_docs` module.

Test local Markdown targets, heading anchors, and ignored build output.

Cover local target resolution, discovery and containment offline.

The Markdown suites collectively cover local link resolution without
accessing external sites.

Notes
-----
Create local fixtures for headings, references, code fences, discovery
exclusions, and containment rules. Symlink scenarios skip when the platform
cannot create them; external destinations are not fetched.
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from popo.checks import docs
from popo.checks.docs import validate
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestMarkdownLinks:
    """Cover local target resolution, discovery and containment offline."""

    def test_anchor_cache_is_shared_within_but_not_between_checks(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Reuse resolved targets during a run, then reread them after edits.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
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
        """
        Verify missing local files and anchors retain their source line in
        diagnostics.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        link : str
            Markdown link text or destination selected for the scenario.
        message : str
            Expected diagnostic text for the missing local file or anchor.
        """
        readme = write_file('README.md', f'[Missing]({link})\n')
        assert validate(tmp_path) == [f'{readme}:1: {message}: {link}']

    def test_checks_github_but_ignores_generated_files(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify discovery includes GitHub Markdown and excludes generated/vendor
        paths.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
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
        """
        Verify plain directory links pass without requiring a README target.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        link : str
            Markdown link text or destination selected for the scenario.
        """
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
        """
        Keep maintained documentation whose name resembles build output.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        name : str
            Maintained Markdown path chosen to resemble an excluded directory
            name.
        """
        source = write_file(name, '[Missing](missing.md)\n')
        assert validate(tmp_path) == [
            f'{source}:1: local target does not exist: missing.md',
        ]

    @pytest.mark.parametrize(
        'target',
        [
            'http://[broken',
            '//[broken',
            'https://example.com／path',
            'bad%00.md',
            'bad%00.md#intro',
        ],
    )
    @pytest.mark.parametrize('kind', ('link', 'image', 'reference'))
    def test_invalid_destination_keeps_later_findings(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        target: str,
        kind: str,
    ) -> None:
        """Report invalid URLs/paths and continue checking later links."""
        line = (
            f'[bad]: {target}'
            if kind == 'reference'
            else f'{'!' if kind == 'image' else ''}[bad]({target})'
        )
        source = write_file('README.md', line + '\n[missing](missing.md)\n')
        before = snapshot_files(tmp_path)
        assert validate(tmp_path) == [
            f'{source}:1: invalid link target: {target}',
            f'{source}:2: local target does not exist: missing.md',
        ]
        assert snapshot_files(tmp_path) == before

    def test_linked_targets_in_excluded_directories(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Discovery exclusions do not disable validation of explicit links.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
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
        """
        Verify supported local destinations and fragments resolve successfully.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        link : str
            Markdown link text or destination selected for the scenario.
        target : str
            Relative file path created to satisfy the Markdown link.
        content : str
            Target-file contents used to resolve the link and any fragment.
        """
        write_file('README.md', f'[Guide]({link})\n[External](HTTPS://example.com)')
        write_file(target, content)
        assert validate(tmp_path) == []

    def test_missing_root(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify a missing repository root produces a discovery diagnostic.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
        root = tmp_path / 'missing'
        assert validate(root) == [f'repository root does not exist: {root}']

    def test_mixed_reference_and_inline_findings_preserve_order(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Keep reference-use findings before ordered link/image destinations."""
        source = write_file(
            'README.md',
            '[Missing][unknown] [Collapsed][] [Known][defined] '
            '[A](missing-a.txt) ![Image](missing-image.png) [B](missing-b.txt)\n'
            '[defined]: missing-definition.txt\n',
        )
        before = snapshot_files(tmp_path)
        assert validate(tmp_path) == [
            f'{source}:1: undefined reference: unknown',
            f'{source}:1: undefined reference: Collapsed',
            f'{source}:1: local target does not exist: missing-a.txt',
            f'{source}:1: local target does not exist: missing-image.png',
            f'{source}:1: local target does not exist: missing-b.txt',
            f'{source}:2: local target does not exist: missing-definition.txt',
        ]
        assert snapshot_files(tmp_path) == before

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
        """
        Check existence without treating arbitrary file formats as Markdown.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        filename : str
            Non-Markdown target filename populated with binary bytes.
        """
        (tmp_path / filename).write_bytes(b'\xff\xfe\x00')
        write_file('README.md', f'[Target]({filename}#section)\n')
        assert validate(tmp_path) == []

    def test_non_markdown_fragments_still_require_existing_files(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify non-Markdown fragment links still require the target file to
        exist.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
        readme = write_file('README.md', '[Manual](missing.pdf#page=2)\n')
        assert validate(tmp_path) == [
            f'{readme}:1: local target does not exist: missing.pdf#page=2',
        ]

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
        """
        Reject traversal before checking existence or reading target anchors.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        target : str
            Destination or expected configuration value selected for the
            scenario.
        reference : bool
            Whether to use a reference definition instead of an inline link.
        """
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
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Resolve links and directory README targets before anchor inspection.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        symlink : collections.abc.Callable
            Platform-aware creator for temporary symbolic links.
        target : str
            Destination or expected configuration value selected for the
            scenario.
        """
        outside = write_file('outside/private.md', '# Secret\n')
        source = write_file('repo/README.md', f'[Outside]({target})\n')
        root = source.parent
        (root / 'docs').mkdir()
        symlink(root / 'external', outside)
        symlink(root / 'directory', outside.parent)
        symlink(root / 'docs/README.md', outside)
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
        """
        Reject escapes rather than every use of a parent-directory component.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        monkeypatch : pytest.MonkeyPatch
            Restore environment, attributes, and working directory.
        """
        write_file('repo/README.md', '# Home\n')
        write_file('repo/docs/guide.md', '[Home](../README.md#home)\n')
        monkeypatch.chdir(tmp_path)
        assert validate(Path('repo')) == []

    def test_uppercase_markdown_extension_keeps_fragment_validation(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify uppercase Markdown extensions still receive heading-anchor
        checks.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
        readme = write_file('README.md', '[Guide](guide.MD#missing)\n')
        write_file('guide.MD', '# Intro\n')
        assert validate(tmp_path) == [
            f'{readme}:1: anchor does not exist: guide.MD#missing',
        ]


class TestTitledDestinations:
    """Normalize supported titles and wrappers before local path checks."""

    @pytest.mark.parametrize('image', (False, True), ids=('link', 'image'))
    @pytest.mark.parametrize('present', (False, True), ids=('missing', 'present'))
    @pytest.mark.parametrize(
        'destination',
        ('guide.md', 'guide.md#intro', 'my guide.md#intro'),
    )
    def test_titled_angle_destinations(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        image: bool,
        present: bool,
        destination: str,
    ) -> None:
        """Resolve wrapped paths/fragments and report normalized failures."""
        readme = write_file(
            'README.md',
            f'{'!' if image else ''}[Guide](<{destination}> "Guide title")\n',
        )
        if present:
            write_file(destination.partition('#')[0], '# Intro\n')
        before = snapshot_files(tmp_path)
        assert validate(tmp_path) == (
            []
            if present
            else [f'{readme}:1: local target does not exist: {destination}']
        )
        assert snapshot_files(tmp_path) == before


class TestHeadingSlugCollisions:
    """Allocate unique heading suffixes without affecting explicit anchors."""

    def test_explicit_anchors_do_not_reserve_heading_suffixes(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """Keep HTML anchors separate from heading suffix allocation."""
        path = write_file(
            'README.md',
            '<a id="echo-1"></a>\n# Echo\n# Echo\n',
        )
        assert docs._anchors(path) == {'echo', 'echo-1'}
        assert validate(tmp_path) == []

    @pytest.mark.parametrize(
        'headings,expected',
        (
            (
                ('Echo', 'Echo', 'Echo 1', 'Echo-1', 'Echo'),
                ('echo', 'echo-1', 'echo-1-1', 'echo-1-2', 'echo-2'),
            ),
            (
                ('Foxtrot-1', 'Foxtrot', 'Foxtrot'),
                ('foxtrot-1', 'foxtrot', 'foxtrot-2'),
            ),
            (
                ('A-1', 'A-2', 'A', 'A', 'A'),
                ('a-1', 'a-2', 'a', 'a-3', 'a-4'),
            ),
        ),
    )
    def test_generated_suffixes_reserve_heading_names(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        headings: tuple[str, ...],
        expected: tuple[str, ...],
    ) -> None:
        """
        Resolve links to headings colliding with generated or natural IDs.
        """
        path = write_file(
            'README.md',
            '\n'.join(
                [
                    *(f'# {heading}' for heading in headings),
                    *(f'[Heading](#{slug})' for slug in expected),
                ],
            ),
        )
        before = snapshot_files(tmp_path)
        assert docs._anchors(path) == set(expected)
        assert validate(tmp_path) == []
        assert snapshot_files(tmp_path) == before


# !SECTION
