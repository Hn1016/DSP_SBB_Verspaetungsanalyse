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

> Download-Befehle folgen in Phase 1.

## Befehle je Ergebnis

| Ergebnis | Befehl |
|---|---|
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
