import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import importlib.util

    import duckdb
    import marimo as mo
    import polars as pl

    from sbb_delays import build, ranking
    from sbb_delays.download import service_points_snapshot

    return build, duckdb, importlib, mo, pl, ranking, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Rangliste der Halte aus dem Pipeline-Schritt: Prüfung

    Issue #61. Entscheide und Erwartungen im Projektlog (Einträge vom 26.11.2026, Commit
    `70e40b1`, vor dem Rechnen gepusht). Basis: die Datei aus dem Schritt `stop_ranking` von
    `uv run build`, eine Zeile pro Zürcher Halt und Fenster.

    - **(a) Übernahme:** Im ganzen Zeitraum dieselben 152 Halte mit Wert wie Notebook 12, mit
      gleichen Fahrten, Betriebstagen, Mittel roh, Mittel mit Referenzwert und Zuwachs (gerundet
      wie in Notebook 12). Die fünf Halte ohne Ankunft und Abfahrt `REAL` haben keine Zeile oder
      einen Grund.
    - **(b) Klasse:** Von der Top 10 nach Zuwachs mit Referenzwert aus Notebook 12 sind genau
      Zürich Hardbrücke, Zürich Flughafen, Dietikon Stoffelbach und Horgen Oberdorf Verstärker,
      die übrigen sechs neutral.

    Die Werte von Notebook 12 kommen aus Notebook 12 selbst (`app.run()`, Tabelle `ranking`),
    nicht aus `stop_ranking.py`.
    """)
    return


@app.cell
def _(build, duckdb, pl, ranking, service_points_snapshot):
    WINDOWS = [name for _, name in ranking.WINDOWS]
    _names = duckdb.sql(
        f"""
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        """
    ).pl()
    stop_file = build.stop_ranking_parquet()
    table = (
        pl.read_parquet(stop_file)
        .join(_names, on="BPUIC", how="left")
        .with_columns(
            halbe_breite=(pl.col("ki_oben") - pl.col("ki_unten")) / 2,
            nr=pl.col("fenster").replace_strict(
                {w: i for i, w in enumerate(WINDOWS)}, return_dtype=pl.Int32
            ),
        )
    )
    with_value = table.filter(pl.col("grund").is_null())
    whole = table.filter(pl.col("fenster") == "ganzer Zeitraum")
    return WINDOWS, stop_file, table, whole, with_value


@app.cell
def _(WINDOWS, mo, pl, stop_file, table, whole):
    _stops = table["BPUIC"].n_unique()
    _both = table.filter(pl.col("grund").is_null() != pl.col("zuwachs").is_not_null()).height
    mo.md(f"""
    ## Form der Datei

    `{stop_file.name}`: {table.height} Zeilen = {_stops} Halte × {len(WINDOWS)} Fenster
    ({_stops * len(WINDOWS)}). Halte mit Wert im ganzen Zeitraum:
    {whole.filter(pl.col("grund").is_null()).height}; Halteereignisse im ganzen Zeitraum:
    {whole["fahrten"].sum()} (Befund #46: 7'616'139). Zeilen mit Wert und Grund zugleich oder
    ohne beides: {_both}.
    Namen ohne Treffer im Schnappschuss: {table["name"].null_count()}.
    """)
    return


@app.cell
def _(importlib, mo):
    # Notebook 12 runs as it is; its table `ranking` holds the values of Befund #46.
    _spec = importlib.util.spec_from_file_location(
        "nb12", mo.notebook_dir() / "12_referenzwert_halte.py"
    )
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    _, _defs = _module.app.run()
    nb12 = _defs["ranking"]
    return (nb12,)


@app.cell
def _(mo):
    mo.md("""
    ## (a) Ganzer Zeitraum gegen Notebook 12

    Notebook 12 rundet die Mittel auf zwei Stellen und den Zuwachs auf ganze Minuten
    (DuckDB `round`); die Werte der Pipeline sind hier gleich gerundet. Verbunden wird über den
    Namen des Halts, wie Notebook 12 ihn ausgibt.
    """)
    return


@app.cell
def _(duckdb, nb12, whole):
    _con = duckdb.connect()
    _con.register("pipe", whole)
    _con.register("nb12", nb12)
    compare = _con.sql(
        """
        select coalesce(p.name, n.halt) as halt,
               p.fahrten, n.fahrten as fahrten_12, p.tage, n.tage as tage_12,
               round(p.mittel_roh, 2) as mittel_roh, n.mittel_roh as mittel_roh_12,
               round(p.mittel_referenz, 2) as mittel_referenz,
               n.mittel_referenz as mittel_referenz_12,
               round(p.zuwachs) as zuwachs, n.zuwachs_referenz as zuwachs_12,
               p.grund,
               p.fahrten is not distinct from n.fahrten
                   and p.tage is not distinct from n.tage
                   and round(p.mittel_roh, 2) is not distinct from n.mittel_roh
                   and round(p.mittel_referenz, 2) is not distinct from n.mittel_referenz
                   and round(p.zuwachs) is not distinct from n.zuwachs_referenz as gleich
        from (select * from pipe where grund is null) p
        full join nb12 n on n.halt = p.name
        order by gleich, halt
        """
    ).pl()
    compare.head(10)
    return (compare,)


@app.cell
def _(duckdb, mo, nb12, pl, table):
    # Befund #46: five stops with stop events but none with arrival and departure REAL
    _five = ["Neuthal", "Bäretswil", "Ettenhausen-Emmetschloo", "Sihlwald", "Zürich Langstrasse"]
    five = (
        pl.DataFrame({"halt": _five})
        .join(
            table.filter(pl.col("fenster") == "ganzer Zeitraum").select(
                pl.col("name").alias("halt"), "fahrten", "grund"
            ),
            on="halt",
            how="left",
        )
        .with_columns(zeile=pl.col("fahrten").is_not_null())
    )
    _unique = duckdb.sql("select count(*) = count(distinct halt) from nb12").fetchone()[0]
    mo.vstack([mo.md(f"Namen in Notebook 12 eindeutig: {_unique}."), five])
    return (five,)


@app.cell
def _(mo):
    mo.md("""
    ## (b) Klasse der Top 10 nach Zuwachs aus Notebook 12

    Top 10 nach `rang_referenz` (Zuwachs mit Referenzwert) in Notebook 12, daneben Klasse,
    Tagesmittel und Intervall aus dem Schritt `stop_ranking`. `erwartet`: Klasse laut Hypothese.
    """)
    return


@app.cell
def _(nb12, pl, whole):
    _amplifiers = [
        "Zürich Hardbrücke",
        "Zürich Flughafen",
        "Dietikon Stoffelbach",
        "Horgen Oberdorf",
    ]
    top12 = (
        nb12.filter(pl.col("rang_referenz") <= 10)
        .select("rang_referenz", "halt", "mittel_referenz", "zuwachs_referenz")
        .join(
            whole.select(
                pl.col("name").alias("halt"),
                "fahrten",
                "tage",
                pl.col("tagesmittel").round(3),
                pl.col("ki_unten").round(3),
                pl.col("ki_oben").round(3),
                "klasse",
                "rang",
            ),
            on="halt",
            how="left",
        )
        .with_columns(
            erwartet=pl.when(pl.col("halt").is_in(_amplifiers))
            .then(pl.lit("Verstärker"))
            .otherwise(pl.lit("neutral"))
        )
        .with_columns(wie_erwartet=pl.col("klasse") == pl.col("erwartet"))
        .sort("rang_referenz")
    )
    top12.head(10)
    return (top12,)


@app.cell
def _(mo):
    mo.md("""
    ## Top 10 der Verstärker im ganzen Zeitraum (Entscheidung #45)

    Die zehn Halte der Klasse «Verstärker» mit dem grössten Zuwachs; `rang` ist der Rang nach
    dem Zuwachs unter allen Halten mit Wert.
    """)
    return


@app.cell
def _(pl, with_value):
    top_amplifiers = (
        with_value.filter(
            (pl.col("fenster") == "ganzer Zeitraum") & (pl.col("klasse") == "Verstärker")
        )
        .sort("zuwachs", descending=True)
        .head(10)
        .select(
            pl.col("name").alias("halt"),
            "fahrten",
            "tage",
            pl.col("mittel_roh").round(2),
            pl.col("mittel_referenz").round(2),
            pl.col("tagesmittel").round(2),
            pl.col("ki_unten").round(2),
            pl.col("ki_oben").round(2),
            pl.col("zuwachs").round(),
            "rang",
        )
    )
    top_amplifiers.head(10)
    return (top_amplifiers,)


@app.cell
def _(mo, pl, top_amplifiers, whole):
    # Entscheidung #45, «Bezugsgrösse»: numerator and total after the reference value; total =
    # Zuwachs of all stops with a positive mean. Companion figure: raw Zuwachs (mittel_roh x
    # fahrten) of the same ten stops over the raw total of the positive Zuwachs.
    _v = whole.filter(pl.col("grund").is_null()).with_columns(
        zuwachs_roh=pl.col("mittel_roh") * pl.col("fahrten")
    )
    _top = _v.filter(pl.col("name").is_in(top_amplifiers["halt"].to_list()))
    share = {
        "zaehler": _top["zuwachs"].sum(),
        "total": _v.filter(pl.col("mittel_referenz") > 0)["zuwachs"].sum(),
        "halte_positiv": _v.filter(pl.col("mittel_referenz") > 0).height,
        "zaehler_roh": _top["zuwachs_roh"].sum(),
        "total_roh": _v.filter(pl.col("mittel_roh") > 0)["zuwachs_roh"].sum(),
        "halte_positiv_roh": _v.filter(pl.col("mittel_roh") > 0).height,
    }
    mo.md(f"""
    **Anteil der Top 10 am positiven Zuwachs (mit Referenzwert):** {share["zaehler"]:,.0f} von
    {share["total"]:,.0f} min auf {share["halte_positiv"]} Halten mit positivem Mittel =
    {100 * share["zaehler"] / share["total"]:.1f} %.

    **Begleitzahl roh (dieselben zehn Halte):** {share["zaehler_roh"]:,.0f} von
    {share["total_roh"]:,.0f} min auf {share["halte_positiv_roh"]} Halten mit positivem rohem
    Mittel = {100 * share["zaehler_roh"] / share["total_roh"]:.1f} %.
    """)
    return (share,)


@app.cell
def _(mo):
    mo.md("""
    ## Je Fenster: Klassen, Gründe und halbe Intervallbreite

    `schmal`: Halte mit Wert, deren halbe Breite des 95-%-Intervalls unter 0.25 min liegt,
    `schmal_pct` ihr Anteil; Median, 90. Perzentil und Maximum der halben Breite in Minuten.
    `neutral_nur_effekt`: neutral, obwohl das Intervall die 0 nicht enthält.
    """)
    return


@app.cell
def _(WINDOWS, pl, table):
    by_window = (
        table.group_by("nr", "fenster")
        .agg(
            mit_wert=pl.col("grund").is_null().sum(),
            verstaerker=(pl.col("klasse") == "Verstärker").sum(),
            absorber=(pl.col("klasse") == "Absorber").sum(),
            neutral=(pl.col("klasse") == "neutral").sum(),
            neutral_nur_effekt=(
                (pl.col("klasse") == "neutral")
                & ((pl.col("ki_unten") > 0) | (pl.col("ki_oben") < 0))
            ).sum(),
            keine_fahrt=(pl.col("grund") == "keine Fahrt im Fenster").sum(),
            zu_wenige_fahrten=(pl.col("grund") == "zu wenige Fahrten").sum(),
            zu_wenige_tage=(pl.col("grund") == "zu wenige Betriebstage").sum(),
            schmal=(pl.col("halbe_breite") < 0.25).sum(),
            breite_median=pl.col("halbe_breite").median().round(3),
            breite_p90=pl.col("halbe_breite").quantile(0.9).round(3),
            breite_max=pl.col("halbe_breite").max().round(3),
        )
        .sort("nr")
        .with_columns(schmal_pct=(100 * pl.col("schmal") / pl.col("mit_wert")).round(1))
        .drop("nr")
    )
    assert by_window["fenster"].to_list() == WINDOWS
    by_window.head(13)
    return (by_window,)


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (a) und (b)
    """)
    return


@app.cell
def _(compare, five, pl, top12):
    _with_value = int(compare["fahrten"].is_not_null().sum())
    _diff = int((~compare["gleich"]).sum())
    _five_ok = int((~five["zeile"] | five["grund"].is_not_null()).sum())
    _as_expected = int(top12["wie_erwartet"].fill_null(False).sum())
    checks = pl.DataFrame(
        {
            "pruefung": [
                "(a) Halte mit Wert im ganzen Zeitraum",
                "(a) Halte mit einer Abweichung zu Notebook 12",
                "(a) der fünf Halte ohne REAL: keine Zeile oder Grund",
                "(b) Halte der Top 10 aus Notebook 12 mit erwarteter Klasse",
            ],
            "ergebnis": [_with_value, _diff, _five_ok, _as_expected],
            "erwartung": ["= 152", "= 0", "= 5", "= 10"],
            "gehalten": [_with_value == 152, _diff == 0, _five_ok == 5, _as_expected == 10],
        }
    )
    checks.head(4)
    return (checks,)


@app.cell
def _(mo):
    mo.md("""
    ## Halte mit halber Breite ab 0.25 min
    """)
    return


@app.cell
def _(pl, with_value):
    wide = (
        with_value.filter(pl.col("halbe_breite") >= 0.25)
        .sort("nr", "halbe_breite", descending=[False, True])
        .select(
            "fenster",
            "name",
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
