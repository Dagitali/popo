"""
:mod:`tests.unit.checks.test_u_docs_references` module.

Cover reference definitions, reference labels and inline images offline.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from popo.checks.docs import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestMarkdownReferencesAndImages:
    """
    Cover markdown references and images.

    Cover reference definitions, reference labels and inline images offline.
    """

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
        """
        Check even unused definitions and retain their source line numbers.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        target : str
            Destination of an unused reference definition that must fail
            validation.
        message : str
            Expected diagnostic text for the broken reference destination.
        """
        readme = write_file('README.md', f'# Project\n\n[unused]: {target}\n')
        assert validate(tmp_path) == [f'{readme}:3: {message}: {target}']

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
        ('content', 'message'),
        [
            ('[Text][missing]', 'undefined reference: missing'),
            ('[Text][]', 'undefined reference: Text'),
            ('![Image][missing]', 'undefined reference: missing'),
            ('[same]: one.png\n[ SAME ]: two.png', 'conflicting reference:  SAME '),
            ('![Image](missing.png)', 'local target does not exist: missing.png'),
            ('![](missing.png)', 'local target does not exist: missing.png'),
            ('![Image](../outside.png)', 'link escapes repository: ../outside.png'),
            ('![Image](images/)', 'local target does not exist: images/'),
        ],
    )
    def test_reference_and_image_failures(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        content: str,
        message: str,
    ) -> None:
        """
        Reject missing labels, conflicting definitions and invalid images.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Root containing only synthetic consumer documentation.
        write_file : FileWriter
            UTF-8 writer for the Markdown source and target files.
        content : str
            Active Markdown whose observable failure is checked.
        message : str
            Expected diagnostic independent of the temporary root.
        """
        write_file('README.md', content)
        write_file('one.png', 'synthetic')
        write_file('two.png', 'synthetic')
        (tmp_path / 'images').mkdir()
        assert any(message in failure for failure in validate(tmp_path))

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
        assert validate(tmp_path) == []

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
