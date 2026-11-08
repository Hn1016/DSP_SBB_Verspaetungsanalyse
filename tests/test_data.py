"""Tests on the real derived data. Skipped when the data has not been built yet
(run `uv run build` first)."""

import duckdb
import pytest

from sbb_delays import build, quality
from sbb_delays.download import service_points_snapshot
from sbb_delays.paths import ISTDATEN_RAIL
from sbb_delays.period import END, START
from sbb_delays.sections import period_days

# Months in which ZEILE runs back in time more often than the threshold: a known finding
# (log 2026-11-08, «Befund: Zwölf Monate», A4 «teilweise»), capped so they cannot get much worse.
KNOWN_BACK_IN_TIME = {(2026, 5): 2e-4, (2026, 6): 2e-4}

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
    # within the period from period.py; the archive of July 2025 starts on the 13th (log 2026-11-08)
    first, last = period_days(START, END)
    days, data_first, data_last = con.sql(
        f"""
        select count(distinct BETRIEBSTAG), min(BETRIEBSTAG), max(BETRIEBSTAG) from rail
        where BETRIEBSTAG between date '{first}' and date '{last}'
        """
    ).fetchone()
    assert data_last == last
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


@pytest.mark.parametrize("year, month", build.period_months())
def test_trip_id_has_one_operator_and_line(year, month):
    # one month at a time: over the whole period the query needs more than 10 GB of disk
    con = duckdb.connect()
    con.execute(
        f"""
        create view rail as select *, {quality.IN_CH} as IN_CH
        from read_parquet('{ISTDATEN_RAIL}/{year}-{month:02d}-*.parquet')
        """
    )
    relation = quality.trip_structure(con)
    structure = dict(zip(relation.columns, relation.fetchone(), strict=True))
    assert structure["trips_mixed"] == 0
    # ZEILE must order the stops: at most 1 in 10'000 Swiss sections may run back in time
    limit = KNOWN_BACK_IN_TIME.get((year, month), 1e-4)
    assert structure["back_in_time_in_ch"] / structure["sections"] < limit


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
