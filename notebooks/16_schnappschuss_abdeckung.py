import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from sbb_delays import quality
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.period import END, SERVICE_POINTS_DATE, START
    from sbb_delays.sections import period_days

    con = quality.connect()
    first, last = period_days(START, END)
    return SERVICE_POINTS_DATE, con, first, last, mo, quality, service_points_snapshot


@app.cell
def _(SERVICE_POINTS_DATE, first, last, mo):
    mo.md(f"""
    # Halte im Zeitraum, die im Schnappschuss fehlen

    Issue #54, für Issue #28 (Frage 2). Erwartung und Regeln im Projektlog (Hypothese vom
    24.11.2026, vor der Zählung gepusht, Commit `18bf729`):

    - **(a)** Höchstens 0.1 % der Schweizer Halteereignisse im Zeitraum betreffen einen Halt, der
      im Schnappschuss fehlt.
    - **(b)** Unter den fehlenden Halten ist keiner im Raum Zürich (nach Namen beurteilt).

    Halteereignis: jede Zeile aus `quality.delays()` vom {first} bis {last}. Ein Halt fehlt, wenn
    seine `BPUIC` nicht als `number` im Schnappschuss vom {SERVICE_POINTS_DATE} steht, unabhängig
    von Koordinaten (so ordnet die Pipeline den Kanton zu).
    """)
    return


@app.cell
def _(con, first, last, quality, service_points_snapshot):
    con.execute(
        f"""
        create or replace view snapshot as
        select distinct number::integer as BPUIC
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        """
    )
    quality.delays(con).create_view("events", replace=True)
    con.execute(
        f"""
        create or replace view stops as
        select BPUIC,
               mode(HALTESTELLEN_NAME) as name,
               count(*) as ereignisse,
               count(*) filter (
                   AN_PROGNOSE_STATUS = 'REAL' or AB_PROGNOSE_STATUS = 'REAL'
               ) as mit_real,
               min(BETRIEBSTAG) as erster_tag,
               max(BETRIEBSTAG) as letzter_tag,
               BPUIC not in (select BPUIC from snapshot) as fehlt
        from events
        where BETRIEBSTAG between '{first}' and '{last}'
        group by BPUIC
        """
    )
    return


@app.cell
def _(con, mo):
    summary = con.sql(
        """
        select count(*) as halte,
               count(*) filter (fehlt) as halte_fehlend,
               sum(ereignisse) as ereignisse,
               coalesce(sum(ereignisse) filter (fehlt), 0) as ereignisse_fehlend,
               round(100 * coalesce(sum(ereignisse) filter (fehlt), 0) / sum(ereignisse), 4)
                   as pct_ereignisse_fehlend,
               round(100 * sum(mit_real) / sum(ereignisse), 1) as pct_mit_real
        from stops
        """
    ).pl()
    mo.ui.table(summary)
    return (summary,)


@app.cell
def _(mo):
    mo.md("""
    ## Fehlende Halte

    Alle Halte, die im Zeitraum vorkommen und im Schnappschuss fehlen, nach Zahl der Ereignisse.
    Name aus den Tagesdateien (häufigster Name im Zeitraum). `zh_im_namen` ist nur eine Hilfe für
    das Urteil «Raum Zürich»: Der Name enthält «Zürich» oder «ZH».
    """)
    return


@app.cell
def _(con, mo):
    missing = con.sql(
        """
        select BPUIC, name, ereignisse, mit_real, erster_tag, letzter_tag,
               name ilike '%zürich%' or name like '% ZH%' as zh_im_namen
        from stops
        where fehlt
        order by ereignisse desc
        """
    ).pl()
    mo.ui.table(missing)
    return (missing,)


@app.cell
def _(missing, mo, summary):
    _pct = summary["pct_ereignisse_fehlend"][0]
    _zh = missing.filter(missing["zh_im_namen"]).height
    mo.md(f"""
    ## Prüfung

    - **(a)** {_pct} % der Ereignisse betreffen einen fehlenden Halt:
      **{"gehalten" if _pct <= 0.1 else "gescheitert"}** (Erwartung höchstens 0.1 %).
    - **(b)** {missing.height} fehlende Halte, davon {_zh} mit «Zürich» oder «ZH» im Namen. Das
      Urteil «Raum Zürich» trifft der Befund im Log anhand der Liste oben.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Gegenprobe und Namen (nach der Zählung ergänzt)

    Gegenprobe: Ohne die fünf Halte mit den meisten Ereignissen im Schnappschuss muss dieselbe
    Abfrage genau diese fünf als fehlend melden. Sonst könnte die Zählung gar nicht scheitern.

    Namen: Halte, deren Name in den Tagesdateien vom Namen im Schnappschuss abweicht. Eine andere
    Nummernvergabe für einen anderen Ort fiele hier auf.
    """)
    return


@app.cell
def _(con, mo):
    _found = con.sql(
        """
        with reduced as (
            select BPUIC from snapshot
            where BPUIC not in (select BPUIC from stops order by ereignisse desc limit 5)
        )
        select count(*) from stops where BPUIC not in (select BPUIC from reduced)
        """
    ).fetchone()[0]
    assert _found == 5, f"Gegenprobe: {_found} statt 5 fehlende Halte gemeldet"
    mo.md(f"Gegenprobe: {_found} von 5 entfernten Halten als fehlend gemeldet.")
    return


@app.cell
def _(con, mo, service_points_snapshot):
    names = con.sql(
        f"""
        with snap as (
            select number::integer as BPUIC, designationOfficial as name_schnappschuss,
                   cantonAbbreviation as kanton
            from read_csv('{service_points_snapshot()}', delim=';', header=true,
                          all_varchar=true)
        )
        select BPUIC, name, name_schnappschuss, kanton, ereignisse
        from stops join snap using (BPUIC)
        where name <> name_schnappschuss
        order by ereignisse desc
        """
    ).pl()
    mo.ui.table(names)
    return (names,)


if __name__ == "__main__":
    app.run()
