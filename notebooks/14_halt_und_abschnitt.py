import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl

    from sbb_delays import build, quality, ranking
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.period import END, START
    from sbb_delays.sections import period_days

    con = quality.connect()
    return (
        END,
        START,
        build,
        con,
        mo,
        period_days,
        pl,
        quality,
        ranking,
        service_points_snapshot,
    )


@app.cell
def _(mo):
    mo.md("""
    # Halt und folgender Abschnitt: wird dieselbe Minute doppelt gezählt?

    Issue #55. Entscheide und Erwartungen im Projektlog (Entscheidung und Hypothese vom
    22.11.2026, Commit `a7dbbc6`, vor dem Rechnen gepusht):

    - **(a)** Spearman zwischen Wert am Halt und Wert der Abschnitte danach ≤ −0.4.
    - **(b)** Mindestens 7 der Top 10 Halte (Zuwachs mit Referenzwert) haben einen negativen
      Wert auf den Abschnitten danach.
    - **(c)** Mindestens 6 der 10 grössten Absorber der Abschnitte beginnen an einem Halt mit
      positivem Wert am Halt.

    **Wert am Halt:** wie `notebooks/12_referenzwert_halte.py` (Issue #46), Zuwachs = Mittel nach
    Referenzwert je Soll-Haltezeit × Fahrten. **Wert der Abschnitte danach:** Summe des Zuwachses
    der Zürcher Abschnitte mit Wert ab dem Halt, Ranglisten-Datei, Fenster «ganzer Zeitraum».
    **Gemeinsame Einheit «Abschnitt mit Halt am Ende»:** Abfahrtsverspätung an B −
    Abfahrtsverspätung an A, Referenzwert je Soll-Zeit Abfahrt A bis Abfahrt B (0 … 5+ min),
    bewertet mit `ranking.class_means()` und `ranking.ranking()`.
    """)
    return


@app.cell
def _(END, START, con, period_days, quality, service_points_snapshot):
    MIN_TRIPS, MIN_DAYS = 100, 30  # as in notebooks/12 (log 2026-11-10, «Systematisch»)

    _first, _last = period_days(START, END)
    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    quality.delays(con).create_view("cleaned", replace=True)
    # Value at the stop: the SQL of notebooks/12_referenzwert_halte.py, unchanged.
    con.execute(
        f"""
        create or replace table events as
        select BETRIEBSTAG, BPUIC, an_delay, ab_delay,
               case when soll_halt_min >= 3 then '3+' else soll_halt_min::varchar end as klasse,
               ab_delay - greatest(an_delay, 0) as halt
        from (
            select *, datediff('minute', ANKUNFTSZEIT, ABFAHRTSZEIT) as soll_halt_min
            from cleaned
            where BETRIEBSTAG between date '{_first}' and date '{_last}'
              and BPUIC in (select BPUIC from zh)
              and ANKUNFTSZEIT is not null and ABFAHRTSZEIT is not null
        )
        where not DURCHFAHRT_TF and an_delay is not null and ab_delay is not null
          and soll_halt_min >= 0
        """
    )
    stops = con.sql(
        f"""
        with class_means as (select klasse, avg(halt) as referenz from events group by klasse)
        select e.BPUIC as a_id, z.name as halt,
               count(*) as fahrten_halt,
               round(100 * avg((e.klasse = '0')::int), 1) as klasse0_pct,
               avg(e.halt) as mittel_halt_roh,
               avg(e.halt - c.referenz) as mittel_halt_ref,
               sum(e.halt) as zuwachs_halt_roh,
               sum(e.halt - c.referenz) as zuwachs_halt,
               rank() over (order by sum(e.halt - c.referenz) desc) as rang_halt
        from events e join class_means c using (klasse) join zh z using (BPUIC)
        group by e.BPUIC, z.name
        having count(*) >= {MIN_TRIPS} and count(distinct e.BETRIEBSTAG) >= {MIN_DAYS}
        """
    ).pl()
    return (stops,)


@app.cell
def _(build, con, pl):
    sections = con.sql(
        f"""
        select r.*, a.name as halt_a, b.name as halt_b, a.name || ' → ' || b.name as abschnitt
        from read_parquet('{build.ranking_parquet()}') r
        join zh a on a.BPUIC = r.a_id
        join zh b on b.BPUIC = r.b_id
        where r.fenster = 'ganzer Zeitraum'
        """
    ).pl()
    after = sections.group_by("a_id").agg(
        zuwachs_danach=pl.col("zuwachs").filter(pl.col("grund").is_null()).sum(),
        zuwachs_danach_roh=(pl.col("mittel_roh") * pl.col("fahrten"))
        .filter(pl.col("grund").is_null())
        .sum(),
        fahrten_danach=pl.col("fahrten").filter(pl.col("grund").is_null()).sum(),
        abschnitte_mit_wert=pl.col("grund").is_null().sum(),
        abschnitte_ohne_wert=pl.col("grund").is_not_null().sum(),
    )
    return after, sections


@app.cell
def _(after, pl, stops):
    # Stops with a value at the stop; zuwachs_danach is null where no section with a value starts.
    compare = (
        stops.join(after, on="a_id", how="left")
        .with_columns(
            pl.when(pl.col("abschnitte_mit_wert") > 0).then(pl.col("zuwachs_danach")),
            pl.when(pl.col("abschnitte_mit_wert") > 0).then(pl.col("zuwachs_danach_roh")),
        )
        .sort("rang_halt")
    )
    return (compare,)


@app.cell
def _(mo):
    mo.md("""
    ## Gemeinsame Einheit «Abschnitt mit Halt am Ende»

    Zürcher Abschnittsfahrten aus der Abschnittsdatei, an B die Abfahrt aus `quality.delays()`
    (gleiche Zeile). Die Schritte gelten nacheinander. Eine Durchfahrt an B bleibt drin
    (Präzisierung 1).
    """)
    return


@app.cell
def _(build, con, ranking):
    ranking.zurich_sections(con, build.sections_parquet()).create_view("zsec", replace=True)
    con.execute(
        """
        create or replace table units_all as
        select s.a_id, s.b_id, s.BETRIEBSTAG, s.abfahrt_a, s.ab_delay_a,
               b.ABFAHRTSZEIT as abfahrt_b, b.ab_delay as ab_delay_b,
               b.DURCHFAHRT_TF as durchfahrt_b
        from zsec s
        join cleaned b on b.BETRIEBSTAG = s.BETRIEBSTAG and b.ZEILE = s.zeile_b
        """
    )
    con.execute(
        """
        create or replace view units as
        select a_id, b_id, BETRIEBSTAG, abfahrt_a,
               ab_delay_b - ab_delay_a as section_delay,
               datediff('minute', abfahrt_a, abfahrt_b) as scheduled_min
        from units_all
        where abfahrt_b is not null and ab_delay_b is not null and abfahrt_b >= abfahrt_a
        """
    )
    con.sql(
        """
        select count(*) as abschnittsfahrten,
               count(*) filter (abfahrt_b is null) as endet_in_b,
               count(*) filter (abfahrt_b is not null and ab_delay_b is null)
                   as abfahrt_b_nicht_real,
               count(*) filter (ab_delay_b is not null and abfahrt_b < abfahrt_a)
                   as soll_abfahrt_b_vor_a,
               (select count(*) from units) as einheiten,
               count(*) filter (durchfahrt_b and abfahrt_b is not null and ab_delay_b is not null)
                   as davon_durchfahrt_b
        from units_all
        """
    ).pl()
    return


@app.cell
def _(con, pl, ranking):
    _rel = con.view("units")
    unit_means = ranking.class_means(_rel)
    unit_ranking = (
        ranking.ranking(_rel, unit_means)
        .filter(pl.col("fenster") == "ganzer Zeitraum")
        .join(con.sql("select BPUIC as a_id, name as halt_a from zh").pl(), on="a_id", how="left")
        .join(con.sql("select BPUIC as b_id, name as halt_b from zh").pl(), on="b_id", how="left")
        .with_columns(abschnitt=pl.col("halt_a") + " → " + pl.col("halt_b"))
    )
    con.sql(
        """
        select case when scheduled_min >= 5 then '5+' else scheduled_min::varchar end
                   as klasse_soll_min,
               count(*) as einheiten
        from units group by 1
        """
    ).pl().join(
        pl.DataFrame(
            {"klasse_soll_min": list(unit_means), "referenz_min": list(unit_means.values())}
        ),
        on="klasse_soll_min",
    ).sort("klasse_soll_min")
    return (unit_ranking,)


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (a) bis (c)

    (b): Ein Halt der Top 10 ohne Abschnitt mit Wert danach zählt als «nicht negativ»; (c): ein
    Absorber, dessen Halt A keinen Wert am Halt hat, zählt als «nicht positiv» (Präzisierung 3).
    """)
    return


@app.cell
def _(compare, pl, sections, stops):
    _both = compare.filter(pl.col("zuwachs_danach").is_not_null())
    spearman = _both.select(pl.corr("zuwachs_halt", "zuwachs_danach", method="spearman")).item()
    top_stops = compare.filter(pl.col("rang_halt") <= 10)
    _b = top_stops.filter(pl.col("zuwachs_danach") < 0).height
    top_absorbers = (
        sections.filter(pl.col("klasse") == "Absorber")
        .sort("zuwachs")
        .head(10)
        .join(stops.select("a_id", "zuwachs_halt", "rang_halt"), on="a_id", how="left")
    )
    _c = top_absorbers.filter(pl.col("zuwachs_halt") > 0).height
    _rows = [
        ("(a) Spearman", round(spearman, 3), "≤ −0.4", spearman <= -0.4),
        ("(b) Top 10 Halte mit negativem Wert danach", _b, "≥ 7", _b >= 7),
        ("(c) Top 10 Absorber mit positivem Wert am Halt A", _c, "≥ 6", _c >= 6),
        ("Halte mit beiden Werten", _both.height, "ohne", None),
        ("Halte mit Wert am Halt, ohne Abschnitt mit Wert danach",
         compare.height - _both.height, "ohne", None),
        ("Top 10 Halte ohne Abschnitt mit Wert danach",
         top_stops.filter(pl.col("zuwachs_danach").is_null()).height, "ohne", None),
        ("Top 10 Absorber ohne Wert am Halt A",
         top_absorbers.filter(pl.col("zuwachs_halt").is_null()).height, "ohne", None),
        # added after the first run (log, finding on issue #55): base rates and per trip
        ("nachträglich: alle Halte mit negativem Wert danach (%)",
         round(100 * _both.filter(pl.col("zuwachs_danach") < 0).height / _both.height, 1),
         "ohne", None),
        ("nachträglich: alle Halte mit positivem Wert am Halt (%)",
         round(100 * stops.filter(pl.col("zuwachs_halt") > 0).height / stops.height, 1),
         "ohne", None),
        ("nachträglich: Spearman pro Fahrt (Mittel am Halt, Mittel danach)",
         round(_both.select(pl.corr(
             "mittel_halt_ref", pl.col("zuwachs_danach") / pl.col("fahrten_danach"),
             method="spearman")).item(), 3), "ohne", None),
        ("nachträglich: Spearman Zuwachs am Halt, Fahrten danach",
         round(_both.select(pl.corr("zuwachs_halt", "fahrten_danach", method="spearman"))
               .item(), 3), "ohne", None),
    ]  # fmt: skip
    pl.DataFrame(_rows, schema=["pruefung", "ergebnis", "erwartung", "gehalten"], orient="row")
    return top_absorbers, top_stops


@app.cell
def _(pl, top_stops):
    top_stops.select(
        "rang_halt",
        "halt",
        "klasse0_pct",
        "fahrten_halt",
        pl.col("mittel_halt_ref").round(2),
        pl.col("zuwachs_halt").round(),
        pl.col("zuwachs_danach").round(),
        "abschnitte_mit_wert",
        "abschnitte_ohne_wert",
    )
    return


@app.cell
def _(pl, top_absorbers):
    top_absorbers.select(
        "abschnitt",
        "fahrten",
        pl.col("mittel_referenz").round(2),
        pl.col("zuwachs").round(),
        pl.col("zuwachs_halt").round().alias("zuwachs_halt_a"),
        pl.col("rang_halt").alias("rang_halt_a"),
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Beschreibend: Top 10 der gemeinsamen Einheit und der Verstärker-Abschnitte

    Beide nach Zuwachs, nur Verstärker (Intervall über die Tagesmittel über 0, Tagesmittel
    mindestens 0.25 min). `in_beiden`: dasselbe Haltepaar steht in beiden Top 10.
    """)
    return


@app.cell
def _(pl, sections, unit_ranking):
    def _top(table):
        return (
            table.filter(pl.col("klasse") == "Verstärker")
            .sort("zuwachs", descending=True)
            .head(10)
            .with_row_index("top", offset=1)
        )

    top_units, top_sections = _top(unit_ranking), _top(sections)
    _shared = set(zip(top_units["a_id"], top_units["b_id"], strict=True)) & set(
        zip(top_sections["a_id"], top_sections["b_id"], strict=True)
    )

    def _show(top):
        return top.select(
            "top",
            "abschnitt",
            "fahrten",
            pl.col("mittel_referenz").round(2),
            pl.col("zuwachs").round(),
            pl.struct("a_id", "b_id")
            .map_elements(lambda r: (r["a_id"], r["b_id"]) in _shared, return_dtype=pl.Boolean)
            .alias("in_beiden"),
        )

    pl.concat(
        [
            _show(top_units).rename(lambda c: f"{c} (Einheit)"),
            _show(top_sections).drop("top").rename(lambda c: f"{c} (Abschnitt)"),
        ],
        how="horizontal_extend",
    )
    return


@app.cell
def _(pl, unit_ranking):
    unit_ranking.group_by(pl.col("klasse").fill_null("ohne Wert")).len().sort("klasse")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Zürich Hardbrücke und Zürich Wiedikon

    Wert am Halt (roh und mit Referenzwert), jeder Abschnitt ab dem Halt (Ranglisten-Datei) und
    jede Einheit, die am Halt beginnt oder endet. Rechenprobe aus dem Review zu PR #49:
    Hardbrücke +66'170 min am Halt, −144'801 min auf den Abschnitten danach (roh +209'142 und
    −307'549).
    """)
    return


@app.cell
def _(compare, pl):
    _names = ["Zürich Hardbrücke", "Zürich Wiedikon"]
    focus = compare.filter(pl.col("halt").is_in(_names))
    focus.select(
        "halt",
        "rang_halt",
        "fahrten_halt",
        "klasse0_pct",
        pl.col("mittel_halt_roh").round(2),
        pl.col("mittel_halt_ref").round(2),
        pl.col("zuwachs_halt_roh").round(),
        pl.col("zuwachs_halt").round(),
        pl.col("zuwachs_danach_roh").round(),
        pl.col("zuwachs_danach").round(),
    )
    return (focus,)


@app.cell
def _(focus, pl, sections, unit_ranking):
    _ids = focus["a_id"].to_list()
    _cols = ["abschnitt", "fahrten", "klasse", "mittel_roh", "mittel_referenz", "zuwachs", "grund"]
    pl.concat(
        [
            sections.filter(pl.col("a_id").is_in(_ids)).select(
                pl.lit("Abschnitt ab Halt").alias("art"), *_cols
            ),
            unit_ranking.filter(pl.col("a_id").is_in(_ids)).select(
                pl.lit("Einheit ab Halt").alias("art"), *_cols
            ),
            unit_ranking.filter(pl.col("b_id").is_in(_ids)).select(
                pl.lit("Einheit bis Halt").alias("art"), *_cols
            ),
        ]
    ).with_columns(pl.col("mittel_roh", "mittel_referenz").round(2), pl.col("zuwachs").round())
    return


if __name__ == "__main__":
    app.run()
