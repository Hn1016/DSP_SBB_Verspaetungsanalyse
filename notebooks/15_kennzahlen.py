import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo
    import polars as pl

    from sbb_delays import build, ranking
    from sbb_delays.download import fetch_sbb_dataset, service_points_snapshot, sha256sum

    con = duckdb.connect()
    return build, con, fetch_sbb_dataset, mo, pl, ranking, service_points_snapshot, sha256sum


@app.cell
def _(mo):
    mo.md("""
    # Kennzahlen der Rangliste

    Issue #53. Erwartungen und Durchführung im Projektlog (Hypothese und Entscheidung vom
    22.11.2026, vor der Analyse gepusht, Commit `4023693`). Schwellen und Regeln aus Issue #32 und
    #45, Plan B aus Issue #42.

    - **(1)** Luftlinie im Median mindestens 85 % der Streckenlänge, Spearman der beiden Längen
      mindestens 0.9 (an den 275 eindeutigen Längen aus #42).
    - **(2)** Anteil der Top 10 am positiven Zuwachs (relativ) zwischen 15 und 22 %; aus der
      Abschnittsdatei nachgerechnet höchstens 0.1 Prozentpunkte Abweichung.
    - **(3)** Höchstens 4 der Top 10 stehen auch in der Top 10 nach Zahl der Fahrten.
    - **(4)** Steigung der Streckenverspätung auf die Abfahrtsverspätung an A negativ, über alle
      Fahrten und innerhalb der Abschnitte.
    - **(4b)** Nur mit Abfahrten höchstens 1 Minute verspätet bleiben mindestens 7 der Top 10
      Verstärker.

    Basis: Ranglisten-Datei, Fenster «ganzer Zeitraum». Top 10: die zehn Verstärker mit dem
    grössten Zuwachs.
    """)
    return


@app.cell
def _(build, con, service_points_snapshot):
    con.execute(
        f"""
        create or replace view stops as
        select number::integer as bpuic, designationOfficial as name,
               try_cast(wgs84East as double) as lon, try_cast(wgs84North as double) as lat
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        """
    )
    # Great-circle distance between A and B, earth radius 6371 km (log 2026-11-22, point 2).
    con.execute(
        f"""
        create or replace table base as
        select r.*, a.name || ' → ' || b.name as abschnitt,
               2 * 6371 * asin(sqrt(
                   pow(sin(radians(b.lat - a.lat) / 2), 2)
                   + cos(radians(a.lat)) * cos(radians(b.lat))
                     * pow(sin(radians(b.lon - a.lon) / 2), 2)
               )) as luftlinie_km
        from read_parquet('{build.ranking_parquet()}') r
        join stops a on a.bpuic = r.a_id
        join stops b on b.bpuic = r.b_id
        where r.fenster = 'ganzer Zeitraum' and r.grund is null
        """
    )
    base = con.table("base").pl()
    return (base,)


@app.cell
def _(base, pl):
    top10 = (
        base.filter(pl.col("klasse") == "Verstärker")
        .sort("zuwachs", descending=True)
        .head(10)
        .with_columns(
            rang_top=pl.int_range(1, 11),
            mittel_pro_km=pl.col("mittel_referenz") / pl.col("luftlinie_km"),
        )
    )
    return (top10,)


@app.cell
def _(mo):
    mo.md("""
    ## Top 10 der Verstärker

    Zuwachs in Minuten im Zeitraum (nach Referenzwert); Mittel pro Fahrt in Minuten, roh und nach
    Referenzwert; Luftlinie in km; pro km = Mittel pro Fahrt nach Referenzwert / Luftlinie.
    Beschreibend, ohne Prüfung.
    """)
    return


@app.cell
def _(pl, top10):
    top10.select(
        "rang_top",
        "abschnitt",
        "fahrten",
        pl.col("zuwachs").round(0),
        pl.col("mittel_referenz").round(2),
        pl.col("mittel_roh").round(2),
        pl.col("luftlinie_km").round(2),
        pl.col("mittel_pro_km").round(3),
        pl.col("rang").alias("rang_alle"),
    ).head(10)
    return


@app.cell
def _(mo):
    mo.md("""
    ## (1) Luftlinie und Streckenlänge

    Streckenlänge: die Abschnitte mit genau einer gemeinsamen Linie in
    `linie-mit-betriebspunkten`, wie in `notebooks/11_zuordnung_data_sbb.py`.
    """)
    return


@app.cell
def _(fetch_sbb_dataset, mo, sha256sum):
    # Same snapshot as finding #42 (data/raw/manifest.csv); review PR #43.
    _sha = "497f0e22a32ecd10b4164d99acb079ac15781f3a513d37e5d65664e0a9359e4f"
    lines_file = fetch_sbb_dataset("linie-mit-betriebspunkten")
    mo.callout(
        mo.md(f"**Anderer Stand als im Befund #42:** {lines_file.name}."), kind="danger"
    ) if sha256sum(lines_file) != _sha else mo.md(
        "`linie-mit-betriebspunkten` hat die Prüfsumme des Befunds #42 (Stand 2026-11-14)."
    )
    return (lines_file,)


@app.cell
def _(con, lines_file):
    lengths = con.sql(
        f"""
        with lines as (
            select bpuic, linie, km
            from read_csv('{lines_file}', delim=';', header=true)
        ),
        common as (
            select s.a_id, s.b_id, count(*) as linien, any_value(abs(b.km - a.km)) as km
            from base s
            join lines a on a.bpuic = s.a_id
            join lines b on b.bpuic = s.b_id and b.linie = a.linie
            group by all
        )
        select s.abschnitt, s.luftlinie_km, c.km as strecke_km,
               s.luftlinie_km / c.km as verhaeltnis
        from base s join common c using (a_id, b_id)
        where c.linien = 1
        """
    ).pl()
    return (lengths,)


@app.cell
def _(lengths, pl):
    from scipy import stats

    _rho = stats.spearmanr(lengths["luftlinie_km"], lengths["strecke_km"]).statistic
    _median = lengths["verhaeltnis"].median()
    pl.DataFrame(
        {
            "pruefung": ["(1) Median Luftlinie / Strecke", "(1) Spearman der Längen"],
            "ergebnis": [round(_median, 3), round(_rho, 3)],
            "erwartung": ["≥ 0.85", "≥ 0.9"],
            "gehalten": [bool(_median >= 0.85), bool(_rho >= 0.9)],
            "abschnitte": [lengths.height, lengths.height],
        }
    )
    return (stats,)


@app.cell
def _(lengths, pl):
    # the sections where the straight line is furthest from the track length
    lengths.sort("verhaeltnis").select(
        "abschnitt", pl.col(["luftlinie_km", "strecke_km", "verhaeltnis"]).round(3)
    ).head(8)
    return


@app.cell
def _(mo):
    mo.md("""
    ## (2) Anteil der Top 10 am positiven Zuwachs

    Total: Summe des Zuwachses aller Abschnitte mit Wert und positivem Mittel. Nachrechnung direkt
    aus der Abschnittsdatei: Klassenmittel, Mindestzahlen und Summen in SQL, ohne die
    Ranglisten-Datei; aus ihr kommen nur die zehn Abschnitte der Top 10.
    """)
    return


@app.cell
def _(base, build, con, pl, ranking, service_points_snapshot, top10):
    _share = top10["zuwachs"].sum() / base.filter(pl.col("zuwachs") > 0)["zuwachs"].sum()
    _raw = base.with_columns(zuwachs_roh=pl.col("mittel_roh") * pl.col("fahrten"))
    _top_raw = _raw.join(top10.select("a_id", "b_id"), on=["a_id", "b_id"])["zuwachs_roh"].sum()
    _share_raw = _top_raw / _raw.filter(pl.col("zuwachs_roh") > 0)["zuwachs_roh"].sum()

    _ids = ", ".join(f"({a}, {b})" for a, b in top10.select("a_id", "b_id").iter_rows())
    zh = ranking.zurich_sections(con, build.sections_parquet(), service_points_snapshot())
    _recount = zh.query(
        "zh",
        f"""
        with classed as (
            select *, case when scheduled_min >= 5 then '5+' else scheduled_min::varchar end as k
            from zh
        ),
        means as (select k, avg(section_delay) as m from classed group by k),
        per_section as (
            select a_id, b_id, sum(section_delay - m) as zuwachs
            from classed join means using (k)
            group by a_id, b_id
            having count(*) >= {ranking.MIN_TRIPS}
               and count(distinct BETRIEBSTAG) >= {ranking.MIN_DAYS}
        )
        select sum(zuwachs) filter (where (a_id, b_id) in ({_ids}))
               / sum(zuwachs) filter (where zuwachs > 0)
        from per_section
        """,
    ).fetchone()[0]
    _diff = abs(_share - _recount) * 100
    pl.DataFrame(
        {
            "pruefung": [
                "(2) Anteil relativ",
                "(2) Nachrechnung aus der Abschnittsdatei",
                "Begleitzahl: Anteil roh (dieselben zehn)",
            ],
            "ergebnis": [
                f"{100 * _share:.2f} %",
                f"{100 * _recount:.2f} % (Abweichung {_diff:.3f} Prozentpunkte)",
                f"{100 * _share_raw:.2f} %",
            ],
            "erwartung": ["15 bis 22 %", "≤ 0.1 Prozentpunkte", "beschreibend"],
            "gehalten": [bool(0.15 <= _share <= 0.22), bool(_diff <= 0.1), None],
        }
    )
    return (zh,)


@app.cell
def _(mo):
    mo.md("""
    ## (3) Baseline: Top 10 nach Zahl der Fahrten

    Die zehn Abschnitte mit Wert mit den meisten Fahrten, alle Klassen.
    """)
    return


@app.cell
def _(base, mo, pl, top10):
    by_trips = base.sort("fahrten", descending=True).head(10)
    _both = by_trips.join(top10.select("a_id", "b_id"), on=["a_id", "b_id"]).height
    _table = by_trips.select(
        "abschnitt",
        "fahrten",
        "klasse",
        pl.col("mittel_referenz").round(2),
        pl.col("zuwachs").round(0),
        pl.col("rang").alias("rang_alle"),
    )
    _check = pl.DataFrame(
        {
            "pruefung": ["(3) in beiden Top 10"],
            "ergebnis": [_both],
            "erwartung": ["≤ 4"],
            "gehalten": [_both <= 4],
        }
    )
    mo.vstack([_check, _table])
    return


@app.cell
def _(mo):
    mo.md("""
    ## (4) Regression auf die Abfahrtsverspätung an A

    Kleinste Quadrate über alle Zürcher Abschnittsfahrten der Abschnitte mit Wert:
    Streckenverspätung nach Referenzwert auf die Abfahrtsverspätung an A, beide in Minuten.
    Einmal gemeinsam, einmal innerhalb der Abschnitte (beide Grössen je Abschnitt um das Mittel
    bereinigt).
    """)
    return


@app.cell
def _(base, con, pl, ranking, zh):
    means = ranking.class_means(zh)
    _reference = ", ".join(f"('{k}', {m!r})" for k, m in means.items())
    con.register("with_value", base.select("a_id", "b_id"))
    _slopes = zh.query(
        "zh",
        f"""
        with reference(k, m) as (values {_reference}),
        trips as (
            select z.a_id, z.b_id, z.ab_delay_a as x, z.section_delay - r.m as y
            from zh z
            join reference r
              on r.k = case when z.scheduled_min >= 5 then '5+' else z.scheduled_min::varchar end
            semi join with_value v on v.a_id = z.a_id and v.b_id = z.b_id
        ),
        centred as (
            select x, y,
                   x - avg(x) over (partition by a_id, b_id) as xc,
                   y - avg(y) over (partition by a_id, b_id) as yc
            from trips
        )
        select count(*), regr_slope(y, x), regr_slope(yc, xc), corr(y, x) from centred
        """,
    ).fetchone()
    _n, _pooled, _within, _corr = _slopes
    pl.DataFrame(
        {
            "pruefung": ["(4) Steigung über alle Fahrten", "(4) Steigung innerhalb der Abschnitte"],
            "ergebnis": [round(_pooled, 4), round(_within, 4)],
            "erwartung": ["< 0", "< 0"],
            "gehalten": [_pooled < 0, _within < 0],
            "fahrten": [_n, _n],
            "korrelation": [round(_corr, 4), None],
        }
    )
    return (means,)


@app.cell
def _(mo):
    mo.md("""
    ## (4b) Nur pünktliche Abfahrten an A

    Fahrten mit Abfahrtsverspätung an A von höchstens 1 Minute, frühe eingeschlossen. Klasse mit
    `ranking.ranking()`, Referenzwert und Mindestzahlen wie im ganzen Zeitraum; Fenster «ganzer
    Zeitraum».
    """)
    return


@app.cell
def _(means, pl, ranking, top10, zh):
    _on_time = ranking.ranking(zh.filter("ab_delay_a <= 1"), means).filter(
        pl.col("fenster") == "ganzer Zeitraum"
    )
    _compare = top10.select("rang_top", "abschnitt", "a_id", "b_id", "mittel_referenz").join(
        _on_time.select(
            "a_id",
            "b_id",
            pl.col("fahrten").alias("fahrten_puenktlich"),
            pl.col("mittel_referenz").alias("mittel_puenktlich"),
            pl.col("klasse").alias("klasse_puenktlich"),
            "grund",
        ),
        on=["a_id", "b_id"],
        how="left",
    )
    _kept = _compare.filter(pl.col("klasse_puenktlich") == "Verstärker").height
    (
        pl.DataFrame(
            {
                "pruefung": ["(4b) Top 10 bleiben Verstärker"],
                "ergebnis": [_kept],
                "erwartung": ["≥ 7"],
                "gehalten": [_kept >= 7],
            }
        ),
        _compare.drop("a_id", "b_id").with_columns(pl.col(r"^mittel.*$").round(2)),
    )
    return


if __name__ == "__main__":
    app.run()
