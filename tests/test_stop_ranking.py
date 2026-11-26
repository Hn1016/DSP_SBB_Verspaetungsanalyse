"""Ranking of the Zurich stops per time window on hand-written cases (issue #61).

Fälle und Erwartungswerte von Claude Code für hasan8953 von Hand gerechnet (Issue #61).

The fixture tests/fixtures/stop_ranking_cases.csv holds stop events as quality.delays() returns
them, one stop per case; its header lists the cases and the calculations. Rules 1 to 7 of issue
#46 and the decisions of 2026-11-26 in the log (time of day by the scheduled departure at the
stop; thresholds and windows from ranking.py). Interval bounds are compared on 3 decimals.
"""

from datetime import date
from pathlib import Path

import duckdb
import polars as pl
import pytest

from sbb_delays import ranking, stop_ranking

FIXTURE = Path(__file__).parent / "fixtures" / "stop_ranking_cases.csv"

TYPES = {
    "BETRIEBSTAG": "DATE",
    "BPUIC": "INTEGER",
    "ANKUNFTSZEIT": "TIMESTAMP",
    "ABFAHRTSZEIT": "TIMESTAMP",
    "DURCHFAHRT_TF": "BOOLEAN",
    "an_delay": "DOUBLE",
    "ab_delay": "DOUBLE",
}

FIRST, LAST = date(2025, 8, 1), date(2026, 7, 31)
THRESHOLDS = {"min_trips": 4, "min_days": 3, "min_days_window": 3, "min_effect": 0.25}
MEANS = {"0": 0.0, "1": 0.0, "2": 0.5, "3+": 0.25}  # given class means, not those of the fixture

# All fixture stops are in Zurich except 8500010.
STOPS = [*range(8500001, 8500010), *range(8500011, 8500015)]

BASE_WINDOWS = ["ganzer Zeitraum", "Morgenspitze", "Mo–Fr", "Frühling", "Fahrplan 2026"]
ALL_WINDOWS = [name for _, name in ranking.WINDOWS]
VALUE_COLUMNS = ["mittel_roh", "mittel_referenz", "tagesmittel", "ki_unten", "ki_oben", "klasse"]


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


@pytest.fixture(scope="module")
def service_points(tmp_path_factory) -> Path:
    """A stop list as the snapshot has it: the fixture stops in Zurich, 8500010 in Bern."""
    path = tmp_path_factory.mktemp("stops") / "service_points.csv"
    lines = ["number;designationOfficial;cantonAbbreviation"]
    lines += [f"{nr};Halt {nr};ZH" for nr in STOPS] + ["8500010;Halt 8500010;BE"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def events(con, service_points) -> duckdb.DuckDBPyRelation:
    cleaned = con.sql(
        f"select * from read_csv('{FIXTURE}', header=true, comment='#', types={TYPES})"
    )
    return stop_ranking.stop_events(cleaned, FIRST, LAST, service_points)


@pytest.fixture(scope="module")
def result(events) -> pl.DataFrame:
    return stop_ranking.stop_ranking(events, MEANS, **THRESHOLDS)


def rows(result: pl.DataFrame, stop: int, windows: list[str]) -> list[dict]:
    """The rows of the stop in the given windows, in the order of ranking.WINDOWS."""
    found = result.filter((pl.col("BPUIC") == stop) & pl.col("fenster").is_in(windows))
    assert found.height == len(windows)
    return found.to_dicts()


def halts(events: duckdb.DuckDBPyRelation, stop: int) -> list[tuple[str, float]]:
    """(class of the scheduled dwell, halt) of the events of the stop, sorted."""
    return sorted(
        events.filter(f"BPUIC = {stop}").select("halt_klasse, halt").fetchall(),
        key=lambda r: (r[0], r[1]),
    )


# Rules 1 to 4 of issue #46 on the single stop events
def test_early_arrival_is_capped_late_arrival_is_not(events):
    assert halts(events, 8500005) == [("0", 0.5)] * 4  # uncapped 2.5
    assert halts(events, 8500002) == [("1", -1.0)] * 4


def test_pass_through_dropped_dwell_0_kept_as_class_0(events):
    assert halts(events, 8500008) == [("0", 0.0)] * 4


def test_not_real_negative_dwell_and_outside_the_period_dropped(events):
    assert halts(events, 8500009) == [("0", 1.0)] * 4


def test_stop_outside_zurich_dropped(events):
    assert halts(events, 8500010) == []


def test_classes_of_the_scheduled_dwell(events):
    assert halts(events, 8500001) == [("0", 1.0)] * 4
    assert halts(events, 8500006) == [("2", 1.0)] * 4
    assert halts(events, 8500007) == [("3+", 1.0)] * 4  # 4 and 5 minutes


def test_class_means_over_all_events(events):
    assert stop_ranking.class_means(events) == pytest.approx(
        {"0": 0.65, "1": -0.5, "2": 1.0, "3+": 1.0}
    )


# (stop, trips, days, raw mean, trip mean after reference, day mean after reference,
#  lower bound, upper bound, class, Zuwachs)
VALUE_CASES = {
    "amplifier": (8500001, 4, 4, 1.0, 1.0, 1.0, 1.0, 1.0, "Verstärker", 4.0),
    "absorber": (8500002, 4, 4, -1.0, -1.0, -1.0, -1.0, -1.0, "Absorber", -4.0),
    "neutral_below_min_effect": (8500003, 4, 4, 0.1, 0.1, 0.1, 0.1, 0.1, "neutral", 0.4),
    "neutral_interval": (8500004, 4, 4, 0.5, 0.5, 0.5, -2.256, 3.256, "neutral", 2.0),
    "early_arrival_capped": (8500005, 4, 4, 0.5, 0.5, 0.5, 0.5, 0.5, "Verstärker", 2.0),
    "reference_subtracted": (8500006, 4, 4, 1.0, 0.5, 0.5, 0.5, 0.5, "Verstärker", 2.0),
    "class_3_plus": (8500007, 4, 4, 1.0, 0.75, 0.75, 0.75, 0.75, "Verstärker", 3.0),
    "pass_through_dropped": (8500008, 4, 4, 0.0, 0.0, 0.0, 0.0, 0.0, "neutral", 0.0),
    "rows_dropped": (8500009, 4, 4, 1.0, 1.0, 1.0, 1.0, 1.0, "Verstärker", 4.0),
}


@pytest.mark.parametrize("case", VALUE_CASES)
def test_base_case_with_value(result, case):
    stop, trips, days, raw, per_trip, per_day, low, high, klasse, zuwachs = VALUE_CASES[case]

    for row in rows(result, stop, BASE_WINDOWS):
        assert row["grund"] is None
        assert (row["fahrten"], row["tage"]) == (trips, days)
        assert row["mittel_roh"] == pytest.approx(raw)
        assert row["mittel_referenz"] == pytest.approx(per_trip)
        assert row["tagesmittel"] == pytest.approx(per_day)
        assert (round(row["ki_unten"], 3), round(row["ki_oben"], 3)) == (low, high)
        assert row["klasse"] == klasse
        assert row["zuwachs"] == pytest.approx(zuwachs)


@pytest.mark.parametrize("stop", [VALUE_CASES[case][0] for case in VALUE_CASES])
def test_base_case_with_value_has_no_trip_in_the_other_8_windows(result, stop):
    others = rows(result, stop, [w for w in ALL_WINDOWS if w not in BASE_WINDOWS])

    assert len(others) == 8
    for row in others:
        assert row["grund"] == "keine Fahrt im Fenster"
        assert (row["fahrten"], row["tage"]) == (0, 0)


@pytest.mark.parametrize(
    ("stop", "trips", "days", "reason"),
    [
        (8500011, 3, 3, "zu wenige Fahrten"),
        (8500012, 4, 2, "zu wenige Betriebstage"),
    ],
)
def test_reason_of_the_whole_period_in_all_13_windows(result, stop, trips, days, reason):
    for row in rows(result, stop, ALL_WINDOWS):
        in_base = row["fenster"] in BASE_WINDOWS
        assert row["grund"] == reason
        assert (row["fahrten"], row["tage"]) == ((trips, days) if in_base else (0, 0))
        assert [row[c] for c in [*VALUE_COLUMNS, "zuwachs", "rang"]] == [None] * 8


def test_too_few_days_in_the_window(result):
    whole, weekdays, weekend = rows(result, 8500013, ["ganzer Zeitraum", "Mo–Fr", "Sa/So"])

    assert (whole["fahrten"], whole["tage"], whole["grund"]) == (4, 4, None)
    assert (whole["klasse"], whole["zuwachs"]) == ("Verstärker", pytest.approx(4.0))
    assert (weekdays["fahrten"], weekdays["tage"], weekdays["grund"]) == (3, 3, None)
    assert weekdays["zuwachs"] == pytest.approx(3.0)
    assert (weekend["fahrten"], weekend["tage"]) == (1, 1)
    assert weekend["grund"] == "zu wenige Betriebstage"
    assert [weekend[c] for c in [*VALUE_COLUMNS, "zuwachs", "rang"]] == [None] * 8


def test_window_borders_by_scheduled_departure_at_the_stop(result):
    found = rows(result, 8500014, ALL_WINDOWS)
    trips = {row["fenster"]: row["fahrten"] for row in found}
    reasons = {row["fenster"]: row["grund"] for row in found}

    assert trips == {
        "ganzer Zeitraum": 5,
        "Morgenspitze": 1,
        "Tag": 1,
        "Abendspitze": 1,
        "Abend/Nacht": 2,
        "Mo–Fr": 2,
        "Sa/So": 3,
        "Winter": 3,
        "Frühling": 2,
        "Sommer": 0,
        "Herbst": 0,
        "Fahrplan 2025": 1,
        "Fahrplan 2026": 4,
    }
    assert reasons["Sommer"] == reasons["Herbst"] == "keine Fahrt im Fenster"
    assert reasons["Tag"] == "zu wenige Betriebstage"
    assert reasons["ganzer Zeitraum"] is reasons["Sa/So"] is reasons["Winter"] is None


def test_rank_by_zuwachs_within_a_window(result):
    def ranks(window: str) -> dict[int, int]:
        found = result.filter((pl.col("fenster") == window) & pl.col("grund").is_null())
        return dict(found.select("BPUIC", "rang").iter_rows())

    assert ranks("ganzer Zeitraum") == {
        8500001: 1,
        8500009: 1,
        8500013: 1,
        8500007: 4,
        8500004: 5,
        8500005: 5,
        8500006: 5,
        8500003: 8,
        8500008: 9,
        8500014: 9,
        8500002: 11,
    }
    assert ranks("Morgenspitze") == {
        8500001: 1,
        8500009: 1,
        8500013: 1,
        8500007: 4,
        8500004: 5,
        8500005: 5,
        8500006: 5,
        8500003: 8,
        8500008: 9,
        8500002: 10,
    }
    assert ranks("Sa/So") == {8500014: 1}


def test_every_stop_has_one_row_per_window(result):
    per_stop = result.group_by("BPUIC").agg(pl.col("fenster").sort())
    assert sorted(per_stop["BPUIC"].to_list()) == STOPS
    assert all(w == sorted(ALL_WINDOWS) for w in per_stop["fenster"].to_list())

    # a value or a reason, never both
    with_value = result.filter(pl.col("grund").is_null())
    assert with_value.null_count().sum_horizontal().item() == with_value.height  # only `grund`


def test_thresholds_and_windows_come_from_ranking():
    assert stop_ranking.WINDOWS is ranking.WINDOWS
    for name in ["MIN_TRIPS", "MIN_DAYS", "MIN_DAYS_WINDOW", "MIN_EFFECT", "CONFIDENCE"]:
        assert getattr(stop_ranking, name) == getattr(ranking, name)


def test_missing_class_mean_raises(events):
    with pytest.raises(ValueError, match="Klassenmittel"):
        stop_ranking.stop_ranking(events, {"0": 0.0, "1": 0.0, "2": 0.5}, **THRESHOLDS)
