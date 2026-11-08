"""Section building on hand-written cases (issue #24).

The fixture tests/fixtures/sections_cases.csv holds six trips on 2026-09-07, one per case; its
header states the rule for pass-throughs. The expected rows were computed by hand (schwagia).
"""

from pathlib import Path

import duckdb

from sbb_delays import quality, sections

FIXTURE = Path(__file__).parent / "fixtures" / "sections_cases.csv"

# Types as written by load.SELECT_TYPED; the other columns are varchar.
TYPES = {
    "ZEILE": "BIGINT",
    "BETRIEBSTAG": "DATE",
    "ZUSATZFAHRT_TF": "BOOLEAN",
    "FAELLT_AUS_TF": "BOOLEAN",
    "BPUIC": "INTEGER",
    "ANKUNFTSZEIT": "TIMESTAMP",
    "AN_PROGNOSE": "TIMESTAMP",
    "ABFAHRTSZEIT": "TIMESTAMP",
    "AB_PROGNOSE": "TIMESTAMP",
    "DURCHFAHRT_TF": "BOOLEAN",
}

# (stop A, stop B, section delay in min, scheduled running time in min); cases 2 to 5 give none.
EXPECTED = [
    (8500010, 8500020, 1.5, 5),
    (8500120, 8500130, -0.5, 3),
    (8500130, 8500140, 1.0, 4),
]

SEPTEMBER = {"start": (2026, 9), "end": (2026, 9)}


def connect_fixture(tmp_path: Path, shift: str = "0 days") -> duckdb.DuckDBPyConnection:
    """Write the fixture as one daily rail Parquet, all dates moved by `shift`, and connect."""
    rail_dir = tmp_path / "rail"
    rail_dir.mkdir()
    duckdb.sql(
        f"""
        copy (
            select * replace (
                (BETRIEBSTAG + interval '{shift}')::date as BETRIEBSTAG,
                ANKUNFTSZEIT + interval '{shift}' as ANKUNFTSZEIT,
                AN_PROGNOSE + interval '{shift}' as AN_PROGNOSE,
                ABFAHRTSZEIT + interval '{shift}' as ABFAHRTSZEIT,
                AB_PROGNOSE + interval '{shift}' as AB_PROGNOSE
            )
            from read_csv('{FIXTURE}', header=true, comment='#', all_varchar=false,
                          types={TYPES})
        ) to '{rail_dir}/day.parquet' (format parquet)
        """
    )
    return quality.connect(rail_dir, service_points=tmp_path / "no_service_points.csv")


def section_rows(con, **period) -> list[tuple]:
    rel = sections.sections(con, **period)
    return rel.order("zeile_a").select("a_id, b_id, section_delay, scheduled_min").fetchall()


def test_fixture_gives_the_expected_sections(tmp_path):
    assert section_rows(connect_fixture(tmp_path), **SEPTEMBER) == EXPECTED


def test_day_outside_the_period_gives_no_sections(tmp_path):
    con = connect_fixture(tmp_path, shift="1 month")  # all cases on 2026-10-07

    assert section_rows(con, **SEPTEMBER) == []
    # the same rows do form sections when the period includes their day
    assert section_rows(con, start=(2026, 10), end=(2026, 10)) == EXPECTED
