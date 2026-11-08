"""Order and skipping of `uv run build`, without network and without real data.

Only the network (requests.get) and the paths are replaced. download.fetch,
download.fetch_service_points and load.zip_to_rail_parquet run unchanged.
"""

import functools
import io
import zipfile

import pytest
from test_load import HEADER, TRAIN, TRAIN_ORIGIN

from sbb_delays import build, download, load


def month_archive(missing: frozenset[int] = frozenset()) -> bytes:
    """A September 2026 archive with one train per day, except for the missing days."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for day in sorted(set(range(1, 31)) - missing):
            rows = [r.replace("01.09.2026", f"{day:02d}.09.2026") for r in (TRAIN_ORIGIN, TRAIN)]
            archive.writestr(f"2026-09-{day:02d}_IstDaten.csv", "\n".join([HEADER, *rows]))
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.headers = {"content-length": str(len(content))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.content


@pytest.fixture
def env(tmp_path, monkeypatch):
    raw, processed = tmp_path / "raw", tmp_path / "processed"
    manifest = raw / "manifest.csv"
    monkeypatch.setattr(download, "RAW", raw)
    monkeypatch.setattr(
        download, "append_manifest", functools.partial(download.append_manifest, manifest=manifest)
    )
    monkeypatch.setattr(build, "ISTDATEN_RAW", raw / "istdaten")
    monkeypatch.setattr(build, "SERVICE_POINTS_RAW", raw / "service_points")
    monkeypatch.setattr(build, "ISTDATEN_RAIL", processed / "istdaten_rail")

    served = {"archive": month_archive()}  # a test may replace it before the first run
    requests_made = []

    def fake_get(url, **kwargs):
        requests_made.append(url)
        content = served["archive"] if url.endswith(".zip") else b"number;designation\n"
        return FakeResponse(content)

    monkeypatch.setattr(download.requests, "get", fake_get)

    calls = []
    for module, name in [
        (download, "fetch_service_points"),
        (download, "fetch_istdaten"),
        (load, "zip_to_rail_parquet"),
    ]:
        original = getattr(module, name)

        def spy(*args, _original=original, _name=name, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(module, name, spy)

    return {
        "raw": raw,
        "manifest": manifest,
        "requests": requests_made,
        "calls": calls,
        "served": served,
    }


def stdout_lines(capsys) -> list[str]:
    return capsys.readouterr().out.splitlines()


def warnings(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if line.startswith("Warnung")]


def test_first_run_downloads_then_loads(env, capsys):
    build.build()

    assert env["calls"] == ["fetch_service_points", "fetch_istdaten", "zip_to_rail_parquet"]
    out, err = capsys.readouterr()
    assert out.splitlines() == ["download: gebaut", "load: gebaut"]
    assert warnings(err) == []
    assert all(path.exists() for path in build.rail_parquets())
    assert len(build.rail_parquets()) == 30
    # the archive build checks is the one fetch_istdaten writes
    assert build.istdaten_zip(2026, 9).exists()


def test_second_run_skips_every_step(env, capsys):
    build.build()
    capsys.readouterr()
    manifest_before = env["manifest"].read_text()
    mtimes = [path.stat().st_mtime_ns for path in build.rail_parquets()]
    env["calls"].clear()

    build.build()

    assert stdout_lines(capsys) == ["download: übersprungen", "load: übersprungen"]
    assert env["calls"] == []
    assert len(env["requests"]) == 2  # only the first run
    assert env["manifest"].read_text() == manifest_before
    assert [path.stat().st_mtime_ns for path in build.rail_parquets()] == mtimes


def test_force_rebuilds_processed_but_not_raw(env, capsys):
    build.build()
    capsys.readouterr()
    raw_before = {p: p.read_bytes() for p in env["raw"].rglob("*") if p.is_file()}
    env["calls"].clear()

    build.build(force=True)

    assert stdout_lines(capsys) == ["download: übersprungen", "load: gebaut"]
    assert env["calls"] == ["zip_to_rail_parquet"]
    assert len(env["requests"]) == 2
    assert {p: p.read_bytes() for p in env["raw"].rglob("*") if p.is_file()} == raw_before
    assert all(path.exists() for path in build.rail_parquets())


def test_missing_day_in_archive_warns_and_still_skips(env, capsys):
    env["served"]["archive"] = month_archive(missing=frozenset({15}))
    build.build()
    out, err = capsys.readouterr()
    assert out.splitlines() == ["download: gebaut", "load: gebaut"]
    assert warnings(err) == ["Warnung: im Archiv fehlen Tage des Zeitraums: 2026-09-15"]
    assert len(build.rail_parquets()) == 29
    env["calls"].clear()

    build.build()

    out, err = capsys.readouterr()
    assert out.splitlines() == ["download: übersprungen", "load: übersprungen"]
    assert warnings(err) == ["Warnung: im Archiv fehlen Tage des Zeitraums: 2026-09-15"]
    assert env["calls"] == []
