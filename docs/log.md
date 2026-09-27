# Projektlog

Einträge mit Datum, neueste unten. Typen: Entscheidung, Annahme, Hypothese, KI-Einsatz.

---

## 2026-09-27 — Entscheidung: Umgebung und Werkzeuge

- **Python-Umgebung: uv, Python 3.13 fixiert** (`.python-version`, `requires-python >=3.13,<3.14`).
  Alternativen: conda, pip + venv. Begründung: von den Richtlinien vorgegeben, Lockfile (`uv.lock`)
  garantiert identische Umgebungen bei beiden Teammitgliedern.
- **Datenverarbeitung: DuckDB (+ Polars).** Alternative: pandas. Begründung: ein Jahr IstDaten
  einer Region liegt im GB-Bereich; DuckDB liest CSV/Parquet direkt, out-of-core, per SQL auf dem Laptop.
- **Notebooks: marimo.** Alternative: Jupyter. Begründung: reine `.py`-Dateien, diffbar im PR, von den
  Richtlinien empfohlen.
- **Karte: folium** (vorläufig). Alternative: pydeck, kepler.gl. Wird beim ersten Kartenprototyp überprüft.
- **Qualität: pytest + ruff.**
- Noch nicht eingesetzt: DVC, dbt, GCP. Entscheidung, sobald Datenumfang und Pipeline-Struktur klar sind.

## 2026-09-27 — Entscheidung: Sprache

Code und Code-Kommentare Englisch, Dokumentation (README, Log, Bericht) Deutsch.

## 2026-09-27 — KI-Einsatz: Repository-Setup

- **Aufgabe:** Grundgerüst (uv-Projekt, Paketstruktur, `.gitignore`, README, AGENTS.md/CLAUDE.md,
  Download-Hilfsfunktion mit Manifest) von Claude Code erstellen lassen.
- **Reflektion:** Boilerplate mit geringem fachlichem Risiko, gut delegierbar.
- **Prüfung:** `uv sync`, `uv run pytest` und `ruff` laufen durch; Dateien manuell gelesen.
- **Übernommen/verworfen:** _(vom Team auszufüllen)_
