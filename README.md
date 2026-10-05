# SBB Verspätungsanalyse — Verstärker und Absorber

Wo entstehen und wo verschwinden Verspätungen im Schweizer Bahnnetz? Aus den SBB IstDaten
werden Abschnitte (zwei aufeinanderfolgende Halte einer Fahrt) rekonstruiert und pro Abschnitt
bzw. Halt die Streckenverspätung und die Haltverspätung aggregiert. Ergebnis: eine Rangliste und
eine interaktive Netzkarte der Verstärker und Absorber.

Projekt 24, DS-Projekt HS 2026, ZHAW IWI. Anforderungen: [docs/requirements.md](docs/requirements.md),
Projektlog: [docs/log.md](docs/log.md).

## Setup

Voraussetzung: [uv](https://docs.astral.sh/uv/) (Python 3.13 wird von uv verwaltet).

```bash
git clone <repo-url>
cd DSP
uv sync
uv run pytest
```

## Datenbeschaffung

Rohdaten liegen in `data/raw/` und werden nicht verändert und nicht versioniert. Jeder Download
wird mit Quelle, Abrufdatum und SHA-256-Prüfsumme in `data/raw/manifest.csv` protokolliert
(`src/sbb_delays/download.py`).

```bash
# 1. Rohdaten laden: Monatsarchive IstDaten (v2) und Haltestellen (Service Points)
uv run python -m sbb_delays.download --from 2026-09 --to 2026-09

# 2. Monatsarchive in Parquet umwandeln (ein File pro Betriebstag, nur Züge)
uv run python -m sbb_delays.load
```

- Quelle IstDaten: Monatsarchiv `https://archive.opentransportdata.swiss/istdaten/<Jahr>/ist-daten-v2-<Jahr>-<Monat>.zip`
  (v2-Format, verfügbar ab 2025-07). Ein Monat ist ca. 1.4 GB als ZIP und ca. 19 GB entpackt.
- Quelle Haltestellen: Permalink `https://data.opentransportdata.swiss/dataset/service-point-v2/permalink`.
  Die Datei wird vom Anbieter täglich aktualisiert; jeder Download ist ein Schnappschuss mit Abrufdatum im
  Dateinamen (`data/raw/service_points/service-points_<Datum>.csv`). Ein vorhandener Schnappschuss wird
  wiederverwendet; zum Aktualisieren die Datei löschen und Schritt 1 erneut ausführen.
- Schritt 2 entpackt jeweils nur einen Tag temporär, filtert auf `PRODUKT_ID = 'Zug'` und schreibt
  typisierte Parquet-Dateien nach `data/processed/istdaten_rail/` (September 2026: 61 MB).
- Bereits vorhandene Dateien werden übersprungen; beide Befehle können beliebig oft ausgeführt werden.
- Prüfsummen vergleichen: `shasum -a 256 data/raw/istdaten/*.zip` gegen die Spalte `sha256` im Manifest.

## Befehle je Ergebnis

| Ergebnis | Befehl |
|---|---|
| Rohdaten laden | `uv run python -m sbb_delays.download --from YYYY-MM --to YYYY-MM` |
| Parquet erzeugen | `uv run python -m sbb_delays.load` |
| Stichprobe ansehen | `uv run marimo edit notebooks/01_sample.py` |
| Tests | `uv run pytest` |
| Linting | `uv run ruff check . && uv run ruff format --check .` |
| Notebook bearbeiten | `uv run marimo edit notebooks/<name>.py` |

## Struktur

```
data/raw/         Rohdaten (unverändert, nicht in git) + manifest.csv
data/processed/   Abgeleitete Daten (Parquet/DuckDB, nicht in git)
docs/             Anforderungen, Projektlog
notebooks/        marimo-Notebooks (Exploration, Ergebnisdarstellung)
src/sbb_delays/   Wiederverwendbare Logik
tests/            pytest (Unit- und Datentests)
```

## Datenquellen und Lizenzen

| Datensatz | Anbieter | Lizenz |
|---|---|---|
| IstDaten (Soll-/Ist-Zeiten je Halt) | [opentransportdata.swiss](https://opentransportdata.swiss) | Nutzungsbedingungen opentransportdata.swiss |
| Haltestellen (Koordinaten) | opentransportdata.swiss | Nutzungsbedingungen opentransportdata.swiss |
| Zugzahlen pro Streckenabschnitt, Linie, Kilometrierung | [data.sbb.ch](https://data.sbb.ch) | Nutzungsbedingungen data.sbb.ch |

> Lizenzangaben beim ersten Download je Datensatz prüfen und präzisieren.
