"""
:mod:`tests.unit.config.test_u_common` module.

Verify shared configuration parsing independently of domain-specific policy.
"""

from datetime import date

import pytest

from popo.config._common import parse_iso_date

# SECTION: TESTS


class TestCanonicalDates:
    """Keep shared date syntax strict without imposing expiry policy."""

    @pytest.mark.parametrize(
        'text,expected',
        (
            pytest.param('0001-01-01', date.min, id='minimum-date'),
            pytest.param('9999-12-31', date.max, id='maximum-date'),
            pytest.param('2024-02-29', date(2024, 2, 29), id='leap-day'),
            pytest.param('2000-02-29', date(2000, 2, 29), id='leap-century'),
            pytest.param('2026-10-28', date(2026, 10, 28), id='ordinary-date'),
        ),
    )
    def test_accepts_canonical_calendar_dates(
        self,
        text: str,
        expected: date,
    ) -> None:
        """
        Accept valid leap dates without imposing expiry or timezone policy.

        Parameters
        ----------
        text : str
            Canonical ISO date text supplied to the shared parser.
        expected : datetime.date
            Exact calendar date, including supported minimum/maximum bounds.
        """
        assert parse_iso_date(text) == expected

    @pytest.mark.parametrize(
        'text',
        (
            pytest.param('1900-02-29', id='non-leap-century'),
            pytest.param('2026-02-29', id='non-leap-year'),
            pytest.param('20240229', id='compact-date'),
            pytest.param('2024-W09-4', id='week-date'),
            pytest.param(' 2024-02-29', id='leading-space'),
            pytest.param('2024-02-29 ', id='trailing-space'),
            pytest.param('2024-02-29\n', id='trailing-newline'),
            pytest.param('2024-2-29', id='unpadded-month'),
            pytest.param('2024-02-29T00:00:00', id='datetime'),
            pytest.param('２０２４-０２-２９', id='fullwidth-digits'),
            pytest.param('٢٠٢٤-٠٢-٢٩', id='arabic-indic-digits'),
        ),
    )
    def test_rejects_alternate_or_impossible_dates(
        self,
        text: str,
    ) -> None:
        """
        Reject alternate ISO spellings and impossible calendar dates.

        Parameters
        ----------
        text : str
            Noncanonical or impossible date text supplied to the parser.
        """
        with pytest.raises(ValueError):
            parse_iso_date(text)


# !SECTION
