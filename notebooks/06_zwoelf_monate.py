import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from sbb_delays import quality
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.period import END, START
    from sbb_delays.sections import period_days

    con = quality.connect()
    first, last = period_days(START, END)
    return con, first, last, mo, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Zwölf Monate: Annahmen A3 und A4, Halte im Schnappschuss

    Issue #30. Erwartungen im Projektlog (Hypothese vom 8.11.2026, vor der Analyse gepusht,
    Commit `ed40418`):

    - **(A3)** `REAL`-Anteil im Kanton Zürich in jedem Monat über 95 %, Unterschied zwischen den
      beiden Fahrplänen unter 1 Prozentpunkt.
    - **(A4)** In jedem Monat widerspricht die `ZEILE`-Reihenfolge bei weniger als 0.1 % der
      Fahrten der Soll-Zeit.
    - **(Halte)** Kein im Kanton Zürich bedienter Halt fehlt im Schnappschuss.

    Fahrplan 2025 bis 13.12.2025, Fahrplan 2026 ab 14.12.2025.
    """)
    return


@app.cell
def _(con, first, last, service_points_snapshot):
    PERIOD = f"BETRIEBSTAG between date '{first}' and date '{last}'"
    TIMETABLE = "case when BETRIEBSTAG <= date '2025-12-13' then 2025 else 2026 end"

    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    # A3, counted as in H1 (quality.status_coverage): one event per arrival or departure with a
    # scheduled time at a stop that is not cancelled; here only stops in canton Zurich.
    con.execute(
        f"""
        create or replace view zh_events as
        select BETRIEBSTAG, AN_PROGNOSE_STATUS as status from rail
        where {PERIOD} and ANKUNFTSZEIT is not null and not FAELLT_AUS_TF
          and BPUIC in (select BPUIC from zh)
        union all
        select BETRIEBSTAG, AB_PROGNOSE_STATUS from rail
        where {PERIOD} and ABFAHRTSZEIT is not null and not FAELLT_AUS_TF
          and BPUIC in (select BPUIC from zh)
        """
    )
    # A4: a trip contradicts when, for two consecutive rows by ZEILE, the first scheduled time of
    # the later row lies before the last scheduled time of the earlier row. All trips, as loaded.
    con.execute(
        f"""
        create or replace view trip_order as
        select BETRIEBSTAG, FAHRT_BEZEICHNER, bool_or(next_first < this_last) as contradicts
        from (
            select BETRIEBSTAG, FAHRT_BEZEICHNER,
                   coalesce(ABFAHRTSZEIT, ANKUNFTSZEIT) as this_last,
                   lead(coalesce(ANKUNFTSZEIT, ABFAHRTSZEIT)) over (
                       partition by BETRIEBSTAG, FAHRT_BEZEICHNER order by ZEILE
                   ) as next_first
            from rail where {PERIOD}
        )
        group by all
        """
    )
    return (TIMETABLE,)


@app.cell
def _(mo):
    mo.md("""
    ## Pro Monat
    """)
    return


@app.cell
def _(con):
    per_month = con.sql(
        """
        with a3 as (
            select strftime(BETRIEBSTAG, '%Y-%m') as monat,
                   count(distinct BETRIEBSTAG) as tage,
                   round(100 * avg((status = 'REAL')::int), 2) as real_pct_zh
            from zh_events group by all
        ),
        a4 as (
            select strftime(BETRIEBSTAG, '%Y-%m') as monat,
                   count(*) as fahrten,
                   count(*) filter (where contradicts) as fahrten_widerspruch,
                   round(100 * avg(contradicts::int), 3) as widerspruch_pct
            from trip_order group by all
        )
        select * from a3 join a4 using (monat) order by monat
        """
    ).pl()
    per_month.head(12)
    return (per_month,)


@app.cell
def _(mo):
    mo.md("""
    ## A3: Vergleich der Fahrpläne
    """)
    return


@app.cell
def _(TIMETABLE, con):
    by_timetable = con.sql(
        f"""
        select {TIMETABLE} as fahrplan, count(distinct BETRIEBSTAG) as tage, count(*) as ereignisse,
               round(100 * avg((status = 'REAL')::int), 2) as real_pct_zh
        from zh_events group by all order by fahrplan
        """
    ).pl()
    by_timetable.head(2)
    return (by_timetable,)


@app.cell
def _(by_timetable, per_month):
    import polars as pl

    _diff = abs(by_timetable["real_pct_zh"][1] - by_timetable["real_pct_zh"][0])
    pl.DataFrame(
        {
            "pruefung": ["A3 jeder Monat über 95 %", "A3 Unterschied Fahrpläne", "A4 jeder Monat"],
            "ergebnis": [
                f"min {per_month['real_pct_zh'].min()} %",
                f"{_diff:.2f} Prozentpunkte",
                f"max {per_month['widerspruch_pct'].max()} %",
            ],
            "erwartung": ["> 95 %", "< 1", "< 0.1 %"],
            "gehalten": [
                bool(per_month["real_pct_zh"].min() > 95),
                bool(_diff < 1),
                bool(per_month["widerspruch_pct"].max() < 0.1),
            ],
        }
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Halte, die im Schnappschuss fehlen

    Ob ein fehlender Halt in Zürich liegt, steht gerade nicht im Schnappschuss. Darum: jede
    Schweizer `BPUIC` (85…) des Zeitraums, die im Schnappschuss fehlt, mit Name und Fahrten.
    """)
    return


@app.cell
def _(con, first, last, service_points_snapshot):
    con.sql(
        f"""
        select BPUIC, any_value(HALTESTELLEN_NAME) as name,
               count(distinct (BETRIEBSTAG, FAHRT_BEZEICHNER)) as fahrten,
               min(BETRIEBSTAG) as erster_tag, max(BETRIEBSTAG) as letzter_tag
        from rail
        where BETRIEBSTAG between date '{first}' and date '{last}'
          and BPUIC // 100000 = 85
          and BPUIC not in (
              select number::integer
              from read_csv('{service_points_snapshot()}', delim=';', header=true,
                            all_varchar=true)
          )
        group by BPUIC
        order by fahrten desc
        """
    ).pl()
    return


if __name__ == "__main__":
    app.run()
