"""Build all derived data from the raw files with one command.

Runs the existing steps in order: download (monthly archives and stops into data/raw), then
load (rail Parquet per operating day into data/processed). Before each step the target files
of the period are checked: if all exist, the step is skipped. Otherwise the step runs, and the
existing functions skip single files that already exist, so an interrupted build continues.
The targets of load are the daily files in the archives; calendar days of the period that an
archive lacks are reported as a warning.

Each step prints one line on stdout; progress bars and warnings go to stderr.

Usage:
    uv run build            # build what is missing
    uv run build --force    # rebuild data/processed for the period; data/raw stays untouched
"""

import argparse
import sys
import zipfile
from calendar import monthrange
from datetime import date
from pathlib import Path

from sbb_delays import download, load
from sbb_delays.paths import ISTDATEN_RAIL, ISTDATEN_RAW, SERVICE_POINTS_RAW
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
    if download.latest_service_points(SERVICE_POINTS_RAW) and all(z.exists() for z in zips):
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


def build(force: bool = False) -> None:
    print(f"download: {build_download()}", flush=True)
    print(f"load: {build_load(force)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build all derived data from the raw files.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild data/processed for the period; data/raw stays untouched",
    )
    build(parser.parse_args().force)


if __name__ == "__main__":
    main()
