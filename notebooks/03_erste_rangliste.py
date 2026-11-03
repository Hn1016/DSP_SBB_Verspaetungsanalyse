import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from sbb_delays import quality
    from sbb_delays.download import latest_service_points

    con = quality.connect()
    return con, latest_service_points, mo, quality


@app.cell
def _(mo):
    mo.md("""
    # Erste Rangliste — Kanton Zürich, Mo 7.9. bis So 13.9.2026

    Issue #14. Hypothese und Regeln stehen im Projektlog (Eintrag vom 1.11.2026, vor der Analyse
    notiert): Abschnitte je Richtung, beide Halte im Kanton Zürich und gemessen (`REAL`);
    Haltverspätung nur bei Soll-Haltezeit ab 1 Minute; mindestens 20 gemessene Fahrten je Zeile.
    """)
    return


@app.cell
def _(con, latest_service_points, quality):
    WEEK = "BETRIEBSTAG between date '2026-09-07' and date '2026-09-13'"
    MIN_TRIPS = 20

    # Canton is not in the shared service_points view, so it is read here from the same snapshot.
    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{latest_service_points()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    quality.delays(con).filter(WEEK).create_view("week", replace=True)

    # Neighbours over the whole trip (all rows, incl. foreign and cancelled stops), so a pair
    # across a cancelled stop or a stretch outside the canton cannot form a section.
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
               a.LINIEN_TEXT as line, a.DURCHFAHRT_TF or b.DURCHFAHRT_TF as pass_through
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
def _(MIN_TRIPS, con):
    section_ranking = con.sql(
        f"""
        select za.name || ' → ' || zb.name as abschnitt,
               count(*) as fahrten,
               round(avg(section_delay), 2) as mittel_min,
               round(median(section_delay), 2) as median_min,
               rank() over (order by avg(section_delay) desc) as rang
        from sections
        join zh za on za.BPUIC = a_id
        join zh zb on zb.BPUIC = b_id
        group by all
        having count(*) >= {MIN_TRIPS}
        order by rang
        """
    ).pl()
    section_ranking.head(10)
    return (section_ranking,)


@app.cell
def _(MIN_TRIPS, con):
    stop_ranking = con.sql(
        f"""
        select z.name as halt,
               count(*) as fahrten,
               round(avg(ab_delay - an_delay), 2) as mittel_min,
               round(median(ab_delay - an_delay), 2) as median_min,
               rank() over (order by avg(ab_delay - an_delay) desc) as rang
        from week
        join zh z using (BPUIC)
        where an_delay is not null and ab_delay is not null
          and epoch(ABFAHRTSZEIT - ANKUNFTSZEIT) / 60 >= 1
        group by all
        having count(*) >= {MIN_TRIPS}
        order by rang
        """
    ).pl()
    stop_ranking.head(10)
    return (stop_ranking,)


@app.cell
def _(mo):
    mo.md("""
    ## Erwartung gegen Befund

    Wo stehen die erwarteten Einträge, und aus wie vielen Zeilen besteht jede Rangliste?
    """)
    return


@app.cell
def _(section_ranking, stop_ranking):
    import polars as pl

    pl.concat(
        [
            section_ranking.filter(pl.col("abschnitt") == "Zürich Hardbrücke → Zürich HB")
            .select(pl.col("abschnitt").alias("eintrag"), "fahrten", "mittel_min", "rang")
            .with_columns(von=pl.lit(section_ranking.height)),
            stop_ranking.filter(pl.col("halt") == "Zürich HB")
            .select(pl.col("halt").alias("eintrag"), "fahrten", "mittel_min", "rang")
            .with_columns(von=pl.lit(stop_ranking.height)),
        ]
    )
    return


@app.cell
def _(con):
    # Size of the base: section passages, distinct sections, total section delay.
    con.sql(
        """
        select count(*) as abschnitte_je_fahrt,
               count(distinct (a_id, b_id)) as abschnitte,
               round(sum(section_delay), 1) as summe_min
        from sections
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Prüfungen aus dem Review (PR #17)

    Durchfahrten stehen als Zeilen in `rail` und können Halt A oder B eines Abschnitts sein.
    Wie viele Abschnittsfahrten betrifft das, und ändern sich die Top 10 ohne sie?
    """)
    return


@app.cell
def _(MIN_TRIPS, con):
    con.sql(
        f"""
        with g as (
            select a_id, b_id,
                   avg(section_delay) as with_pt,
                   avg(section_delay) filter (where not pass_through) as without_pt
            from sections
            group by all
            having count(*) >= {MIN_TRIPS}
        )
        select (select count(*) filter (where pass_through) from sections) as mit_durchfahrt,
               (select count(*) from sections) as alle,
               round(max(abs(with_pt - without_pt)), 3) as max_diff_min,
               list((a_id, b_id) order by with_pt desc)[1:10]
                 = list((a_id, b_id) order by without_pt desc)[1:10] as top10_gleich
        from g
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    Welche Linien fahren die Abschnitte mit wenigen Fahrten in den Top 10?
    """)
    return


@app.cell
def _(con, section_ranking):
    import polars as _pl

    _few = section_ranking.head(10).filter(_pl.col("fahrten") < 50)["abschnitt"].to_list()
    con.sql(
        """
        select za.name || ' → ' || zb.name as abschnitt, line as linie, count(*) as fahrten
        from sections
        join zh za on za.BPUIC = a_id
        join zh zb on zb.BPUIC = b_id
        group by all
        """
    ).pl().filter(_pl.col("abschnitt").is_in(_few))
    return


if __name__ == "__main__":
    app.run()
