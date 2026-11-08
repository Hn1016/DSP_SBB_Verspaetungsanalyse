"""Section passages: two consecutive stops of one trip with measured delays (issue #24).

Rules as in notebooks/03_erste_rangliste.py (issue #14) and review PR #17:
- Neighbours by ZEILE over the whole trip, all rows of `rail` (incl. foreign and cancelled
  stops), so no section spans a cancelled stop or a stop outside Switzerland.
- Stops A and B come from quality.delays(), where the cleaning rules apply (Swiss stops, no
  cancelled stops, no duplicate rows, no delays beyond 12 h).
- Departure delay at A and arrival delay at B are measured (REAL); sections whose scheduled
  time runs backwards are dropped.
- A pass-through (DURCHFAHRT_TF) counts as a point and can be stop A or B (rule a, as #14).
"""

from calendar import monthrange
from datetime import date

import duckdb

from sbb_delays import quality
from sbb_delays.period import END, START


def period_days(start: tuple[int, int], end: tuple[int, int]) -> tuple[date, date]:
    """First and last calendar day of the months start to end (both inclusive)."""
    return date(*start, 1), date(*end, monthrange(*end)[1])


def sections(
    con: duckdb.DuckDBPyConnection,
    start: tuple[int, int] = START,
    end: tuple[int, int] = END,
) -> duckdb.DuckDBPyRelation:
    """Section passages of the operating days from start to end, from the `rail` view of con.

    section_delay = arrival delay at B - departure delay at A; scheduled_min = scheduled
    arrival at B - scheduled departure at A; both in minutes. pass_through: A or B is one.
    """
    first, last = period_days(start, end)
    in_period = f"BETRIEBSTAG between date '{first}' and date '{last}'"
    stops = quality.delays(con).filter(in_period)  # noqa: F841 (referenced in the SQL below)
    return con.sql(
        f"""
        with pairs as (
            select BETRIEBSTAG, ZEILE as zeile_a,
                   lead(ZEILE) over (partition by {quality.TRIP} order by ZEILE) as zeile_b
            from rail
            where {in_period}
        )
        select a.BETRIEBSTAG, a.FAHRT_BEZEICHNER, a.LINIEN_TEXT,
               p.zeile_a, p.zeile_b,
               a.BPUIC as a_id, b.BPUIC as b_id,
               a.ab_delay as ab_delay_a, b.an_delay as an_delay_b,
               b.an_delay - a.ab_delay as section_delay,
               datediff('minute', a.ABFAHRTSZEIT, b.ANKUNFTSZEIT) as scheduled_min,
               a.DURCHFAHRT_TF or b.DURCHFAHRT_TF as pass_through
        from pairs p
        join stops a on a.BETRIEBSTAG = p.BETRIEBSTAG and a.ZEILE = p.zeile_a
        join stops b on b.BETRIEBSTAG = p.BETRIEBSTAG and b.ZEILE = p.zeile_b
        where a.ab_delay is not null and b.an_delay is not null
          and a.ABFAHRTSZEIT <= b.ANKUNFTSZEIT
        """
    )
