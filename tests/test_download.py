import csv
import functools
import hashlib

import pytest
import requests
from test_build import FakeResponse

from sbb_delays import download, period
from sbb_delays.download import (
    ISTDATEN_URL,
    SnapshotUnavailable,
    append_manifest,
    fetch_service_points,
    months_between,
    parse_month,
    service_points_snapshot,
    sha256sum,
)
from sbb_delays.paths import MANIFEST


def test_sha256sum_matches_hashlib(tmp_path):
    f = tmp_path / "a.csv"
    f.write_bytes(b"BETRIEBSTAG;FAHRT_BEZEICHNER\n")
    assert sha256sum(f) == hashlib.sha256(f.read_bytes()).hexdigest()


def test_append_manifest_writes_header_once(tmp_path):
    manifest = tmp_path / "manifest.csv"
    for name in ["a.csv", "b.csv"]:
        f = tmp_path / name
        f.write_text(name)
        append_manifest(f, f"https://example.org/{name}", manifest=manifest)

    rows = list(csv.DictReader(manifest.open()))
    assert [r["file"] for r in rows] == ["a.csv", "b.csv"]
    assert all(len(r["sha256"]) == 64 for r in rows)


def test_months_between_crosses_year_end():
    assert months_between((2025, 11), (2026, 2)) == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]


def test_months_between_rejects_reversed_range():
    with pytest.raises(ValueError):
        months_between((2026, 2), (2026, 1))


def test_parse_month():
    assert parse_month("2026-09") == (2026, 9)
    with pytest.raises(ValueError):
        parse_month("2026-13")


def test_istdaten_url_pads_month():
    url = ISTDATEN_URL.format(year=2026, month=9)
    assert url.endswith("/istdaten/2026/ist-daten-v2-2026-09.zip")


def test_append_manifest_skips_same_file_and_checksum(tmp_path):
    manifest = tmp_path / "manifest.csv"
    f = tmp_path / "a.csv"
    f.write_text("one")
    append_manifest(f, "https://example.org/a.csv", manifest=manifest)
    append_manifest(f, "https://example.org/a.csv", manifest=manifest)
    f.write_text("two")  # same name, other content: a new row
    append_manifest(f, "https://example.org/a.csv", manifest=manifest)

    rows = list(csv.DictReader(manifest.open()))
    assert len(rows) == 2
    assert rows[0]["sha256"] != rows[1]["sha256"]


SNAPSHOT = b"number;designationOfficial\n8503000;Z\xc3\xbcrich HB\n"


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    """Network replaced by a release that serves `served["content"]` (None: not found)."""
    manifest = tmp_path / "manifest.csv"
    monkeypatch.setattr(
        download, "append_manifest", functools.partial(download.append_manifest, manifest=manifest)
    )
    monkeypatch.setattr(download, "SERVICE_POINTS_SHA256", hashlib.sha256(SNAPSHOT).hexdigest())
    served = {"content": SNAPSHOT, "urls": []}

    def fake_get(url, **kwargs):
        served["urls"].append(url)
        if served["content"] is None:
            raise requests.HTTPError("404 Not Found")
        return FakeResponse(served["content"])

    monkeypatch.setattr(download.requests, "get", fake_get)
    return {"dir": tmp_path / "service_points", "manifest": manifest, "served": served}


def test_fetch_service_points_downloads_the_pinned_snapshot(mirror):
    directory = mirror["dir"]
    directory.mkdir()
    (directory / "service-points_2026-11-08.csv").write_text("newer list\n")  # ignored

    path = fetch_service_points(directory)

    assert path == service_points_snapshot(directory)
    assert path.read_bytes() == SNAPSHOT
    assert mirror["served"]["urls"] == [
        download.SERVICE_POINTS_RELEASE_URL.format(date=period.SERVICE_POINTS_DATE)
    ]
    # a second clone on another day: no download, same file, no second manifest row
    assert fetch_service_points(directory) == path
    assert len(mirror["served"]["urls"]) == 1
    assert len(list(csv.DictReader(mirror["manifest"].open()))) == 1


def test_fetch_service_points_aborts_on_other_checksum(mirror):
    mirror["served"]["content"] = b"number;designationOfficial\n8503000;Zuerich\n"

    with pytest.raises(SnapshotUnavailable, match="nicht verfügbar"):
        fetch_service_points(mirror["dir"])
    assert not any(mirror["dir"].iterdir())  # neither the file nor a .part is left
    assert not mirror["manifest"].exists()


def test_fetch_service_points_aborts_when_release_is_missing(mirror):
    mirror["served"]["content"] = None

    with pytest.raises(SnapshotUnavailable, match="nicht verfügbar"):
        fetch_service_points(mirror["dir"])
    assert not service_points_snapshot(mirror["dir"]).exists()


def test_fetch_service_points_rejects_a_changed_local_file(mirror):
    mirror["dir"].mkdir()
    service_points_snapshot(mirror["dir"]).write_bytes(b"edited\n")

    with pytest.raises(SnapshotUnavailable, match="Prüfsumme"):
        fetch_service_points(mirror["dir"])
    assert mirror["served"]["urls"] == []


def test_pinned_checksum_is_the_one_in_the_manifest():
    rows = {r["file"]: r for r in csv.DictReader(MANIFEST.open())}
    row = rows[f"service_points/service-points-ch_{period.SERVICE_POINTS_DATE}.csv"]
    assert row["sha256"] == period.SERVICE_POINTS_SHA256
    assert row["url"] == download.SERVICE_POINTS_RELEASE_URL.format(date=period.SERVICE_POINTS_DATE)


def test_fetch_sbb_dataset_returns_the_newest_snapshot_without_download(tmp_path, monkeypatch):
    for day in ["2026-11-14", "2026-12-01"]:
        (tmp_path / f"zugzahlen_{day}.csv").write_text("jahr;anzahl_zuege\n")
    (tmp_path / "zugzahlen_pro_monat_2026-12-24.csv").write_text("x\n")  # another dataset
    monkeypatch.setattr(download, "fetch", lambda *args, **kwargs: pytest.fail("no download"))

    assert download.fetch_sbb_dataset("zugzahlen", tmp_path).name == "zugzahlen_2026-12-01.csv"


def test_fetch_sbb_dataset_downloads_a_dated_snapshot(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(download, "fetch", lambda url, dest: calls.append((url, dest)) or dest)

    path = download.fetch_sbb_dataset("zugzahlen", tmp_path)

    assert path.parent == tmp_path
    assert path.name.startswith("zugzahlen_20") and path.suffix == ".csv"
    assert calls[0][0].startswith("https://data.sbb.ch/") and "/zugzahlen/" in calls[0][0]
