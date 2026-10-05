"""Central project paths. All code resolves data locations through this module."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
MANIFEST = RAW / "manifest.csv"
ISTDATEN_RAW = RAW / "istdaten"
ISTDATEN_RAIL = PROCESSED / "istdaten_rail"
SERVICE_POINTS_RAW = RAW / "service_points"
