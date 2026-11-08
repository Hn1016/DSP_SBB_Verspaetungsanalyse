"""Build all derived data from the raw files with one command.

Runs the existing steps in order: download (monthly archives and stops into data/raw), then
load (rail Parquet per operating day into data/processed), then sections (section passages of
the period, one Parquet file named after the period, issue #24). Before each step the target files
of the period are checked: if all exist, the step is skipped. Otherwise the step runs, and the
existing functions skip single files that already exist, so an interrupted build continues.
The targets of load are the daily files in the archives; calendar days of the period that an
archive lacks are reported as a warning. sections is also rebuilt when load built something,
and when its rules change: a short checksum of sections.py and quality.py is in the file name.

Each step prints one line on stdout; progress bars and warnings go to stderr.

Usage:
    uv run build            # build what is missing
    uv run build --force    # rebuild data/processed for the period; data/raw stays untouched
"""

import argparse
import hashlib
import sys
import zipfile
from calendar import monthrange
from datetime import date
from pathlib import Path

from sbb_delays import download, load, quality, sections
from sbb_delays.paths import ISTDATEN_RAIL, ISTDATEN_RAW, PROCESSED, SERVICE_POINTS_RAW
from sbb_delays.period import END, START


def period_months() -> list[tuple[int, int]]:
    return download.months_between(START, END)


def istdaten_zip(year: int, month: int) -> Path:
    """The archive that download.fetch_istdaten writes for this month."""
    name = download.ISTDATEN_URL.format(year=year, month=month).rsplit("/", 1)[1]
    return ISTDATEN_RAW / name


def archive_days(zip_path: Path) -> list[str]:
    """Operating days (YYYY-MM-DD) of the daily CSVs in an archive, read as load reads them."""
    with zipfile.ZipFile(zip_path) as archive:
        members = [m for m in archive.namelist() if m.lower().endswith(".csv")]
    return sorted(Path(m).name[:10] for m in members)


def rail_parquets() -> list[Path]:
    """One file per daily CSV in the period's archives, named as load.zip_to_rail_parquet does."""
    return [
        ISTDATEN_RAIL / f"{day}.parquet"
        for year, month in period_months()
        for day in archive_days(istdaten_zip(year, month))
    ]


def missing_days(parquets: list[Path]) -> list[str]:
    """Calendar days of the period without a daily file in the archives."""
    present = {path.stem for path in parquets}
    calendar = [
        f"{date(year, month, day):%Y-%m-%d}"
        for year, month in period_months()
        for day in range(1, monthrange(year, month)[1] + 1)
    ]
    return [day for day in calendar if day not in present]


def build_download() -> str:
    zips = [istdaten_zip(year, month) for year, month in period_months()]
    if download.service_points_ok(SERVICE_POINTS_RAW) and all(z.exists() for z in zips):
        return "übersprungen"
    download.fetch_service_points(SERVICE_POINTS_RAW)
    for year, month in period_months():
        download.fetch_istdaten(year, month)
    return "gebaut"


def build_load(force: bool = False) -> str:
    parquets = rail_parquets()
    if missing := missing_days(parquets):
        print(
            f"Warnung: im Archiv fehlen Tage des Zeitraums: {', '.join(missing)}", file=sys.stderr
        )
    if force:
        for path in parquets:
            path.unlink(missing_ok=True)
    if all(path.exists() for path in parquets):
        return "übersprungen"
    for year, month in period_months():
        load.zip_to_rail_parquet(istdaten_zip(year, month), ISTDATEN_RAIL)
    return "gebaut"


# The files that hold the section rules; a change in either builds sections anew.
RULE_FILES = [Path(sections.__file__), Path(quality.__file__)]


def rules_hash() -> str:
    """First 8 hex characters of SHA-256 over the contents of RULE_FILES, in order."""
    digest = hashlib.sha256()
    for path in RULE_FILES:
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


def sections_prefix() -> str:
    (y1, m1), (y2, m2) = START, END
    return f"sections_{y1}-{m1:02d}_{y2}-{m2:02d}"


def sections_parquet() -> Path:
    """Target of sections; period and rules are in the name, so a change of either builds anew."""
    return PROCESSED / f"{sections_prefix()}_{rules_hash()}.parquet"


def build_sections(force: bool = False) -> str:
    target = sections_parquet()
    if target.exists() and not force:
        return "übersprungen"
    con = quality.connect(ISTDATEN_RAIL)
    tmp = target.with_suffix(".parquet.part")
    sections.sections(con, START, END).write_parquet(str(tmp), compression="zstd")
    tmp.rename(target)
    # older files of the same period (other rules, or from before the checksum was in the name)
    for old in PROCESSED.glob(f"{sections_prefix()}*.parquet"):
        if old != target:
            old.unlink()
    return "gebaut"


def build(force: bool = False) -> None:
    print(f"download: {build_download()}", flush=True)
    loaded = build_load(force)
    print(f"load: {loaded}", flush=True)
    print(f"sections: {build_sections(force or loaded == 'gebaut')}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build all derived data from the raw files.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild data/processed for the period; data/raw stays untouched",
    )
    try:
        build(parser.parse_args().force)
    except download.SnapshotUnavailable as e:
        sys.exit(f"Abbruch: {e}")


if __name__ == "__main__":
    main()
