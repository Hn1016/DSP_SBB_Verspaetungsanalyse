"""Ranking of sections per time window on hand-written cases (issue #38).

The fixture tests/fixtures/ranking_cases.csv holds section passages, one section per case; its
header lists the cases. The expected values were set and computed by hand (schwagia); interval
bounds are compared on 3 decimals. test_every_section_has_one_row_per_window holds no numbers
of its own: it checks the form of the output as decided in the log (2026-11-12, «Details der
Rangliste», points 4 and 5).
"""

from pathlib import Path

import duckdb
import polars as pl
import pytest

from sbb_delays import ranking

FIXTURE = Path(__file__).parent / "fixtures" / "ranking_cases.csv"

TYPES = {
    "BETRIEBSTAG": "DATE",
    "a_id": "INTEGER",
    "b_id": "INTEGER",
    "abfahrt_a": "TIMESTAMP",
    "section_delay": "DOUBLE",
    "scheduled_min": "BIGINT",
}

THRESHOLDS = {"min_trips": 4, "min_days": 3, "min_days_window": 3, "min_effect": 0.25}
MEANS = {"3": 0.0, "2": 0.5}  # given class means, not those of the fixture

# The windows the base cases lie in; all 13 are in ranking.WINDOWS.
BASE_WINDOWS = ["ganzer Zeitraum", "Morgenspitze", "Mo–Fr", "Frühling", "Fahrplan 2026"]
ALL_WINDOWS = [
    "ganzer Zeitraum",
    "Morgenspitze",
    "Tag",
    "Abendspitze",
    "Abend/Nacht",
    "Mo–Fr",
    "Sa/So",
    "Winter",
    "Frühling",
    "Sommer",
    "Herbst",
    "Fahrplan 2025",
    "Fahrplan 2026",
]
VALUE_COLUMNS = ["mittel_roh", "mittel_referenz", "tagesmittel", "ki_unten", "ki_oben", "klasse"]


@pytest.fixture(scope="module")
def result() -> pl.DataFrame:
    con = duckdb.connect()
    rel = con.sql(f"select * from read_csv('{FIXTURE}', header=true, comment='#', types={TYPES})")
    return ranking.ranking(rel, MEANS, **THRESHOLDS)


def rows(result: pl.DataFrame, a_id: int, windows: list[str]) -> list[dict]:
    """The rows of the section starting at a_id in the given windows, one per window."""
    found = result.filter((pl.col("a_id") == a_id) & pl.col("fenster").is_in(windows))
    assert found["b_id"].to_list() == [a_id + 1] * len(windows)
    return found.to_dicts()


def other_windows(windows: list[str]) -> list[str]:
    return [w for w in ALL_WINDOWS if w not in windows]


# (stop A, trips, days, raw mean, trip mean after reference, day mean after reference,
#  lower bound, upper bound, class, Zuwachs)
VALUE_CASES = {
    "amplifier": (8500001, 4, 4, 1.0, 1.0, 1.0, 1.0, 1.0, "Verstärker", 4.0),
    "absorber": (8500003, 4, 4, -1.0, -1.0, -1.0, -1.0, -1.0, "Absorber", -4.0),
    "neutral_below_min_effect": (8500005, 4, 4, 0.1, 0.1, 0.1, 0.1, 0.1, "neutral", 0.4),
    "neutral_interval": (8500007, 4, 4, 0.5, 0.5, 0.5, -2.256, 3.256, "neutral", 2.0),
    "reference_subtracted": (8500013, 4, 4, 1.0, 0.5, 0.5, 0.5, 0.5, "Verstärker", 2.0),
    "two_means": (8500015, 6, 4, 0.5, 0.5, 0.25, -0.546, 1.046, "neutral", 3.0),
}


@pytest.mark.parametrize("case", VALUE_CASES)
def test_base_case_with_value(result, case):
    a_id, trips, days, raw, per_trip, per_day, low, high, klasse, zuwachs = VALUE_CASES[case]

    for row in rows(result, a_id, BASE_WINDOWS):
        assert row["grund"] is None
        assert (row["fahrten"], row["tage"]) == (trips, days)
        assert row["mittel_roh"] == pytest.approx(raw)
        assert row["mittel_referenz"] == pytest.approx(per_trip)
        assert row["tagesmittel"] == pytest.approx(per_day)
        assert (round(row["ki_unten"], 3), round(row["ki_oben"], 3)) == (low, high)
        assert row["klasse"] == klasse
        assert row["zuwachs"] == pytest.approx(zuwachs)


@pytest.mark.parametrize(
    ("a_id", "trips", "days", "reason"),
    [
        (8500009, 3, 3, "zu wenige Fahrten"),
        (8500011, 4, 2, "zu wenige Betriebstage"),
    ],
)
def test_base_case_with_reason(result, a_id, trips, days, reason):
    for row in rows(result, a_id, BASE_WINDOWS):
        assert row["grund"] == reason
        assert (row["fahrten"], row["tage"]) == (trips, days)
        assert [row[c] for c in [*VALUE_COLUMNS, "zuwachs", "rang"]] == [None] * 8


@pytest.mark.parametrize(
    "a_id", [8500001, 8500003, 8500005, 8500007, 8500009, 8500011, 8500013, 8500015]
)
def test_base_case_is_never_measured_in_the_other_8_windows(result, a_id):
    others = rows(result, a_id, other_windows(BASE_WINDOWS))

    assert len(others) == 8
    for row in others:
        assert row["grund"] == "nie gemessen"
        assert (row["fahrten"], row["tage"]) == (0, 0)


def test_window_borders(result):
    trips = {row["fenster"]: row["fahrten"] for row in rows(result, 8500017, ALL_WINDOWS)}
    reasons = {row["fenster"]: row["grund"] for row in rows(result, 8500017, ALL_WINDOWS)}

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
    assert reasons["Sommer"] == reasons["Herbst"] == "nie gemessen"


def test_every_section_has_one_row_per_window(result):
    assert [name for _, name in ranking.WINDOWS] == ALL_WINDOWS
    per_section = result.group_by("a_id", "b_id").agg(pl.col("fenster").sort())
    assert per_section.height == 9
    assert all(windows == sorted(ALL_WINDOWS) for windows in per_section["fenster"])

    # a value or a reason, never both; a rank only with a value
    with_value = result.filter(pl.col("grund").is_null())
    with_reason = result.filter(pl.col("grund").is_not_null())
    assert with_value.null_count().sum_horizontal().item() == with_value.height  # only `grund`
    assert with_reason.select(pl.all_horizontal(pl.col("zuwachs", "rang").is_null()).all()).item()

    # rank by Zuwachs within each window
    for window in ALL_WINDOWS:
        ranked = with_value.filter(pl.col("fenster") == window).sort("zuwachs", descending=True)
        assert ranked["rang"].to_list() == ranked["zuwachs"].rank("min", descending=True).to_list()


def test_class_means():
    con = duckdb.connect()
    rel = con.sql(
        """
        select * from (values (0, 2.0), (1, 0.4), (1, 0.2), (5, 1.0), (7, -3.0))
            as passages(scheduled_min, section_delay)
        """
    )

    assert ranking.class_means(rel) == pytest.approx({"0": 2.0, "1": 0.3, "5+": -1.0})


def test_missing_class_mean_raises():
    con = duckdb.connect()
    rel = con.sql(f"select * from read_csv('{FIXTURE}', header=true, comment='#', types={TYPES})")

    with pytest.raises(ValueError, match="Klassenmittel"):
        ranking.ranking(rel, {"3": 0.0}, **THRESHOLDS)  # class 2 is in the fixture
