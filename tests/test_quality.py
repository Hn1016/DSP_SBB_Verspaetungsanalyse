import duckdb
import pytest

from sbb_delays import quality

# Trip A: Zürich -> Olten -> Bern, all measured. Olten: scheduled dwell 0, actual dwell 60 s.
# Trip B: Bern -> Basel Bad (foreign stop, forecast only), second stop cancelled twice (duplicate).
ROWS = """
    (1, 'A', 8503000, NULL, NULL, NULL, '08:00', '08:01:00', 'REAL', false),
    (2, 'A', 8500218, '08:30', '08:31:00', 'REAL', '08:30', '08:32:00', 'REAL', false),
    (3, 'A', 8507000, '09:00', '09:00:30', 'REAL', NULL, NULL, NULL, false),
    (4, 'B', 8507000, NULL, NULL, NULL, '10:00', '10:00:00', 'REAL', false),
    (5, 'B', 8000026, '11:00', NULL, 'UNBEKANNT', NULL, NULL, NULL, true),
    (6, 'B', 8000026, '11:00', NULL, 'UNBEKANNT', NULL, NULL, NULL, true)
"""


@pytest.fixture
def con(tmp_path):
    rail_dir = tmp_path / "rail"
    rail_dir.mkdir()
    duckdb.sql(
        f"""
        copy (
            select zeile as ZEILE, date '2026-09-01' as BETRIEBSTAG, trip as FAHRT_BEZEICHNER,
                   '85:11' as BETREIBER_ID, 'SBB' as BETREIBER_ABK, '1' as LINIEN_ID,
                   cancelled as FAELLT_AUS_TF, false as DURCHFAHRT_TF, false as ZUSATZFAHRT_TF,
                   bpuic as BPUIC,
                   ('2026-09-01 ' || an)::timestamp as ANKUNFTSZEIT,
                   ('2026-09-01 ' || an_ist)::timestamp as AN_PROGNOSE,
                   an_status as AN_PROGNOSE_STATUS,
                   ('2026-09-01 ' || ab)::timestamp as ABFAHRTSZEIT,
                   ('2026-09-01 ' || ab_ist)::timestamp as AB_PROGNOSE,
                   ab_status as AB_PROGNOSE_STATUS
            from (values {ROWS})
                 t(zeile, trip, bpuic, an, an_ist, an_status, ab, ab_ist, ab_status, cancelled)
        ) to '{rail_dir}/2026-09-01.parquet' (format parquet)
        """
    )
    service_points = tmp_path / "service-points_2026-10-05.csv"
    service_points.write_text(
        "number;designationOfficial;hasGeolocation;wgs84East;wgs84North\n"
        "8503000;Zürich HB;true;8.54;47.38\n"
        "8500218;Olten;true;7.91;47.35\n"
        "8507000;Bern;true;7.44;46.95\n"
    )
    return quality.connect(rail_dir, service_points)


def as_dicts(relation):
    return [dict(zip(relation.columns, row, strict=True)) for row in relation.fetchall()]


def test_status_coverage_counts_scheduled_non_cancelled_events(con):
    rows = {r["IN_CH"]: r for r in as_dicts(quality.status_coverage(con))}
    # Swiss events: 3 departures + 2 arrivals, all REAL. The foreign rows are cancelled.
    assert rows[True]["events"] == 5
    assert rows[True]["pct_real"] == 100.0
    assert False not in rows


def test_trip_structure(con):
    (row,) = as_dicts(quality.trip_structure(con))
    assert row["trips"] == 2
    assert row["trips_mixed"] == 0
    assert row["trips_not_contiguous"] == 0
    assert row["trips_repeating_a_stop"] == 1
    assert row["duplicate_rows"] == 1
    assert row["sections"] == 4
    assert row["back_in_time"] == 0


def test_cancelled_trips(con):
    (row,) = as_dicts(quality.cancelled_trips(con))
    assert (row["fully_cancelled"], row["partly_cancelled"]) == (0, 1)


def test_stop_match_only_swiss_stops_have_coordinates(con):
    rows = {r["IN_CH"]: r for r in as_dicts(quality.stop_match(con))}
    assert rows[True]["stops"] == rows[True]["stops_with_coordinates"] == 3
    assert rows[False]["stops_with_coordinates"] == 0


def test_delay_summary_in_minutes(con):
    rows = {r["event"]: r for r in as_dicts(quality.delay_summary(con))}
    assert rows["Ankunft"]["n"] == 2  # Olten +1.0, Bern +0.5
    assert rows["Ankunft"]["mean"] == 0.75
    assert rows["Abfahrt"]["n"] == 3  # Zürich +1.0, Olten +2.0, Bern 0.0
    assert rows["Abfahrt"]["mean"] == 1.0


def test_dwell_bias_stop_delay_equals_actual_dwell_when_scheduled_dwell_is_zero(con):
    (row,) = as_dicts(quality.dwell_bias(con))
    assert row["scheduled_dwell_min"] == 0
    assert row["actual_dwell_mean"] == row["stop_delay_mean"] == 1.0


def test_delays_keep_forecast_apart_from_measurement(con):
    # Turn the Olten arrival (+1.0 min) into a forecast
    con.execute("create table rail_copy as select * from rail")
    con.execute(
        """
        create or replace view rail as
        select * replace (
            case when ZEILE = 2 then 'PROGNOSE' else AN_PROGNOSE_STATUS end as AN_PROGNOSE_STATUS
        ) from rail_copy
        """
    )
    rows = as_dicts(
        quality.delays(con)
        .filter("ANKUNFTSZEIT is not null")
        .order("ZEILE")
        .select("an_delay, an_delay_prognose")
    )
    assert rows == [
        {"an_delay": None, "an_delay_prognose": 1.0},  # Olten, forecast only
        {"an_delay": 0.5, "an_delay_prognose": None},  # Bern, measured
    ]
    by_status = {(r["event"], r["status"]): r["n"] for r in as_dicts(quality.delay_by_status(con))}
    assert by_status[("Ankunft", "PROGNOSE")] == 1
    assert by_status[("Ankunft", "REAL")] == 1


def test_stops_by_real_coverage_classifies_every_swiss_stop(con):
    rows = as_dicts(quality.stops_by_real_coverage(con))
    # Zürich: departure REAL; Olten: both REAL; Bern: arrival and departure REAL
    assert rows == [
        {
            "coverage": "d) immer REAL",
            "stops": 3,
            "events": 5,
            "events_not_real": 0,
            "pct_of_all_not_real": None,
        }
    ]


def test_real_share_by_previous_delay(con):
    rows = as_dicts(quality.real_share_by_previous_delay(con))
    # Olten (previous departure +1.0 min) and Bern (previous departure +2.0 min), both REAL
    assert rows == [{"previous_delay_min": "c) 1 bis 3", "arrivals": 2, "pct_real": 100.0}]


def test_delays_apply_the_cleaning_rules(con):
    # Add a duplicate of the Olten row and shift the Bern arrival by one day (date error)
    con.execute("create table rail_copy as select * from rail")
    con.execute(
        """
        create or replace view rail as
        select * replace (
            case when ZEILE = 3 then AN_PROGNOSE + interval 1 day else AN_PROGNOSE end
                as AN_PROGNOSE
        ) from rail_copy
        union all
        select * replace (7 as ZEILE) from rail_copy where ZEILE = 2
        """
    )
    rows = as_dicts(
        quality.delays(con).order("ZEILE").select("ZEILE, an_delay, an_date_error, ab_delay")
    )
    assert rows == [
        {"ZEILE": 1, "an_delay": None, "an_date_error": False, "ab_delay": 1.0},
        {"ZEILE": 2, "an_delay": 1.0, "an_date_error": False, "ab_delay": 2.0},  # once only
        {"ZEILE": 3, "an_delay": None, "an_date_error": True, "ab_delay": None},  # Bern
        {"ZEILE": 4, "an_delay": None, "an_date_error": False, "ab_delay": 0.0},
    ]
    summary = {r["event"]: r for r in as_dicts(quality.delay_summary(con))}
    assert summary["Ankunft"]["n"] == 1
    assert summary["Ankunft"]["n_date_errors"] == 1
