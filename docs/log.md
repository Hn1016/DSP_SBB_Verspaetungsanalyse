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

## 2026-10-17 — KI-Einsatz: One-Pager

- **Aufgabe:** Claude Code hat `docs/one-pager.md` (Abschnitte Warum, Was, Wie, Nicht-Ziele, Fertig, nach dem
  Tutorial `vp-82/ds-projekt-2026-tutorial`, Kapitel 1) erstellt.
- **Reflektion:** Quellen sind nur die Aufgabenstellung und Entscheidungen in diesem Log; nicht Entschiedenes ist als
  «offen» markiert und nicht vom Agenten ergänzt. Die offenen Entscheidungsregeln (u. a. Richtung, «systematisch»,
  Hauptkennzahl, Zeitfenster, Stabilitätsschwelle) werden vor der ersten Rangliste festgelegt.
- **Prüfung:** Jede Aussage gegen `docs/requirements.md` bzw. den zitierten Log-Eintrag gelesen.
- **Übernommen/verworfen:** _(vom Team auszufüllen)_

## 2026-10-25 — Hypothese H6: Fehlende `REAL`-Zeiten sind nicht systematisch (vor der Analyse notiert)

Anlass: Review-Frage zu PR #2, «Warum wird die PROGNOSE-Verspätung verworfen, wenn Annahme 2 sie braucht?».
Annahme 2 (`docs/assumptions.md`): Ob eine Zeit `REAL` ist, hängt nicht von der Verspätung oder vom Abschnitt ab.
`quality.delays()` setzt die Verspätung für alle Nicht-`REAL`-Zeilen auf leer; damit lässt sich die Annahme nicht prüfen.

- **H6a — Verteilung:** Die `PROGNOSE`-Verspätung an Schweizer Halten hat einen ähnlichen Median wie die
  `REAL`-Verspätung (Differenz unter 0.5 min). *Einschränkung:* `PROGNOSE` ist die letzte Prognose, keine Messung;
  sie dient nur als Näherung für die unbekannte Ist-Zeit.
- **H6b — Abhängigkeit von der Verspätung:** Der Anteil `REAL` an einem Halt hängt nicht von der gemessenen
  Abfahrtsverspätung am vorherigen Halt derselben Fahrt ab (Anteil `REAL` in allen Verspätungsklassen innerhalb
  von ±2 Prozentpunkten).
- **H6c — Abhängigkeit vom Ort:** Fehlende `REAL`-Zeiten verteilen sich auf viele Halte. *Erwartung:* Die zehn Halte
  mit den meisten Nicht-`REAL`-Ereignissen tragen weniger als 20 % davon.
- *Folge bei Widerlegung:* Annahme 2 gilt nicht; betroffene Abschnitte bzw. Halte werden ausgewiesen oder
  ausgeschlossen, und die Rangliste wird mit und ohne sie verglichen.

## 2026-10-25 — Befund H6 und Antwort auf die Review-Frage zu `PROGNOSE`

**Frage (Review PR #2):** Warum wird die `PROGNOSE`-Verspätung verworfen, wenn Annahme 2 sie braucht?

**Antwort:** Zu Recht kritisiert. `delays()` hat `PROGNOSE` verworfen, weil es keine Messung ist und nicht in die
Rangliste gehört. Damit fehlte aber die einzige Vergleichsgrösse, um Annahme 2 zu prüfen. Geändert: `delays()`
liefert die `PROGNOSE`-Verspätung jetzt getrennt (`an_delay_prognose`, `ab_delay_prognose`); für die Rangliste
zählen weiterhin nur `an_delay`/`ab_delay` aus `REAL`. Neue Prüfungen in `quality.py` und im Notebook (Abschnitt H6).

Befunde, September 2026, Halte in der Schweiz, ohne Ausfälle:

- **H6a — gestützt.** Median `PROGNOSE` gegenüber `REAL`: Ankunft 0.50 zu 0.53 min, Abfahrt 0.98 zu 1.00 min
  (Differenz unter 0.5 min). Der Mittelwert der Ankunft liegt bei `PROGNOSE` höher (1.17 zu 0.84 min). Für ca. 8'000
  `PROGNOSE`-Zeilen je Ereignisart fehlt auch die Prognosezeit.
- **H6b — gestützt.** Der Anteil `REAL` hängt kaum von der Verspätung am vorherigen Halt ab: 98.0 % bis 99.6 % über
  alle Klassen (Schwelle ±2 Prozentpunkte eingehalten). Leicht tiefer bei 15 min und mehr (98.0 %) und bei zu
  frühen Zügen (98.6 %).
- **H6c — formal gestützt, inhaltlich widerlegt.** Die zehn Halte mit den meisten Nicht-`REAL`-Ereignissen tragen
  17.4 % davon (Schwelle 20 %). Die Schwelle war aber das falsche Mass: Das Fehlen ist an bestimmte Halte gebunden.
  52 Schweizer Halte haben nie eine `REAL`-Zeit (36.9 % aller Nicht-`REAL`-Ereignisse), 108 Halte haben 20 bis 99 %
  Nicht-`REAL` (44.1 %). Betroffen sind v. a. Strecken mit deutschen Betreibern auf Schweizer Gebiet (Klettgau
  Neuhausen–Trasadingen, Basel Bad Bf, Riehen, Herblingen–Thayngen) sowie die BLM (Grütschalp–Mürren).
- **Folgerung für Annahme 2:** Der Teil «hängt nicht von der Verspätung ab» ist gestützt. Der Teil «hängt nicht vom
  Abschnitt ab» ist widerlegt.

**Entscheidungen:**

- Die 52 nie gemessenen Halte fehlen in Rangliste und Karte; sie werden im Bericht als Abdeckungslücke genannt,
  nicht als «unauffällig».
- Die Abdeckung je Halt bzw. Abschnitt wird bei der Abschnittsbildung als Spalte geführt. Die Rangliste wird mit
  und ohne Abschnitte unter 80 % `REAL` berechnet und verglichen (Stabilitätsprüfung).
- `PROGNOSE`-Werte fliessen nicht in die Rangliste ein.

## 2026-10-25 — KI-Einsatz: Antwort auf die Review-Frage

- **Aufgabe:** Claude Code hat H6 formuliert (Commit vor der Analyse), die Abfragen im laufenden Notebook ausgeführt
  (marimo pair), `quality.py` erweitert und diesen Eintrag geschrieben.
- **Prüfung:** 25 pytest-Tests, davon einer mit einer künstlichen `PROGNOSE`-Zeile; Notebook läuft.
- **Offen für das Team:** Ob die Schwelle von 80 % `REAL` für die Rangliste fachlich passt.

## 2026-10-28 — Entscheidung: Annahmen A1–A10 lösen die Hypothesen H1–H6 als Gliederung ab

- **Entscheidung:** Ab jetzt gliedern die Annahmen A1–A10 (`docs/assumptions.md`, Branch `docs/one-pager`,
  2026-10-17) die Prüfungen. H1–H6 werden nicht weitergeführt; ihre Einträge bleiben als Nachweis im Log stehen.
- **Begründung:** H1–H5 wurden vor dem Tutorial aus der Datensicht formuliert. Die Annahmen A1–A10 sind aus dem
  One-Pager abgeleitet und nach Wichtigkeit sortiert; so wird zuerst geprüft, was das Projekt gefährdet.
- **Was weiter gilt:** Die Entscheidungen aus H1–H6 bleiben in Kraft: nur Züge, nur Halte in der Schweiz, nur `REAL`
  als Messung, Reihenfolge nach `ZEILE`, doppelte Zeilen, rückwärts laufende Soll-Zeiten und Werte über ±12 Stunden
  verwerfen, `PROGNOSE` getrennt führen. Der One-Pager stützt sich darauf («Eingrenzung», Log 2026-10-06).
- **Zuordnung:**

| Hypothese | Annahme | Was der Befund für die Annahme bedeutet |
|---|---|---|
| H1 Abdeckung | A2, A3 | Abdeckung im September 96.2 % an Schweizer Halten; für A3 nur ein Monat |
| H2 Fahrten rekonstruierbar | A4, A5 | `ZEILE` ordnet die Halte (September); rückwärts laufende Abschnitte am 25.–27.9. deuten auf Umleitungen (A5) |
| H3 Ausfälle | A9 | Ausfälle häufen sich an Wochenenden; ob sie die Rangliste verschieben, prüft erst A9 |
| H4 Koordinaten | – | reine Datenprüfung ohne eigene Annahme; bleibt bestehen |
| H5 Verspätungswerte | A1 | Werte plausibel; Datumsfehler verworfen |
| Nebenbefund Haltverspätung | A7, A8 | Minutenauflösung verzerrt die Haltverspätung; Grundlage für A8, Hinweis auf A7 |
| H6 Fehlende `REAL`-Zeiten | A2 | gestützt für «unabhängig von der Verspätung», widerlegt für «unabhängig vom Ort» |

- **Offen:** Die Spalte «Evidenz» in `docs/assumptions.md` gibt den Stand vom 2026-10-17 wieder, vor diesen Befunden.
  Sie wird nachgeführt, sobald `docs/assumptions.md` auf `main` liegt.

## 2026-10-28 — Entscheidung: Bereinigungsregeln zentral in `delays()` (Review PR #2, Frage 1)

- **Frage (schwagia, `quality.py`):** Warum werden die Bereinigungen vom 6.10. in `delays()` nicht gemacht, und wo
  sollen sie zentral sein, damit die Rangliste sie sicher bekommt?
- **Befund:** Die Regeln waren verteilt. `delays()` filterte nur auf Schweiz und Ausfälle; die doppelten Zeilen
  blieben drin; Datumsfehler (über ±12 h: 448 Ankünfte, 456 Abfahrten) waren in `delay_summary()` nur aus dem
  Mittelwert ausgeschlossen, nicht aus Quantilen und Anteilen.
- **Entscheidung:** Alle Regeln, die je Halt gelten, stehen jetzt in `delays()`: nur Schweiz, ohne Ausfälle, ohne
  doppelte Zeilen, Datumsfehler ohne Verspätung (markiert in `an_date_error`/`ab_date_error`). Alle Prüfungen bauen
  darauf auf und filtern nicht mehr selbst. Rückwärts laufende Soll-Zeiten sind nur je Abschnitt erkennbar; die
  Abschnittsbildung verwirft sie und baut ebenfalls auf `delays()` auf. Regel in `AGENTS.md`.
- **Rechenprobe, September 2026:** gemessene Ankünfte 4'131'201 → 4'130'730; Anteil ausserhalb ±60 min 0.018 % →
  0.007 % (vorher zählten die Datumsfehler mit); 5-%-Quantil der Ankunft −0.92 → −0.90 min; Median und Mittelwert
  unverändert. Die Befunde vom 6.10. und 25.10. bleiben in der Aussage gleich.

## 2026-10-28 — Korrektur H6b: Vorhalte ohne Messung mitzählen (Review PR #2, Frage 2)

- **Frage (schwagia, `quality.py`):** H6b zählte nur Ankünfte nach einem gemessenen Vorhalt. Fallen damit nicht genau
  die Strecken weg, auf denen `REAL` systematisch fehlt, und sind die 98–99.6 % zu optimistisch?
- **Befund (September 2026, Schweizer Halte, nach den zentralen Regeln in `delays()`):**

| Vorhalt | Anteil der Ankünfte | davon gemessen | Spanne über die Verspätungsklassen |
|---|---|---|---|
| gemessen | 96.55 % | 99.49 % | 97.9 % bis 99.6 % |
| nur Prognose | 2.54 % | 16.09 % | 5.9 % bis 29.9 % (Klasse nach Prognose-Verspätung) |
| ohne Zeit | 0.91 % | 1.27 % | – |
| alle | 100 % | 96.48 % | |

- **Korrektur:** Die 98–99.6 % gelten nur für Ankünfte nach einem gemessenen Vorhalt, nicht für alle Ankünfte.
  Fehlt die Messung am Vorhalt, fehlt sie meist auch am nächsten Halt: Das Fehlen zieht sich über Streckenstücke
  (passend zu H6c).
- **Was bleibt:** Die Aussage von H6b, dass das Fehlen nicht von der Verspätung abhängt, bleibt bestehen. Auch bei
  Vorhalten mit nur Prognose sinkt der gemessene Anteil mit der Verspätung nicht (12.1 % bei 1–3 min, 29.9 % bei
  6–15 min). Einschränkung: Die Prognose ist nur eine Näherung der unbekannten Verspätung.
- **Folge für A2:** unverändert «teilweise»; das Fehlen ist an Orte und Streckenstücke gebunden, nicht an die
  Verspätung. `real_share_by_previous_delay()` weist jetzt alle Vorhalt-Klassen aus.

## 2026-10-29 — One-Pager Schritt 2 nachgeführt (Review PR #3, Frage 2)

- **Frage (schwagia, `one-pager.md`):** Warum werden Abschnitte nur aus `REAL`-Halten gebildet, ohne die Entscheidung
  vom 25.10.? Sonst fallen die 52 nie gemessenen Halte still weg, obwohl unter «Fertig» jeder Abschnitt einen Wert
  oder einen Grund bekommen soll.
- **Antwort:** Der One-Pager stammt vom 17.10., die Entscheidung vom 25.10.; Schritt 2 war veraltet. Nachgeführt:
  Anteil `REAL` als Spalte je Abschnitt und Halt, nie gemessene Halte als Abdeckungslücke im Bericht, Vergleich der
  Rangliste mit und ohne Abschnitte unter 80 % `REAL`, Verweis auf die zentralen Regeln in `quality.delays()`. Neu
  offen: ob die Schwelle von 80 % passt. Der offene Punkt unter «Fertig» bleibt offen; entschieden ist nur der
  Grund «nie gemessen».
- Es wurde nur übernommen, was im Log bereits entschieden ist; offene Punkte sind nicht vom Agenten gefüllt.

## 2026-10-29 — Evidenz von A9 und A10 ohne Grundlage (Review PR #3, Frage 1)

- **Frage (schwagia, `assumptions.md`):** Worauf stützt sich «Evidenz hoch» bei A9? H3 zeigt nur, dass Ausfälle
  selten sind und sich am Wochenende häufen.
- **Antwort:** Auf nichts Belastbares. Die Spalte «Evidenz» ist die Einschätzung des Teams vom 17.10., gemacht ohne
  die Daten zu öffnen (Kopf von `assumptions.md`). H3 hat Ausfälle nur gezählt; ob sie die Rangliste verschieben,
  wurde nicht geprüft (Zuordnung vom 28.10.: «prüft erst A9»). Dasselbe gilt für A10: Fahrten je Abschnitt und
  Zeitfenster wurden nie gezählt. Beide müssten «tief» sein und rückten damit in der Tabelle nach oben.
- **Entscheidung:** Die Tabelle bleibt in diesem PR, wie sie ist (Vorgabe: One-Pager-PR mit den offenen Punkten so,
  wie sie sind). Das geplante Paket «Evidenz nachführen» umfasst nicht nur A2, sondern die ganze Spalte, mindestens
  A2, A9 und A10, und sortiert die Tabelle danach neu.
- **Hinweis für dieses Paket:** Auf `feat/assumption-checks` (noch nicht auf `main`) gibt es inzwischen Prüfungen für
  A1–A10. A9 hielt dort nur knapp (7 von 10 Top-Abschnitten gleich, Schwelle 7), und das Kriterium für A10 erwies
  sich als zu schwach. Auch danach wäre «hoch» bei beiden nicht begründet.

## 2026-10-29 — KI-Einsatz: Issue-Formular «Paket»

- **Mine:** Ein Issue-Formular «Paket» mit fünf Pflicht-Textfeldern (Was am Ende existiert, Welcher Frage es dient,
  Fertig wenn, Art und Umfang, Nicht enthalten); leere Issues sind ausgeschaltet. Neue Regel: Ein Paket beginnt als
  Issue, das eine Person mit dem Formular schreibt, bevor der Branch existiert, und sein Pull Request schliesst dieses
  Issue. Vorlage sind `package.yml`, `config.yml` und die letzte Workflow-Regel aus dem Tutorial-Repository.
  Nach dem Review von PR #4: Das Feld «Art und Umfang» heisst «Art und Grösse», wörtlich wie «Kind and size» in der
  Vorlage. Der PR-Text beginnt mit «Closes #N» und enthält einen Abschnitt «Was vom Issue abweicht» (Regel in
  `AGENTS.md`).
- **Delegated:** Claude Code hat Feldnamen und Beschreibungen ins Deutsche übersetzt (die Vorlage hat keine
  Platzhalter, es wurden keine ergänzt), die Regel in `AGENTS.md` unter «Workflow» eingetragen (`CLAUDE.md`
  importiert nur `AGENTS.md`), die Begründung in Klammern aus der Vorlage weggelassen (die übrigen Regeln haben keine)
  und diesen Eintrag geschrieben.
- **Hinweis:** GitHub zeigt Issue-Formulare erst, wenn sie auf dem Standard-Branch liegen. Die Regel gilt deshalb ab
  dem Merge; dieses Paket selbst hat noch kein Issue.
