"""Download raw files and record source, retrieval date and SHA-256 checksum.

Raw files are never modified after download. Every download appends one row to
data/raw/manifest.csv so the provenance of each file is traceable; a file whose name and
checksum are already in the manifest adds no second row.

The stop list is a fixed snapshot (date and checksum in sbb_delays.period). The provider only
serves the current list, so the snapshot is kept as an extract (Swiss stops, the columns the
code reads) in a release of this repository and checked against its checksum.

Usage:
    uv run python -m sbb_delays.download --from 2026-09 --to 2026-09
"""

import argparse
import csv
import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import requests
from tqdm import tqdm

from sbb_delays.paths import MANIFEST, RAW, SBB_DATA_RAW, SERVICE_POINTS_RAW
from sbb_delays.period import SERVICE_POINTS_DATE, SERVICE_POINTS_SHA256

# Monthly archive of IstDaten (v2 format, available from 2025-07). The daily files on
# data.opentransportdata.swiss have random resource ids and cannot be derived from a date.
ISTDATEN_URL = (
    "https://archive.opentransportdata.swiss/istdaten/{year}/ist-daten-v2-{year}-{month:02d}.zip"
)
# Source of the stop list. The permalink redirects to the current file, which the provider
# updates daily; older versions cannot be downloaded again.
SERVICE_POINTS_URL = "https://data.opentransportdata.swiss/dataset/service-point-v2/permalink"
# Release of this repository that holds the extract of the fixed snapshot.
SERVICE_POINTS_RELEASE_URL = (
    "https://github.com/Hn1016/DSP_SBB_Verspaetungsanalyse/releases/download/"
    "service-points-{date}/service-points-ch_{date}.csv"
)
# Columns of the extract: the ones the code reads, with the provider's names.
SERVICE_POINTS_COLUMNS = [
    "number",
    "designationOfficial",
    "cantonAbbreviation",
    "hasGeolocation",
    "wgs84East",
    "wgs84North",
    "validFrom",
    "validTo",
]

# CSV export of a dataset of data.sbb.ch (issue #42). The provider serves only the current
# state, so a download is kept as a snapshot named after its retrieval date.
SBB_DATA_URL = (
    "https://data.sbb.ch/api/explore/v2.1/catalog/datasets/{dataset}/exports/csv?delimiter=%3B"
)

MANIFEST_FIELDS = ["file", "url", "retrieved_at", "sha256", "bytes"]
CHUNK_SIZE = 1 << 20


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def append_manifest(path: Path, url: str, manifest: Path = MANIFEST) -> dict:
    """Add a row for path, unless the manifest already lists this file with this checksum."""
    row = {
        "file": path.relative_to(manifest.parent).as_posix(),
        "url": url,
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": sha256sum(path),
        "bytes": path.stat().st_size,
    }
    is_new = not manifest.exists()
    if not is_new:
        with manifest.open(newline="") as f:
            for existing in csv.DictReader(f):
                if (existing["file"], existing["sha256"]) == (row["file"], row["sha256"]):
                    return existing
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return row


def fetch(url: str, dest: Path, overwrite: bool = False, sha256: str | None = None) -> Path:
    """Download url to dest (relative paths resolve under data/raw) and log it.

    With sha256, a download with another checksum is deleted and raises ValueError.
    """
    dest = dest if dest.is_absolute() else RAW / dest
    if dest.exists() and not overwrite:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0)) or None
        with (
            tmp.open("wb") as f,
            tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar,
        ):
            for chunk in r.iter_content(CHUNK_SIZE):
                f.write(chunk)
                bar.update(len(chunk))
    if sha256 and (actual := sha256sum(tmp)) != sha256:
        tmp.unlink()
        raise ValueError(f"checksum {actual} instead of {sha256}")
    tmp.rename(dest)
    append_manifest(dest, url)
    return dest


def parse_month(text: str) -> tuple[int, int]:
    year, month = text.split("-")
    if not 1 <= int(month) <= 12:
        raise ValueError(f"invalid month: {text}")
    return int(year), int(month)


def months_between(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    """All (year, month) from start to end, both inclusive."""
    if start > end:
        raise ValueError(f"start {start} is after end {end}")
    months = []
    year, month = start
    while (year, month) <= end:
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def fetch_istdaten(year: int, month: int) -> Path:
    url = ISTDATEN_URL.format(year=year, month=month)
    return fetch(url, Path("istdaten") / url.rsplit("/", 1)[1])


class SnapshotUnavailable(RuntimeError):
    """The fixed snapshot of the stop list is missing or has another checksum."""


def service_points_snapshot(directory: Path = SERVICE_POINTS_RAW) -> Path:
    """Path of the fixed snapshot (extract); it may not exist yet."""
    return directory / f"service-points-ch_{SERVICE_POINTS_DATE}.csv"


def service_points_ok(directory: Path = SERVICE_POINTS_RAW) -> bool:
    path = service_points_snapshot(directory)
    return path.exists() and sha256sum(path) == SERVICE_POINTS_SHA256


def fetch_service_points(directory: Path = SERVICE_POINTS_RAW) -> Path:
    """Return the fixed snapshot of the stop list; download it from the release if missing."""
    path = service_points_snapshot(directory)
    if path.exists():
        if not service_points_ok(directory):
            raise SnapshotUnavailable(
                f"{path} hat nicht die Prüfsumme aus sbb_delays.period ({SERVICE_POINTS_SHA256}). "
                "Datei löschen und uv run build erneut ausführen."
            )
        return path
    url = SERVICE_POINTS_RELEASE_URL.format(date=SERVICE_POINTS_DATE)
    try:
        return fetch(url, path, sha256=SERVICE_POINTS_SHA256)
    except (requests.RequestException, ValueError) as e:
        raise SnapshotUnavailable(
            f"Haltestellen-Schnappschuss {SERVICE_POINTS_DATE} nicht verfügbar ({url}): {e}"
        ) from e


def fetch_sbb_dataset(dataset: str, directory: Path = SBB_DATA_RAW) -> Path:
    """Return the newest local snapshot of a data.sbb.ch dataset; download one if none exists."""
    if snapshots := sorted(directory.glob(f"{dataset}_20[0-9][0-9]-*.csv")):
        return snapshots[-1]
    url = SBB_DATA_URL.format(dataset=dataset)
    return fetch(url, directory / f"{dataset}_{date.today():%Y-%m-%d}.csv")


def extract_service_points(source: Path, dest: Path) -> Path:
    """Write the extract of a downloaded stop list: Swiss stops, SERVICE_POINTS_COLUMNS, by number.

    Used once per snapshot to create the file for the release (log 2026-11-08, issue #26).
    """
    columns = ", ".join(SERVICE_POINTS_COLUMNS)
    duckdb.sql(
        f"""
        copy (
            select {columns}
            from read_csv('{source}', delim=';', header=true, all_varchar=true)
            where uicCountryCode = '85'
            order by number::integer
        ) to '{dest}' (delimiter ';', header true)
        """
    )
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download SBB IstDaten and service points.")
    parser.add_argument("--from", dest="start", type=parse_month, required=True, metavar="YYYY-MM")
    parser.add_argument("--to", dest="end", type=parse_month, required=True, metavar="YYYY-MM")
    args = parser.parse_args()

    fetch_service_points()
    for year, month in months_between(args.start, args.end):
        fetch_istdaten(year, month)


if __name__ == "__main__":
    main()
