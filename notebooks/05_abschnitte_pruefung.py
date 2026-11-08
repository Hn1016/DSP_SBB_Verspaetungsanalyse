import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from sbb_delays import build, quality
    from sbb_delays.download import service_points_snapshot

    con = quality.connect()
    return build, con, mo, quality, service_points_snapshot


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
def _(build, con, quality, service_points_snapshot):
    WEEK = "BETRIEBSTAG between date '2026-09-07' and date '2026-09-13'"
    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    # The new step, restricted to the week and the canton.
    con.execute(
        f"""
        create or replace view new_sections as
        select * from read_parquet('{build.sections_parquet()}')
        where {WEEK}
          and a_id in (select BPUIC from zh) and b_id in (select BPUIC from zh)
        """
    )
    # The logic of notebook 03, copied unchanged except for the output columns ZEILE A and B.
    quality.delays(con).filter(WEEK).create_view("week", replace=True)
    con.execute(
        f"""
        create or replace view pairs as
        select BETRIEBSTAG, ZEILE as zeile_a,
               lead(ZEILE) over (partition by {quality.TRIP} order by ZEILE) as zeile_b
        from rail where {WEEK}
        """
    )
    con.execute(
        """
        create or replace view nb03_sections as
        select a.BETRIEBSTAG, p.zeile_a, p.zeile_b, a.BPUIC as a_id, b.BPUIC as b_id,
               b.an_delay - a.ab_delay as section_delay
        from pairs p
        join week a on a.BETRIEBSTAG = p.BETRIEBSTAG and a.ZEILE = p.zeile_a
        join week b on b.BETRIEBSTAG = p.BETRIEBSTAG and b.ZEILE = p.zeile_b
        where a.BPUIC in (select BPUIC from zh) and b.BPUIC in (select BPUIC from zh)
          and a.ab_delay is not null and b.an_delay is not null
          and a.ABFAHRTSZEIT <= b.ANKUNFTSZEIT
        """
    )
    return


@app.cell
def _(con):
    con.sql(
        """
        select count(*) as abschnittsfahrten,
               count(distinct (a_id, b_id)) as abschnitte,
               count(*) filter (where pass_through) as mit_durchfahrt
        from new_sections
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Zeilenvergleich mit der Logik aus Notebook 03

    Gleiche Anzahlen können sich aufheben. Darum werden die Zeilen verglichen (Betriebstag,
    `ZEILE` von A und B, Halte, Streckenverspätung), in beide Richtungen, Duplikate eingeschlossen
    (`except all`). Erwartung, vor dem Lauf notiert: **0 Abweichungen in beiden Richtungen**.
    """)
    return


@app.cell
def _(con):
    cols = "BETRIEBSTAG, zeile_a, zeile_b, a_id, b_id, section_delay"
    con.sql(
        f"""
        select (select count(*) from new_sections) as zeilen_neu,
               (select count(*) from nb03_sections) as zeilen_nb03,
               (select count(*) from (select {cols} from new_sections
                                      except all select {cols} from nb03_sections))
                   as nur_neu,
               (select count(*) from (select {cols} from nb03_sections
                                      except all select {cols} from new_sections))
                   as nur_nb03
        """
    )
    return


if __name__ == "__main__":
    app.run()
