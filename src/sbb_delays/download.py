"""Download raw files and record source, retrieval date and SHA-256 checksum.

Raw files are never modified after download. Every download appends one row to
data/raw/manifest.csv so the provenance of each file is traceable.

Usage:
    uv run python -m sbb_delays.download --from 2026-09 --to 2026-09
"""

import argparse
import csv
import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import requests
from tqdm import tqdm

from sbb_delays.paths import MANIFEST, RAW, SERVICE_POINTS_RAW

# Monthly archive of IstDaten (v2 format, available from 2025-07). The daily files on
# data.opentransportdata.swiss have random resource ids and cannot be derived from a date.
ISTDATEN_URL = (
    "https://archive.opentransportdata.swiss/istdaten/{year}/ist-daten-v2-{year}-{month:02d}.zip"
)
# The permalink redirects to the current file; the direct resource URL changes with every update.
# The provider updates the file daily, so each download is a snapshot named by retrieval date.
SERVICE_POINTS_URL = "https://data.opentransportdata.swiss/dataset/service-point-v2/permalink"

MANIFEST_FIELDS = ["file", "url", "retrieved_at", "sha256", "bytes"]
CHUNK_SIZE = 1 << 20


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def append_manifest(path: Path, url: str, manifest: Path = MANIFEST) -> dict:
    row = {
        "file": path.relative_to(manifest.parent).as_posix(),
        "url": url,
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": sha256sum(path),
        "bytes": path.stat().st_size,
    }
    is_new = not manifest.exists()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return row


def fetch(url: str, dest: Path, overwrite: bool = False) -> Path:
    """Download url to dest (relative paths resolve under data/raw) and log it."""
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


def latest_service_points(directory: Path = SERVICE_POINTS_RAW) -> Path | None:
    snapshots = sorted(directory.glob("service-points_*.csv"))
    return snapshots[-1] if snapshots else None


def fetch_service_points(directory: Path = SERVICE_POINTS_RAW) -> Path:
    """Download a snapshot of the stop list unless one exists. Delete the file to refresh."""
    existing = latest_service_points(directory)
    if existing:
        return existing
    return fetch(SERVICE_POINTS_URL, directory / f"service-points_{date.today():%Y-%m-%d}.csv")


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
