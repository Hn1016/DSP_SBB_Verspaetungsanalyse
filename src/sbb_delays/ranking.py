"""Ranking of the Zurich sections per time window: amplifier, absorber or neutral (issue #38).

One row per section (a_id, b_id) and window, with a value or a named reason. Rules: log
2026-11-10 (issue #32), reference value per scheduled running time (issue #23), details in the
log of 2026-11-12, «Details der Rangliste»:
- Reference value: mean section delay of the class of the scheduled running time (0, 1, 2, 3,
  4, 5+ minutes) over all passages; the same for every window.
- Two means after the reference value. mittel_referenz is the mean over the trips; zuwachs =
  mittel_referenz x fahrten and gives the rank within a window. tagesmittel is the mean of the
  daily means; its 95 % interval (t distribution over the operating days) gives the class.
- Class: «Verstärker» if the interval lies above 0 and tagesmittel >= min_effect, «Absorber» if
  it lies below 0 and tagesmittel <= -min_effect, else «neutral». Early arrivals are not capped.
- Reason instead of a value, checked in this order (log 2026-11-14, «Name und Reihenfolge der
  Gründe»): «zu wenige Fahrten» (fewer than min_trips in the whole period), «zu wenige
  Betriebstage» (fewer than min_days in the whole period), «keine Fahrt im Fenster», «zu wenige
  Betriebstage» (fewer than min_days_window in the window). «nie gemessen» is not a reason
  here: it names a stop without a REAL time (log 2026-10-25).
- Time of day by the scheduled departure at A, start included, end excluded; weekday, season
  and timetable by BETRIEBSTAG.
"""

from pathlib import Path

import duckdb
import polars as pl
from scipy import stats

from sbb_delays.download import service_points_snapshot

# Minimums and effect size, kept after the finding on A10 (log 2026-11-12, issue #39).
MIN_TRIPS = 100  # measured trips of a section in the whole period
MIN_DAYS = 30  # operating days with a measurement in the whole period
MIN_DAYS_WINDOW = 20  # operating days with a measurement in the window
MIN_EFFECT = 0.25  # minutes; smallest mean of the daily means of an amplifier or absorber

CONFIDENCE = 0.95

# (fenster_typ, fenster, condition on a section passage)
_WINDOWS = [
    ("Zeitraum", "ganzer Zeitraum", "true"),
    ("Tageszeit", "Morgenspitze", "hour(abfahrt_a) between 6 and 8"),
    ("Tageszeit", "Tag", "hour(abfahrt_a) between 9 and 15"),
    ("Tageszeit", "Abendspitze", "hour(abfahrt_a) between 16 and 18"),
    ("Tageszeit", "Abend/Nacht", "hour(abfahrt_a) >= 19 or hour(abfahrt_a) < 6"),
    ("Wochentag", "Mo–Fr", "isodow(BETRIEBSTAG) <= 5"),
    ("Wochentag", "Sa/So", "isodow(BETRIEBSTAG) >= 6"),
    ("Jahreszeit", "Winter", "month(BETRIEBSTAG) in (12, 1, 2)"),
    ("Jahreszeit", "Frühling", "month(BETRIEBSTAG) in (3, 4, 5)"),
    ("Jahreszeit", "Sommer", "month(BETRIEBSTAG) in (6, 7, 8)"),
    ("Jahreszeit", "Herbst", "month(BETRIEBSTAG) in (9, 10, 11)"),
    ("Fahrplan", "Fahrplan 2025", "BETRIEBSTAG < date '2025-12-14'"),
    ("Fahrplan", "Fahrplan 2026", "BETRIEBSTAG >= date '2025-12-14'"),
]
WINDOWS = [(kind, name) for kind, name, _ in _WINDOWS]

# Class of the scheduled running time, as in notebooks/07_rangliste_referenzwert.py.
_CLASS = "case when scheduled_min >= 5 then '5+' else scheduled_min::varchar end"

_VALUE_COLUMNS = ["mittel_roh", "mittel_referenz", "tagesmittel", "ki_unten", "ki_oben", "zuwachs"]


def zurich_sections(
    con: duckdb.DuckDBPyConnection, sections_file: Path, service_points: Path | None = None
) -> duckdb.DuckDBPyRelation:
    """The section passages of sections_file with both stops in the canton of Zurich."""
    service_points = service_points or service_points_snapshot()
    return con.sql(
        f"""
        with zh as (
            select number::integer as BPUIC
            from read_csv('{service_points}', delim=';', header=true, all_varchar=true)
            where cantonAbbreviation = 'ZH'
        )
        select * from read_parquet('{sections_file}')
        where a_id in (from zh) and b_id in (from zh)
        """
    )


def class_means(rel: duckdb.DuckDBPyRelation) -> dict[str, float]:
    """Mean section delay per class of the scheduled running time ('0' to '4', '5+')."""
    return dict(rel.aggregate(f"{_CLASS} as klasse, avg(section_delay) as mittel").fetchall())


def ranking(
    rel: duckdb.DuckDBPyRelation,
    means: dict[str, float],
    min_trips: int = MIN_TRIPS,
    min_days: int = MIN_DAYS,
    min_days_window: int = MIN_DAYS_WINDOW,
    min_effect: float = MIN_EFFECT,
) -> pl.DataFrame:
    """One row per section of rel and window of WINDOWS, with a value or a reason (`grund`).

    rel: section passages as written by sections.sections(). means: reference value per class
    of the scheduled running time, as class_means() returns it. fahrten and tage count the
    window; the value columns, klasse and rang are null in rows with a reason.
    """
    if min_days_window < 2:
        raise ValueError("min_days_window muss mindestens 2 sein: ein Intervall braucht zwei Tage")
    classes = {row[0] for row in rel.aggregate(f"{_CLASS} as klasse").fetchall()}
    if missing := sorted(classes - means.keys()):
        raise ValueError(f"Klassenmittel fehlt für die Soll-Fahrzeit-Klassen {missing}")

    reference = ", ".join(f"('{klasse}', {float(mean)!r})" for klasse, mean in means.items())
    reference = reference or "(null, null)"  # no passages, no classes
    windows = ", ".join(f"({nr}, '{kind}', '{name}')" for nr, (kind, name) in enumerate(WINDOWS))
    in_windows = "\nunion all\n".join(
        f"select {nr} as nr, * from passages_ref where {condition}"
        for nr, (_, _, condition) in enumerate(_WINDOWS)
    )
    table = rel.query(
        "passages",
        f"""
        with reference(klasse, mittel) as (values {reference}),
        windows(nr, fenster_typ, fenster) as (values {windows}),
        passages_ref as (
            select p.a_id, p.b_id, p.BETRIEBSTAG, p.abfahrt_a, p.section_delay,
                   p.section_delay - r.mittel as delay_ref
            from passages p join reference r on r.klasse = {_CLASS}
        ),
        days as (
            select nr, a_id, b_id, BETRIEBSTAG, count(*) as fahrten,
                   sum(section_delay) as sum_raw, sum(delay_ref) as sum_ref,
                   avg(delay_ref) as day_mean
            from ({in_windows})
            group by all
        ),
        per_window as (
            select nr, a_id, b_id, sum(fahrten)::bigint as fahrten, count(*) as tage,
                   sum(sum_raw) / sum(fahrten) as mittel_roh,
                   sum(sum_ref) / sum(fahrten) as mittel_referenz,
                   avg(day_mean) as tagesmittel, stddev_samp(day_mean) as sd,
                   sum(sum_ref) as zuwachs
            from days
            group by all
        ),
        whole as (select * from per_window where nr = 0)
        select s.a_id, s.b_id, w.fenster_typ, w.fenster,
               coalesce(v.fahrten, 0) as fahrten, coalesce(v.tage, 0) as tage,
               v.mittel_roh, v.mittel_referenz, v.tagesmittel, v.sd, v.zuwachs,
               whole.fahrten as fahrten_zeitraum, whole.tage as tage_zeitraum
        from (select distinct a_id, b_id from passages) s
        cross join windows w
        join whole using (a_id, b_id)
        left join per_window v on v.a_id = s.a_id and v.b_id = s.b_id and v.nr = w.nr
        order by s.a_id, s.b_id, w.nr
        """,
    ).pl()

    # the minimums of the whole period first: such a section has the same reason in every window
    reason = (
        pl.when(pl.col("fahrten_zeitraum") < min_trips)
        .then(pl.lit("zu wenige Fahrten"))
        .when(pl.col("tage_zeitraum") < min_days)
        .then(pl.lit("zu wenige Betriebstage"))
        .when(pl.col("fahrten") == 0)
        .then(pl.lit("keine Fahrt im Fenster"))
        .when(pl.col("tage") < min_days_window)
        .then(pl.lit("zu wenige Betriebstage"))
    )
    table = table.with_columns(grund=reason)
    has_value = pl.col("grund").is_null()

    # half width of the interval of the mean over the daily means; only rows with a value
    # have at least two days
    quantile = stats.t.ppf((1 + CONFIDENCE) / 2, table["tage"].clip(lower_bound=2).to_numpy() - 1)
    half_width = pl.Series(quantile) * pl.col("sd") / pl.col("tage").sqrt()
    table = table.with_columns(
        ki_unten=pl.col("tagesmittel") - half_width, ki_oben=pl.col("tagesmittel") + half_width
    ).with_columns(pl.when(has_value).then(pl.col(c)).alias(c) for c in _VALUE_COLUMNS)
    klasse = (
        pl.when((pl.col("ki_unten") > 0) & (pl.col("tagesmittel") >= min_effect))
        .then(pl.lit("Verstärker"))
        .when((pl.col("ki_oben") < 0) & (pl.col("tagesmittel") <= -min_effect))
        .then(pl.lit("Absorber"))
        .when(has_value)
        .then(pl.lit("neutral"))
    )
    return table.select(
        "a_id",
        "b_id",
        "fenster_typ",
        "fenster",
        "fahrten",
        "tage",
        "mittel_roh",
        "mittel_referenz",
        "tagesmittel",
        "ki_unten",
        "ki_oben",
        klasse.alias("klasse"),
        "zuwachs",
        pl.col("zuwachs").rank("min", descending=True).over("fenster").alias("rang"),
        "grund",
    )
