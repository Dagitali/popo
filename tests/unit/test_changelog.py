"""
:mod:`tests.unit.test_changelog` module.

Test release headings, calendar dates, and missing changelog errors.
"""

from pathlib import Path

import pytest

from popo.checks.changelog import validate
from tests.support.files import FileWriter

# SECTION: TESTS


class TestChangelog:
    """Validate dated semantic releases with precise failure diagnostics."""

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
        assert validate(write_file('CHANGELOG.md', content), release) == expected

    @pytest.mark.parametrize('release', ['latest', 'v1.2', '1.2.3rc1', '01.2.3'])
    def test_invalid_release(self, tmp_path: Path, release: str) -> None:
        failures = validate(tmp_path / 'CHANGELOG.md', release)
        assert len(failures) == 1
        assert 'release version must use' in failures[0]

    def test_missing_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'CHANGELOG.md'
        assert validate(path, '1.2.3') == [f'changelog does not exist: {path}']


# !SECTION
