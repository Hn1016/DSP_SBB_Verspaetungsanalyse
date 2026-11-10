import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo
    import polars as pl

    from sbb_delays import build
    from sbb_delays.download import service_points_snapshot

    con = duckdb.connect()
    return build, con, mo, pl, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Rangliste der Abschnitte mit Referenzwert je Soll-Fahrzeit

    Issue #23. Erwartung und Regeln im Projektlog (Hypothese vom 10.11.2026, Commit `f9e690f`, und
    Nachtrag vor dem zweiten Lauf, Commit `0563070`):

    - **(a)** In der rohen Top 10 haben mindestens 4 Abschnitte eine Soll-Fahrzeit von höchstens
      2 Minuten, in der Top 10 mit Referenzwert höchstens 2.
    - **(b)** Höchstens 5 der Abschnitte aus der rohen Top 10 stehen auch in der Top 10 mit
      Referenzwert.

    Basis: Abschnittsfahrten aus `uv run build` für den Zeitraum in `period.py`, beide Halte im
    Kanton Zürich. Referenzwert: Mittel der Klasse der Soll-Fahrzeit (0, 1, 2, 3, 4, 5+ Minuten)
    über alle Zürcher Abschnittsfahrten desselben Zeitraums.

    Regeln aus Issue #32: mindestens 100 gemessene Fahrten und 30 Betriebstage mit Messung; Rang
    nach der Hauptkennzahl Minuten Zuwachs im Zeitraum (Mittel × Fahrten), das Mittel pro Fahrt
    als Begleitspalte.
    """)
    return


@app.cell
def _(build, con, service_points_snapshot):
    MIN_TRIPS, MIN_DAYS = 100, 30  # log 2026-11-10, «Systematisch» (issue #32)

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
        create or replace view zh_sections as
        select *, case when scheduled_min >= 5 then '5+' else scheduled_min::varchar end as klasse
        from read_parquet('{build.sections_parquet()}')
        where a_id in (select BPUIC from zh) and b_id in (select BPUIC from zh)
        """
    )
    con.execute(
        """
        create or replace view class_means as
        select klasse, count(*) as fahrten, avg(section_delay) as mittel,
               median(section_delay) as median
        from zh_sections group by klasse
        """
    )
    return MIN_DAYS, MIN_TRIPS


@app.cell
def _(mo):
    mo.md("""
    ## Klassenmittel der Soll-Fahrzeit

    Zum Vergleich die Werte aus #18 (eine Woche, 7. bis 13.9.2026, Log 2026-11-05).
    """)
    return


@app.cell
def _(con, pl):
    week_18 = pl.DataFrame(
        {
            "klasse": ["1", "2", "3", "4", "5+"],
            "mittel_18": [0.24, -0.11, -0.53, -0.71, -0.79],
        }
    )
    classes = (
        con.sql(
            """
            select klasse, fahrten, round(mittel, 2) as mittel, round(median, 2) as median
            from class_means
            """
        )
        .pl()
        .join(week_18, on="klasse", how="left")
        .sort(pl.col("klasse").str.replace(r"\+", "").cast(pl.Int32))
    )
    classes.head(6)
    return


@app.cell
def _(MIN_DAYS, MIN_TRIPS, con):
    ranking = con.sql(
        f"""
        select a.name || ' → ' || b.name as abschnitt,
               count(*) as fahrten,
               count(distinct s.BETRIEBSTAG) as tage,
               median(s.scheduled_min) as soll_min,
               round(avg(s.section_delay), 2) as mittel_roh,
               round(avg(s.section_delay - c.mittel), 2) as mittel_referenz,
               round(sum(s.section_delay)) as zuwachs_roh,
               round(sum(s.section_delay - c.mittel)) as zuwachs_referenz,
               rank() over (order by sum(s.section_delay) desc) as rang_roh,
               rank() over (order by sum(s.section_delay - c.mittel) desc) as rang_referenz,
               rank() over (order by avg(s.section_delay) desc) as rang_mittel_roh,
               rank() over (order by avg(s.section_delay - c.mittel) desc)
                   as rang_mittel_referenz
        from zh_sections s
        join class_means c using (klasse)
        join zh a on a.BPUIC = s.a_id
        join zh b on b.BPUIC = s.b_id
        group by s.a_id, s.b_id, a.name, b.name
        having count(*) >= {MIN_TRIPS} and count(distinct s.BETRIEBSTAG) >= {MIN_DAYS}
        """
    ).pl()
    return (ranking,)


@app.cell
def _(mo, ranking):
    mo.md(f"""
    ## Beide Top 10

    {ranking.height} Abschnitte mit mindestens 100 Fahrten und 30 Betriebstagen. Links roh, rechts
    mit Referenzwert, je nach Minuten Zuwachs im Zeitraum (Mittel × Fahrten); Soll-Fahrzeit als
    Median über die Fahrten des Abschnitts, Mittel in Minuten pro Fahrt.
    """)
    return


@app.cell
def _(pl, ranking):
    _columns = ["abschnitt", "fahrten", "soll_min"]
    top_raw = ranking.filter(pl.col("rang_roh") <= 10).sort("rang_roh")
    top_ref = ranking.filter(pl.col("rang_referenz") <= 10).sort("rang_referenz")
    side_by_side = pl.concat(
        [
            top_raw.select(
                pl.col("rang_roh").alias("rang"), *_columns, "mittel_roh", "zuwachs_roh"
            ).rename({c: f"{c} (roh)" for c in _columns}),
            top_ref.select(*_columns, "mittel_referenz", "zuwachs_referenz").rename(
                {c: f"{c} (ref)" for c in _columns}
            ),
        ],
        how="horizontal_extend",
    )
    side_by_side.head(10)
    return top_raw, top_ref


@app.cell
def _(mo):
    mo.md("""
    ## Anteil der Top 10 am positiven Zuwachs

    Total = Summe über alle Abschnitte mit positivem Mittel (Issue #32, «Positiver Zuwachs»).
    """)
    return


@app.cell
def _(pl, ranking, top_raw, top_ref):
    _total_raw = ranking.filter(pl.col("zuwachs_roh") > 0)["zuwachs_roh"].sum()
    _total_ref = ranking.filter(pl.col("zuwachs_referenz") > 0)["zuwachs_referenz"].sum()
    pl.DataFrame(
        {
            "rangliste": ["roh", "mit Referenzwert"],
            "abschnitte_positiv": [
                ranking.filter(pl.col("zuwachs_roh") > 0).height,
                ranking.filter(pl.col("zuwachs_referenz") > 0).height,
            ],
            "total_min": [_total_raw, _total_ref],
            "top10_min": [top_raw["zuwachs_roh"].sum(), top_ref["zuwachs_referenz"].sum()],
            "top10_anteil_pct": [
                round(100 * top_raw["zuwachs_roh"].sum() / _total_raw, 1),
                round(100 * top_ref["zuwachs_referenz"].sum() / _total_ref, 1),
            ],
        }
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Beide Top 10 nach dem Mittel pro Fahrt (Review PR #37)

    Dieselbe Basis und Mindestzahl, Rang nach dem Mittel pro Fahrt statt nach Mittel × Fahrten:
    die Grösse, für die die Erwartungen (a) und (b) geschrieben wurden (zweiter Nachtrag im Log,
    Commit `eb5b77f`, vor dem Rechnen gepusht).
    """)
    return


@app.cell
def _(pl, ranking):
    _columns = ["abschnitt", "fahrten", "soll_min"]
    top_mean_raw = ranking.filter(pl.col("rang_mittel_roh") <= 10).sort("rang_mittel_roh")
    top_mean_ref = ranking.filter(pl.col("rang_mittel_referenz") <= 10).sort("rang_mittel_referenz")
    pl.concat(
        [
            top_mean_raw.select(
                pl.col("rang_mittel_roh").alias("rang"), *_columns, "mittel_roh"
            ).rename({c: f"{c} (roh)" for c in _columns}),
            top_mean_ref.select(*_columns, "mittel_referenz").rename(
                {c: f"{c} (ref)" for c in _columns}
            ),
        ],
        how="horizontal_extend",
    )
    return top_mean_raw, top_mean_ref


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (a) und (b)
    """)
    return


@app.cell
def _(pl, top_mean_raw, top_mean_ref, top_raw, top_ref):
    def _check(name, raw, ref):
        short_raw = raw.filter(pl.col("soll_min") <= 2).height
        short_ref = ref.filter(pl.col("soll_min") <= 2).height
        both = len(set(raw["abschnitt"]) & set(ref["abschnitt"]))
        return pl.DataFrame(
            {
                "rang_nach": [name] * 3,
                "pruefung": [
                    "(a) roh: Soll-Fahrzeit ≤ 2 min",
                    "(a) Referenz: Soll-Fahrzeit ≤ 2 min",
                    "(b) in beiden Top 10",
                ],
                "ergebnis": [short_raw, short_ref, both],
                "erwartung": ["≥ 4", "≤ 2", "≤ 5"],
                "gehalten": [short_raw >= 4, short_ref <= 2, both <= 5],
            }
        )

    pl.concat(
        [
            _check("Mittel pro Fahrt", top_mean_raw, top_mean_ref),
            _check("Mittel × Fahrten", top_raw, top_ref),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
