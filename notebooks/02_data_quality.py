import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from sbb_delays import quality

    con = quality.connect()
    return con, mo, quality


@app.cell
def _(mo):
    mo.md("""
    # Datenqualität IstDaten — September 2026, nur Züge

    Prüft die Hypothesen H1–H5 aus `docs/log.md` (Eintrag vom 6.10.2026). Die Logik liegt in
    `src/sbb_delays/quality.py`, Befunde und Entscheidungen stehen im Projektlog.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## H1 — Abdeckung mit gemessenen Zeiten

    Ein Ereignis ist eine Ankunft oder Abfahrt mit Soll-Zeit, die nicht ausgefallen ist.
    `IN_CH`: Halt in der Schweiz (BPUIC beginnt mit 85).
    """)
    return


@app.cell
def _(con, quality):
    quality.status_coverage(con)
    return


@app.cell
def _(con, quality):
    quality.status_coverage(con, by="BETREIBER_ABK").filter("events > 1000")
    return


@app.cell
def _(mo):
    mo.md("""
    ## H2 — Fahrten sind rekonstruierbar

    `ZEILE` ist die Zeilennummer in der Tages-CSV und dient als Haltreihenfolge.
    `same_minute`: Abschnitte, deren Soll-Ankunft in derselben Minute liegt wie die Soll-Abfahrt
    davor (über die Soll-Zeit nicht zu ordnen). `back_in_time`: Soll-Zeit läuft rückwärts.
    """)
    return


@app.cell
def _(con, quality):
    quality.trip_structure(con)
    return


@app.cell
def _(mo):
    mo.md("""
    ## H3 — Ausfälle und Durchfahrten
    """)
    return


@app.cell
def _(con, quality):
    quality.cancelled_trips(con)
    return


@app.cell
def _(con, quality):
    quality.flag_shares(con)
    return


@app.cell
def _(mo):
    mo.md("""
    ## H4 — Halte haben Koordinaten
    """)
    return


@app.cell
def _(con, quality):
    quality.stop_match(con)
    return


@app.cell
def _(mo):
    mo.md("""
    ## H5 — Verspätungswerte sind plausibel

    Verspätung in Minuten, nur `REAL`, nur Halte in der Schweiz, ohne Ausfälle.
    `n_date_errors`: Werte über ±12 Stunden (Datumsfehler in der Quelle).
    """)
    return


@app.cell
def _(con, quality):
    quality.delay_summary(con)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Nebenbefund: Haltverspätung und Minutenauflösung des Fahrplans

    Haltverspätung = Abfahrts- minus Ankunftsverspätung. Bei Soll-Haltezeit 0 (Ankunft und Abfahrt
    in derselben Minute) entspricht sie der tatsächlichen Haltezeit und ist zwangsläufig positiv.
    """)
    return


@app.cell
def _(con, quality):
    quality.dwell_bias(con)
    return


if __name__ == "__main__":
    app.run()
