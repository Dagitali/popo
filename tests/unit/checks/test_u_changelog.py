"""
:mod:`tests.unit.checks.test_u_changelog` module.

Test release headings, calendar dates, and missing changelog errors.
"""

from pathlib import Path

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
            ('## [1.2.3] - 2026-09-20\n', []),
            ('# Changelog\n', ['CHANGELOG.md has no dated section for 1.2.3']),
            (
                '## [1.2.3] - 2026-02-30\n',
                ['CHANGELOG.md has an invalid date for 1.2.3: 2026-02-30'],
            ),
        ],
        ids=['dated-release', 'missing-section', 'impossible-date'],
    )
    @pytest.mark.parametrize('release', ['1.2.3', 'v1.2.3'])
    def test_dated_release(
        self,
        write_file: FileWriter,
        content: str,
        expected: list[str],
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
        expected : list[str]
            Exact expected validator result or command text for the scenario.
        release : str
            Release-version string supplied to changelog validation.
        """
        assert validate(write_file('CHANGELOG.md', content), release) == expected

    @pytest.mark.parametrize('release', ['latest', 'v1.2', '1.2.3rc1', '01.2.3'])
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
        failures = validate(tmp_path / 'CHANGELOG.md', release)
        assert len(failures) == 1
        assert 'release version must use' in failures[0]

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
