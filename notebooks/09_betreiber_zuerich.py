import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo

    from sbb_delays import build
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.paths import ISTDATEN_RAIL
    from sbb_delays.period import END, START
    from sbb_delays.sections import period_days

    con = duckdb.connect()
    first, last = period_days(START, END)
    OPERATORS = ["LEB", "MBC", "ZB"]  # issue #36
    return ISTDATEN_RAIL, OPERATORS, build, con, first, last, mo, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Fahren LEB, MBC und ZB im Kanton Zürich?

    Issue #36. Erwartung und Zählweise im Projektlog (Hypothese vom 14.11.2026, vor der Analyse
    gepusht, Commit `5efaf1b`): **0 Abschnittsfahrten von LEB, MBC und ZB im Kanton Zürich**
    (beide Halte im Kanton, Zeitraum aus `period.py`).

    Betreiber einer Abschnittsfahrt: `BETREIBER_ABK` am Halt A, aus den Tagesdateien über
    `BETRIEBSTAG` und `ZEILE`. Zwei Gegenproben, damit die 0 scheitern kann:

    - **Abkürzung:** dieselbe Zählung für die ganze Schweiz; dort muss jeder der drei vorkommen.
    - **Messung:** Zeilen der drei an Zürcher Halten, unabhängig vom Status; auch sie muss 0 sein.
    """)
    return


@app.cell
def _(ISTDATEN_RAIL, build, con, first, last, service_points_snapshot):
    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    con.execute(
        f"""
        create or replace view rail as
        select * from read_parquet('{ISTDATEN_RAIL}/*.parquet')
        where BETRIEBSTAG between date '{first}' and date '{last}'
        """
    )
    # One row per section passage with the operator at stop A (not in the sections file).
    con.execute(
        f"""
        create or replace table passages as
        select s.a_id, s.b_id, r.BETREIBER_ABK as betreiber,
               s.a_id in (select BPUIC from zh) and s.b_id in (select BPUIC from zh) as in_zh
        from read_parquet('{build.sections_parquet()}') s
        join rail r on r.BETRIEBSTAG = s.BETRIEBSTAG and r.ZEILE = s.zeile_a
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## LEB, MBC und ZB: Prüfung und Gegenproben
    """)
    return


@app.cell
def _(OPERATORS, con):
    _ops = ", ".join(f"('{o}')" for o in OPERATORS)
    con.sql(
        f"""
        select o.betreiber,
               count(p.betreiber) as abschnittsfahrten_schweiz,
               count(p.betreiber) filter (where p.in_zh) as abschnittsfahrten_zh,
               (select count(*) from rail r
                where r.BETREIBER_ABK = o.betreiber
                  and r.BPUIC in (select BPUIC from zh)) as zeilen_zh_alle_status
        from (values {_ops}) o(betreiber)
        left join passages p using (betreiber)
        group by o.betreiber
        order by o.betreiber
        """
    ).pl()
    return


@app.cell
def _(mo):
    mo.md("""
    ## Die fünf Betreiber mit den meisten Abschnittsfahrten im Kanton Zürich
    """)
    return


@app.cell
def _(con):
    con.sql(
        """
        select betreiber, count(*) as abschnittsfahrten,
               round(100 * count(*) / sum(count(*)) over (), 1) as anteil_pct,
               sum(count(*)) over () as total_zh
        from passages where in_zh
        group by betreiber
        order by abschnittsfahrten desc
        limit 5
        """
    ).pl()
    return


@app.cell
def _(mo):
    mo.md("""
    ## Betroffene Abschnitte (leer, wenn die Erwartung hält)
    """)
    return


@app.cell
def _(OPERATORS, con):
    con.sql(
        f"""
        select p.betreiber, a.name || ' → ' || b.name as abschnitt, count(*) as fahrten
        from passages p
        join zh a on a.BPUIC = p.a_id
        join zh b on b.BPUIC = p.b_id
        where p.in_zh and p.betreiber in ({", ".join(f"'{o}'" for o in OPERATORS)})
        group by all
        order by fahrten desc
        """
    ).pl()
    return


if __name__ == "__main__":
    app.run()
