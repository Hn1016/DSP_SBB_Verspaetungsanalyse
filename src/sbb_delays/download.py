"""Download raw files and record source, retrieval date and SHA-256 checksum.

Raw files are never modified after download. Every download appends one row to
data/raw/manifest.csv so the provenance of each file is traceable.
"""

import csv
import hashlib
from datetime import UTC, datetime
from pathlib import Path

import requests
from tqdm import tqdm

from sbb_delays.paths import MANIFEST, RAW

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
