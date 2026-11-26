"""Ranking of the Zurich stops per time window: amplifier, absorber or neutral (issue #61).

The stop ranking of notebooks/12_referenzwert_halte.py (issue #46) as a build step. One row per
stop (BPUIC) and window, with a value or a named reason. Rules 1 to 7 of issue #46 (log
2026-11-15, «Haltverspätung und Referenzwert der Halte»):
- Stop events from quality.delays(), Zurich stops of the snapshot, in the period. Arrival and
  departure REAL, no pass-throughs (DURCHFAHRT_TF), scheduled dwell >= 0 minutes.
- halt = departure delay - max(arrival delay, 0): early arrivals are capped at 0.
- Reference value: mean halt of the class of the scheduled dwell (0, 1, 2, 3+ minutes) over all
  Zurich stop events of the period; the same for every window.
The ranking itself follows ranking.ranking() (issue #38): the same thresholds and windows,
imported from ranking.py, the same two means, interval, class, reasons in the same order and
rank by Zuwachs within a window (log 2026-11-26, decision 2). Time of day by the scheduled
departure at the stop, start included, end excluded (decision 1).
"""

from datetime import date
from pathlib import Path

import duckdb
import polars as pl
from scipy import stats

from sbb_delays.download import service_points_snapshot
from sbb_delays.ranking import (
    _WINDOWS,
    CONFIDENCE,
    MIN_DAYS,
    MIN_DAYS_WINDOW,
    MIN_EFFECT,
    MIN_TRIPS,
    WINDOWS,
)

__all__ = [
    "CONFIDENCE",
    "MIN_DAYS",
    "MIN_DAYS_WINDOW",
    "MIN_EFFECT",
    "MIN_TRIPS",
    "WINDOWS",
    "class_means",
    "stop_events",
    "stop_ranking",
]

# Class of the scheduled dwell, as in notebooks/12_referenzwert_halte.py.
_CLASS = "case when soll_halt_min >= 3 then '3+' else soll_halt_min::varchar end"

_VALUE_COLUMNS = ["mittel_roh", "mittel_referenz", "tagesmittel", "ki_unten", "ki_oben", "zuwachs"]


def stop_events(
    cleaned: duckdb.DuckDBPyRelation,
    first: date,
    last: date,
    service_points: Path | None = None,
) -> duckdb.DuckDBPyRelation:
    """The Zurich stop events of cleaned (as quality.delays() returns it) between first and last.

    Columns: BETRIEBSTAG, BPUIC, abfahrt (scheduled departure), halt_klasse (class of the
    scheduled dwell) and halt (stop delay with the arrival delay capped at 0).
    """
    service_points = service_points or service_points_snapshot()
    return cleaned.query(
        "cleaned",
        f"""
        with zh as (
            select number::integer as BPUIC
            from read_csv('{service_points}', delim=';', header=true, all_varchar=true)
            where cantonAbbreviation = 'ZH'
        ),
        candidates as (
            select BETRIEBSTAG, BPUIC, ABFAHRTSZEIT as abfahrt, an_delay, ab_delay,
                   datediff('minute', ANKUNFTSZEIT, ABFAHRTSZEIT) as soll_halt_min
            from cleaned
            where BETRIEBSTAG between date '{first}' and date '{last}'
              and BPUIC in (from zh)
              and not DURCHFAHRT_TF
              and an_delay is not null and ab_delay is not null
              and ANKUNFTSZEIT is not null and ABFAHRTSZEIT is not null
        )
        select BETRIEBSTAG, BPUIC, abfahrt, {_CLASS} as halt_klasse,
               ab_delay - greatest(an_delay, 0) as halt
        from candidates
        where soll_halt_min >= 0
        """,
    )


def class_means(events: duckdb.DuckDBPyRelation) -> dict[str, float]:
    """Mean halt per class of the scheduled dwell ('0', '1', '2', '3+')."""
    return dict(events.aggregate("halt_klasse, avg(halt) as mittel").fetchall())


def stop_ranking(
    events: duckdb.DuckDBPyRelation,
    means: dict[str, float],
    min_trips: int = MIN_TRIPS,
    min_days: int = MIN_DAYS,
    min_days_window: int = MIN_DAYS_WINDOW,
    min_effect: float = MIN_EFFECT,
) -> pl.DataFrame:
    """One row per stop of events and window of WINDOWS, with a value or a reason (`grund`).

    events: as stop_events() returns them. means: reference value per class of the scheduled
    dwell, as class_means() returns it. fahrten and tage count the window; the value columns,
    klasse and rang are null in rows with a reason.
    """
    if min_days_window < 2:
        raise ValueError("min_days_window muss mindestens 2 sein: ein Intervall braucht zwei Tage")
    classes = {row[0] for row in events.aggregate("halt_klasse").fetchall()}
    if missing := sorted(classes - means.keys()):
        raise ValueError(f"Klassenmittel fehlt für die Soll-Haltezeit-Klassen {missing}")

    reference = ", ".join(f"('{klasse}', {float(mean)!r})" for klasse, mean in means.items())
    reference = reference or "(null, null)"  # no events, no classes
    windows = ", ".join(f"({nr}, '{kind}', '{name}')" for nr, (kind, name) in enumerate(WINDOWS))
    # The window conditions of ranking.py name the scheduled departure abfahrt_a.
    in_windows = "\nunion all\n".join(
        f"select {nr} as nr, * from events_ref where {condition}"
        for nr, (_, _, condition) in enumerate(_WINDOWS)
    )
    table = events.query(
        "events",
        f"""
        with reference(halt_klasse, mittel) as (values {reference}),
        windows(nr, fenster_typ, fenster) as (values {windows}),
        events_ref as (
            select e.BPUIC, e.BETRIEBSTAG, e.abfahrt as abfahrt_a, e.halt,
                   e.halt - r.mittel as halt_ref
            from events e join reference r using (halt_klasse)
        ),
        days as (
            select nr, BPUIC, BETRIEBSTAG, count(*) as fahrten,
                   sum(halt) as sum_raw, sum(halt_ref) as sum_ref, avg(halt_ref) as day_mean
            from ({in_windows})
            group by all
        ),
        per_window as (
            select nr, BPUIC, sum(fahrten)::bigint as fahrten, count(*) as tage,
                   sum(sum_raw) / sum(fahrten) as mittel_roh,
                   sum(sum_ref) / sum(fahrten) as mittel_referenz,
                   avg(day_mean) as tagesmittel, stddev_samp(day_mean) as sd,
                   sum(sum_ref) as zuwachs
            from days
            group by all
        ),
        whole as (select * from per_window where nr = 0)
        select s.BPUIC, w.fenster_typ, w.fenster,
               coalesce(v.fahrten, 0) as fahrten, coalesce(v.tage, 0) as tage,
               v.mittel_roh, v.mittel_referenz, v.tagesmittel, v.sd, v.zuwachs,
               whole.fahrten as fahrten_zeitraum, whole.tage as tage_zeitraum
        from (select distinct BPUIC from events) s
        cross join windows w
        join whole using (BPUIC)
        left join per_window v on v.BPUIC = s.BPUIC and v.nr = w.nr
        order by s.BPUIC, w.nr
        """,
    ).pl()

    # the minimums of the whole period first: such a stop has the same reason in every window
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
        "BPUIC",
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
