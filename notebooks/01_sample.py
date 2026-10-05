import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo

    from sbb_delays.paths import ISTDATEN_RAIL

    return ISTDATEN_RAIL, duckdb, mo


@app.cell
def _(mo):
    mo.md("""
    # Stichprobe IstDaten — September 2026, nur Züge

    Datenbasis: `data/processed/istdaten_rail/*.parquet`, erzeugt mit
    `uv run python -m sbb_delays.download --from 2026-09 --to 2026-09` und
    `uv run python -m sbb_delays.load`.
    """)
    return


@app.cell
def _(ISTDATEN_RAIL, duckdb):
    rail = duckdb.sql(f"select * from read_parquet('{ISTDATEN_RAIL}/*.parquet')")
    rail.limit(200)
    return (rail,)


@app.cell
def _(mo):
    mo.md("""
    ## Rechenprobe: Zeilen pro Betriebstag
    """)
    return


@app.cell
def _(duckdb, rail):
    duckdb.sql("""
        select BETRIEBSTAG, dayname(BETRIEBSTAG) as wochentag, count(*) as zeilen,
               count(distinct FAHRT_BEZEICHNER) as fahrten
        from rail
        group by all
        order by BETRIEBSTAG
    """)
    return


if __name__ == "__main__":
    app.run()
