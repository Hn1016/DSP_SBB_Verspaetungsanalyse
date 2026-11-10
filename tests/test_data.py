"""Tests on the real derived data. Skipped when the data has not been built yet
(run `uv run build` first)."""

import functools

import duckdb
import pytest

from sbb_delays import build, quality
from sbb_delays.download import service_points_snapshot
from sbb_delays.paths import ISTDATEN_RAIL
from sbb_delays.period import END, START
from sbb_delays.sections import period_days

# Months that fail the ZEILE order test: a known finding, not a looser rule (log 2026-11-08,
# «Befund: Zwölf Monate», and 2026-11-10, review PR #31). strict: the test turns red when such a
# month passes again; any other month over the limit fails as usual.
KNOWN_BACK_IN_TIME = {(2026, 5), (2026, 6)}

pytestmark = pytest.mark.skipif(
    not any(ISTDATEN_RAIL.glob("*.parquet")) or not service_points_snapshot().exists(),
    reason="derived data not built",
)


@pytest.fixture(scope="module")
def con():
    return quality.connect()


def scalar(con, sql):
    return con.sql(sql).fetchone()[0]


def test_one_file_per_operating_day_without_gaps(con):
    # every day of the period from period.py, from its first to its last day (issue #33)
    first, last = period_days(START, END)
    days, data_first, data_last = con.sql(
        f"""
        select count(distinct BETRIEBSTAG), min(BETRIEBSTAG), max(BETRIEBSTAG) from rail
        where BETRIEBSTAG between date '{first}' and date '{last}'
        """
    ).fetchone()
    assert (data_first, data_last) == (first, last)
    assert days == (data_last - data_first).days + 1
    files = [p for p in ISTDATEN_RAIL.glob("*.parquet") if str(first) <= p.stem <= str(last)]
    assert days == len(files)


def test_file_name_matches_operating_day(con):
    mismatches = scalar(
        con,
        f"""
        select count(*) from read_parquet('{ISTDATEN_RAIL}/*.parquet', filename = true)
        where strftime(BETRIEBSTAG, '%Y-%m-%d') <> parse_filename(filename, true)
        """,
    )
    assert mismatches == 0


def test_row_key_is_unique(con):
    assert scalar(con, "select count(*) - count(distinct (BETRIEBSTAG, ZEILE)) from rail") == 0


def test_only_trains(con):
    assert scalar(con, "select count(*) from rail where PRODUKT_ID <> 'Zug'") == 0


@functools.cache
def month_structure(year: int, month: int) -> dict:
    # one month at a time: over the whole period the query needs more than 10 GB of disk
    con = duckdb.connect()
    con.execute(
        f"""
        create view rail as select *, {quality.IN_CH} as IN_CH
        from read_parquet('{ISTDATEN_RAIL}/{year}-{month:02d}-*.parquet')
        """
    )
    relation = quality.trip_structure(con)
    return dict(zip(relation.columns, relation.fetchone(), strict=True))


@pytest.mark.parametrize("year, month", build.period_months())
def test_trip_id_has_one_operator_and_line(year, month):
    assert month_structure(year, month)["trips_mixed"] == 0


@pytest.mark.parametrize(
    "year, month",
    [
        pytest.param(
            *month,
            marks=pytest.mark.xfail(
                reason="reroutings: cancelled stops after the added stop (log 2026-11-10)",
                strict=True,
            ),
        )
        if month in KNOWN_BACK_IN_TIME
        else month
        for month in build.period_months()
    ],
)
def test_zeile_orders_the_stops(year, month):
    # at most 1 in 10'000 Swiss sections may run back in time, the same limit for every month
    structure = month_structure(year, month)
    assert structure["back_in_time_in_ch"] / structure["sections"] < 1e-4


def test_cancelled_rows_have_no_measured_times(con):
    assert (
        scalar(
            con,
            """
            select count(*) from rail
            where FAELLT_AUS_TF and (AN_PROGNOSE_STATUS = 'REAL' or AB_PROGNOSE_STATUS = 'REAL')
            """,
        )
        == 0
    )


def test_swiss_stops_are_mostly_measured_and_have_coordinates(con):
    coverage = {row[0]: row[2] for row in quality.status_coverage(con).fetchall()}
    assert coverage[True] > 90  # pct_real at Swiss stops
    in_ch, stops, with_coordinates, _ = quality.stop_match(con).fetchall()[0]
    assert in_ch and stops == with_coordinates
