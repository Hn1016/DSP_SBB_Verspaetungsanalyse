import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    from collections import deque

    import duckdb
    import marimo as mo
    import polars as pl

    from sbb_delays import build
    from sbb_delays.download import fetch_sbb_dataset, service_points_snapshot

    con = duckdb.connect()
    return build, con, deque, fetch_sbb_dataset, mo, pl, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Annahme A6: Zuordnung der Abschnitte zu data.sbb.ch

    Issue #42. Erwartung und Zählweise im Projektlog (Hypothese vom 14.11.2026, Commit `d451249`,
    und Nachtrag «was eine Kette ist», Commit `80e83dc`; beide vor dem Zuordnen gepusht). Basis:
    die 394 Zürcher Abschnitte mit Wert im Fenster «ganzer Zeitraum» aus dem Schritt `ranking`.

    - **(1)** Mindestens 80 % lassen sich eindeutig einem Streckenabschnitt mit Länge in km
      zuordnen.
    - **(2)** Mindestens 9 der Top 10 lassen sich eindeutig zuordnen (Länge).
    - **(3)** Für mindestens 80 % gibt es eine Zugzahl.

    Länge: A und B liegen auf genau einer gemeinsamen Linie in `linie-mit-betriebspunkten`.
    Zugzahl: genau ein kürzester Weg von A nach B im Netz von `zugzahlen` (Personenverkehr 2025,
    ohne Richtung). Schlüssel ist die `BPUIC`.
    """)
    return


@app.cell
def _(build, con, fetch_sbb_dataset, service_points_snapshot):
    YEAR = 2025  # latest year in zugzahlen (log 2026-11-14, addendum)

    con.execute(
        f"""
        create or replace view stops as
        select number::integer as bpuic, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        """
    )
    con.execute(
        f"""
        create or replace table base as
        select r.a_id, r.b_id, a.name || ' → ' || b.name as abschnitt, r.rang, r.fahrten
        from read_parquet('{build.ranking_parquet()}') r
        join stops a on a.bpuic = r.a_id
        join stops b on b.bpuic = r.b_id
        where r.fenster = 'ganzer Zeitraum' and r.grund is null
        """
    )
    con.execute(
        f"""
        create or replace table lines as
        select bpuic, linie, km, linienname
        from read_csv('{fetch_sbb_dataset("linie-mit-betriebspunkten")}', delim=';', header=true)
        """
    )
    # One edge per pair of operating points: passenger trains of YEAR, both directions added;
    # an exact duplicate row counts once.
    con.execute(
        f"""
        create or replace table edges as
        select least(von_bpuic, bis_bpuic) as u, greatest(von_bpuic, bis_bpuic) as v,
               sum(anzahl_zuege) as zuege
        from (
            select distinct pid_abschnitt, in_richtung, von_bpuic, bis_bpuic, anzahl_zuege
            from read_csv('{fetch_sbb_dataset("zugzahlen")}', delim=';', header=true)
            where jahr = {YEAR} and geschaeftscode = 'Personenverkehr'
              and von_bpuic is not null and bis_bpuic is not null
        )
        group by all
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Länge: gemeinsame Linie und Kilometer
    """)
    return


@app.cell
def _(con):
    length = con.sql(
        """
        with common as (
            select s.a_id, s.b_id, count(*) as linien,
                   any_value(a.linie) as linie, any_value(a.linienname) as linienname,
                   any_value(abs(b.km - a.km)) as km,
                   max(abs(b.km - a.km)) - min(abs(b.km - a.km)) as km_spanne
            from base s
            join lines a on a.bpuic = s.a_id
            join lines b on b.bpuic = s.b_id and b.linie = a.linie
            group by all
        )
        select s.*, coalesce(c.linien, 0) as linien,
               case when c.linien = 1 then 'eindeutig'
                    when c.linien > 1 then 'mehrdeutig'
                    else 'nicht zuordenbar' end as laenge,
               case when c.linien = 1 then null
                    when c.linien > 1 then 'mehrere gemeinsame Linien'
                    when s.a_id not in (select bpuic from lines)
                         and s.b_id not in (select bpuic from lines) then 'A und B fehlen'
                    when s.a_id not in (select bpuic from lines) then 'A fehlt'
                    when s.b_id not in (select bpuic from lines) then 'B fehlt'
                    else 'keine gemeinsame Linie' end as laenge_grund,
               case when c.linien = 1 then c.linie end as linie,
               case when c.linien = 1 then c.linienname end as linienname,
               case when c.linien = 1 then round(c.km, 3) end as km,
               case when c.linien > 1 then round(c.km_spanne, 3) end as km_spanne
        from base s left join common c using (a_id, b_id)
        """
    ).pl()
    length.group_by("laenge", "laenge_grund").len().sort("len", descending=True)
    return (length,)


@app.cell
def _(mo):
    mo.md("""
    ## Zugzahl: kürzester Weg im Netz

    `kanten`: Zahl der Kanten der Kette; `zuege_min` und `zuege_max`: kleinste und grösste
    Zugzahl (Personenverkehr 2025, beide Richtungen) auf der Kette.
    """)
    return


@app.cell
def _(con, deque, pl):
    _trains = {(u, v): n for u, v, n in con.sql("select u, v, zuege from edges").fetchall()}
    _neighbours = {}
    for _u, _v in _trains:
        _neighbours.setdefault(_u, []).append(_v)
        _neighbours.setdefault(_v, []).append(_u)

    def _chain(a, b):
        """(status, reason, edges of the one shortest path) from a to b, by number of edges."""
        if a not in _neighbours or b not in _neighbours:
            missing = [n for n, x in (("A", a), ("B", b)) if x not in _neighbours]
            return "nicht zuordenbar", " und ".join(missing) + " nicht im Netz", None
        dist, paths, parent = {a: 0}, {a: 1}, {}
        queue = deque([a])
        while queue:
            x = queue.popleft()
            if x == b:
                break
            for y in _neighbours[x]:
                if y not in dist:
                    dist[y], paths[y], parent[y] = dist[x] + 1, paths[x], x
                    queue.append(y)
                elif dist[y] == dist[x] + 1:
                    paths[y] += paths[x]
        if b not in dist:
            return "nicht zuordenbar", "kein Weg im Netz", None
        if paths[b] > 1:
            return "mehrdeutig", f"{paths[b]} gleich kurze Wege", None
        path, x = [], b
        while x != a:
            path.append((min(x, parent[x]), max(x, parent[x])))
            x = parent[x]
        return "eindeutig", None, path

    _rows = []
    for _a, _b in con.sql("select a_id, b_id from base").fetchall():
        _status, _reason, _path = _chain(_a, _b)
        _counts = [_trains[e] for e in _path] if _path else []
        _rows.append(
            {
                "a_id": _a,
                "b_id": _b,
                "zugzahl": _status,
                "zugzahl_grund": _reason,
                "kanten": len(_counts) or None,
                "zuege_min": min(_counts, default=None),
                "zuege_max": max(_counts, default=None),
            }
        )
    trains = pl.DataFrame(_rows, infer_schema_length=None)
    trains.group_by("zugzahl", "zugzahl_grund").len().sort("len", descending=True)
    return (trains,)


@app.cell
def _(length, trains):
    mapping = length.join(trains, on=["a_id", "b_id"], how="left", validate="1:1")
    mapping.group_by("kanten").len().sort("kanten")
    return (mapping,)


@app.cell
def _(mo):
    mo.md("""
    ## Je Ziel: eindeutig, mehrdeutig, nicht zuordenbar
    """)
    return


@app.cell
def _(mapping, pl):
    _states = ["eindeutig", "mehrdeutig", "nicht zuordenbar"]
    per_target = pl.DataFrame(
        {
            "ziel": ["Länge (km)", "Zugzahl"],
            **{s: [(mapping[c] == s).sum() for c in ("laenge", "zugzahl")] for s in _states},
            "eindeutig_pct": [
                round(100 * (mapping[c] == "eindeutig").mean(), 1) for c in ("laenge", "zugzahl")
            ],
        }
    )
    per_target.head(2)
    return (per_target,)


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (1), (2) und (3)
    """)
    return


@app.cell
def _(mapping, per_target, pl):
    top10 = mapping.filter(pl.col("rang") <= 10).sort("rang")
    _km, _trains = per_target["eindeutig_pct"]
    _top = (top10["laenge"] == "eindeutig").sum()
    pl.DataFrame(
        {
            "pruefung": [
                "(1) Länge eindeutig, Anteil der 394",
                "(2) Länge eindeutig, Top 10",
                "(3) Zugzahl eindeutig, Anteil der 394",
            ],
            "ergebnis": [f"{_km} %", f"{_top} von 10", f"{_trains} %"],
            "erwartung": ["≥ 80 %", "≥ 9", "≥ 80 %"],
            "gehalten": [bool(_km >= 80), bool(_top >= 9), bool(_trains >= 80)],
        }
    )
    return (top10,)


@app.cell
def _(mo):
    mo.md("""
    ## Die Top 10
    """)
    return


@app.cell
def _(top10):
    _columns = ["rang", "abschnitt", "laenge", "laenge_grund", "linienname", "km"]
    top10.select(*_columns, "zugzahl", "zugzahl_grund", "kanten", "zuege_min", "zuege_max")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Beide Ziele zusammen und Beispiele

    Wie viele Abschnitte beide Zuordnungen haben, und je Grund die Abschnitte mit den meisten
    Fahrten.
    """)
    return


@app.cell
def _(mapping):
    mapping.group_by("laenge", "zugzahl").len().sort("len", descending=True)
    return


@app.cell
def _(mapping, pl):
    examples = pl.concat(
        [
            mapping.filter(pl.col(c) != "eindeutig")
            .sort("fahrten", descending=True)
            .group_by(pl.lit(c).alias("ziel"), pl.col(f"{c}_grund").alias("grund"))
            .agg(
                pl.len().alias("abschnitte"),
                pl.col("fahrten").sum(),
                pl.col("abschnitt").head(3).str.join("; ").alias("beispiele"),
            )
            for c in ("laenge", "zugzahl")
        ]
    ).sort("ziel", "abschnitte", descending=[False, True])
    examples.head(30)
    return


@app.cell
def _(mapping, pl):
    # long chains: the shortest path may differ from the route the trains take
    mapping.filter(pl.col("kanten") >= 4).sort("kanten", "fahrten", descending=True).select(
        "abschnitt", "fahrten", "kanten", "zuege_min", "zuege_max", "laenge", "km"
    ).head(15)
    return


if __name__ == "__main__":
    app.run()
