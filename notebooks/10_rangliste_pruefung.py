import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo
    import polars as pl

    from sbb_delays import build, ranking
    from sbb_delays.download import service_points_snapshot

    return build, duckdb, mo, pl, ranking, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Rangliste aus dem Pipeline-Schritt: drei Prüfungen

    Issue #38. Erwartungen und Zählweise im Projektlog (Hypothese vom 12.11.2026, vor dem Bau der
    Rangliste gepusht, Commit `a2d5dcc`). Basis: die Datei aus dem Schritt `ranking` von
    `uv run build`, eine Zeile pro Zürcher Abschnitt und Fenster.

    - **(a)** Im Fenster «ganzer Zeitraum» sind Zuwachs und Rang der Top 10 gleich wie im Befund
      zu #23.
    - **(b)** Die Zahl der Abschnitte mit mindestens 20 Betriebstagen je Fenster stimmt mit der
      Tabelle im Befund zu #39 überein.
    - **(c)** In jedem der 13 Fenster haben mindestens 90 % der Abschnitte mit Wert eine halbe
      Intervallbreite unter 0.25 min.
    """)
    return


@app.cell
def _(build, duckdb, pl, ranking, service_points_snapshot):
    WINDOWS = [name for _, name in ranking.WINDOWS]
    _names = duckdb.sql(
        f"""
        select number::integer as id, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        """
    ).pl()
    _name = dict(zip(_names["id"], _names["name"], strict=True))
    table = pl.read_parquet(build.ranking_parquet()).with_columns(
        abschnitt=pl.col("a_id").replace_strict(_name, return_dtype=pl.String)
        + " → "
        + pl.col("b_id").replace_strict(_name, return_dtype=pl.String),
        halbe_breite=(pl.col("ki_oben") - pl.col("ki_unten")) / 2,
        nr=pl.col("fenster").replace_strict(
            {w: i for i, w in enumerate(WINDOWS)}, return_dtype=pl.Int32
        ),
    )
    with_value = table.filter(pl.col("grund").is_null())
    return WINDOWS, table, with_value


@app.cell
def _(WINDOWS, mo, pl, table):
    _sections = table.select(pl.struct("a_id", "b_id").n_unique()).item()
    _whole = table.filter(pl.col("fenster") == "ganzer Zeitraum")
    mo.md(f"""
    ## Form der Datei

    {table.height} Zeilen = {_sections} Abschnitte × {len(WINDOWS)} Fenster
    ({_sections * len(WINDOWS)}); {_whole["fahrten"].sum()} Abschnittsfahrten im ganzen Zeitraum
    (Befund #33: 7'739'652), davon {_whole.filter(pl.col("grund").is_null())["fahrten"].sum()} auf
    Abschnitten mit Wert (Befund #39: 7'738'519). Zeilen mit Wert und Grund zugleich oder ohne
    beides: {table.filter(pl.col("grund").is_null() != pl.col("zuwachs").is_not_null()).height}.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## (a) Top 10 im ganzen Zeitraum gegen den Befund zu #23

    Erwartet: die Tabelle «Top 10 mit Referenzwert» aus dem Log vom 10.11.2026 (Abschnitt,
    Fahrten, Zuwachs auf ganze Minuten). Die Spalten rechts kommen neu aus dem Schritt `ranking`.
    """)
    return


@app.cell
def _(pl, with_value):
    # log 2026-11-10, Befund #23, «Top 10 mit Referenzwert»
    expected_top = pl.DataFrame(
        {
            "rang": list(range(1, 11)),
            "abschnitt_23": [
                "Zürich HB → Zürich Oerlikon",
                "Zürich Oerlikon → Zürich Hardbrücke",
                "Zürich Flughafen → Zürich Oerlikon",
                "Effretikon → Dietlikon",
                "Zürich HB → Zürich Wiedikon",
                "Winterthur → Stettbach",
                "Zürich HB → Zürich Hardbrücke",
                "Thalwil → Zürich Enge",
                "Uster → Zürich Stadelhofen",
                "Zürich Stadelhofen → Stettbach",
            ],
            "fahrten_23": [75748, 73486, 58589, 36704, 41688, 26710, 128172, 13398, 27321, 56560],
            "zuwachs_23": [70872, 65570, 47814, 30857, 29644, 26406, 24095, 23829, 23694, 22338],
        }
    )
    top = (
        with_value.filter((pl.col("fenster") == "ganzer Zeitraum") & (pl.col("rang") <= 10))
        .with_columns(pl.col("rang").cast(pl.Int64), pl.col("zuwachs").round().cast(pl.Int64))
        .join(expected_top, on="rang", how="full", coalesce=True)
        .sort("rang")
        .with_columns(
            gleich=(pl.col("abschnitt") == pl.col("abschnitt_23"))
            & (pl.col("fahrten") == pl.col("fahrten_23"))
            & (pl.col("zuwachs") == pl.col("zuwachs_23"))
        )
        .select(
            "rang",
            "abschnitt",
            "fahrten",
            "zuwachs",
            "gleich",
            pl.col("mittel_referenz").round(2),
            pl.col("tagesmittel").round(2),
            pl.col("ki_unten").round(2),
            pl.col("ki_oben").round(2),
            "klasse",
        )
    )
    top.head(12)
    return (top,)


@app.cell
def _(mo):
    mo.md("""
    ## (b) und (c) je Fenster, Klassen und Gründe

    `mit_wert`: Abschnitte mit mindestens 100 Fahrten und 30 Betriebstagen im Zeitraum und 20
    Betriebstagen im Fenster; `erreicht_39`: Spalte «erreicht» im Befund zu #39. `schmal`:
    Abschnitte mit Wert, deren halbe Intervallbreite unter 0.25 min liegt, `schmal_pct` ihr
    Anteil; Median, 90. Perzentil und Maximum der halben Breite in Minuten.
    """)
    return


@app.cell
def _(WINDOWS, pl, table):
    # log 2026-11-12, Befund #39, column «erreicht» of the single windows; whole period: the base
    _expected = [394, 376, 363, 375, 377, 390, 370, 391, 392, 392, 390, 390, 394]
    _narrow = pl.col("halbe_breite") < 0.25
    by_window = (
        table.group_by("nr", "fenster")
        .agg(
            mit_wert=pl.col("grund").is_null().sum(),
            schmal=_narrow.sum(),
            breite_median=pl.col("halbe_breite").median().round(3),
            breite_p90=pl.col("halbe_breite").quantile(0.9).round(3),
            breite_max=pl.col("halbe_breite").max().round(3),
            verstaerker=(pl.col("klasse") == "Verstärker").sum(),
            absorber=(pl.col("klasse") == "Absorber").sum(),
            neutral=(pl.col("klasse") == "neutral").sum(),
            # neutral although the interval excludes 0: only the minimum effect decides
            neutral_nur_effekt=(
                (pl.col("klasse") == "neutral")
                & ((pl.col("ki_unten") > 0) | (pl.col("ki_oben") < 0))
            ).sum(),
            keine_fahrt=(pl.col("grund") == "keine Fahrt im Fenster").sum(),
            zu_wenige_fahrten=(pl.col("grund") == "zu wenige Fahrten").sum(),
            zu_wenige_tage=(pl.col("grund") == "zu wenige Betriebstage").sum(),
        )
        .sort("nr")
        .with_columns(
            erreicht_39=pl.Series(_expected, dtype=pl.UInt32),
            schmal_pct=(100 * pl.col("schmal") / pl.col("mit_wert")).round(1),
        )
    )
    assert by_window["fenster"].to_list() == WINDOWS
    by_window.select(
        "fenster",
        "mit_wert",
        "erreicht_39",
        "schmal",
        "schmal_pct",
        "breite_median",
        "breite_p90",
        "breite_max",
    ).head(13)
    return (by_window,)


@app.cell
def _(by_window):
    by_window.select(
        "fenster",
        "verstaerker",
        "absorber",
        "neutral",
        "neutral_nur_effekt",
        "keine_fahrt",
        "zu_wenige_fahrten",
        "zu_wenige_tage",
    ).head(13)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (a), (b) und (c)
    """)
    return


@app.cell
def _(by_window, pl, top):
    _same_top = int(top["gleich"].fill_null(False).sum())
    _same_counts = int((by_window["mit_wert"] == by_window["erreicht_39"]).sum())
    _lowest = by_window["schmal_pct"].min()
    checks = pl.DataFrame(
        {
            "pruefung": [
                "(a) Zeilen der Top 10 gleich wie Befund #23",
                "(b) Fenster mit gleicher Zahl wie Befund #39",
                "(c) kleinster Anteil mit halber Breite < 0.25 min (%)",
            ],
            "ergebnis": [float(_same_top), float(_same_counts), _lowest],
            "erwartung": ["= 10", "= 13", "≥ 90"],
            "gehalten": [_same_top == 10, _same_counts == 13, _lowest >= 90],
        }
    )
    checks.head(3)
    return (checks,)


@app.cell
def _(mo):
    mo.md("""
    ## Abschnitte mit halber Breite ab 0.25 min

    Die Zeilen mit Wert, bei denen das Intervall einen Effekt von 0.25 min nicht eingrenzt.
    """)
    return


@app.cell
def _(pl, with_value):
    wide = (
        with_value.filter(pl.col("halbe_breite") >= 0.25)
        .sort("nr", "halbe_breite", descending=[False, True])
        .select(
            "fenster",
            "abschnitt",
            "fahrten",
            "tage",
            pl.col("tagesmittel").round(2),
            pl.col("halbe_breite").round(2),
            "klasse",
        )
    )
    wide.head(60)
    return (wide,)


if __name__ == "__main__":
    app.run()
