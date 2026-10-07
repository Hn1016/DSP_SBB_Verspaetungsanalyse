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

## 2026-10-05 — Entscheidung: Datenbeschaffung über das Monatsarchiv

- **Entscheidung:** IstDaten werden als Monats-ZIP vom Archiv (`archive.opentransportdata.swiss`, v2-Format)
  geladen, nicht als Tagesdateien von `data.opentransportdata.swiss`.
- **Alternativen:** Tagesdateien (URL enthält eine zufällige Ressourcen-ID, nicht aus dem Datum ableitbar);
  CKAN-API (antwortet ohne Token mit 401/403).
- **Begründung:** Archiv-URL ist aus Jahr und Monat ableitbar, damit ist der Download ohne manuelle Schritte
  reproduzierbar. v2 deckt 2025-07 bis 2026-09 ab und enthält den Fahrplanwechsel Dezember 2025.
- **Beleg:** `uv run python -m sbb_delays.download --from 2026-09 --to 2026-09`, Eintrag in `data/raw/manifest.csv`.
- **Bereinigt:** Die am 4.10.2026 manuell geladenen Dateien (Tagesdateien 1.–3.10.2026, Haltestellenliste)
  wurden gelöscht und aus dem Manifest entfernt, da sie nicht per Skript abrufbar sind und nicht mehr verwendet werden.

## 2026-10-05 — Entscheidung: Haltestellen über Permalink, Schnappschuss mit Datum

- **Entscheidung:** Die Haltestellenliste (Service Points) wird über den Permalink des Datensatzes
  `service-point-v2` geladen und als `service-points_<Abrufdatum>.csv` gespeichert.
- **Alternative:** Direkte Ressourcen-URL. Verworfen: die am 4.10.2026 verwendete URL lieferte am 5.10.2026
  bereits 404, weil die Ressourcen-ID bei jeder Aktualisierung wechselt.
- **Einschränkung:** Der Inhalt ändert sich täglich (4.10. und 5.10. haben unterschiedliche Prüfsummen). Wer an
  einem anderen Tag lädt, erhält einen anderen Schnappschuss; das Manifest dokumentiert, welcher verwendet wurde.
- **Annahme:** Die täglichen Änderungen betreffen die Koordinaten der Bahnhalte im Analysezeitraum nicht
  wesentlich. Prüfung: beim Verknüpfen mit den IstDaten den Anteil der Halte ohne Koordinaten ausweisen.

## 2026-10-05 — Entscheidung: Parquet pro Betriebstag, nur Züge

- **Entscheidung:** Jede Tages-CSV wird einzeln entpackt, auf `PRODUKT_ID = 'Zug'` gefiltert, typisiert und als
  Parquet gespeichert (`src/sbb_delays/load.py`).
- **Alternativen:** Ganzen Monat entpacken (19 GB, passt nicht auf den Laptop); alle Verkehrsmittel behalten.
- **Begründung:** Züge sind ca. 7 % der Zeilen (1.9.2026: 182'143 von ca. 2.6 Mio.). September 2026 belegt als
  Parquet 61 MB.
- **Rechenprobe:** Zeilenzahl je Tag im Parquet = Zeilenzahl der gefilterten CSV (im Code erzwungen).
  September 2026: 5'327'156 Zeilen, 30 Betriebstage, Wochenenden mit weniger Zeilen.

## 2026-10-05 — Annahme: `PRODUKT_ID = 'Zug'` erfasst den relevanten Bahnverkehr

- Ausgeschlossen sind damit u. a. `Zahnradbahn` (1.9.2026: 1'796 Zeilen) und `Metro`.
- **Prüfung:** Bei der Eingrenzung des Raums (Phase 2) kontrollieren, ob im gewählten Raum relevante Linien fehlen.

## 2026-10-05 — Beobachtungen aus der Stichprobe (noch ungeprüft)

- Neben `REAL`, `PROGNOSE` gibt es den Status `UNBEKANNT` und leere Werte (erster/letzter Halt). `GESCHAETZT`
  kam am 1.9.2026 bei Zügen nicht vor.
- Am 1.9.2026 haben ca. 70 % der Zug-Zeilen `REAL` für Ankunft und Abfahrt (128'434 von 182'143).
- 34 Gruppen identischer Zeilen bezüglich (Betriebstag, Fahrt, Halt, Soll-Ankunft, Soll-Abfahrt) im September:
  vor der Abschnittsbildung klären.

## 2026-10-05 — KI-Einsatz: Download- und Ladeskript

- **Aufgabe:** Claude Code hat `download.py` um einen Monatsbereich erweitert, `load.py` (CSV → Parquet) und Tests
  geschrieben und den September 2026 geladen.
- **Reflektion:** Infrastruktur-Code, gut testbar; fachliche Entscheidung (nur Züge) ist oben als Annahme notiert.
- **Prüfung:** 8 pytest-Tests, Rechenprobe Zeilenzahl, Plausibilität Zeilen pro Wochentag.
- **Übernommen/verworfen:** _(vom Team auszufüllen)_

## 2026-10-06 — Hypothesen zur Datenqualität (vor der Analyse notiert)

Datenbasis: September 2026, nur Züge (`data/processed/istdaten_rail/`). Reihenfolge nach Tragweite: Scheitert H1
oder H2, ändert sich das Projekt am stärksten. Befunde und Entscheidungen folgen in einem eigenen Eintrag.

- **H1 — Abdeckung mit gemessenen Zeiten.** Von allen Ankünften und Abfahrten mit Soll-Zeit (nicht ausgefallen)
  haben mindestens 85 % den Status `REAL`. *Erwartung:* SBB über 90 %, einzelne Betreiber (v. a. ausländische und
  kleine Privatbahnen) deutlich darunter. *Vorwissen:* Am 1.9.2026 hatten ca. 70 % der Zeilen `REAL` für Ankunft
  und Abfahrt, darin sind aber erste/letzte Halte ohne Ankunft bzw. Abfahrt enthalten.
- **H2 — Fahrten sind rekonstruierbar.** (`BETRIEBSTAG`, `FAHRT_BEZEICHNER`) bezeichnet genau eine Fahrt (ein
  Betreiber, eine Linie), und die Halte lassen sich über die Soll-Zeit eindeutig ordnen. *Erwartung:* über 99 %
  der Fahrten ohne Mehrdeutigkeit; die 34 Duplikatgruppen sind Einzelfälle.
- **H3 — Ausfälle und Durchfahrten sind selten.** Weniger als 3 % der Zeilen sind `FAELLT_AUS_TF` oder
  `DURCHFAHRT_TF`. *Erwartung:* Ausfälle häufen sich an wenigen Tagen.
- **H4 — Halte haben Koordinaten.** Mindestens 99 % der Halte in der Schweiz (nach Zeilen gewichtet) finden über
  `BPUIC` einen Eintrag mit Koordinaten in der Haltestellenliste. *Erwartung:* fehlende Treffer vor allem im Ausland.
- **H5 — Verspätungswerte sind plausibel.** Für `REAL`-Zeilen liegt der Median der Ankunftsverspätung zwischen 0
  und 2 Minuten, weniger als 1 % der Werte liegen ausserhalb von ±60 Minuten, und Abfahrten mehr als 1 Minute vor
  Soll-Zeit sind selten (unter 1 %).

## 2026-10-06 — Befunde zu H1–H5 und Entscheidungen

Datenbasis: September 2026, nur Züge: 5'327'156 Zeilen, 463'995 Fahrten, 52 Betreiber. Nachvollziehbar mit
`notebooks/02_data_quality.py` (Logik in `src/sbb_delays/quality.py`).

**H1 — Abdeckung: gestützt für die Schweiz, widerlegt für das Ausland.**

- Über alle Halte haben 87.8 % der Ankünfte und Abfahrten den Status `REAL` (Erwartung: mindestens 85 %).
- Der Durchschnitt verdeckt eine Zweiteilung: Halte in der Schweiz 96.2 % `REAL`, Halte im Ausland 10.7 %.
- SBB 97.5 % an Schweizer Halten. Deutlich darunter (bei mehr als 50'000 Ereignissen): LEB 65 %, MBC 85 %, ZB 88 %;
  SBB GmbH und DB liefern fast nur `PROGNOSE`.
- Stabil über die Tage: Tageswerte Schweiz zwischen 95.5 % und 96.7 %.
- `GESCHAETZT` kommt bei Zügen nicht vor. `UNBEKANNT` ist kein Messwert; alle ausgefallenen Zeilen tragen diesen Status.
- **Entscheidung:** Analyse auf Halte in der Schweiz beschränken (BPUIC 85…), nur `REAL` verwenden. Betreiber mit
  tiefer Abdeckung werden bei der Eingrenzung des Raums (Phase 2) ausgeschlossen oder separat ausgewiesen.

**H2 — Fahrten rekonstruierbar: gestützt, aber nicht über die Soll-Zeit.**

- (`BETRIEBSTAG`, `FAHRT_BEZEICHNER`) ist eindeutig: keine Fahrt mit mehreren Betreibern oder Linien.
- Die Erwartung «über die Soll-Zeit eindeutig ordnen» ist widerlegt: Soll-Zeiten haben Minutenauflösung, bei
  32'338 Abschnitten (0.66 %) liegt die Soll-Ankunft in derselben Minute wie die Soll-Abfahrt davor.
- Die Zeilenreihenfolge der CSV ist die Fahrreihenfolge. Geprüft am 8.9.2026: alle 15'772 Fahrten stehen als
  zusammenhängender Block; bei Abschnitten in derselben Minute stimmen die Ist-Zeiten in 1'120 von 1'120 Fällen
  mit der Zeilenreihenfolge überein.
- **Entscheidung:** `load.py` speichert die Zeilennummer als Spalte `ZEILE`; Abschnitte werden nach `ZEILE` gebildet.
- Restfehler: 145 Abschnitte in der Schweiz (0.003 %) laufen in der Soll-Zeit rückwärts, fast alle SBB und gehäuft
  am 25.–27.9. (vermutlich Umleitungen). 34 exakt doppelte Zeilen in 4 Fahrten, 73 Fahrten mit nur einem Halt,
  1'436 Fahrten bedienen einen Halt mehrfach.
- **Entscheidung:** Doppelte Zeilen entfernen; Abschnitte mit rückwärts laufender Soll-Zeit verwerfen.

**H3 — Ausfälle und Durchfahrten selten: gestützt auf Zeilenebene, auf Fahrtebene relevant.**

- 2.15 % der Zeilen sind ausgefallen, 0.04 % Durchfahrten (zusammen 2.19 %, Erwartung unter 3 %).
- Auf Fahrtebene sind 4.98 % betroffen: 4'689 Fahrten ganz, 18'408 teilweise ausgefallen. Ein Teilausfall
  unterbricht die Kette der Abschnitte.
- Häufung an Wochenenden, Maximum 26./27.9. mit 5.5 % und 5.7 % (gleichzeitig am meisten Zusatzfahrten).
- Abweichung von der Aufgabenstellung: 83 % der Durchfahrten haben eine `REAL`-Zeit.
- **Entscheidung:** Abschnitte nur zwischen zwei nicht ausgefallenen Halten bilden. **Annahme:** Durchfahrten
  werden vorerst wie Halte ohne Fahrgastwechsel behandelt und nicht als Halt ausgewertet; Prüfung bei der
  Abschnittsbildung.

**H4 — Koordinaten: gestützt für die Schweiz.**

- Alle 1'677 Schweizer Halte haben Koordinaten in der Haltestellenliste (100 % der Zeilen).
- Keiner der 612 ausländischen Halte ist enthalten. Wegen H1 werden sie ohnehin nicht ausgewertet.

**H5 — Verspätungswerte plausibel: gestützt.**

- Median Ankunft 0.53 min, Abfahrt 1.00 min; 0.018 % der Werte ausserhalb ±60 min; Abfahrten mehr als 1 min vor
  Soll-Zeit 0.15 %. Ankünfte mehr als 1 min zu früh: 4.1 %.
- 448 Ankünfte und 456 Abfahrten weichen um mehr als 12 Stunden ab (Datumsfehler in der Quelle, z. B. Soll-Zeit
  um einen Tag verschoben).
- **Entscheidung:** Werte über ±12 Stunden als Datenfehler verwerfen.

**Nebenbefund mit Folgen für die Methode — Haltverspätung ist durch die Minutenauflösung verzerrt.**

- Bei 73 % der Halte liegen Soll-Ankunft und Soll-Abfahrt in derselben Minute. Dort ist die Haltverspätung
  gleich der tatsächlichen Haltezeit (Mittel 0.67 min) und zwangsläufig positiv. Bei Soll-Haltezeit ab 1 min liegt
  das Mittel bei 0.27 bis 0.44 min.
- Folge: Fast jeder Halt erscheint als «Verstärker», und der Abschnitt danach entsprechend als «Absorber». Die
  rohe Kennzahl aus der Aufgabenstellung misst teilweise die Fahrplanrundung, nicht den Betrieb.
- **Nächste Hypothese (noch zu prüfen):** Nach Abzug eines Referenzwerts je Soll-Haltezeit (bzw. bei gemeinsamer
  Betrachtung von Halt und folgendem Abschnitt) bleibt eine Rangliste, die sich von der rohen deutlich unterscheidet.

## 2026-10-06 — KI-Einsatz: Datenqualitätsprüfung

- **Aufgabe:** Claude Code hat die Hypothesen H1–H5 formuliert, die Abfragen geschrieben, `quality.py`, das
  Notebook und die Tests erstellt und `load.py` um `ZEILE` erweitert.
- **Reflektion:** Die Hypothesen wurden in einem eigenen Commit vor den Abfragen festgehalten («Log data quality hypotheses before analysis»). Schwellenwerte (85 %, 3 %,
  99 %) sind Setzungen des Agenten und fachlich zu hinterfragen.
- **Prüfung:** 22 pytest-Tests (davon 7 auf den echten Daten); zwei Fehler in den Abfragen des Agenten wurden beim
  Gegenprüfen gefunden und korrigiert (Duplikatzähler; Sortierung über Soll-Zeit).
- **Übernommen/verworfen:** _(vom Team auszufüllen)_
