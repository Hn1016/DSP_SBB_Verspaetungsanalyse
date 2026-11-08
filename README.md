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
- `build` führt drei Schritte der Reihe nach aus und druckt pro Schritt eine Zeile, `gebaut` oder `übersprungen`:
  1. `download` lädt die Monatsarchive IstDaten (v2) und die Haltestellen (Service Points) nach `data/raw/`.
  2. `load` wandelt die Monatsarchive in Parquet um (eine Datei pro Betriebstag, nur Züge).
  3. `sections` bildet die Abschnittsfahrten des Zeitraums für die ganze Schweiz
     (`data/processed/sections_<Start>_<Ende>.parquet`, z. B. `sections_2026-09_2026-09.parquet`; Regeln in
     `src/sbb_delays/sections.py`, Issue #24).
- Ein Schritt wird übersprungen, wenn alle seine Zieldateien für den Zeitraum existieren (ZIP und Haltestellen bzw.
  eine Parquet-Datei pro Tagesdatei im ZIP bzw. die Abschnittsdatei des Zeitraums). `sections` läuft auch, wenn
  `load` etwas gebaut hat. Fehlt im Archiv ein Kalendertag des Zeitraums, erscheint eine Warnung.
  Fortschrittsbalken und Warnungen erscheinen auf stderr.
- Ein zweiter Lauf lädt nichts neu.

- Quelle IstDaten: Monatsarchiv `https://archive.opentransportdata.swiss/istdaten/<Jahr>/ist-daten-v2-<Jahr>-<Monat>.zip`
  (v2-Format, verfügbar ab 2025-07). Ein Monat ist ca. 1.4 GB als ZIP und ca. 19 GB entpackt.
- Haltestellen: ein fester Schnappschuss, Datum und Prüfsumme in `src/sbb_delays/period.py` (zurzeit 2026-10-05).
  Quelle ist der Permalink `https://data.opentransportdata.swiss/dataset/service-point-v2/permalink`; der Anbieter
  aktualisiert die Datei täglich und bietet frühere Fassungen nicht mehr an. Darum lädt `build` einen Auszug des
  Schnappschusses (Schweizer Halte, nur die verwendeten Spalten) aus dem Release
  [`service-points-2026-10-05`](https://github.com/Hn1016/DSP_SBB_Verspaetungsanalyse/releases/tag/service-points-2026-10-05)
  dieses Repositorys nach `data/raw/service_points/service-points-ch_<Datum>.csv` und prüft die Prüfsumme. Fehlt
  der Auszug oder weicht die Prüfsumme ab, bricht `build` mit einer Meldung ab. Erzeugt wurde der Auszug mit
  `download.extract_service_points` (Log 2026-11-08, Issue #26).
- Manifest: Ein Download fügt nur dann eine Zeile hinzu, wenn Datei und Prüfsumme noch nicht im Manifest stehen.
  Ein frischer Klon lässt `data/raw/manifest.csv` darum unverändert.
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
| Haltestellen (Koordinaten, Kanton) | opentransportdata.swiss; Auszug im Release dieses Repositorys | Nutzungsbedingungen opentransportdata.swiss |
| Zugzahlen pro Streckenabschnitt, Linie, Kilometrierung | [data.sbb.ch](https://data.sbb.ch) | Nutzungsbedingungen data.sbb.ch |

> Lizenzangaben beim ersten Download je Datensatz prüfen und präzisieren. Haltestellen: Die Nutzungsbedingungen
> Open Data von opentransportdata.swiss erlauben, die Daten aufbereitet zu publizieren, mit opentransportdata.swiss
> als Bezugsort der Rohdaten (§1, §5.1). Der Auszug im Release ist eine solche Aufbereitung.
