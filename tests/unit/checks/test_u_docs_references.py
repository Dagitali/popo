"""
:mod:`tests.unit.checks.test_u_docs_references` module.

Cover reference definitions, reference labels and inline images offline.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.checks.docs import validate
from tests.support.files import FileWriter, snapshot_files

# SECTION: TESTS


class TestMarkdownReferencesAndImages:
    """
    Cover markdown references and images.

    Cover reference definitions, reference labels and inline images offline.
    """

    def test_inline_images_cannot_escape_through_symlinks(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Resolve image symlinks before accepting repository-local targets.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Parent directory containing the repository and outside target.
        write_file : FileWriter
            Writer supplying synthetic Markdown and image files.
        symlink : Callable[[Path, Path], None]
            Platform-aware symlink creator.
        """
        outside = write_file('outside.png', 'synthetic')
        source = write_file('repo/README.md', '![Image](image.png)')
        symlink(source.parent / 'image.png', outside)
        assert validate(source.parent) == [
            f'{source}:1: link escapes repository: image.png',
        ]

    @pytest.mark.parametrize(
        ('content', 'line', 'message'),
        [
            pytest.param(
                '# Project\n\n[unused]: missing.md\n',
                3,
                'local target does not exist: missing.md',
                id='unused-missing-target',
            ),
            pytest.param(
                '# Project\n\n[unused]: #missing\n',
                3,
                'anchor does not exist: #missing',
                id='unused-missing-anchor',
            ),
            ('[Text][missing]', 1, 'undefined reference: missing'),
            ('[Text][]', 1, 'undefined reference: Text'),
            ('![Image][missing]', 1, 'undefined reference: missing'),
            ('[same]: one.png\n[ SAME ]: two.png', 2, 'conflicting reference:  SAME '),
            ('![Image](missing.png)', 1, 'local target does not exist: missing.png'),
            ('![](missing.png)', 1, 'local target does not exist: missing.png'),
            ('![Image](../outside.png)', 1, 'link escapes repository: ../outside.png'),
            ('![Image](images/)', 1, 'local target does not exist: images/'),
        ],
    )
    def test_reference_and_image_failures(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
        line: int,
        message: str,
    ) -> None:
        """
        Reject missing labels, conflicting definitions and invalid images.

        Check even unused definitions and retain their source line numbers.
        Missing local files and anchors fail independently of reference usage.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Root containing only synthetic consumer documentation.
        write_file : FileWriter
            UTF-8 writer for the Markdown source and target files.
        content : str
            Active Markdown whose observable failure is checked.
        line : int
            Exact one-based source line that must supply the sole finding.
        message : str
            Complete diagnostic suffix, independent of the temporary root.
        """
        source = write_file('README.md', content)
        write_file('one.png', 'synthetic')
        write_file('two.png', 'synthetic')
        (tmp_path / 'images').mkdir()
        before = snapshot_files(tmp_path)
        assert validate(tmp_path) == [f'{source}:{line}: {message}']
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'content',
        [
            '[Text][Some Label]\n[some   LABEL]: image.png',
            '[Some Label][]\n[ SOME label ]: image.png',
            '![Text][Some Label]\n[some label]: image.png',
            '[same]: image.png\n[SAME]: <image.png> "Title"',
            '![Image](image.png)',
            '![](image.png "Image title")',
            '![Image](<my image.png>)',
            '![Image](https://example.invalid/image.png)',
            '`[Text][missing]` and ``![Image](missing.png)``',
            '<!-- [Text][missing]\n![Image](missing.png) -->',
            '~~~md\n[Text][missing]\n~~~',
        ],
    )
    def test_reference_and_image_successes(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
    ) -> None:
        """
        Accept normalized labels and local images while ignoring examples.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Synthetic consumer root; no network is used.
        write_file : FileWriter
            UTF-8 writer for the source and synthetic image targets.
        content : str
            Markdown syntax expected to pass the bounded validator.
        """
        write_file('README.md', content)
        write_file('image.png', 'synthetic')
        write_file('my image.png', 'synthetic')
        before = snapshot_files(tmp_path)
        assert validate(tmp_path) == []
        assert snapshot_files(tmp_path) == before

    def test_reference_destination_with_spaces(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify reference destination with spaces.

        Verify angle-bracket reference destinations preserve spaces and
        fragments.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
        write_file('README.md', '[guide]: <my guide.md#intro> "Title"\n')
        write_file('my guide.md', '# Intro\n')
        assert validate(tmp_path) == []

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
        """
        Validate definitions and optional titles without a network request.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        destination : str
            Reference-definition destination, optionally including brackets or
            a title.
        """
        write_file(
            'README.md',
            f'[Guide]\n\n[Guide]: {destination}\n[web]: HTTPS://example.com',
        )
        write_file('guide.md', '# Intro\n')
        assert validate(tmp_path) == []


# !SECTION
