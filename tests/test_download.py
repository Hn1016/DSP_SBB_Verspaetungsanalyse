import csv
import hashlib

from sbb_delays.download import append_manifest, sha256sum


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
