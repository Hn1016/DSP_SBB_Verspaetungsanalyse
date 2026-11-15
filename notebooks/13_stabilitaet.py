import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    from datetime import date, timedelta

    import duckdb
    import marimo as mo
    import numpy as np
    import polars as pl
    from scipy import stats

    from sbb_delays import build, ranking
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.period import END, START
    from sbb_delays.sections import period_days

    con = duckdb.connect()
    first, last = period_days(START, END)
    return (
        build,
        con,
        date,
        first,
        last,
        mo,
        np,
        pl,
        ranking,
        service_points_snapshot,
        stats,
        timedelta,
    )


@app.cell
def _(mo):
    mo.md("""
    # Stabilität der Rangliste

    Issue #48. Erwartung und Durchführung im Projektlog (Hypothese und Entscheidung vom
    15.11.2026, vor der Analyse gepusht, Commit `e1afe77`). Die Schwellen stammen aus Issue #32
    und werden nicht angepasst.

    - **(1)** Spearman-Rangkorrelation zwischen Fahrplan 2025 und Fahrplan 2026 mindestens 0.7.
    - **(2)** Mindestens 7 der Top 10 kommen in beiden Fahrplänen vor.
    - **(3)** Über 20 Paare zufälliger 4-Wochen-Fenster ist der Median der Korrelation
      mindestens 0.7.

    Basis: die Zürcher Abschnitte mit Wert im Fenster «ganzer Zeitraum». Spearman über die
    Hauptkennzahl (`zuwachs`) aller Abschnitte mit Wert in beiden Teilen. Top 10: die zehn
    Verstärker eines Teils mit der grössten Hauptkennzahl (Issue #45).
    """)
    return


@app.cell
def _(build, con, pl, service_points_snapshot):
    KEY = ["a_id", "b_id"]

    _names = con.sql(
        f"""
        select number::integer as id, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        """
    ).pl()
    _name = dict(zip(_names["id"], _names["name"], strict=True))

    def with_names(frame):
        """Add the column abschnitt, «A → B», to a frame with a_id and b_id."""
        return frame.with_columns(
            abschnitt=pl.col("a_id").replace_strict(_name, return_dtype=pl.String)
            + " → "
            + pl.col("b_id").replace_strict(_name, return_dtype=pl.String)
        )

    table = pl.read_parquet(build.ranking_parquet())
    whole = table.filter((pl.col("fenster") == "ganzer Zeitraum") & pl.col("grund").is_null())
    base = whole.select(KEY)
    return KEY, base, table, whole, with_names


@app.cell
def _(KEY, pl, ranking, stats):
    def top10(part, klasse="Verstärker"):
        """The ten sections of a class with the largest (absorbers: most negative) zuwachs."""
        return (
            part.filter(pl.col("klasse") == klasse)
            .sort("zuwachs", descending=klasse == "Verstärker")
            .head(10)
        )

    def spearman(part_1, part_2, column="zuwachs"):
        """Spearman correlation of a column over the sections with a value in both parts."""
        both = part_1.filter(pl.col("grund").is_null()).join(
            part_2.filter(pl.col("grund").is_null()), on=KEY, suffix="_2"
        )
        return stats.spearmanr(both[column], both[f"{column}_2"]).statistic, both.height

    def changes(part_1, part_2, klasse="Verstärker"):
        """Sections in the top 10 of one part but not of the other, each with one reason."""
        rows = []
        for here, there in [(part_1, part_2), (part_2, part_1)]:
            missing = top10(here, klasse).join(top10(there, klasse), on=KEY, how="anti")
            rows.append(
                missing.select(*KEY, "tagesmittel", "zuwachs").join(
                    there.select(
                        *KEY,
                        pl.col("grund").alias("grund_dort"),
                        pl.col("klasse").alias("klasse_dort"),
                        pl.col("tagesmittel").alias("tagesmittel_dort"),
                        pl.col("ki_unten").alias("ki_unten_dort"),
                        pl.col("ki_oben").alias("ki_oben_dort"),
                    ),
                    on=KEY,
                    how="left",
                )
            )
        # the same sign rule for both lists: an absorber is mirrored
        sign = 1 if klasse == "Verstärker" else -1
        inner = pl.col("ki_unten_dort") if sign == 1 else -pl.col("ki_oben_dort")
        return pl.concat(rows).with_columns(
            wechsel=pl.when(pl.col("klasse_dort").is_null())
            .then(pl.lit("kein Wert"))
            .when(
                (pl.col("klasse_dort") == "neutral")
                & (inner > 0)
                & (sign * pl.col("tagesmittel_dort") < ranking.MIN_EFFECT)
            )
            .then(pl.lit("Klassenwechsel an der Grenze"))
            .when(pl.col("klasse_dort") != klasse)
            .then(pl.lit("Klassenwechsel, anderer"))
            .otherwise(pl.lit("Rang"))
        )

    def overlap(part_1, part_2, klasse="Verstärker"):
        return top10(part_1, klasse).join(top10(part_2, klasse), on=KEY).height

    def overlap_without_class(part_1, part_2):
        """Overlap of the ten largest by zuwachs alone, whatever the class."""
        tops = [
            p.filter(pl.col("grund").is_null()).sort("zuwachs", descending=True).head(10)
            for p in (part_1, part_2)
        ]
        return tops[0].join(tops[1], on=KEY).height

    return changes, overlap, overlap_without_class, spearman, top10


@app.cell
def _(mo):
    mo.md("""
    ## Fahrplan 2025 und Fahrplan 2026

    Aus der Ranglisten-Datei, Fenster «Fahrplan 2025» (1.8. bis 13.12.2025) und «Fahrplan 2026»
    (14.12.2025 bis 31.7.2026).
    """)
    return


@app.cell
def _(KEY, base, overlap, overlap_without_class, pl, spearman, table):
    tt_2025 = table.filter(pl.col("fenster") == "Fahrplan 2025").join(base, on=KEY)
    tt_2026 = table.filter(pl.col("fenster") == "Fahrplan 2026").join(base, on=KEY)
    tt_rho, tt_n = spearman(tt_2025, tt_2026)
    tt_overlap = overlap(tt_2025, tt_2026)
    pl.DataFrame(
        {
            "abschnitte_basis": [base.height],
            "mit_wert_in_beiden": [tt_n],
            "spearman": [round(tt_rho, 3)],
            "top10_in_beiden": [tt_overlap],
            "top10_absorber_in_beiden": [overlap(tt_2025, tt_2026, "Absorber")],
            "top10_ohne_klasse_in_beiden": [overlap_without_class(tt_2025, tt_2026)],
        }
    )
    return tt_2025, tt_2026, tt_overlap, tt_rho


@app.cell
def _(mo):
    mo.md("""
    ### Beide Top 10 der Verstärker
    """)
    return


@app.cell
def _(pl, top10, tt_2025, tt_2026, with_names):
    _columns = ["abschnitt", "fahrten", "tagesmittel", "zuwachs"]
    pl.concat(
        [
            with_names(top10(part))
            .select(pl.col(c).alias(f"{c} ({year})") for c in _columns)
            .with_columns(pl.selectors.float().round(2))
            for year, part in [(2025, tt_2025), (2026, tt_2026)]
        ],
        how="horizontal_extend",
    ).with_row_index("rang", offset=1)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Wechsel in der Top 10

    Jeder Abschnitt, der in der Top 10 des einen Fahrplans steht und in der des anderen nicht, mit
    genau einem Grund. `…_dort`: Werte im anderen Fahrplan. «Klassenwechsel an der Grenze»: dort
    neutral, obwohl das Intervall die 0 nicht enthält; nur die Schwelle von 0.25 min fehlt.

    Nach dem Lauf angemerkt: Die Regel sagt nicht, wie nahe an 0.25 min der Wert liegt. Die
    Spalten `tagesmittel` und `tagesmittel_dort` zeigen, ob ein Wechsel knapp ist.
    """)
    return


@app.cell
def _(changes, pl, tt_2025, tt_2026, with_names):
    tt_changes = pl.concat(
        [
            with_names(changes(tt_2025, tt_2026, klasse)).with_columns(liste=pl.lit(klasse))
            for klasse in ["Verstärker", "Absorber"]
        ]
    ).select(
        "liste",
        "abschnitt",
        "wechsel",
        pl.col("tagesmittel", "tagesmittel_dort", "ki_unten_dort", "ki_oben_dort").round(2),
        "klasse_dort",
    )
    tt_changes.head(40)
    return (tt_changes,)


@app.cell
def _(mo):
    mo.md("""
    ## 20 Paare zufälliger 4-Wochen-Fenster

    Ein Fenster sind 28 aufeinanderfolgende Betriebstage. `numpy.random.default_rng(48)` zieht je
    Paar zwei Anfänge; überlappende Paare werden verworfen und neu gezogen. Wert im Fenster:
    mindestens 20 Betriebstage, Klassenmittel des ganzen Zeitraums, gerechnet mit
    `ranking.ranking()` auf den Abschnittsfahrten des Fensters.
    """)
    return


@app.cell
def _(first, last, np, timedelta):
    WINDOW_DAYS, PAIRS, SEED = 28, 20, 48

    _starts = (last - first).days + 1 - (WINDOW_DAYS - 1)  # 338 possible first days
    _rng = np.random.default_rng(SEED)
    pairs, rejected = [], 0
    while len(pairs) < PAIRS:
        _a, _b = (int(x) for x in _rng.integers(0, _starts, size=2))
        if abs(_a - _b) < WINDOW_DAYS:
            rejected += 1
            continue
        pairs.append((first + timedelta(days=_a), first + timedelta(days=_b)))
    return WINDOW_DAYS, pairs, rejected


@app.cell
def _(
    KEY,
    WINDOW_DAYS,
    base,
    build,
    con,
    pairs,
    pl,
    ranking,
    service_points_snapshot,
    timedelta,
):
    # the Zurich passages once in memory; every window filters this table
    _rel = ranking.zurich_sections(con, build.sections_parquet(), service_points_snapshot())
    _rel.create("zh_passages")
    passages = con.table("zh_passages")
    means = ranking.class_means(passages)

    def window_ranking(start):
        """Values of the base sections in the 28 days from start, rules as in the step ranking."""
        end = start + timedelta(days=WINDOW_DAYS - 1)
        result = ranking.ranking(
            passages.filter(f"BETRIEBSTAG between date '{start}' and date '{end}'"),
            means,
            min_trips=1,
            min_days=ranking.MIN_DAYS_WINDOW,
        )
        return result.filter(pl.col("fenster") == "ganzer Zeitraum").join(base, on=KEY)

    windows = {start: window_ranking(start) for start in sorted({d for p in pairs for d in p})}
    return means, windows


@app.cell
def _(
    WINDOW_DAYS,
    changes,
    date,
    overlap,
    pairs,
    pl,
    spearman,
    timedelta,
    top10,
    windows,
):
    _change_day = date(2025, 12, 14)  # first day of timetable 2026

    def _timetable(start):
        end = start + timedelta(days=WINDOW_DAYS - 1)
        if end < _change_day:
            return "2025"
        return "2026" if start >= _change_day else "Wechsel"

    _rows = []
    for _nr, (_s1, _s2) in enumerate(pairs, start=1):
        _w1, _w2 = windows[_s1], windows[_s2]
        _rho, _n = spearman(_w1, _w2)
        _reasons = changes(_w1, _w2)["wechsel"]
        _rows.append(
            {
                "paar": _nr,
                "beginn_1": _s1,
                "beginn_2": _s2,
                "fahrplan": f"{_timetable(_s1)} / {_timetable(_s2)}",
                "mit_wert_in_beiden": _n,
                "spearman": round(_rho, 3),
                "spearman_pro_fahrt": round(spearman(_w1, _w2, "mittel_referenz")[0], 3),
                "spearman_fahrten": round(spearman(_w1, _w2, "fahrten")[0], 3),
                "spearman_roh": round(spearman(_w1, _w2, "mittel_roh")[0], 3),
                "verstaerker_1": _w1.filter(pl.col("klasse") == "Verstärker").height,
                "verstaerker_2": _w2.filter(pl.col("klasse") == "Verstärker").height,
                "top10_1": top10(_w1).height,
                "top10_2": top10(_w2).height,
                "top10_in_beiden": overlap(_w1, _w2),
                "wechsel_grenze": (_reasons == "Klassenwechsel an der Grenze").sum(),
                "wechsel_klasse_anderer": (_reasons == "Klassenwechsel, anderer").sum(),
                "wechsel_rang": (_reasons == "Rang").sum(),
                "wechsel_kein_wert": (_reasons == "kein Wert").sum(),
            }
        )
    per_pair = pl.DataFrame(_rows)
    per_pair.head(len(pairs))
    return (per_pair,)


@app.cell
def _(per_pair, pl, rejected):
    random_summary = per_pair.select(
        paare=pl.len(),
        verworfen_ueberlappend=pl.lit(rejected),
        spearman_median=pl.col("spearman").median().round(3),
        spearman_min=pl.col("spearman").min(),
        spearman_max=pl.col("spearman").max(),
        top10_in_beiden_median=pl.col("top10_in_beiden").median(),
        mit_wert_min=pl.col("mit_wert_in_beiden").min(),
    )
    random_summary.head(1)
    return (random_summary,)


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (1), (2) und (3)
    """)
    return


@app.cell
def _(pl, random_summary, tt_overlap, tt_rho):
    _median = random_summary["spearman_median"].item()
    verdict = pl.DataFrame(
        {
            "pruefung": [
                "(1) Spearman zwischen den Fahrplänen",
                "(2) Top 10 in beiden Fahrplänen",
                "(3) Median Spearman, 20 Paare",
            ],
            "ergebnis": [round(tt_rho, 3), float(tt_overlap), _median],
            "erwartung": ["≥ 0.7", "≥ 7", "≥ 0.7"],
            "gehalten": [bool(tt_rho >= 0.7), tt_overlap >= 7, bool(_median >= 0.7)],
        }
    )
    verdict.head(3)
    return (verdict,)


@app.cell
def _(mo, verdict):
    mo.md(f"""
    **Urteil nach den Kriterien aus Issue #32:**
    {"stabil" if verdict["gehalten"].all() else "nicht stabil"}.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Kommt die Korrelation vom Volumen? (nach dem Befund gerechnet, ohne Erwartung)

    Die Hauptkennzahl ist Mittel × Fahrten. Sind die Ränge nur stabil, weil die Zahl der Fahrten
    stabil ist? Dieselbe Korrelation über das Mittel pro Fahrt nach Referenzwert
    (`mittel_referenz`, ohne Volumen) und über die Zahl der Fahrten allein, dazu als Massstab die
    Korrelation der Hauptkennzahl, wenn die Abschnitte des zweiten Fahrplans zufällig vertauscht
    werden (Median über 1000 Vertauschungen).

    Im Review zu PR #50 dazugekommen (schwagia): Der Referenzwert ist das Klassenmittel des ganzen
    Zeitraums und in beiden Teilen derselbe. Hat ein Abschnitt in beiden Teilen dieselbe
    Soll-Fahrzeit, trägt dieser Abzug zur Korrelation bei, ohne etwas über den Betrieb zu sagen.
    Darum dieselbe Korrelation über das rohe Mittel pro Fahrt (`mittel_roh`, ohne Referenzwert).
    """)
    return


@app.cell
def _(KEY, np, per_pair, pl, spearman, stats, tt_2025, tt_2026):
    _both = tt_2025.filter(pl.col("grund").is_null()).join(
        tt_2026.filter(pl.col("grund").is_null()), on=KEY, suffix="_2"
    )
    _rng = np.random.default_rng(48)
    _shuffled = [
        abs(stats.spearmanr(_both["zuwachs"], _rng.permutation(_both["zuwachs_2"])).statistic)
        for _ in range(1000)
    ]
    _sizes = {
        "Hauptkennzahl": ("zuwachs", "spearman"),
        "Mittel pro Fahrt": ("mittel_referenz", "spearman_pro_fahrt"),
        "Mittel pro Fahrt, roh (ohne Referenzwert)": ("mittel_roh", "spearman_roh"),
        "Zahl der Fahrten": ("fahrten", "spearman_fahrten"),
    }
    volume = pl.DataFrame(
        {
            "groesse": list(_sizes),
            "spearman_fahrplaene": [
                round(spearman(tt_2025, tt_2026, c)[0], 3) for c, _ in _sizes.values()
            ],
            "median_20_paare": [per_pair[c].median() for _, c in _sizes.values()],
            "min_20_paare": [per_pair[c].min() for _, c in _sizes.values()],
        }
    )
    shuffled = pl.DataFrame(
        {
            "vertauscht_median_betrag": [round(float(np.median(_shuffled)), 3)],
            "vertauscht_max_betrag": [round(float(np.max(_shuffled)), 3)],
        }
    )
    volume.head(len(_sizes))
    return shuffled, volume


@app.cell
def _(shuffled):
    shuffled.head(1)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Autokorrelation der Tagesmittel (beschreibend)

    Für die Top 10 der Verstärker im ganzen Zeitraum: Korrelation des Tagesmittels nach
    Referenzwert mit dem des Vortags, über alle Paare aufeinanderfolgender Betriebstage mit
    Messung an beiden Tagen. Ein Wert über 0 heisst: Die Betriebstage sind nicht unabhängig, das
    Intervall aus `ranking` ist zu schmal.
    """)
    return


@app.cell
def _(KEY, con, means, pl, top10, whole, with_names):
    _reference = ", ".join(f"('{klasse}', {mean!r})" for klasse, mean in means.items())
    _top = top10(whole).select(*KEY, "tage", "tagesmittel")
    con.register("top_sections", _top)
    con.execute(
        f"""
        create or replace table top_daily as
        with reference(klasse, mittel) as (values {_reference})
        select p.a_id, p.b_id, p.BETRIEBSTAG, avg(p.section_delay - r.mittel) as day_mean
        from zh_passages p
        join reference r
          on r.klasse = case when p.scheduled_min >= 5 then '5+'
                             else p.scheduled_min::varchar end
        join top_sections t on t.a_id = p.a_id and t.b_id = p.b_id
        group by all
        """
    )
    autocorrelation = with_names(
        con.sql(
            """
            select d.a_id, d.b_id, count(*) as tagespaare,
                   round(corr(d.day_mean, v.day_mean), 2) as autokorrelation
            from top_daily d
            join top_daily v
              on v.a_id = d.a_id and v.b_id = d.b_id and v.BETRIEBSTAG = d.BETRIEBSTAG - 1
            group by all
            """
        )
        .pl()
        .join(_top, on=KEY)
    ).select("abschnitt", "tage", pl.col("tagesmittel").round(2), "tagespaare", "autokorrelation")
    autocorrelation.sort("autokorrelation", descending=True)
    return (autocorrelation,)


if __name__ == "__main__":
    app.run()
