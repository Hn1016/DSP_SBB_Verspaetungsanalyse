"""Order and skipping of `uv run build`, without network and without real data.

Only the network (requests.get) and the paths are replaced. download.fetch,
download.fetch_service_points, load.zip_to_rail_parquet, sections.sections and ranking.ranking
run unchanged.
"""

import functools
import hashlib
import io
import re
import shutil
import zipfile

import duckdb
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
    monkeypatch.setattr(build, "PROCESSED", processed)
    # the test archive is September 2026, independent of the period in period.py
    monkeypatch.setattr(build, "START", (2026, 9))
    monkeypatch.setattr(build, "END", (2026, 9))
    # The stop list as ranking.zurich_sections reads it. Bern is marked as ZH only for this
    # test, so that the one section of the test train (Zürich HB -> Bern) reaches the ranking.
    stops = (
        "number;designationOfficial;cantonAbbreviation\n8503000;Zürich HB;ZH\n8507000;Bern;ZH\n"
    ).encode()
    monkeypatch.setattr(download, "SERVICE_POINTS_SHA256", hashlib.sha256(stops).hexdigest())

    served = {"archive": month_archive()}  # a test may replace it before the first run
    requests_made = []

    def fake_get(url, **kwargs):
        requests_made.append(url)
        content = served["archive"] if url.endswith(".zip") else stops
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
    assert out.splitlines() == [
        "download: gebaut",
        "load: gebaut",
        "sections: gebaut",
        "ranking: gebaut",
    ]
    assert warnings(err) == []
    assert all(path.exists() for path in build.rail_parquets())
    assert len(build.rail_parquets()) == 30
    # the archive build checks is the one fetch_istdaten writes
    assert build.istdaten_zip(2026, 9).exists()
    # one section (Zürich HB -> Bern) per day, in a file named after the period
    assert build.sections_parquet().name == f"sections_2026-09_2026-09_{build.rules_hash()}.parquet"
    assert re.fullmatch(r"[0-9a-f]{8}", build.rules_hash())
    assert duckdb.read_parquet(str(build.sections_parquet())).count("*").fetchone()[0] == 30
    # the one section in each of the 13 windows; 30 trips are below MIN_TRIPS, so no value in
    # any window, also in those without a trip
    ranking_hash = build.rules_hash([*build.RULE_FILES, build.RANKING_FILE])
    assert build.ranking_parquet().name == f"ranking_2026-09_2026-09_{ranking_hash}.parquet"
    assert ranking_hash != build.rules_hash()
    reasons = duckdb.sql(
        f"select grund, count(*) from read_parquet('{build.ranking_parquet()}') group by all"
    ).fetchall()
    assert reasons == [("zu wenige Fahrten", 13)]


def test_second_run_skips_every_step(env, capsys):
    build.build()
    capsys.readouterr()
    manifest_before = env["manifest"].read_text()
    mtimes = [
        path.stat().st_mtime_ns
        for path in [*build.rail_parquets(), build.sections_parquet(), build.ranking_parquet()]
    ]
    env["calls"].clear()

    build.build()

    assert stdout_lines(capsys) == [
        "download: übersprungen",
        "load: übersprungen",
        "sections: übersprungen",
        "ranking: übersprungen",
    ]
    assert env["calls"] == []
    assert len(env["requests"]) == 2  # only the first run
    assert env["manifest"].read_text() == manifest_before
    assert [
        path.stat().st_mtime_ns
        for path in [*build.rail_parquets(), build.sections_parquet(), build.ranking_parquet()]
    ] == mtimes


def test_force_rebuilds_processed_but_not_raw(env, capsys):
    build.build()
    capsys.readouterr()
    raw_before = {p: p.read_bytes() for p in env["raw"].rglob("*") if p.is_file()}
    env["calls"].clear()

    build.build(force=True)

    assert stdout_lines(capsys) == [
        "download: übersprungen",
        "load: gebaut",
        "sections: gebaut",
        "ranking: gebaut",
    ]
    assert env["calls"] == ["zip_to_rail_parquet"]
    assert len(env["requests"]) == 2
    assert {p: p.read_bytes() for p in env["raw"].rglob("*") if p.is_file()} == raw_before
    assert all(path.exists() for path in build.rail_parquets())


def test_missing_day_in_archive_warns_and_still_skips(env, capsys):
    env["served"]["archive"] = month_archive(missing=frozenset({15}))
    build.build()
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "download: gebaut",
        "load: gebaut",
        "sections: gebaut",
        "ranking: gebaut",
    ]
    assert warnings(err) == ["Warnung: im Archiv fehlen Tage des Zeitraums: 2026-09-15"]
    assert len(build.rail_parquets()) == 29
    env["calls"].clear()

    build.build()

    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "download: übersprungen",
        "load: übersprungen",
        "sections: übersprungen",
        "ranking: übersprungen",
    ]
    assert warnings(err) == ["Warnung: im Archiv fehlen Tage des Zeitraums: 2026-09-15"]
    assert env["calls"] == []


def test_new_period_builds_a_new_sections_file(env, monkeypatch, capsys):
    build.build()
    capsys.readouterr()
    old = build.sections_parquet()

    monkeypatch.setattr(build, "START", (2026, 8))  # period.py changed; the old file stays

    assert build.sections_parquet().name == f"sections_2026-08_2026-09_{build.rules_hash()}.parquet"
    assert build.build_sections() == "gebaut"
    assert old.exists() and build.sections_parquet().exists()


def test_changed_rules_rebuild_sections_and_drop_the_old_file(env, tmp_path, monkeypatch, capsys):
    rules = []
    for path in build.RULE_FILES:  # copies, so the test can change the rules
        copy = tmp_path / "rules" / path.name
        copy.parent.mkdir(exist_ok=True)
        shutil.copy(path, copy)
        rules.append(copy)
    monkeypatch.setattr(build, "RULE_FILES", rules)
    build.build()
    capsys.readouterr()
    old = build.sections_parquet()

    assert build.build_sections() == "übersprungen"  # same rules

    rules[1].write_text(rules[1].read_text() + "\n# changed rule\n")

    assert build.sections_parquet() != old
    assert build.build_sections() == "gebaut"
    assert build.sections_parquet().exists()
    assert not old.exists()
    assert build.build_sections() == "übersprungen"


def test_ranking_follows_sections_and_its_own_rules(env, tmp_path, monkeypatch, capsys):
    rules = tmp_path / "rules" / "ranking.py"  # a copy, so the test can change the rules
    rules.parent.mkdir()
    shutil.copy(build.RANKING_FILE, rules)
    monkeypatch.setattr(build, "RANKING_FILE", rules)
    build.build()
    capsys.readouterr()
    old = build.ranking_parquet()

    assert build.build_ranking() == "übersprungen"
    assert build.build_ranking(force=True) == "gebaut"  # as build() does when sections was built

    rules.write_text(rules.read_text() + "\n# changed rule\n")

    assert build.ranking_parquet() != old
    build.build()
    assert stdout_lines(capsys)[-2:] == ["sections: übersprungen", "ranking: gebaut"]
    assert build.ranking_parquet().exists()
    assert not old.exists()
    assert build.build_ranking() == "übersprungen"
