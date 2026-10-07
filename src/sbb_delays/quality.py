"""Data quality checks on the rail-only IstDaten (hypotheses H1-H5 in docs/log.md).

Every check takes a DuckDB connection from connect() and returns a relation, so notebooks
can display it and tests can assert on it.
"""

from pathlib import Path

import duckdb

from sbb_delays.download import latest_service_points
from sbb_delays.paths import ISTDATEN_RAIL

# UIC country code 85 = Switzerland; BPUIC is country code + five-digit stop number.
IN_CH = "BPUIC between 8500000 and 8599999"
TRIP = "BETRIEBSTAG, FAHRT_BEZEICHNER"
# Delays beyond this are date errors in the source (e.g. scheduled time one day off).
MAX_ABS_DELAY_MIN = 720


def connect(
    rail_dir: Path = ISTDATEN_RAIL, service_points: Path | None = None
) -> duckdb.DuckDBPyConnection:
    """Connection with views `rail` (adds IN_CH) and `service_points` (BPUIC, name, lon, lat)."""
    con = duckdb.connect()
    con.execute(
        f"create view rail as select *, {IN_CH} as IN_CH from read_parquet('{rail_dir}/*.parquet')"
    )
    service_points = service_points or latest_service_points()
    if service_points:
        con.execute(
            f"""
            create view service_points as
            select number::integer as BPUIC, designationOfficial as name,
                   wgs84East::double as lon, wgs84North::double as lat
            from read_csv('{service_points}', delim=';', header=true, all_varchar=true)
            where hasGeolocation = 'true'
            """
        )
    return con


def status_coverage(con: duckdb.DuckDBPyConnection, by: str = "IN_CH") -> duckdb.DuckDBPyRelation:
    """H1: share of scheduled, non-cancelled arrivals and departures per status.

    One event = one arrival or one departure that has a scheduled time.
    """
    return con.sql(
        f"""
        with events as (
            select {by} as grp, AN_PROGNOSE_STATUS as status from rail
            where ANKUNFTSZEIT is not null and not FAELLT_AUS_TF
            union all
            select {by}, AB_PROGNOSE_STATUS from rail
            where ABFAHRTSZEIT is not null and not FAELLT_AUS_TF
        )
        select grp as {by.split(".")[-1]},
               count(*) as events,
               round(100 * avg((status = 'REAL')::int), 2) as pct_real,
               round(100 * avg((status = 'PROGNOSE')::int), 2) as pct_prognose,
               round(100 * avg((status = 'GESCHAETZT')::int), 2) as pct_geschaetzt,
               round(100 * avg((status = 'UNBEKANNT')::int), 2) as pct_unbekannt
        from events
        group by grp
        order by events desc
        """
    )


def trip_structure(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """H2: is (BETRIEBSTAG, FAHRT_BEZEICHNER) one trip, and does ZEILE order its stops?

    trips_mixed: more than one operator or line under one trip id.
    same_minute / back_in_time: sections whose scheduled arrival equals / precedes the
    scheduled departure of the previous stop in ZEILE order.
    """
    return con.sql(
        f"""
        with trips as (
            select {TRIP},
                   count(*) as stops,
                   count(distinct BETREIBER_ID) as operators,
                   count(distinct LINIEN_ID) as lines,
                   max(ZEILE) - min(ZEILE) + 1 as zeile_span,
                   count(*) - count(distinct BPUIC) as repeated_stops
            from rail group by {TRIP}
        ),
        ordered as (
            select coalesce(ANKUNFTSZEIT, ABFAHRTSZEIT) as scheduled,
                   lag(coalesce(ABFAHRTSZEIT, ANKUNFTSZEIT)) over trip as prev_scheduled,
                   IN_CH and lag(IN_CH) over trip as section_in_ch
            from rail
            window trip as (partition by {TRIP} order by ZEILE)
        )
        select
            (select count(*) from trips) as trips,
            (select count(*) from trips where operators > 1 or lines > 1) as trips_mixed,
            (select count(*) from trips where stops = 1) as trips_single_stop,
            (select count(*) from trips where zeile_span <> stops) as trips_not_contiguous,
            (select count(*) from trips where repeated_stops > 0) as trips_repeating_a_stop,
            (select count(*) from rail)
                - (select count(*) from (select distinct * exclude (ZEILE) from rail))
                as duplicate_rows,
            (select count(*) from ordered where prev_scheduled is not null) as sections,
            (select count(*) from ordered where scheduled = prev_scheduled) as same_minute,
            (select count(*) from ordered where scheduled < prev_scheduled) as back_in_time,
            (select count(*) from ordered where scheduled < prev_scheduled and section_in_ch)
                as back_in_time_in_ch
        """
    )


def flag_shares(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """H3: cancellations, pass-throughs and extra trips per operating day."""
    return con.sql(
        """
        select BETRIEBSTAG,
               dayname(BETRIEBSTAG) as weekday,
               count(*) as n_rows,
               round(100 * avg(FAELLT_AUS_TF::int), 2) as pct_cancelled,
               round(100 * avg(DURCHFAHRT_TF::int), 2) as pct_pass_through,
               round(100 * avg(ZUSATZFAHRT_TF::int), 2) as pct_extra_trip
        from rail
        group by BETRIEBSTAG
        order by BETRIEBSTAG
        """
    )


def cancelled_trips(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """H3: trips cancelled completely or at some of their stops."""
    return con.sql(
        f"""
        with trips as (
            select sum(FAELLT_AUS_TF::int) as cancelled, count(*) as stops
            from rail group by {TRIP}
        )
        select count(*) as trips,
               count(*) filter (cancelled = stops) as fully_cancelled,
               count(*) filter (cancelled > 0 and cancelled < stops) as partly_cancelled,
               round(100 * avg((cancelled > 0)::int), 2) as pct_trips_affected
        from trips
        """
    )


def stop_match(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """H4: share of stops (and of rows) that have coordinates in the service point list."""
    return con.sql(
        """
        with stops as (select BPUIC, IN_CH, count(*) as n_rows from rail group by all)
        select s.IN_CH,
               count(*) as stops,
               count(p.BPUIC) as stops_with_coordinates,
               round(100 * sum(s.n_rows) filter (p.BPUIC is not null) / sum(s.n_rows), 2)
                   as pct_rows_with_coordinates
        from stops s left join service_points p using (BPUIC)
        group by s.IN_CH
        order by s.IN_CH desc
        """
    )


def delays(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """Measured delays in minutes at Swiss stops; NULL unless the status is REAL."""
    return con.sql(
        f"""
        select *,
               case when AN_PROGNOSE_STATUS = 'REAL'
                    then epoch(AN_PROGNOSE - ANKUNFTSZEIT) / 60 end as an_delay,
               case when AB_PROGNOSE_STATUS = 'REAL'
                    then epoch(AB_PROGNOSE - ABFAHRTSZEIT) / 60 end as ab_delay
        from rail
        where {IN_CH} and not FAELLT_AUS_TF
        """
    )


def delay_summary(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """H5: distribution of measured arrival and departure delays (minutes)."""
    d = delays(con)  # noqa: F841 (referenced by name in the SQL below)
    return con.sql(
        f"""
        with long as (
            select 'Ankunft' as event, an_delay as delay from d where an_delay is not null
            union all
            select 'Abfahrt', ab_delay from d where ab_delay is not null
        )
        select event,
               count(*) as n,
               round(avg(delay) filter (abs(delay) <= {MAX_ABS_DELAY_MIN}), 2) as mean,
               round(quantile_cont(delay, 0.05), 2) as p05,
               round(median(delay), 2) as median,
               round(quantile_cont(delay, 0.95), 2) as p95,
               round(quantile_cont(delay, 0.99), 2) as p99,
               round(100 * avg((delay < -1)::int), 2) as pct_early_over_1min,
               round(100 * avg((delay >= 3)::int), 2) as pct_late_3min_or_more,
               round(100 * avg((abs(delay) > 60)::int), 3) as pct_beyond_60min,
               count(*) filter (abs(delay) > {MAX_ABS_DELAY_MIN}) as n_date_errors
        from long
        group by event
        order by event desc
        """
    )


def dwell_bias(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """Stop delay (departure delay - arrival delay) by scheduled dwell time.

    Scheduled times have minute resolution. Where arrival and departure share the same
    minute, the stop delay equals the actual dwell time and is positive by construction.
    """
    d = delays(con)  # noqa: F841
    return con.sql(
        f"""
        select least(datediff('minute', ANKUNFTSZEIT, ABFAHRTSZEIT), 5) as scheduled_dwell_min,
               count(*) as stops,
               round(100 * count(*) / sum(count(*)) over (), 1) as pct_of_stops,
               round(avg(epoch(AB_PROGNOSE - AN_PROGNOSE)) / 60, 2) as actual_dwell_mean,
               round(avg(ab_delay - an_delay), 2) as stop_delay_mean,
               round(median(ab_delay - an_delay), 2) as stop_delay_median
        from d
        where an_delay is not null and ab_delay is not null
          and abs(an_delay) <= {MAX_ABS_DELAY_MIN} and abs(ab_delay) <= {MAX_ABS_DELAY_MIN}
          and ABFAHRTSZEIT >= ANKUNFTSZEIT
        group by 1
        order by 1
        """
    )
