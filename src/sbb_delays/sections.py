"""Section passages: two consecutive stops of one trip with measured delays (issue #24).

Stub: returns an empty table with the output columns, so the test fails on the expected rows.
"""

import duckdb

from sbb_delays.period import END, START


def sections(
    con: duckdb.DuckDBPyConnection,
    start: tuple[int, int] = START,
    end: tuple[int, int] = END,
) -> duckdb.DuckDBPyRelation:
    return con.sql(
        """
        select null::date as BETRIEBSTAG, null::varchar as FAHRT_BEZEICHNER,
               null::varchar as LINIEN_TEXT, null::bigint as zeile_a, null::bigint as zeile_b,
               null::integer as a_id, null::integer as b_id, null::double as ab_delay_a,
               null::double as an_delay_b, null::double as section_delay,
               null::bigint as scheduled_min, null::boolean as pass_through
        where false
        """
    )
