import zipfile
from datetime import date, datetime

import duckdb

from sbb_delays.load import zip_to_rail_parquet

HEADER = (
    "BETRIEBSTAG;FAHRT_BEZEICHNER;BETREIBER_ID;BETREIBER_ABK;BETREIBER_NAME;PRODUKT_ID;"
    "LINIEN_ID;LINIEN_TEXT;UMLAUF_ID;VERKEHRSMITTEL_TEXT;ZUSATZFAHRT_TF;FAELLT_AUS_TF;BPUIC;"
    "HALTESTELLEN_NAME;ANKUNFTSZEIT;AN_PROGNOSE;AN_PROGNOSE_STATUS;ABFAHRTSZEIT;AB_PROGNOSE;"
    "AB_PROGNOSE_STATUS;DURCHFAHRT_TF;SLOID"
)
TRAIN = (
    "01.09.2026;ch:1:sjyid:100001:10-001;85:11;SBB;Schweizerische Bundesbahnen SBB;Zug;10;IC1;;"
    "IC;false;false;8507000;Bern;01.09.2026 08:02;01.09.2026 08:03:10;REAL;01.09.2026 08:05;"
    "01.09.2026 08:08:31;REAL;false;ch:1:sloid:7000"
)
TRAIN_ORIGIN = (
    "01.09.2026;ch:1:sjyid:100001:10-001;85:11;SBB;Schweizerische Bundesbahnen SBB;Zug;10;IC1;;"
    "IC;false;false;8503000;Zürich HB;;;;01.09.2026 07:02;01.09.2026 07:02:40;REAL;false;"
    "ch:1:sloid:3000"
)
BUS = (
    "01.09.2026;85:801:1-1;85:801;PAG;PostAuto AG;Bus;1;1;;B;false;false;8500001;Dorf;"
    "01.09.2026 08:02;01.09.2026 08:03:10;REAL;01.09.2026 08:02;01.09.2026 08:03:20;REAL;false;"
)


def make_archive(tmp_path):
    zip_path = tmp_path / "ist-daten-v2-2026-09.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("2026-09-01_IstDaten.csv", "\n".join([HEADER, TRAIN_ORIGIN, TRAIN, BUS]))
    return zip_path


def test_zip_to_rail_parquet_keeps_only_trains_and_types_columns(tmp_path):
    out_dir = tmp_path / "rail"
    written = zip_to_rail_parquet(make_archive(tmp_path), out_dir)

    assert [p.name for p in written] == ["2026-09-01.parquet"]
    rows = duckdb.sql(
        f"""
        select PRODUKT_ID, BETRIEBSTAG, ANKUNFTSZEIT, AB_PROGNOSE, FAELLT_AUS_TF, BPUIC
        from '{written[0]}' order by ABFAHRTSZEIT
        """
    ).fetchall()
    assert [r[0] for r in rows] == ["Zug", "Zug"]
    assert rows[0][2] is None  # first stop of a trip has no arrival
    assert rows[1] == (
        "Zug",
        date(2026, 9, 1),
        datetime(2026, 9, 1, 8, 2),
        datetime(2026, 9, 1, 8, 8, 31),
        False,
        8507000,
    )
    assert list(out_dir.iterdir()) == written  # no temporary files left behind


def test_zip_to_rail_parquet_skips_existing_days(tmp_path):
    zip_path = make_archive(tmp_path)
    out_dir = tmp_path / "rail"
    zip_to_rail_parquet(zip_path, out_dir)
    assert zip_to_rail_parquet(zip_path, out_dir) == []
