import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl

    from sbb_delays import quality
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.period import END, START
    from sbb_delays.sections import period_days

    con = quality.connect()
    return END, START, con, mo, period_days, pl, quality, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Referenzwert je Soll-Haltezeit für die Haltverspätung (A8)

    Issue #46. Regeln und Erwartungen im Projektlog (Entscheidung und Hypothese vom 15.11.2026,
    Commit `2542ce5`, vor dem Rechnen gepusht):

    - **(a)** Ungekappte Klassenmittel: Klasse 0 zwischen 0.5 und 0.8 min, Klassen 1 und 2 je
      zwischen 0.2 und 0.5 min.
    - **(b)** Top 10 nach dem Mittel pro Fahrt: roh haben mindestens 7 Halte überwiegend
      Soll-Haltezeit 0, mit Referenzwert höchstens 5; höchstens 5 Halte stehen in beiden Top 10.
    - **(c)** Das Mittel der Haltverspätung mit gekappter Ankunft ist höchstens 0.2 min kleiner
      als ohne Kappen.

    Basis: Halteereignisse aus `quality.delays()` an Halten im Kanton Zürich, Zeitraum aus
    `period.py`, Ankunft und Abfahrt `REAL`, ohne Durchfahrten (`DURCHFAHRT_TF`).

    Haltverspätung = Abfahrtsverspätung − max(Ankunftsverspätung, 0) (gekappt); «ungekappt» ist
    Abfahrtsverspätung − Ankunftsverspätung. Klassen der Soll-Haltezeit: 0, 1, 2, 3+ Minuten.
    Referenzwert: Mittel der gekappten Haltverspätung der Klasse über alle Halteereignisse der
    Basis.
    """)
    return


@app.cell
def _(END, START, con, period_days, quality, service_points_snapshot):
    MIN_TRIPS, MIN_DAYS = 100, 30  # log 2026-11-10, «Systematisch» (issue #32)

    _first, _last = period_days(START, END)
    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    quality.delays(con).create_view("cleaned", replace=True)  # the cleaning rules live there
    # One row per stop event of a trip that has a scheduled arrival and a scheduled departure.
    con.execute(
        f"""
        create or replace table candidates as
        select BETRIEBSTAG, BPUIC, DURCHFAHRT_TF, an_delay, ab_delay,
               datediff('minute', ANKUNFTSZEIT, ABFAHRTSZEIT) as soll_halt_min
        from cleaned
        where BETRIEBSTAG between date '{_first}' and date '{_last}'
          and BPUIC in (select BPUIC from zh)
          and ANKUNFTSZEIT is not null and ABFAHRTSZEIT is not null
        """
    )
    con.execute(
        """
        create or replace table events as
        select BETRIEBSTAG, BPUIC, soll_halt_min, an_delay, ab_delay,
               case when soll_halt_min >= 3 then '3+' else soll_halt_min::varchar end as klasse,
               ab_delay - an_delay as halt_ungekappt,
               ab_delay - greatest(an_delay, 0) as halt
        from candidates
        where not DURCHFAHRT_TF and an_delay is not null and ab_delay is not null
          and soll_halt_min >= 0
        """
    )
    con.execute(
        """
        create or replace view class_means as
        select klasse, avg(halt) as referenz from events group by klasse
        """
    )
    return MIN_DAYS, MIN_TRIPS


@app.cell
def _(mo):
    mo.md("""
    ## Basis

    Von den Zürcher Halteereignissen mit Soll-Ankunft und Soll-Abfahrt zu den Halteereignissen
    der Auswertung. Die Schritte gelten nacheinander.
    """)
    return


@app.cell
def _(con):
    con.sql(
        """
        select count(*) as mit_soll_ankunft_und_abfahrt,
               count(*) filter (DURCHFAHRT_TF) as durchfahrten,
               count(*) filter (not DURCHFAHRT_TF and (an_delay is null or ab_delay is null))
                   as nicht_beide_real,
               count(*) filter (not DURCHFAHRT_TF and an_delay is not null
                                and ab_delay is not null and soll_halt_min < 0)
                   as soll_abfahrt_vor_ankunft,
               (select count(*) from events) as halteereignisse,
               (select count(distinct BPUIC) from events) as halte,
               (select count(distinct BETRIEBSTAG) from events) as betriebstage
        from candidates
        """
    ).pl()
    return


@app.cell
def _(mo):
    mo.md("""
    ## Klassenmittel der Soll-Haltezeit und frühe Ankünfte

    Mittel in Minuten. `frueh_pct`: Anteil der Halteereignisse mit Ankunftsverspätung unter 0.
    `kappen_diff` = ungekappt − gekappt. Die Zeile «alle» ist die Basis für (c).
    """)
    return


@app.cell
def _(con):
    classes = con.sql(
        """
        select coalesce(klasse, 'alle') as klasse,
               count(*) as halteereignisse,
               round(100 * count(*) / (select count(*) from events), 1) as anteil_pct,
               avg(halt_ungekappt) as mittel_ungekappt,
               avg(halt) as mittel_gekappt,
               avg(halt_ungekappt) - avg(halt) as kappen_diff,
               median(halt_ungekappt) as median_ungekappt,
               median(halt) as median_gekappt,
               round(100 * avg((an_delay < 0)::int), 1) as frueh_pct,
               avg(an_delay) filter (an_delay < 0) as mittel_fruehe_ankunft
        from events
        group by rollup (klasse)
        order by grouping(klasse), klasse
        """
    ).pl()
    classes.head(5)
    return (classes,)


@app.cell
def _(MIN_DAYS, MIN_TRIPS, con):
    ranking = con.sql(
        f"""
        select z.name as halt,
               count(*) as fahrten,
               count(distinct e.BETRIEBSTAG) as tage,
               mode(e.klasse) as klasse,
               round(100 * avg((e.klasse = '0')::int), 1) as klasse0_pct,
               round(avg(e.halt), 2) as mittel_roh,
               round(avg(e.halt - c.referenz), 2) as mittel_referenz,
               round(sum(e.halt)) as zuwachs_roh,
               round(sum(e.halt - c.referenz)) as zuwachs_referenz,
               rank() over (order by avg(e.halt) desc) as rang_mittel_roh,
               rank() over (order by avg(e.halt - c.referenz) desc) as rang_mittel_referenz,
               rank() over (order by sum(e.halt) desc) as rang_roh,
               rank() over (order by sum(e.halt - c.referenz) desc) as rang_referenz
        from events e
        join class_means c using (klasse)
        join zh z using (BPUIC)
        group by e.BPUIC, z.name
        having count(*) >= {MIN_TRIPS} and count(distinct e.BETRIEBSTAG) >= {MIN_DAYS}
        """
    ).pl()
    return (ranking,)


@app.cell
def _(pl):
    def side_by_side(ranking, rank_raw, rank_ref, value_raw, value_ref):
        """Top 10 by rank_raw (left) next to the top 10 by rank_ref (right)."""
        columns = ["halt", "klasse", "klasse0_pct", "fahrten"]
        raw = ranking.filter(pl.col(rank_raw) <= 10).sort(rank_raw)
        ref = ranking.filter(pl.col(rank_ref) <= 10).sort(rank_ref)
        table = pl.concat(
            [
                raw.select(pl.col(rank_raw).alias("rang"), *columns, *value_raw).rename(
                    {c: f"{c} (roh)" for c in columns}
                ),
                ref.select(*columns, *value_ref).rename({c: f"{c} (ref)" for c in columns}),
            ],
            how="horizontal_extend",
        )
        return raw, ref, table

    return (side_by_side,)


@app.cell
def _(mo, ranking):
    mo.md(f"""
    ## Beide Top 10 nach dem Mittel pro Fahrt

    {ranking.height} Halte mit mindestens 100 Halteereignissen an mindestens 30 Betriebstagen,
    beide Richtungen zusammen. Links roh, rechts mit Referenzwert; beide mit gekappter Ankunft.
    `klasse`: häufigste Klasse der Soll-Haltezeit des Halts; `klasse0_pct`: Anteil seiner
    Halteereignisse in Klasse 0. Das ist die Grösse, für die Erwartung (b) geschrieben wurde.
    """)
    return


@app.cell
def _(ranking, side_by_side):
    top_mean_raw, top_mean_ref, _table = side_by_side(
        ranking, "rang_mittel_roh", "rang_mittel_referenz", ["mittel_roh"], ["mittel_referenz"]
    )
    _table.head(10)
    return top_mean_raw, top_mean_ref


@app.cell
def _(mo):
    mo.md("""
    ## Beide Top 10 nach der Hauptkennzahl (Mittel × Fahrten)

    Dieselbe Basis und Mindestzahl, Rang nach Minuten Zuwachs im Zeitraum. Ohne eigene Erwartung
    (Lehre aus Issue #23: Die Verzerrung betrifft das Mittel pro Fahrt).
    """)
    return


@app.cell
def _(ranking, side_by_side):
    top_raw, top_ref, _table = side_by_side(
        ranking,
        "rang_roh",
        "rang_referenz",
        ["mittel_roh", "zuwachs_roh"],
        ["mittel_referenz", "zuwachs_referenz"],
    )
    _table.head(10)
    return top_raw, top_ref


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (a) bis (c)

    Die Zeilen mit Erwartung «ohne» zeigen dieselben Zählungen für die Top 10 nach der
    Hauptkennzahl und, als Vergleich für (b), den Anteil aller Halte der Rangliste, die überwiegend
    Soll-Haltezeit 0 haben. Der Vergleich kam nach dem ersten Lauf dazu (Log, Befund zu Issue #46).
    """)
    return


@app.cell
def _(classes, pl, ranking, top_mean_raw, top_mean_ref, top_raw, top_ref):
    def _mean(klasse, column):
        return classes.filter(pl.col("klasse") == klasse)[column].item()

    def _mostly_zero(top):
        return top.filter(pl.col("klasse0_pct") > 50).height

    def _both(raw, ref):
        return len(set(raw["halt"]) & set(ref["halt"]))

    _a = [(k, _mean(k, "mittel_ungekappt"), lo, hi) for k, lo, hi in
          [("0", 0.5, 0.8), ("1", 0.2, 0.5), ("2", 0.2, 0.5)]]  # fmt: skip
    _c = _mean("alle", "kappen_diff")
    _rows = [
        (f"(a) Klasse {k}, ungekappt (min)", round(v, 3), f"{lo} bis {hi}", lo <= v <= hi)
        for k, v, lo, hi in _a
    ] + [
        ("(b) roh: überwiegend Klasse 0", _mostly_zero(top_mean_raw), "≥ 7",
         _mostly_zero(top_mean_raw) >= 7),
        ("(b) Referenz: überwiegend Klasse 0", _mostly_zero(top_mean_ref), "≤ 5",
         _mostly_zero(top_mean_ref) <= 5),
        ("(b) in beiden Top 10", _both(top_mean_raw, top_mean_ref), "≤ 5",
         _both(top_mean_raw, top_mean_ref) <= 5),
        ("(c) ungekappt − gekappt, alle (min)", round(_c, 3), "≤ 0.2", _c <= 0.2),
        ("Hauptkennzahl, roh: überwiegend Klasse 0", _mostly_zero(top_raw), "ohne", None),
        ("Hauptkennzahl, Referenz: überwiegend Klasse 0", _mostly_zero(top_ref), "ohne", None),
        ("Hauptkennzahl: in beiden Top 10", _both(top_raw, top_ref), "ohne", None),
        ("Vergleich: alle Halte, überwiegend Klasse 0 (%)",
         round(100 * _mostly_zero(ranking) / ranking.height, 1), "ohne", None),
    ]  # fmt: skip
    pl.DataFrame(_rows, schema=["pruefung", "ergebnis", "erwartung", "gehalten"], orient="row")
    return


if __name__ == "__main__":
    app.run()
