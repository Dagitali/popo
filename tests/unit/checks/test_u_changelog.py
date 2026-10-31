"""
:mod:`tests.unit.checks.test_u_changelog` module.

Test release headings, calendar dates, and missing changelog errors.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from popo.checks.changelog import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestChangelog:
    """
    Validate dated semantic releases with precise failure diagnostics.

    Notes
    -----
    Exercise optional version prefixes, real calendar dates, missing files, and
    invalid version syntax using temporary changelog text.
    """

    @pytest.mark.parametrize(
        ('content', 'expected'),
        [
            pytest.param('## [1.2.3] - 2026-09-20\n', (), id='dated-release'),
            pytest.param(
                '# Changelog\n',
                ('CHANGELOG.md has no dated section for 1.2.3',),
                id='missing-section',
            ),
            pytest.param(
                '## [1.2.3] - 2026-02-30\n',
                ('CHANGELOG.md has an invalid date for 1.2.3: 2026-02-30',),
                id='impossible-date',
            ),
            pytest.param('## [1.2.3] - 2028-02-29\n', (), id='future-leap-day'),
            pytest.param('## [1.2.3] - 2000-02-29\n', (), id='leap-century'),
            pytest.param(
                '## [1.2.3] - 1900-02-29\n',
                ('CHANGELOG.md has an invalid date for 1.2.3: 1900-02-29',),
                id='non-leap-century',
            ),
            pytest.param(
                '## [1.2.3] - 2026-09-20\n## [1.2.3] - 2026-02-30\n',
                (),
                id='first-valid-heading-wins',
            ),
            pytest.param(
                '## [1.2.3] - 2026-02-30\n## [1.2.3] - 2026-09-20\n',
                ('CHANGELOG.md has an invalid date for 1.2.3: 2026-02-30',),
                id='first-invalid-heading-wins',
            ),
            pytest.param(
                '```markdown\n## [1.2.3] - 2026-09-20\n```\n',
                (),
                id='textual-heading-in-fence',
            ),
            pytest.param(
                '## 1.2.3 - 2026-09-20\n',
                ('CHANGELOG.md has no dated section for 1.2.3',),
                id='brackets-required',
            ),
        ],
    )
    @pytest.mark.parametrize('release', ['1.2.3', 'v1.2.3'])
    def test_dated_release(
        self,
        write_file: FileWriter,
        content: str,
        expected: tuple[str, ...],
        release: str,
    ) -> None:
        """
        Verify release headings, dates, and optional version prefixes.

        Parameters
        ----------
        write_file : FileWriter
            UTF-8 writer creating parent directories in ``tmp_path``.
        content : str
            File contents selected for the parameterized success or failure
            scenario.
        expected : tuple[str, ...]
            Immutable expected diagnostics; an empty tuple means success.
        release : str
            Release-version string supplied to changelog validation.
        """
        path = write_file('CHANGELOG.md', content)
        before = path.read_bytes()
        assert validate(path, release) == list(expected)
        assert path.read_bytes() == before

    @pytest.mark.parametrize(
        'release',
        ['latest', 'v1.2', '1.2.3rc1', '01.2.3', '1١.2.3', 'v1.2.3１'],
    )
    def test_invalid_release(
        self,
        tmp_path: Path,
        release: str,
    ) -> None:
        """
        Verify invalid release syntax produces one version-format diagnostic.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        release : str
            Release-version string supplied to changelog validation.
        """
        with (
            patch.object(Path, 'is_file', autospec=True) as is_file,
            patch.object(Path, 'read_text', autospec=True) as read,
        ):
            assert validate(tmp_path / 'CHANGELOG.md', release) == [
                'release version must use vMAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH: '
                f'{release!r}',
            ]
        is_file.assert_not_called()
        read.assert_not_called()

    def test_missing_file(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify a missing changelog produces the expected file diagnostic.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory for isolated test inputs.
        """
        path = tmp_path / 'CHANGELOG.md'
        assert validate(path, '1.2.3') == [f'changelog does not exist: {path}']


# !SECTION
