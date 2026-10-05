import csv
import hashlib

import pytest

from sbb_delays.download import (
    ISTDATEN_URL,
    append_manifest,
    fetch_service_points,
    months_between,
    parse_month,
    sha256sum,
)


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


def test_fetch_service_points_reuses_latest_snapshot(tmp_path):
    for day in ["2026-10-04", "2026-10-05"]:
        (tmp_path / f"service-points_{day}.csv").write_text("sloid\n")
    # no network call: an existing snapshot is returned as is
    assert fetch_service_points(tmp_path).name == "service-points_2026-10-05.csv"
