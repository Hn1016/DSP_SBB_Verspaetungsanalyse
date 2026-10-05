"""Convert raw IstDaten archives to typed Parquet, one file per operating day, rail only.

A month of IstDaten is ~19 GB as CSV, of which ~7 % are trains. Each daily CSV is extracted
to a temporary directory, filtered to PRODUKT_ID = 'Zug', typed and written as Parquet, so
the full month is never unpacked on disk.

Usage:
    uv run python -m sbb_delays.load
"""

import tempfile
import zipfile
from pathlib import Path

import duckdb
from tqdm import tqdm

from sbb_delays.paths import ISTDATEN_RAIL, ISTDATEN_RAW

RAIL_PRODUCT = "Zug"

# Column names stay as in the source so they match the official documentation.
SELECT_TYPED = """
    strptime(BETRIEBSTAG, '%d.%m.%Y')::date as BETRIEBSTAG,
    FAHRT_BEZEICHNER,
    BETREIBER_ID,
    BETREIBER_ABK,
    BETREIBER_NAME,
    PRODUKT_ID,
    LINIEN_ID,
    LINIEN_TEXT,
    UMLAUF_ID,
    VERKEHRSMITTEL_TEXT,
    ZUSATZFAHRT_TF::boolean as ZUSATZFAHRT_TF,
    FAELLT_AUS_TF::boolean as FAELLT_AUS_TF,
    BPUIC::integer as BPUIC,
    HALTESTELLEN_NAME,
    strptime(ANKUNFTSZEIT, '%d.%m.%Y %H:%M') as ANKUNFTSZEIT,
    strptime(AN_PROGNOSE, '%d.%m.%Y %H:%M:%S') as AN_PROGNOSE,
    AN_PROGNOSE_STATUS,
    strptime(ABFAHRTSZEIT, '%d.%m.%Y %H:%M') as ABFAHRTSZEIT,
    strptime(AB_PROGNOSE, '%d.%m.%Y %H:%M:%S') as AB_PROGNOSE,
    AB_PROGNOSE_STATUS,
    DURCHFAHRT_TF::boolean as DURCHFAHRT_TF,
    SLOID
"""


def csv_to_rail_parquet(csv_path: Path, parquet_path: Path) -> int:
    """Write the rail rows of one daily CSV as typed Parquet. Returns the row count."""
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = parquet_path.with_suffix(".parquet.part")
    con = duckdb.connect()
    source = "read_csv(?, delim=';', header=true, all_varchar=true)"
    expected = con.execute(
        f"select count(*) from {source} where PRODUKT_ID = ?", [str(csv_path), RAIL_PRODUCT]
    ).fetchone()[0]
    con.execute(
        f"""
        copy (
            select {SELECT_TYPED}
            from {source}
            where PRODUKT_ID = ?
        ) to '{tmp}' (format parquet, compression zstd)
        """,
        [str(csv_path), RAIL_PRODUCT],
    )
    written = con.execute("select count(*) from read_parquet(?)", [str(tmp)]).fetchone()[0]
    if written != expected:
        tmp.unlink()
        raise RuntimeError(f"{csv_path.name}: wrote {written} rows, expected {expected}")
    tmp.rename(parquet_path)
    return written


def zip_to_rail_parquet(zip_path: Path, out_dir: Path = ISTDATEN_RAIL) -> list[Path]:
    """Convert every daily CSV in a monthly archive. Days already converted are skipped."""
    written = []
    with zipfile.ZipFile(zip_path) as archive:
        members = sorted(m for m in archive.namelist() if m.lower().endswith(".csv"))
        for member in tqdm(members, desc=zip_path.name):
            day = Path(member).name[:10]  # file names start with YYYY-MM-DD
            target = out_dir / f"{day}.parquet"
            if target.exists():
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=out_dir) as tmp_dir:
                csv_path = Path(archive.extract(member, tmp_dir))
                csv_to_rail_parquet(csv_path, target)
            written.append(target)
    return written


def main() -> None:
    zips = sorted(ISTDATEN_RAW.glob("ist-daten-v2-*.zip"))
    if not zips:
        raise SystemExit(f"No archives in {ISTDATEN_RAW}. Run sbb_delays.download first.")
    for zip_path in zips:
        zip_to_rail_parquet(zip_path)


if __name__ == "__main__":
    main()
