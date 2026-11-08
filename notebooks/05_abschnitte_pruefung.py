import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo

    from sbb_delays import build
    from sbb_delays.download import service_points_snapshot

    return build, duckdb, mo, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Prüfung des Schritts `sections` gegen Issue #14

    Issue #24. Der Build-Schritt `sections` bildet die Abschnittsfahrten für die ganze Schweiz
    und den ganzen Zeitraum aus `period.py`. Eingeschränkt auf Mo 7.9. bis So 13.9.2026 und auf
    Abschnitte mit beiden Halten im Kanton Zürich (fester Schnappschuss der Haltestellenliste)
    muss er dieselbe Basis ergeben wie `notebooks/03_erste_rangliste.py`.

    Erwartung, vor dem Lauf notiert (Befund zu Issue #14 im Log): **148'772 Abschnittsfahrten
    auf 400 Abschnitten**. Weicht eine der beiden Zahlen ab, bildet der Schritt die Abschnitte
    anders als #14.

    Voraussetzung: `uv run build`.
    """)
    return


@app.cell
def _(build, duckdb, service_points_snapshot):
    con = duckdb.connect()
    con.sql(
        f"""
        select count(*) as abschnittsfahrten,
               count(distinct (a_id, b_id)) as abschnitte,
               count(*) filter (where pass_through) as mit_durchfahrt
        from read_parquet('{build.sections_parquet()}') s
        where BETRIEBSTAG between date '2026-09-07' and date '2026-09-13'
          and a_id in (select number::integer from read_csv('{service_points_snapshot()}',
                       delim=';', header=true, all_varchar=true) where cantonAbbreviation = 'ZH')
          and b_id in (select number::integer from read_csv('{service_points_snapshot()}',
                       delim=';', header=true, all_varchar=true) where cantonAbbreviation = 'ZH')
        """
    )
    return


if __name__ == "__main__":
    app.run()
