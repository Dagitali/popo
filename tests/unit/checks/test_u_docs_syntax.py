"""
:mod:`tests.unit.checks.test_u_docs_syntax` module.

Cover explicit anchors, code fences, inline code and comment boundaries.
"""

from pathlib import Path

import pytest

from popo.checks.docs import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestMarkdownSyntax:
    """
    Cover explicit anchors, code fences, inline code and comment boundaries.
    """

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
        """
        Verify maintained HTML id/name anchors satisfy inline and reference
        links.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        anchor : str
            Explicit HTML anchor declaration tested against matching local
            links.
        """
        write_file('README.md', f'{anchor}\n[Old](#legacy)\n[old]: #legacy\n')
        assert validate(tmp_path) == []

    def test_fenced_explicit_anchors_are_not_targets(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Verify HTML anchors inside code fences cannot satisfy active links.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
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
        """
        Use the same fence rules for link scanning and heading discovery.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
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
        """
        Verify reference definitions inside fenced examples are not checked.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        """
        write_file('README.md', '```markdown\n[example]: missing.md\n```\n')
        assert validate(tmp_path) == []

    def test_multiline_comments_preserve_diagnostic_line_numbers(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Keep diagnostics on original lines after masking HTML comments.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Synthetic consumer root.
        write_file : FileWriter
            Writer supplying a multiline comment and active reference.
        """
        source = write_file(
            'README.md',
            '<!--\n[Example][hidden]\n-->\n[Real][missing]',
        )
        assert validate(tmp_path) == [f'{source}:4: undefined reference: missing']

    @pytest.mark.parametrize(
        'block',
        [
            '```markdown\n[Example](missing.md)\n```',
            '~~~markdown\n[Example](missing.md)\n~~~',
            '```\n~~~\n[Example](missing.md)\n```',
            '````\n```\n[Example](missing.md)\n````',
            '```\n```python\n[Example](missing.md)\n```',
            '   ```markdown\n[Example](missing.md)\n  ````  ',
            '```html\n<!-- literal comment opener\n```',
            '`<!--` is a literal comment opener.',
        ],
        ids=[
            'backticks',
            'tildes',
            'mixed',
            'shorter',
            'info-string',
            'indented',
            'fenced-comment-delimiter',
            'inline-comment-delimiter',
        ],
    )
    def test_skips_code_examples_and_preserves_line_numbers(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        block: str,
    ) -> None:
        """
        Only a matching, sufficiently long closing fence ends an example.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        block : str
            Fenced code example inserted before an active broken link.
        """
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
        """
        Do not interpret unfinished code examples as active links.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        fence : str
            Opening code fence deliberately left without a matching close.
        """
        write_file('README.md', f'{fence}\n[Example](missing.md)\n')
        assert validate(tmp_path) == []


# !SECTION
