import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl

    from sbb_delays import quality
    from sbb_delays.download import service_points_snapshot

    con = quality.connect()
    return con, service_points_snapshot, mo, pl, quality


@app.cell
def _(mo):
    mo.md("""
    # Annahme A7 — Streckenverspätung nach Soll-Fahrzeit

    Issue #18. Erwartung im Projektlog (Eintrag vom 3.11.2026, vor der Analyse notiert). Basis wie
    Issue #14 (`03_erste_rangliste.py`): Mo 7.9. bis So 13.9.2026, beide Halte im Kanton Zürich,
    Abfahrt A und Ankunft B gemessen (`REAL`).
    """)
    return


@app.cell
def _(con, service_points_snapshot, quality):
    WEEK = "BETRIEBSTAG between date '2026-09-07' and date '2026-09-13'"
    MIN_TRIPS = 20

    # Same base as notebook 03; src/ is out of scope for issue #18, so the views are repeated here.
    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    quality.delays(con).filter(WEEK).create_view("week", replace=True)
    con.execute(
        f"""
        create or replace view pairs as
        select BETRIEBSTAG, ZEILE as zeile_a,
               lead(ZEILE) over (partition by {quality.TRIP} order by ZEILE) as zeile_b
        from rail where {WEEK}
        """
    )
    con.execute(
        """
        create or replace view sections as
        select a.BPUIC as a_id, b.BPUIC as b_id, b.an_delay - a.ab_delay as section_delay,
               epoch(b.ANKUNFTSZEIT - a.ABFAHRTSZEIT) / 60 as runtime_min
        from pairs p
        join week a on a.BETRIEBSTAG = p.BETRIEBSTAG and a.ZEILE = p.zeile_a
        join week b on b.BETRIEBSTAG = p.BETRIEBSTAG and b.ZEILE = p.zeile_b
        where a.BPUIC in (select BPUIC from zh) and b.BPUIC in (select BPUIC from zh)
          and a.ab_delay is not null and b.an_delay is not null
          and a.ABFAHRTSZEIT <= b.ANKUNFTSZEIT
        """
    )
    return (MIN_TRIPS,)


@app.cell
def _(mo):
    mo.md("""
    ## Mittlere Streckenverspätung je Klasse der Soll-Fahrzeit

    Klassen aus dem Issue: 1, 2, 3, 4, 5 und mehr Minuten.
    """)
    return


@app.cell
def _(con):
    by_class = con.sql(
        """
        select case when runtime_min >= 5 then '5+' else runtime_min::int::varchar end as soll_min,
               count(*) as fahrten,
               round(avg(section_delay), 2) as mittel_min,
               round(median(section_delay), 2) as median_min
        from sections
        group by all
        order by soll_min
        """
    ).pl()
    by_class.head(10)
    return (by_class,)


@app.cell
def _(by_class, pl):
    def _mean(c):
        return by_class.filter(pl.col("soll_min") == c)["mittel_min"].item()

    diff_1_vs_5 = round(_mean("1") - _mean("5+"), 2)
    pl.DataFrame({"differenz_1_minus_5plus_min": [diff_1_vs_5], "erwartung_min": [">= 0.3"]})
    return


@app.cell
def _(mo):
    mo.md("""
    ## Soll-Fahrzeit der Top 10 Abschnitte aus Issue #14

    Rangliste wie in `03_erste_rangliste.py` (Mittel, mindestens 20 Fahrten); Soll-Fahrzeit je
    Abschnitt als Median über seine Fahrten in der Woche.
    """)
    return


@app.cell
def _(MIN_TRIPS, con):
    top10 = con.sql(
        f"""
        select za.name || ' → ' || zb.name as abschnitt,
               count(*) as fahrten,
               round(avg(section_delay), 2) as mittel_min,
               median(runtime_min) as soll_min,
               rank() over (order by avg(section_delay) desc) as rang
        from sections
        join zh za on za.BPUIC = a_id
        join zh zb on zb.BPUIC = b_id
        group by all
        having count(*) >= {MIN_TRIPS}
        order by rang
        limit 10
        """
    ).pl()
    top10.head(10)
    return (top10,)


@app.cell
def _(pl, top10):
    pl.DataFrame(
        {
            "top10_mit_hoechstens_2_min": [top10.filter(pl.col("soll_min") <= 2).height],
            "erwartung": [">= 5"],
        }
    )
    return


if __name__ == "__main__":
    app.run()
