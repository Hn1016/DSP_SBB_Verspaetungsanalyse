"""Tests on the real derived data. Skipped when the data has not been built yet
(run `sbb_delays.download` and `sbb_delays.load` first)."""

import pytest

from sbb_delays import quality
from sbb_delays.download import latest_service_points
from sbb_delays.paths import ISTDATEN_RAIL

pytestmark = pytest.mark.skipif(
    not any(ISTDATEN_RAIL.glob("*.parquet")) or latest_service_points() is None,
    reason="derived data not built",
)


@pytest.fixture(scope="module")
def con():
    return quality.connect()


def scalar(con, sql):
    return con.sql(sql).fetchone()[0]


def test_one_file_per_operating_day_without_gaps(con):
    days, first, last = con.sql(
        "select count(distinct BETRIEBSTAG), min(BETRIEBSTAG), max(BETRIEBSTAG) from rail"
    ).fetchone()
    assert days == (last - first).days + 1
    assert days == len(list(ISTDATEN_RAIL.glob("*.parquet")))


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


def test_trip_id_has_one_operator_and_line(con):
    relation = quality.trip_structure(con)
    structure = dict(zip(relation.columns, relation.fetchone(), strict=True))
    assert structure["trips_mixed"] == 0
    # ZEILE must order the stops: at most 1 in 10'000 Swiss sections may run back in time
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
