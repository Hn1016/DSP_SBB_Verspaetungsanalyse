import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo
    import polars as pl

    from sbb_delays import build
    from sbb_delays.download import service_points_snapshot
    from sbb_delays.paths import ISTDATEN_RAIL
    from sbb_delays.period import END, START
    from sbb_delays.sections import period_days

    con = duckdb.connect()
    first, last = period_days(START, END)
    return ISTDATEN_RAIL, build, con, first, last, mo, pl, service_points_snapshot


@app.cell
def _(mo):
    mo.md("""
    # Annahme A10: genug Betriebstage pro Abschnitt und Zeitfenster

    Issue #39. Erwartung und Zählweise im Projektlog (Hypothese vom 12.11.2026, vor der Analyse
    gepusht, Commit `12fea26`). Basis: die Zürcher Abschnitte mit mindestens 100 Fahrten und 30
    Betriebstagen im Zeitraum (Befund #23).

    - **(1)** Mindestens 80 % der Abschnitte erreichen in Morgenspitze, Tag und Abendspitze, je
      Montag bis Freitag, mindestens 20 Betriebstage.
    - **(2)** Abend/Nacht (Montag bis Freitag) und Samstag/Sonntag: weniger, aber mindestens 60 %.
    - **(3)** Mindestens 90 % kommen in beiden Fahrplänen mit mindestens 20 Betriebstagen vor.

    Ein Betriebstag zählt in einem Fenster, wenn der Abschnitt dort mindestens eine
    Abschnittsfahrt hat. Tageszeit nach der Soll-Abfahrt an A, Wochentag und Fahrplan nach dem
    `BETRIEBSTAG`.
    """)
    return


@app.cell
def _(ISTDATEN_RAIL, build, con, first, last, service_points_snapshot):
    MIN_TRIPS, MIN_DAYS, MIN_WINDOW_DAYS = 100, 30, 20  # log 2026-11-10, «Systematisch»

    con.execute(
        f"""
        create or replace view zh as
        select number::integer as BPUIC, designationOfficial as name
        from read_csv('{service_points_snapshot()}', delim=';', header=true, all_varchar=true)
        where cantonAbbreviation = 'ZH'
        """
    )
    # One row per section and operating day, with the time-of-day windows it has a trip in. The
    # scheduled departure at A is not in the sections file; it comes from the daily files.
    con.execute(
        f"""
        create or replace table section_days as
        select s.a_id, s.b_id, s.BETRIEBSTAG,
               count(*) as fahrten,
               count(*) filter (where r.ABFAHRTSZEIT is null) as ohne_abfahrt,
               bool_or(hour(r.ABFAHRTSZEIT) between 6 and 8) as morgenspitze,
               bool_or(hour(r.ABFAHRTSZEIT) between 9 and 15) as tag,
               bool_or(hour(r.ABFAHRTSZEIT) between 16 and 18) as abendspitze,
               bool_or(hour(r.ABFAHRTSZEIT) >= 19 or hour(r.ABFAHRTSZEIT) < 6) as abend_nacht
        from read_parquet('{build.sections_parquet()}') s
        join (
            select BETRIEBSTAG, ZEILE, ABFAHRTSZEIT
            from read_parquet('{ISTDATEN_RAIL}/*.parquet')
            where BETRIEBSTAG between date '{first}' and date '{last}'
        ) r on r.BETRIEBSTAG = s.BETRIEBSTAG and r.ZEILE = s.zeile_a
        where s.a_id in (select BPUIC from zh) and s.b_id in (select BPUIC from zh)
        group by s.a_id, s.b_id, s.BETRIEBSTAG
        """
    )
    return MIN_DAYS, MIN_TRIPS, MIN_WINDOW_DAYS


@app.cell
def _(MIN_DAYS, MIN_TRIPS, con):
    WEEKDAY = "isodow(BETRIEBSTAG) <= 5"
    WINDOWS = {
        # crossed, as in the expectations
        "Morgenspitze Mo–Fr": f"morgenspitze and {WEEKDAY}",
        "Tag Mo–Fr": f"tag and {WEEKDAY}",
        "Abendspitze Mo–Fr": f"abendspitze and {WEEKDAY}",
        "Abend/Nacht Mo–Fr": f"abend_nacht and {WEEKDAY}",
        "Samstag/Sonntag": f"not {WEEKDAY}",
        # each window of issue #32 on its own
        "Morgenspitze": "morgenspitze",
        "Tag": "tag",
        "Abendspitze": "abendspitze",
        "Abend/Nacht": "abend_nacht",
        "Montag–Freitag": WEEKDAY,
        "Winter (Dez–Feb)": "month(BETRIEBSTAG) in (12, 1, 2)",
        "Frühling (Mär–Mai)": "month(BETRIEBSTAG) in (3, 4, 5)",
        "Sommer (Jun–Aug)": "month(BETRIEBSTAG) in (6, 7, 8)",
        "Herbst (Sep–Nov)": "month(BETRIEBSTAG) in (9, 10, 11)",
        "Fahrplan 2025": "BETRIEBSTAG <= date '2025-12-13'",
        "Fahrplan 2026": "BETRIEBSTAG > date '2025-12-13'",
    }
    _counts = ",\n".join(
        f"""count(*) filter (where {condition}) as "{name}\""""
        for name, condition in WINDOWS.items()
    )
    per_section = con.sql(
        f"""
        select a.name || ' → ' || b.name as abschnitt,
               sum(d.fahrten) as fahrten, count(*) as tage, sum(d.ohne_abfahrt) as ohne_abfahrt,
               {_counts}
        from section_days d
        join zh a on a.BPUIC = d.a_id
        join zh b on b.BPUIC = d.b_id
        group by d.a_id, d.b_id, a.name, b.name
        having sum(d.fahrten) >= {MIN_TRIPS} and count(*) >= {MIN_DAYS}
        """
    ).pl()
    return WINDOWS, per_section


@app.cell
def _(mo, per_section):
    mo.md(f"""
    ## Anteil der Abschnitte je Fenster

    {per_section.height} Abschnitte in der Basis (Befund #23: 394), {per_section["fahrten"].sum()}
    Abschnittsfahrten, davon {per_section["ohne_abfahrt"].sum()} ohne Soll-Abfahrt an A.
    `erreicht_pct`: Anteil der Abschnitte mit mindestens 20 Betriebstagen im Fenster; `ohne_fahrt`:
    Abschnitte ohne einen Betriebstag im Fenster; `tage_1_19` und `tage_20_39`: Abschnitte knapp
    unter und knapp über der Mindestzahl; Median und 10. Perzentil der Betriebstage.
    """)
    return


@app.cell
def _(MIN_WINDOW_DAYS, WINDOWS, per_section, pl):
    by_window = pl.DataFrame(
        {
            "fenster": list(WINDOWS),
            "erreicht": [(per_section[w] >= MIN_WINDOW_DAYS).sum() for w in WINDOWS],
            "erreicht_pct": [
                round(100 * (per_section[w] >= MIN_WINDOW_DAYS).mean(), 1) for w in WINDOWS
            ],
            "ohne_fahrt": [(per_section[w] == 0).sum() for w in WINDOWS],
            "tage_1_19": [per_section[w].is_between(1, 19).sum() for w in WINDOWS],
            "tage_20_39": [per_section[w].is_between(20, 39).sum() for w in WINDOWS],
            "tage_median": [per_section[w].median() for w in WINDOWS],
            "tage_p10": [per_section[w].quantile(0.1) for w in WINDOWS],
        }
    )
    by_window.head(len(WINDOWS))
    return (by_window,)


@app.cell
def _(mo):
    mo.md("""
    ## Erwartungen (1), (2) und (3)
    """)
    return


@app.cell
def _(MIN_WINDOW_DAYS, by_window, per_section, pl):
    def _reached(*windows):
        return pl.all_horizontal([pl.col(w) >= MIN_WINDOW_DAYS for w in windows])

    def _pct(expression):
        return round(100 * per_section.select(expression.mean()).item(), 1)

    _share = dict(zip(by_window["fenster"], by_window["erreicht_pct"], strict=True))
    _daytime = ["Morgenspitze Mo–Fr", "Tag Mo–Fr", "Abendspitze Mo–Fr"]
    _all_daytime = _pct(_reached(*_daytime))
    _lowest_daytime = min(_share[w] for w in _daytime)
    _night, _weekend = _share["Abend/Nacht Mo–Fr"], _share["Samstag/Sonntag"]
    _both_timetables = _pct(_reached("Fahrplan 2025", "Fahrplan 2026"))
    pl.DataFrame(
        {
            "pruefung": [
                "(1) alle drei Tageszeit-Fenster Mo–Fr",
                "(2) Abend/Nacht Mo–Fr",
                "(2) Samstag/Sonntag",
                "(3) beide Fahrpläne",
            ],
            "ergebnis_pct": [_all_daytime, _night, _weekend, _both_timetables],
            "erwartung": [
                "≥ 80",
                f"≥ 60 und < {_lowest_daytime}",
                f"≥ 60 und < {_lowest_daytime}",
                "≥ 90",
            ],
            "gehalten": [
                _all_daytime >= 80,
                60 <= _night < _lowest_daytime,
                60 <= _weekend < _lowest_daytime,
                _both_timetables >= 90,
            ],
        }
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Abschnitte, die nicht in beiden Fahrplänen vorkommen

    Abschnitte der Basis mit weniger als 20 Betriebstagen in einem der beiden Fahrpläne.
    """)
    return


@app.cell
def _(MIN_WINDOW_DAYS, per_section, pl):
    one_timetable = (
        per_section.filter(
            (pl.col("Fahrplan 2025") < MIN_WINDOW_DAYS)
            | (pl.col("Fahrplan 2026") < MIN_WINDOW_DAYS)
        )
        .select("abschnitt", "fahrten", "tage", "Fahrplan 2025", "Fahrplan 2026")
        .sort("fahrten", descending=True)
    )
    one_timetable.head(50)
    return (one_timetable,)


@app.cell
def _(mo):
    mo.md("""
    ## Was die Mindestzahl im ganzen Zeitraum ausschliesst

    Alle Zürcher Abschnitte, geteilt nach der Mindestzahl von 100 Fahrten und 30 Betriebstagen.
    """)
    return


@app.cell
def _(MIN_DAYS, MIN_TRIPS, con):
    con.sql(
        f"""
        select case when fahrten >= {MIN_TRIPS} and tage >= {MIN_DAYS} then 'in der Basis'
                    when fahrten < {MIN_TRIPS} and tage < {MIN_DAYS}
                        then 'zu wenige Fahrten und Tage'
                    when fahrten < {MIN_TRIPS} then 'zu wenige Fahrten'
                    else 'zu wenige Betriebstage' end as gruppe,
               count(*) as abschnitte, sum(fahrten) as fahrten,
               max(fahrten) as fahrten_max, max(tage) as tage_max
        from (
            select a_id, b_id, sum(fahrten) as fahrten, count(*) as tage
            from section_days group by a_id, b_id
        )
        group by gruppe
        order by fahrten desc
        """
    ).pl()
    return


if __name__ == "__main__":
    app.run()
