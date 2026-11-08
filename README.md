# SBB Verspätungsanalyse — Verstärker und Absorber

Wo entstehen und wo verschwinden Verspätungen im Schweizer Bahnnetz? Aus den SBB IstDaten
werden Abschnitte (zwei aufeinanderfolgende Halte einer Fahrt) rekonstruiert und pro Abschnitt
bzw. Halt die Streckenverspätung und die Haltverspätung aggregiert. Ergebnis: eine Rangliste und
eine interaktive Netzkarte der Verstärker und Absorber.

Projekt 24, DS-Projekt HS 2026, ZHAW IWI. Anforderungen: [docs/requirements.md](docs/requirements.md),
Projektlog: [docs/log.md](docs/log.md).

## Setup

Voraussetzung: [uv](https://docs.astral.sh/uv/) (Python 3.13 wird von uv verwaltet).
uv 0.13.6 ist Pflicht (`required-version` in `pyproject.toml`, dieselbe Version wie in CI); aktualisieren mit `uv self update 0.13.6`.

```bash
git clone <repo-url>
cd DSP
uv sync
uv run build      # Rohdaten laden und Parquet erzeugen (siehe Datenbeschaffung)
uv run pytest
```

Bei jedem Pull Request und jedem Push auf `main` laufen die Tests automatisch (GitHub Actions, Check `tests`); die Datentests werden dort übersprungen.

## Datenbeschaffung

Rohdaten liegen in `data/raw/` und werden nicht verändert und nicht versioniert. Jeder Download
wird mit Quelle, Abrufdatum und SHA-256-Prüfsumme in `data/raw/manifest.csv` protokolliert
(`src/sbb_delays/download.py`).

Ein Befehl baut alles aus den Rohdaten:

```bash
uv run build            # baut, was fehlt
uv run build --force    # baut data/processed für den Zeitraum neu; data/raw bleibt unangetastet
```

- Der Zeitraum steht nur in `src/sbb_delays/period.py` (vorerst September 2026).
- `build` führt zwei Schritte der Reihe nach aus und druckt pro Schritt eine Zeile, `gebaut` oder `übersprungen`:
  1. `download` lädt die Monatsarchive IstDaten (v2) und die Haltestellen (Service Points) nach `data/raw/`.
  2. `load` wandelt die Monatsarchive in Parquet um (eine Datei pro Betriebstag, nur Züge).
- Ein Schritt wird übersprungen, wenn alle seine Zieldateien für den Zeitraum existieren (ZIP und Haltestellen bzw.
  eine Parquet-Datei pro Tagesdatei im ZIP). Fehlt im Archiv ein Kalendertag des Zeitraums, erscheint eine Warnung.
  Fortschrittsbalken und Warnungen erscheinen auf stderr.
- Ein zweiter Lauf lädt nichts neu.

- Quelle IstDaten: Monatsarchiv `https://archive.opentransportdata.swiss/istdaten/<Jahr>/ist-daten-v2-<Jahr>-<Monat>.zip`
  (v2-Format, verfügbar ab 2025-07). Ein Monat ist ca. 1.4 GB als ZIP und ca. 19 GB entpackt.
- Quelle Haltestellen: Permalink `https://data.opentransportdata.swiss/dataset/service-point-v2/permalink`.
  Die Datei wird vom Anbieter täglich aktualisiert; jeder Download ist ein Schnappschuss mit Abrufdatum im
  Dateinamen (`data/raw/service_points/service-points_<Datum>.csv`). Ein vorhandener Schnappschuss wird
  wiederverwendet; zum Aktualisieren die Datei löschen und `uv run build` erneut ausführen.
- `load` entpackt jeweils nur einen Tag temporär, filtert auf `PRODUKT_ID = 'Zug'` und schreibt
  typisierte Parquet-Dateien nach `data/processed/istdaten_rail/` (September 2026: 61 MB).
- Die Spalte `ZEILE` (Zeilennummer in der Tages-CSV) hält die Haltreihenfolge einer Fahrt fest.
- Prüfsummen vergleichen: `shasum -a 256 data/raw/istdaten/*.zip` gegen die Spalte `sha256` im Manifest.

## Befehle je Ergebnis

| Ergebnis | Befehl |
|---|---|
| Alles aus den Rohdaten bauen | `uv run build` (`--force`: `data/processed` neu) |
| Stichprobe ansehen | `uv run marimo edit notebooks/01_sample.py` |
| Datenqualität (H1–H5) | `uv run marimo edit notebooks/02_data_quality.py` |
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
