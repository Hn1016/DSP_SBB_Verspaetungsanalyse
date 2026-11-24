import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    from itertools import combinations

    import duckdb
    import marimo as mo
    import polars as pl
    from scipy import stats

    from sbb_delays import build
    from sbb_delays.download import service_points_snapshot

    con = duckdb.connect()
    return build, combinations, con, mo, pl, service_points_snapshot, stats


@app.cell
def _(mo):
    mo.md("""
    # Muster der Rangliste über Tageszeit, Wochentag und Jahreszeit

    Issue #59. Erwartung und Regeln im Projektlog (Hypothese vom 24.11.2026, vor der Analyse
    gepusht, Commit `0c34262`). Die Schwellen stammen aus Issue #32 und werden nicht angepasst.

    - Verglichen wird das **Mittel pro Fahrt nach Referenzwert** (`mittel_referenz`), nur über
      Abschnitte mit Wert in beiden Fenstern eines Paars.
    - **Top 10** eines Fensters: die zehn Verstärker dieses Fensters mit der grössten
      Hauptkennzahl (Issue #45), verglichen mit der Top 10 im ganzen Zeitraum.
    - **Urteil je Gruppe:** «stabil», wenn der Median der Spearman-Werte über die Paare mindestens
      0.7 beträgt und jedes Fenster mindestens 7 der Top 10 hat; «teilweise», wenn genau eines
      gehalten ist; «nicht stabil», wenn keines.
    """)
    return


@app.cell
def _(build, con, pl, service_points_snapshot):
    KEY = ["a_id", "b_id"]
    GROUPS = ["Tageszeit", "Wochentag", "Jahreszeit"]

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
    whole = table.filter(pl.col("fenster") == "ganzer Zeitraum")
    windows = {
        g: table.filter(pl.col("fenster_typ") == g)["fenster"].unique(maintain_order=True).to_list()
        for g in GROUPS
    }
    return GROUPS, KEY, table, whole, windows, with_names


@app.cell
def _(mo):
    mo.md("""
    Rechenprobe vor allem anderen: Die Fenster einer Gruppe teilen den Zeitraum ohne Lücke und
    ohne Überschneidung. Dann ist für jeden Abschnitt die Summe der Fahrten über die Fenster einer
    Gruppe gleich den Fahrten im ganzen Zeitraum.
    """)
    return


@app.cell
def _(GROUPS, KEY, pl, table, whole):
    _sums = (
        table.filter(pl.col("fenster_typ").is_in(GROUPS))
        .group_by(*KEY, "fenster_typ")
        .agg(pl.col("fahrten").sum())
        .join(whole.select(*KEY, pl.col("fahrten").alias("fahrten_ganz")), on=KEY)
    )
    assert (_sums["fahrten"] == _sums["fahrten_ganz"]).all(), "Fenster teilen den Zeitraum nicht"
    _sums.group_by("fenster_typ").agg(abschnitte=pl.len(), fahrten=pl.col("fahrten").sum())
    return


@app.cell
def _(KEY, pl, stats):
    def valued(part):
        return part.filter(pl.col("grund").is_null())

    def top10(part):
        """The ten amplifiers of a window with the largest zuwachs (issue #45)."""
        return (
            part.filter(pl.col("klasse") == "Verstärker").sort("zuwachs", descending=True).head(10)
        )

    def spearman(part_1, part_2, column="mittel_referenz"):
        """Spearman correlation of a column over the sections with a value in both windows."""
        both = valued(part_1).join(valued(part_2), on=KEY, suffix="_2")
        return stats.spearmanr(both[column], both[f"{column}_2"]).statistic, both.height

    return spearman, top10, valued


@app.cell
def _(mo):
    mo.md("""
    ## Spearman je Paar von Fenstern

    `weggefallen`: Abschnitte mit Wert in genau einem der beiden Fenster. `spearman_zuwachs` ist
    beschreibend, nicht Teil des Urteils: die Grösse, mit der #48 gerechnet hat.
    """)
    return


@app.cell
def _(GROUPS, combinations, mo, pl, spearman, table, valued, windows):
    _rows = []
    for _g in GROUPS:
        for _w1, _w2 in combinations(windows[_g], 2):
            _p1 = table.filter(pl.col("fenster") == _w1)
            _p2 = table.filter(pl.col("fenster") == _w2)
            _rho, _n = spearman(_p1, _p2)
            _rows.append(
                {
                    "gruppe": _g,
                    "fenster_1": _w1,
                    "fenster_2": _w2,
                    "in_beiden": _n,
                    "weggefallen": valued(_p1).height + valued(_p2).height - 2 * _n,
                    "spearman": round(_rho, 3),
                    "spearman_zuwachs": round(spearman(_p1, _p2, "zuwachs")[0], 3),
                }
            )
    pairs = pl.DataFrame(_rows)
    assert pairs.group_by("gruppe").len().sort("gruppe")["len"].to_list() == [6, 6, 1]
    mo.ui.table(pairs)
    return (pairs,)


@app.cell
def _(mo):
    mo.md("""
    ## Top 10 je Fenster

    `top10_wie_ganz`: wie viele der Top 10 des Fensters auch in der Top 10 des ganzen Zeitraums
    stehen.
    """)
    return


@app.cell
def _(GROUPS, KEY, mo, pl, table, top10, whole, windows):
    top_whole = top10(whole)
    assert top_whole.height == 10
    overlaps = pl.DataFrame(
        [
            {
                "gruppe": _g,
                "fenster": _w,
                "top10_wie_ganz": top10(table.filter(pl.col("fenster") == _w))
                .join(top_whole, on=KEY)
                .height,
            }
            for _g in GROUPS
            for _w in windows[_g]
        ]
    )
    mo.ui.table(overlaps)
    return overlaps, top_whole


@app.cell
def _(mo):
    mo.md("""
    ## Urteil je Gruppe
    """)
    return


@app.cell
def _(GROUPS, mo, overlaps, pairs, pl):
    _rows = []
    for _g in GROUPS:
        _p = pairs.filter(pl.col("gruppe") == _g).sort("spearman")
        _o = overlaps.filter(pl.col("gruppe") == _g).sort("top10_wie_ganz")
        _median = _p["spearman"].median()
        _k1 = _median >= 0.7
        _k2 = _o["top10_wie_ganz"].min() >= 7
        _rows.append(
            {
                "gruppe": _g,
                "spearman_median": round(_median, 3),
                "schwächstes_paar": f"{_p['fenster_1'][0]} / {_p['fenster_2'][0]}",
                "spearman_min": _p["spearman"][0],
                "schwächstes_fenster": _o["fenster"][0],
                "top10_min": _o["top10_wie_ganz"][0],
                "spearman_gehalten": _k1,
                "top10_gehalten": _k2,
                "urteil": "stabil"
                if _k1 and _k2
                else "teilweise"
                if _k1 or _k2
                else "nicht stabil",
            }
        )
    verdict = pl.DataFrame(_rows)
    mo.ui.table(verdict)
    return (verdict,)


@app.cell
def _(mo):
    mo.md("""
    ## Top 10 je Fenster mit Namen

    Je Fenster die Abschnitte, die dort in der Top 10 stehen, im ganzen Zeitraum aber nicht
    (`neu`), und die aus der Top 10 des ganzen Zeitraums, die dort fehlen (`fehlt`), mit Klasse
    und Mittel pro Fahrt im Fenster.
    """)
    return


@app.cell
def _(GROUPS, KEY, mo, pl, table, top10, top_whole, windows, with_names):
    _rows = []
    for _g in GROUPS:
        for _w in windows[_g]:
            _part = table.filter(pl.col("fenster") == _w)
            _top = top10(_part)
            for _art, _frame in [
                ("neu", _top.join(top_whole, on=KEY, how="anti")),
                ("fehlt", top_whole.select(KEY).join(_top, on=KEY, how="anti")),
            ]:
                _rows.append(
                    _frame.select(KEY)
                    .join(_part, on=KEY)
                    .select(*KEY, "klasse", "grund", "mittel_referenz", "rang")
                    .with_columns(gruppe=pl.lit(_g), fenster=pl.lit(_w), art=pl.lit(_art))
                )
    top_changes = with_names(pl.concat(_rows)).select(
        "gruppe",
        "fenster",
        "art",
        "abschnitt",
        "klasse",
        "grund",
        pl.col("mittel_referenz").round(2),
        "rang",
    )
    mo.ui.table(top_changes)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Abschnitte, die nur in einem Fenster Verstärker sind

    Je Gruppe die Abschnitte mit Wert in allen Fenstern der Gruppe, die in genau einem Fenster
    «Verstärker» sind, nach dem Mittel pro Fahrt in diesem Fenster. `spanne`: grösstes minus
    kleinstes Mittel pro Fahrt über die Fenster der Gruppe.
    """)
    return


@app.cell
def _(GROUPS, KEY, pl, table, windows, with_names):
    _parts = []
    for _g in GROUPS:
        _rows = table.filter((pl.col("fenster_typ") == _g) & pl.col("grund").is_null())
        _parts.append(
            _rows.group_by(KEY)
            .agg(
                fenster_mit_wert=pl.len(),
                verstaerker_in=pl.col("fenster").filter(pl.col("klasse") == "Verstärker"),
                mittel_dort=pl.col("mittel_referenz").filter(pl.col("klasse") == "Verstärker"),
                spanne=pl.col("mittel_referenz").max() - pl.col("mittel_referenz").min(),
            )
            .filter(
                (pl.col("fenster_mit_wert") == len(windows[_g]))
                & (pl.col("verstaerker_in").list.len() == 1)
            )
            .with_columns(
                gruppe=pl.lit(_g),
                verstaerker_in=pl.col("verstaerker_in").list.first(),
                mittel_dort=pl.col("mittel_dort").list.first().round(2),
                spanne=pl.col("spanne").round(2),
            )
        )
    only_one = with_names(pl.concat(_parts)).select(
        "gruppe", "verstaerker_in", "abschnitt", "mittel_dort", "spanne"
    )
    (
        only_one.group_by("gruppe", "verstaerker_in").len().sort("gruppe", "verstaerker_in"),
        only_one.sort("gruppe", "mittel_dort", descending=[False, True])
        .group_by("gruppe", maintain_order=True)
        .head(5),
    )
    return


if __name__ == "__main__":
    app.run()
