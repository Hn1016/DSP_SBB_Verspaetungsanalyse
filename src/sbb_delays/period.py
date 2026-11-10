"""Analysis period and fixed inputs: the only place in the code that sets them.

START and END are (year, month), both inclusive: August 2025 to July 2026, twelve full months
without missing days and with the timetable change of 14.12.2025 (issue #32, log 2026-11-10,
issue #33; before: July 2025 to June 2026, issue #30).

SERVICE_POINTS_DATE and SERVICE_POINTS_SHA256 pin the snapshot of the stop list (issue #26):
the extract of the list retrieved on that date, as published in the release of this repository.
The checksum is the one in data/raw/manifest.csv.
"""

START = (2025, 8)
END = (2026, 7)

SERVICE_POINTS_DATE = "2026-10-05"
SERVICE_POINTS_SHA256 = "9e3e9ebc2914b2e29d4da887f29383c540634932a1dc7cf08d4a18d2f5e5f4d8"
