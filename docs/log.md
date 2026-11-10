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

## 2026-10-31 — Entscheidung: Formular «Package» an Richtlinien v3 angeglichen (Issue #5)

- **Entscheidung:** Das Issue-Formular heisst «Package» wie in den Richtlinien v3, Abschnitt 8, der Titel beginnt mit
  «Package: ». Das letzte Feld heisst «Nicht Teil davon» statt «Nicht enthalten». Das Feld «Fertig wenn» behält seinen
  Namen; «mit Erwartungswert» aus v3 steht in der Beschreibung, die den Erwartungswert jetzt verlangt statt nur «wo es
  einen gibt».
- **Begründung:** v3 nennt Formular und Felder so: «Was am Ende existiert, Welcher Frage es dient, Fertig wenn mit
  Erwartungswert, Art und Grösse, Nicht Teil davon». Die Vorlage im Tutorial führt «with the expected value» ebenfalls
  in der Beschreibung, nicht im Feldnamen.
- **Offen:** Die Regel in `AGENTS.md` spricht noch vom «Paket form»; sie war nicht Teil von Issue #5.

## 2026-10-31 — KI-Einsatz: Issue #5

- **Mine:** das Issue (schwagia) und die zwei Entscheide dazu (Haonan): Formular umbenennen in «Package»;
  «Fertig wenn» bleibt der Feldname, der Erwartungswert gehört in die Beschreibung.
- **Delegated:** die vier Zeilen in `package.yml`, der Titel «Package: » (aus der Tutorial-Vorlage übernommen) und
  diese Einträge.
- **Prüfung:** Feldnamen gegen Abschnitt 8 der Richtlinien v3 gelesen; YAML lädt; Tests und `ruff` laufen durch. Ob
  New issue das Formular so zeigt, lässt sich erst nach dem Merge von Hand prüfen.

## 2026-11-01 — Entscheidung: Regeln in `AGENTS.md` an Richtlinien v3 angeglichen (Issue #7)

- **Entscheidung:** Die Workflow-Regel nennt das Formular «Package». Die Regel zu den Prüfungen steht jetzt
  wörtlich in `AGENTS.md` (pro zentraler Zahl die eine Prüfung, deren Scheitern den Satz ändern würde, Erwartung vor
  dem Lauf, nicht alle fünf), mit Quelle «guidelines v3, section 3», statt auf «requirements section 6» zu verweisen.
- **Begründung:** `docs/requirements.md` gibt noch die Richtlinien v2 wieder, dort ist Abschnitt 6 die alte Regel
  («mindestens eine Prüfung»), und das PDF von v3 liegt nicht im Repository. Ein reiner Verweis auf v3 zeigte für
  den Agenten ins Leere; die zitierte Regel gilt auch ohne das Dokument.
- **Offen:** `docs/requirements.md` auf v3 nachführen (eigenes Issue).

## 2026-11-01 — KI-Einsatz: Issue #7

- **Mine:** das Issue (schwagia) und der Entscheid, die Regel zu zitieren statt zu verweisen (Haonan).
- **Delegated:** die englische Fassung der Regel aus Abschnitt 3 der Richtlinien v3, die zwei Änderungen in
  `AGENTS.md` und diese Einträge.
- **Prüfung:** Wortlaut gegen Abschnitt 3 der Richtlinien v3 gelesen; «Paket form» und «section 6» kommen in
  `AGENTS.md` nicht mehr vor; Tests und `ruff` laufen durch.
- **Übernommen/verworfen:** Die Kernregel ist fast wörtlich übernommen. In der ersten Fassung fehlte das Vorgehen
  aus Abschnitt 3 («für jede Prüfung fragen: kann sie hier scheitern, und ändert sich mein Satz; die erste mit
  zweimal ja wird gemacht, die anderen bekommen im Bericht eine Zeile, warum nicht»). Das war kein Entscheid,
  sondern eine Kürzung des Agenten; nach dem Review (schwagia, PR #8) steht es jetzt in `AGENTS.md`.

## 2026-11-01 — Entscheidung: `docs/requirements.md` gibt die Richtlinien v3 wörtlich wieder (Issue #9)

- **Entscheidung:** Der Teil «Arbeitsrichtlinien» ist ganz ersetzt, durch den Text von v3 (Version 3, 25. Oktober 2026)
  mit Titel, Einleitung, zehn Abschnitten, «Tutorial: …»-Hinweisen und allen Tabellen. Die Aufgabenstellung und der
  Dateikopf (Zeile 1–50) bleiben unverändert. Das PDF liegt weiterhin nicht im Repository.
- **Alternativen:** nur die geänderten Stellen nachführen (verworfen: dann stehen v2 und v3 gemischt in einer Datei);
  eine eigene Zusammenfassung (verworfen: der Text soll wörtlich sein).
- **Darstellung, nicht Wortlaut:** «Teil A/B/C» sind Fettzeilen, weil es zwischen «##» und «###» keine freie Ebene
  gibt: als «## Teil A» stünden sie auf derselben Ebene wie «Aufgabenstellung» und «Arbeitsrichtlinien», als «### Teil
  A» gäbe es dreizehn statt zehn Abschnitte. Entscheid des Agenten, nach Review (Hn1016) begründet. «Tutorial: …» steht
  kursiv unter dem Titel. Die über den Seitenumbruch laufende Tabelle in Abschnitt 3 ist eine Tabelle, ihre wiederholte
  Kopfzeile entfällt. Fettdruck wie im PDF; Backticks um Dateien und Befehle wie bisher in dieser Datei, das PDF hat
  keine.
- **Abweichung vom Issue:** Der Teil hat 153 Zeilen statt der geschätzten 80–120, weil v3 länger ist als v2 und nicht
  gekürzt wird.
- **Beleg:** Wortvergleich PDF gegen Markdown, siehe KI-Einsatz unten.
- **Erledigt:** der offene Punkt aus dem Eintrag zu Issue #7.
- **Offen:** `docs/one-pager.md`, Schritt 7, verweist noch auf «Abschnitt 6 der Richtlinien». Das stimmte für v2; in v3
  sind die Prüfungen Abschnitt 3. Die Datei ist nicht Teil von Issue #9 und braucht ein eigenes Issue.

## 2026-11-01 — KI-Einsatz: Issue #9

- **Aufgabe:** den Richtlinienteil von `docs/requirements.md` auf v3 nachführen.
- **Mine:** das Issue (Hn1016) und die Vorgaben dazu (schwagia): Text wörtlich, nicht umformuliert oder gekürzt;
  Aufgabenstellung unverändert; PDF nicht ins Repository; zuerst Plan, dann Go. Der Entscheid, den One-Pager in diesem
  Paket nicht anzufassen (schwagia, auf Vorschlag des Agenten).
- **Delegated:** Claude Code hat den Text aus dem PDF extrahiert (`pypdf`, Schriften mit `pymupdf`, beide nur in einer
  temporären Umgebung, keine neue Abhängigkeit), als Markdown gesetzt, die Darstellungsentscheide oben getroffen, den
  veralteten Verweis im One-Pager gefunden und diese Einträge geschrieben.
- **Prüfung:** Erwartungen vor dem Lauf im Plan notiert. Wortfolge PDF gegen Markdown (1733 Wörter): einziger
  Unterschied wie erwartet die wiederholte Kopfzeile «Prüfung Frage Beispiel». Zeile 1–50 byte-identisch mit `main`.
  Zehn `###`-Abschnitte in der Reihenfolge von v3. «mindestens eine der folgenden» kommt nicht mehr vor; «Package»,
  «Mine», «Delegated» und «die eine, deren Scheitern den Satz ändern würde» kommen vor. Tests und `ruff` laufen durch.
  Nicht geprüft: die Darstellung auf GitHub; Fettdruck und Zellgrenzen sind nicht Teil des Wortvergleichs.
- **Übernommen/verworfen:** Der Text ist unverändert übernommen. Verworfen: die reine Textextraktion als Grundlage für
  die Struktur, weil sie keine Hervorhebungen zeigt; die Schriften wurden deshalb einzeln ausgelesen. Der erste
  Wortvergleich meldete acht weitere Unterschiede; das war ein Fehler im Prüfskript (Backticks trennten Wörter), nicht
  im Text, und ist dort korrigiert. Den Verweis im One-Pager mitzuändern stand als Option im Plan; sie wurde nicht
  gewählt, weil die Datei ausserhalb des Issues liegt und reviewt ist.

## 2026-11-01 — Entscheidung: One-Pager an die Prüfregel der Richtlinien v3 angeglichen (Issue #11)

- **Entscheidung:** Schritt 7 verweist auf Abschnitt 3 der Richtlinien statt auf Abschnitt 6. Unter «Fertig» steht die
  Regel aus v3: pro zentraler Zahl die eine Prüfung, deren Scheitern den Satz ändern würde, mit der Erwartung vor dem
  Lauf. Die Zeile «Stand» nennt die Änderung vom 2026-11-01.
- **Begründung:** Seit `docs/requirements.md` v3 wiedergibt (Issue #9), widersprach der One-Pager den Richtlinien und
  `AGENTS.md`. Er ist Seite 1 des Abschlussberichts (v3, Abschnitt 4).
- **Klärung (Review PR #12):** Die Stabilität der Rangliste ist eine KPI der Aufgabenstellung und kommt in den
  Bericht, unabhängig von der Prüfauswahl. Die v3-Regel gilt zusätzlich für jede zentrale Zahl. Ob die Stabilität für
  die Rangliste auch die eine Prüfung ist, wird mit Erwartung vor dem Lauf festgelegt (offen, siehe One-Pager «Ab
  welcher Rangkorrelation die Rangliste als stabil gilt»).

## 2026-11-01 — KI-Einsatz: Issue #11

- **Aufgabe:** den One-Pager an die Prüfregel der Richtlinien v3 angleichen (Schritt 7, «Fertig», «Stand»).
- **Mine:** das Issue (schwagia) mit beiden Stellen und dem Datum in «Stand».
- **Delegated:** die drei Änderungen im One-Pager, diese Einträge und der Vorschlag für die Antwort zur Stabilität
  (Review PR #12), den Haonan übernommen hat.
- **Prüfung:** Die beiden Greps aus dem Issue finden nichts; «deren Scheitern den Satz ändern würde» steht unter
  «Fertig», «Abschnitt 3» in Schritt 7. Tests und `ruff` laufen durch.
- **Übernommen/verworfen:** Die Regel ist sinngemäss aus v3, Abschnitt 3 übernommen, in der Kurzform von `AGENTS.md`.
  Das Vorgehen «für jede Prüfung fragen …» steht nicht im One-Pager, weil der One-Pager das Ziel nennt, nicht das
  Vorgehen; es steht in `AGENTS.md` und `docs/requirements.md`. Verworfen nach Review (schwagia, PR #12): die
  Aufzählung der fünf Prüfarten wegzulassen. Der Agent hatte sie gestrichen, weil sie in `docs/requirements.md` steht;
  der One-Pager ist aber Seite 1 des Berichts, dessen Leserin das Repository nicht öffnet. Die fünf stehen jetzt als
  Auswahl in der Regel.

## 2026-11-01 — Entscheidung: Tests laufen in CI (Issue #13)

- **Entscheidung:** `.github/workflows/tests.yml` führt bei jedem Pull Request und jedem Push auf `main`
  `uv sync --locked` und `uv run pytest` aus. Job und Check heissen `tests`. Python kommt über uv aus `.python-version`.
- **uv-Version fest auf 0.13.6:** Alternative: immer die neueste uv-Version. Begründung: Der Check wird Pflicht; ein
  neues uv-Release soll keinen roten Check auslösen, der Merges blockiert. Das Issue verlangt das nicht. Die Version
  muss von Hand nachgezogen werden, im Workflow und in `pyproject.toml`.
- **uv-Version auch lokal Pflicht (Review PR #15, Hn1016):** `required-version = "==0.13.6"` unter `[tool.uv]` in
  `pyproject.toml`, damit lokal und in CI dieselbe uv-Version gilt; mit einer anderen Version bricht uv ab. Das README
  nennt die Version beim Setup und den Befehl `uv self update 0.13.6`. `pyproject.toml` war im Issue nicht genannt.
- **Wenn `main` rot wird (Review PR #15, Hn1016):** Wird `main` nach einem Merge rot, kümmert sich, wer zuletzt gemergt
  hat. Ist die Ursache nicht innerhalb eines Tages klar, wird der Merge über den Revert-Button auf GitHub
  zurückgenommen; die Korrektur kommt danach als Paket mit Issue.
- **Action-Versionen:** `actions/checkout@v7` und `astral-sh/setup-uv@v10.3.3`. Bei `setup-uv` gibt es seit v8 nur noch
  unveränderliche Release-Tags; ein Tag `v10` existiert nicht (Beleg: `git ls-remote --tags`, 2026-11-01), und der
  noch vorhandene Tag `v7` steht auf einer alten Version. Deshalb die neueste Major-Version mit vollem Tag.
- **Ruleset von `main` (`main-protection`, aktiv, von Haonan gesetzt):** Pull Request mit 1 Approval; Check `tests`
  (GitHub Actions) Pflicht; Bypass-Liste leer; «Require branches to be up to date» aus; Force Pushes und Löschen von
  `main` blockiert. Beleg: Regeln aus der GitHub-API (2026-11-01); die Bypass-Liste zeigt die API ohne Admin-Rechte
  nicht, sie steht hier nach Angabe von schwagia.
- **«Require branches to be up to date» aus:** Empfehlung an Haonan (schwagia), so umgesetzt. Das spart bei zwei
  Personen Rebases, und der Lauf bei jedem Push auf `main` zeigt, wenn zwei einzeln grüne PRs zusammen rot sind.
- **Prüfung, Erwartung vor dem Lauf:** Normaler PR: Check `tests` grün, 20 passed, 7 skipped. Test-PR gegen `main` mit
  einem absichtlich roten Test: Check rot, 1 failed, 20 passed, 7 skipped, Merge gesperrt; Schliessen ohne Merge.
- **Ergebnis:** Normaler PR #15: Check `tests` grün
  ([Lauf](https://github.com/Hn1016/DSP_SBB_Verspaetungsanalyse/actions/runs/41322544195/job/124895637850?pr=15)).
  Test-PR #16: Check `tests` rot, 1 failed, 20 passed, 7 skipped (der rote Test `test_ci_red`, die sieben Datentests
  übersprungen), im PR als «Required» markiert
  ([Lauf](https://github.com/Hn1016/DSP_SBB_Verspaetungsanalyse/actions/runs/41324264052/job/124900784171?pr=16)).
  Haonan hat #16 approvt, der Merge blieb trotzdem gesperrt; die Sperre kommt also vom Check, nicht vom fehlenden
  Approval. #16 ist ohne Merge geschlossen, der Branch gelöscht. Die Zahlen des grünen Laufs sind nur lokal auf
  demselben Commit belegt (`9b4682c`: 20 passed, 7 skipped), nicht aus dem CI-Log.

## 2026-11-01 — KI-Einsatz: Issue #13

- **Aufgabe:** die Tests als GitHub Action bei jedem Pull Request und jedem Push auf `main` laufen lassen.
- **Mine:** das Issue (Hn1016); die Vorgaben dazu (schwagia): uv mit Python aus `.python-version`, `uv sync --locked`,
  Job-Name `tests`, Tests unverändert. Von schwagia bewusst übernommen: die feste uv-Version (Vorschlag des Agenten)
  und «Require branches to be up to date» aus. Ruleset (Hn1016). Test-PR #16 geöffnet, beurteilt und geschlossen
  (schwagia, Hn1016). Nach Review Hn1016 (schwagia): uv 0.13.6 auch lokal über `required-version` in `pyproject.toml`
  mit Zeile im README; die Regel, wer sich um ein rotes `main` kümmert und wann per Revert zurückgenommen wird.
- **Delegated:** Claude Code hat den Workflow, die Zeilen im README, diese Einträge, den Ablauf des Test-PR und die Datei
  mit dem roten Test vorgeschlagen und geschrieben, die Tags geprüft und `setup-uv@v10.3.3` gewählt.
- **Prüfung:** In einem frischen Klon ohne Daten läuft `uv sync --locked`; `uv run pytest` ergibt 20 passed, 7 skipped
  (die sieben aus `tests/test_data.py`). Tags mit `git ls-remote --tags` geprüft. Auf GitHub: PR #15 grün, Test-PR #16
  rot und nicht mergebar trotz Approval (Ergebnis oben). Die Zahlen des roten Laufs hat schwagia aus dem CI-Log
  abgelesen; Claude Code hat ohne Admin-Rechte keinen Zugriff auf die Logs. Nicht abgelesen: die Zahlen des grünen Laufs.
- **Übernommen/verworfen:** Verworfen: ein eigener Python-Schritt im Workflow, weil uv die Version selbst aus
  `.python-version` liest; `ruff` als Pflicht-Check, weil das Issue ihn ausschliesst; `setup-uv@v10`, weil der Tag nicht
  existiert, und `setup-uv@v7`, der zwar als kurzer Tag existiert, aber drei Major-Versionen zurückliegt. Der Agent hatte
  `@v10` im Plan ungeprüft angenommen; die Prüfung vor dem Commit verlangte schwagia.


## 2026-11-01 — Hypothese: Erste Rangliste, eine Woche im Kanton Zürich (Issue #14, vor der Analyse notiert)

Anlass: erster Durchstich bis zu einer Rangliste (Richtlinien v3, Abschnitt 1, «Start»). Daten: Mo 7.9. bis
So 13.9.2026, Parquet in `data/processed/istdaten_rail/`, Haltestellenliste vom 2026-10-05.

- **Erwartung (schwagia, im Issue):** Zuoberst bei den Abschnitten steht Zürich Hardbrücke → Zürich HB, zuoberst bei
  den Halten steht Zürich HB. Gehalten heisst: der erwartete Eintrag steht auf Rang 1; jede Tabelle wird für sich
  bewertet.
- **Regeln aus dem Issue:**
  - Abschnitt = zwei aufeinanderfolgende Halte einer Fahrt, je Richtung getrennt (A→B ≠ B→A), beide Halte im Kanton
    Zürich laut Haltestellenliste.
  - Streckenverspätung = Ankunftsverspätung an B minus Abfahrtsverspätung an A, nur wenn beide `REAL` sind;
    Bereinigung über `quality.delays()`.
  - Haltverspätung nur an Halten mit geplanter Haltezeit von mindestens 1 Minute.
  - In die Tabelle kommt nur, wer in der Woche mindestens 20 gemessene Fahrten hat. Rangfolge nach Mittelwert.
- **Regeln, vom Team ergänzt (Haonan, 2026-11-01):**
  - «Aufeinanderfolgend» gilt in der ganzen Fahrt, nach `ZEILE`, auch über Halte ausserhalb des Kantons und Halte ohne
    `REAL`. Erst danach bleiben die Paare, bei denen beide Halte in Zürich liegen und gemessen sind. Ein Abschnitt über
    einen ausgefallenen Halt wird verworfen, ebenso einer mit rückwärts laufender Soll-Zeit.
  - Haltverspätung je Halt über beide Richtungen zusammen.
  - Die Schwelle von 1 Minute für die Haltverspätung genügt für diesen ersten Blick. Sie ersetzt nicht den
    Referenzwert je Soll-Haltezeit, den `AGENTS.md` vor einer Rangliste der Halte verlangt; das ist eine bekannte
    Grenze dieser Tabelle.
- *Folge bei Widerlegung:* kein Kurswechsel, sondern Hinweis, wo die Daten anders aussehen als erwartet; die
  Entscheidung trifft das Team nach dem Befund.

## 2026-11-01 — Befund: Erste Rangliste, eine Woche im Kanton Zürich (Issue #14)

Berechnet in `notebooks/03_erste_rangliste.py` nach den Regeln aus dem Hypothesen-Eintrag oben. Basis: 148'772
gemessene Abschnittsfahrten auf 400 Abschnitten, davon 373 mit mindestens 20 Fahrten; 69 Halte mit Soll-Haltezeit ab
1 Minute und mindestens 20 Fahrten.

**Top 10 Abschnitte nach mittlerer Streckenverspätung (min)**

| Rang | Abschnitt | Fahrten | Mittel | Median |
|---|---|---|---|---|
| 1 | Gibswil → Fischenthal | 206 | 1.45 | 1.47 |
| 2 | Thalwil → Zürich Enge | 257 | 1.09 | 0.75 |
| 3 | Zürich Oerlikon → Zürich Affoltern | 25 | 0.99 | 0.77 |
| 4 | Dietikon → Dietikon Schöneggstrasse | 511 | 0.95 | 0.93 |
| 5 | Pfungen → Winterthur Wülflingen | 284 | 0.87 | 0.87 |
| 6 | Zürich Enge → Thalwil | 252 | 0.74 | 0.63 |
| 7 | Eglisau → Glattfelden | 272 | 0.72 | 0.70 |
| 8 | Bauma → Steg | 210 | 0.72 | 0.73 |
| 9 | Winterthur → Zürich Stadelhofen | 25 | 0.62 | 0.37 |
| 10 | Turbenthal → Rämismühle-Zell | 331 | 0.62 | 0.62 |

**Top 10 Halte nach mittlerer Haltverspätung (min), Soll-Haltezeit ab 1 Minute**

| Rang | Halt | Fahrten | Mittel | Median |
|---|---|---|---|---|
| 1 | Oberwinterthur | 133 | 1.34 | 1.42 |
| 2 | Stammheim | 247 | 0.73 | 0.75 |
| 3 | Feuerthalen | 278 | 0.62 | 0.59 |
| 4 | Zürich Flughafen | 1978 | 0.62 | 0.50 |
| 5 | Rikon | 281 | 0.62 | 0.55 |
| 6 | Kloten | 273 | 0.61 | 0.63 |
| 7 | Samstagern | 266 | 0.58 | 0.51 |
| 8 | Saland | 554 | 0.53 | 0.15 |
| 9 | Dietikon | 1515 | 0.49 | 0.37 |
| 10 | Bassersdorf | 273 | 0.48 | 0.57 |

- **Befund Abschnitte: nicht gehalten.** Zürich Hardbrücke → Zürich HB steht auf Rang 326 von 373 (2'501 Fahrten,
  Mittel −1.31 min): Auf diesem Abschnitt nimmt die Verspätung im Mittel ab, er wirkt eher als Absorber.
- **Befund Halte: nicht gehalten.** Zürich HB steht auf Rang 13 von 69 (8'600 Fahrten, Mittel +0.30 min).
- **Grenzen dieses Befunds:**
  - Eine Woche, ein Kanton, nur Mittelwerte, keine Prüfung der Stabilität (laut Issue nicht Teil davon).
  - Zwei Abschnitte in den Top 10 haben nur 25 Fahrten (Rang 3 und 9). Es sind Haltemuster einzelner Linien zur
    Hauptverkehrszeit (Review PR #17): Zürich Oerlikon → Zürich Affoltern fährt nur die S21 ohne Halt in Seebach
    (Mo–Fr, 5 Züge, 16:50–18:50), Winterthur → Zürich Stadelhofen nur die S23 ohne Halt in Stettbach (Mo–Fr, 5 Züge,
    06:19–08:19). Die übrigen Züge (S6; S11, S12, S7) halten dazwischen und zählen zu kürzeren Abschnitten. Ein
    Abschnitt ist also durch die bedienten Halte bestimmt, nicht durch die Strecke; die zwei Mittelwerte gelten nur
    für diese Linien zur Spitzenzeit.
  - Durchfahrten können Halt A oder B sein (Prüfung, die am 6.10. für die Abschnittsbildung vorgemerkt war, Review
    PR #17): 22 von 148'772 Abschnittsfahrten; ohne sie ändert sich kein Mittel um mehr als 0.006 min, und die Top 10
    bleiben gleich. Sie bleiben drin, wie am 6.10. angenommen. Die zwei Abschnitte mit 25 Fahrten erklären sie nicht.
  - Verdacht, noch nicht geprüft (Review PR #17): Die Streckenverspätung könnte von der Soll-Fahrzeit abhängen
    (Annahme A7); kurze Soll-Fahrzeiten könnten wegen der Minutenrundung im Mittel positive Werte zeigen. Eine
    Auswertung dazu liegt nicht im Repository. Ob die Top 10 echte Verstärker oder kurze Abschnitte sind, ist offen.
  - Die Haltverspätung ist bei 1 Minute Soll-Haltezeit noch von der Rundung beeinflusst; ein Referenzwert je
    Soll-Haltezeit fehlt (Grenze, im Hypothesen-Eintrag notiert).
- **Entscheidung (Haonan und schwagia, 2026-11-03, Vorschlag schwagia im Review PR #17):** Die Rangliste wird noch
  nicht interpretiert, weil die Top 10 kurze Abschnitte sein könnten, deren Wert von der Minutenrundung kommt (A7).
  Nächstes Paket: prüfen, ob die Streckenverspätung von der Soll-Fahrzeit abhängt, und falls ja, einen
  Referenzwert je Soll-Fahrzeit einführen.

## 2026-11-01 — KI-Einsatz: Issue #14

- **Aufgabe:** die erste Rangliste der Abschnitte und Halte für eine Woche im Kanton Zürich berechnen.
- **Mine:** das Issue mit Erwartung, Regeln, Woche, Kanton und Schwelle (schwagia); die drei ergänzten Regeln
  (Haonan): «aufeinanderfolgend» über die ganze Fahrt mit Ausfällen als Lücke, Halte über beide Richtungen, 1 Minute
  als Schwelle für den ersten Blick. Die Entscheidung nach dem Befund.
- **Delegated:** das Notebook mit den Abfragen, der Hypothesen-Eintrag aus den Vorgaben, die Tabellen und der Befund
  samt Grenzen. Entscheide des Agenten: Nachbarn über alle Zeilen der Fahrt in `rail` (auch Ausland und Ausfälle),
  dann Abgleich mit `quality.delays()` über Betriebstag und `ZEILE`; Kanton direkt aus der Haltestellenliste gelesen,
  weil die gemeinsame Sicht `service_points` ihn nicht hat und `src/` laut Issue nicht geändert wird; Rang nach
  Mittelwert mit `rank()`, Median als zusätzliche Spalte.
- **Prüfung:** Die Woche enthält keine doppelten Zeilen und keinen Abschnitt mit rückwärts laufender Soll-Zeit; beide
  Rangfolgen einmal als Skript und einmal im Notebook gerechnet, gleiche Werte. Tests und `ruff` laufen durch.
  Nicht geprüft: Stabilität, Abhängigkeit von der Soll-Fahrzeit. Nach dem Review (2026-11-03, Fragen schwagia):
  zwei Zellen im Notebook, Durchfahrten als Abschnittsende und Linien der Abschnitte mit 25 Fahrten. Eine Erwartung
  stand vorher nur als Vermutung im Review («könnte die 25 Fahrten erklären»); sie hat sich nicht bestätigt.
- **Übernommen/verworfen:** Verworfen wurde eine «Rechenprobe» im Notebook, die nur dieselbe Summe zweimal rechnete
  und nicht scheitern konnte; die Zelle zeigt jetzt nur die Grösse der Basis.

## 2026-11-03 — Hypothese: Annahme A7, Streckenverspätung nach Soll-Fahrzeit (Issue #18, vor der Analyse notiert)

Anlass: Entscheidung zu Issue #14 (Rangliste noch nicht interpretieren) und Annahme A7 «Rundung neutral für
Abschnitte» (`docs/assumptions.md`). Basis wie Issue #14: Mo 7.9. bis So 13.9.2026, Kanton Zürich.

- **Erwartung (schwagia, im Issue):**
  - Abschnitte mit 1 Minute Soll-Fahrzeit haben im Mittel eine um mindestens 0.3 Minuten höhere Streckenverspätung als
    Abschnitte mit 5 Minuten und mehr.
  - Mindestens 5 der Top 10 Abschnitte aus Issue #14 haben eine Soll-Fahrzeit von höchstens 2 Minuten.
- **Klassen der Soll-Fahrzeit (aus dem Issue):** 1, 2, 3, 4, 5 und mehr Minuten, mit Anzahl Abschnittsfahrten je
  Klasse.
- *Folge bei Widerlegung:* Die Rangliste aus #14 braucht keinen Referenzwert je Soll-Fahrzeit. Sonst wird der
  Referenzwert ein eigenes Issue.

## 2026-11-05 — Befund: Annahme A7, Streckenverspätung nach Soll-Fahrzeit (Issue #18)

Berechnet in `notebooks/04_soll_fahrzeit.py` auf derselben Basis wie Issue #14 (148'772 gemessene Abschnittsfahrten,
Mo 7.9. bis So 13.9.2026, Kanton Zürich).

**Mittlere Streckenverspätung je Klasse der Soll-Fahrzeit (min)**

| Soll-Fahrzeit | Fahrten | Mittel | Median |
|---|---|---|---|
| 1 min | 9'801 | +0.24 | +0.30 |
| 2 min | 34'495 | −0.11 | −0.12 |
| 3 min | 46'803 | −0.53 | −0.52 |
| 4 min | 24'924 | −0.71 | −0.73 |
| 5 min und mehr | 32'749 | −0.79 | −0.85 |

**Soll-Fahrzeit der Top 10 Abschnitte aus Issue #14 (Median über die Fahrten der Woche)**

| Rang | Abschnitt | Fahrten | Mittel | Soll-Fahrzeit |
|---|---|---|---|---|
| 1 | Gibswil → Fischenthal | 206 | 1.45 | 1 |
| 2 | Thalwil → Zürich Enge | 257 | 1.09 | 6 |
| 3 | Zürich Oerlikon → Zürich Affoltern | 25 | 0.99 | 4 |
| 4 | Dietikon → Dietikon Schöneggstrasse | 511 | 0.95 | 1 |
| 5 | Pfungen → Winterthur Wülflingen | 284 | 0.87 | 2 |
| 6 | Zürich Enge → Thalwil | 252 | 0.74 | 6 |
| 7 | Eglisau → Glattfelden | 272 | 0.72 | 2 |
| 8 | Bauma → Steg | 210 | 0.72 | 4 |
| 9 | Winterthur → Zürich Stadelhofen | 25 | 0.62 | 17 |
| 10 | Turbenthal → Rämismühle-Zell | 331 | 0.62 | 2 |

- **Erwartung 1: gehalten.** Abschnitte mit 1 Minute Soll-Fahrzeit liegen im Mittel 1.03 Minuten über denen mit
  5 Minuten und mehr (Erwartung: mindestens 0.3). Das Mittel sinkt mit jeder Klasse, von +0.24 auf −0.79 min.
- **Erwartung 2: gehalten, genau an der Schwelle.** 5 der Top 10 haben eine Soll-Fahrzeit von höchstens 2 Minuten
  (Rang 1, 4, 5, 7, 10).
- **Befund A7: nicht gehalten.** Die Streckenverspätung hängt von der Soll-Fahrzeit ab. Die rohe Rangliste aus #14
  bevorzugt kurze Abschnitte.
- **Ursache offen (Review PR #19, schwagia):** Die Minutenrundung allein erklärt den Unterschied von gut einer Minute
  kaum; sie verschiebt eine Soll-Fahrzeit um höchstens eine halbe Minute, unabhängig von der Länge. Dass das Mittel
  auch von 3 über 4 zu 5 und mehr Minuten weiter sinkt, passt eher zu Fahrzeitreserven im Fahrplan, die auf langen
  Abschnitten grösser sind. Beides lässt sich mit diesen Daten nicht trennen. Für den Referenzwert ist die Ursache
  egal; im Bericht heisst «Absorber» darum vorerst «Abschnitt, auf dem Züge Zeit aufholen», nicht «Abschnitt mit
  Reserve» und nicht «Rundungseffekt».
- **Grenzen:** Eine Woche, ein Kanton. Die Rangliste aus #14 enthält keine Abschnitte mit 0 Minuten Soll-Fahrzeit;
  die Klassen decken alle 148'772 Fahrten ab.
- **Entscheidung (nach der Regel aus dem Issue):** Die Rangliste braucht einen Referenzwert je Soll-Fahrzeit. Er wird
  ein eigenes Issue. Evidenz von A7 in `docs/assumptions.md` auf «tief» gesetzt und die Tabelle neu sortiert.

## 2026-11-05 — KI-Einsatz: Issue #18

- **Aufgabe:** prüfen, ob die Streckenverspätung von der Soll-Fahrzeit abhängt (Annahme A7).
- **Mine:** das Issue mit Erwartung, Klassen und Basis (schwagia); Hypothese im Wortlaut des Issues, ohne Zusätze
  (Haonan).
- **Delegated:** das Notebook, der Hypothesen-Eintrag, beide Tabellen, Befund und dieser Eintrag. Entscheide des
  Agenten: Basis aus `03_erste_rangliste.py` im Notebook wiederholt, weil `src/` laut Issue nicht geändert wird;
  Mittel je Klasse über alle Abschnittsfahrten; Soll-Fahrzeit eines Abschnitts als Median über seine Fahrten.
- **Prüfung:** Die Summe der Fahrten über die Klassen ergibt die 148'772 aus #14, und die Top 10 stimmen mit dem
  Eintrag zu #14 überein (Abschnitte, Fahrten, Mittel). Tests, `ruff` und `marimo check` laufen durch.
- **Reihenfolge Hypothese und Analyse (Review PR #19, schwagia):** Der Hypothesen-Eintrag wurde am 3.11. geschrieben
  und am 4.11. auf den Wortlaut des Issues gekürzt, aber erst am 5.11. zusammen mit der Analyse committet; beide
  Commits tragen dieselbe Sekunde. Der Agent hat die Analyse gerechnet, bevor der Hypothesen-Commit bestand. Der
  eigene Commit belegt die Reihenfolge darum nicht. Beleg ist Issue #18 vom 3.11., 20:17 UTC, mit beiden Erwartungen;
  laut GitHub seither nicht bearbeitet. Ab dem nächsten Paket wird die Hypothese committet, bevor gerechnet wird.
- **Übernommen/verworfen:** Von `feat/assumption-checks` nichts übernommen: Die Prüfung dort rechnet über die ganze
  Schweiz und den ganzen September mit eigener Abschnittsbildung und wäre nicht dieselbe Basis wie #14.

## 2026-11-08 — Entscheidung: Status und Evidenz der Annahmen nachgeführt (Issue #20)

- **Entscheidung:** `docs/assumptions.md` hat eine Spalte «Status» (offen, gestützt, teilweise, widerlegt) mit Verweis
  auf den Log-Eintrag. Status und Evidenz stammen nur aus Einträgen in diesem Log auf `main`; wo keiner etwas belegt,
  gilt «offen» bzw. «tief». Evidenz heisst, wie stark das Log dafür spricht, dass die Annahme gilt (so verwendet in
  #18 für A7); der Status zeigt, ob «tief» «nicht geprüft» oder «widerlegt» bedeutet (Review PR #19).
- **Alternative:** Wo kein Log-Eintrag existiert, die Evidenz vom 17.10. stehen lassen. Verworfen: Diese Einschätzungen
  wurden ohne Daten gemacht (Kopf von `assumptions.md`, Eintrag 2026-10-29).
- **Änderungen (Evidenz bisher → neu, Status, Beleg):**

| # | Evidenz | Status | Beleg im Log |
|---|---|---|---|
| 1 | hoch → mittel | offen | 2026-10-06, H5: Werte plausibel; ob `REAL` gemessen und nicht interpoliert ist, nie geprüft |
| 2 | tief → mittel | teilweise | 2026-10-25, H6; 2026-10-28, Korrektur H6b: unabhängig von der Verspätung gestützt, vom Ort widerlegt |
| 3 | tief → tief | offen | 2026-10-28, Zuordnung: nur September |
| 4 | hoch → mittel | offen | 2026-10-06, H2: nur am 8.9.2026 geprüft; andere Monate nie |
| 5 | mittel → tief | offen | 2026-10-06, H2: 145 rückwärts laufende Abschnitte, «vermutlich Umleitungen», nur ein Hinweis |
| 6 | hoch → tief | offen | kein Eintrag |
| 7 | tief → tief | widerlegt | 2026-11-05, Befund A7 (#18): hängt von der Soll-Fahrzeit ab; Ursache offen |
| 8 | mittel → tief | offen | 2026-10-06, Nebenbefund: zeigt nur die Verzerrung, nicht dass ein Referenzwert sie behebt |
| 9 | hoch → tief | offen | 2026-10-29: H3 hat Ausfälle nur gezählt |
| 10 | hoch → tief | offen | 2026-10-29: Fahrten je Abschnitt und Zeitfenster nie gezählt |

- **Nicht verwendet:** die Prüfungen auf `feat/assumption-checks` (Hinweis im Eintrag 2026-10-29), weil sie nicht auf
  `main` liegen. Der Befund aus #14, dass ein Abschnitt durch die bedienten Halte bestimmt ist, betrifft verschiedene
  Haltepaare auf derselben Strecke und nicht A5.
- **Sortierung:** Wichtigkeit, Evidenz, Status («offen» zuerst), Nummer; A10, A9 und A5 (alle hoch, tief, offen) in der
  Prüfreihenfolge aus dem nächsten Eintrag. Die Wichtigkeit bleibt die Einschätzung vom 17.10.
- **Erledigt:** der offene Punkt aus dem Eintrag 2026-10-28 («Evidenz wird nachgeführt») und das Paket aus dem Eintrag
  2026-10-29.

## 2026-11-08 — Entscheidung: Reihenfolge der nächsten Prüfungen, zuerst «Regeln festlegen» (Issue #20)

- **Entscheidung (Team, nach Review PR #21):** Von den Annahmen mit hoher Wichtigkeit sind A10, A9 und A5 offen mit
  Evidenz «tief». Die Reihenfolge:
  1. Zeitraum und Zeitfenster festlegen, im Paket «Regeln festlegen».
  2. Beim Laden der zwölf Monate A3 und A4 mitprüfen; beide brauchen nur die neuen Monate.
  3. A10, dann A9, zuletzt A5.
- **Begründung:** A10 lässt sich erst prüfen, wenn Zeitraum und Zeitfenster festgelegt und die zwölf Monate geladen
  sind. Scheitert A10 (zu wenige gemessene Fahrten je Abschnitt und Zeitfenster), ändern sich Region oder Zeitfenster
  und damit die Regeln für die Rangliste; A10 ist danach günstig zu prüfen. A9 und A5 nach den Folgen eines
  Scheiterns: Scheitern A10 oder A9, betrifft es die ganze Rangliste; scheitert A5, betrifft es einzelne Abschnitte
  mit Umleitungen.
- Die Erwartung wird jeweils im eigenen Issue vor der Analyse notiert.
- **Abweichung vom Issue:** Das Issue verlangte, die oberste offene Annahme mit hoher Wichtigkeit als nächste
  Hypothese zu nennen. A10 bleibt die erste der drei, aber vor ihr kommen «Regeln festlegen» und A3 und A4.

## 2026-11-08 — KI-Einsatz: Issue #20

- **Aufgabe:** Status und Evidenz der zehn Annahmen in `docs/assumptions.md` nach dem Log nachführen und die Tabelle neu
  sortieren.
- **Mine:** das Issue (Hn1016); die Vorgaben (schwagia): Status und Evidenz nur aus Log-Einträgen auf `main`, pro
  Annahme der Eintrag, ohne Eintrag «offen»; Tabelle zuerst im Plan; Hypothesen-Hinweis und KI-Einsatz als eigene
  Einträge. Die Entscheide zum Plan (schwagia): Die Regel «nur aus dem Log» gilt, auch wenn A1, A4, A5, A6 und A8
  abgestuft werden, weil die Einschätzungen vom 17.10. ohne Daten waren; die vorgeschlagene Tabelle übernommen; nächste
  Hypothese A10, dann A9, dann A5, mit Begründung (der Agent hatte nur A5 und A9 als Gleichstand genannt und A10
  übersehen); Eintragstyp «Entscheidung» statt «Hypothese», weil v3 bei einer Hypothese eine Erwartung verlangt;
  Gleichstand nach dieser Prüfreihenfolge statt nach Nummer sortiert. Nach Review PR #21 (schwagia, nach Review
  Hn1016): zuerst Zeitraum und Zeitfenster im Paket «Regeln festlegen», dann A3 und A4 beim Laden der zwölf Monate,
  danach A10, A9, A5, weil A10 erst mit festgelegtem Zeitraum und geladenen Monaten prüfbar ist; Begründung für A5
  nach den Folgen eines Scheiterns statt nach den 145 rückwärts laufenden Abschnitten, die nur Umleitungen mit
  rückwärts laufender Zeit zeigen.
- **Delegated:** Claude Code hat die Regel für Status und Evidenz, die Tabelle mit Status, Evidenz und Begründung je
  Annahme, die Sortierschlüssel Status und Nummer, die Kopfzeile und diese Einträge vorgeschlagen und geschrieben.
- **Prüfung:** Jede Zeile gegen den zitierten Log-Eintrag gelesen (schwagia im Plan); jeder Verweis in der Tabelle
  steht als Eintrag im Log auf `main`; Fertig-Kriterien aus dem Issue (A2 teilweise, A7 widerlegt, A9 und A10 offen,
  alle zehn mit Status); Tests und `ruff` laufen durch.
- **Übernommen/verworfen:** Tabelle übernommen. Verworfen: die Sortierung des Gleichstands nach Nummer, die A5 zur
  nächsten Hypothese gemacht hätte; die Nummer ist kein fachlicher Grund. Gegenüber der Tabelle im Plan stehen A1 und A4
  vor A2: Das folgt aus dem Status als drittem Sortierschlüssel, den der Plan nannte, aber in der Tabelle nicht
  angewendet hatte.

## 2026-11-08 — Entscheidung: Ein Befehl `uv run build` baut alles aus den Rohdaten (Issue #22)

- **Entscheidung:** `uv run build` (`src/sbb_delays/build.py`) ruft die bestehenden Schritte `download` und `load`
  der Reihe nach auf, ohne deren Logik zu ändern. Der Zeitraum steht nur in `src/sbb_delays/period.py`
  (`START`, `END`), vorerst September 2026.
- **Gebaut oder übersprungen:** Vor jedem Schritt prüft `build`, ob alle Zieldateien des Zeitraums existieren:
  Haltestellen-Schnappschuss und ein ZIP pro Monat für `download`, eine Parquet-Datei pro Tagesdatei im ZIP für
  `load` (Namen aus der Dateiliste des ZIPs, ohne zu entpacken; Review PR #25).
  Existieren alle, wird der Schritt nicht aufgerufen («übersprungen»). Fehlt eine, läuft der Schritt («gebaut»), und
  die bestehenden Funktionen überspringen einzelne vorhandene Dateien selbst (`fetch`, `fetch_service_points`,
  `zip_to_rail_parquet`). Ein abgebrochener Lauf setzt so dort fort, wo er stand.
- **Ausgabe:** «Eine Zeile pro Schritt» gilt für stdout. Die Fortschrittsbalken der Schritte (tqdm) bleiben auf
  stderr, weil sie beim Download von 1.4 GB pro Monat nützlich sind und ein Ausblenden die Schritte ändern würde.
- **`--force`:** löscht nur die Parquet-Dateien der Tagesdateien im Zeitraum und baut sie neu. `data/raw` bleibt
  unangetastet; `download` meldet dann «übersprungen».
- **Fehlende Tage:** Fehlt im Monatsarchiv ein Kalendertag des Zeitraums, druckt `build` eine Warnung auf stderr;
  «übersprungen» stimmt trotzdem, weil die Zieldateien aus den Tagesdateien im ZIP kommen (Review PR #25). Für
  September 2026 liegen alle 30 Tage vor.
- **README:** nennt nur noch `uv run build` als Weg zu den Daten; die Einzelbefehle `download` und `load` stehen
  nicht mehr darin, damit der Zeitraum nur in `period.py` steht (Review PR #25). `download.py` und `load.py` bleiben
  unverändert und lassen sich weiterhin einzeln aufrufen.
- **Offen:** Lokale Downloads hängen Zeilen an das versionierte `data/raw/manifest.csv` an (zurzeit zwei
  uncommittete Zeilen vom 3.11.2026: ein neuer Haltestellen-Schnappschuss und das September-ZIP noch einmal, mit
  gleicher Prüfsumme). Wie wir damit umgehen, wird ein eigenes Paket; die Zeilen sind nicht Teil dieses Pakets.
  Ebenfalls Teil desselben Pakets: Ein frischer Klon lädt eine neue Haltestellenliste (2026-11-08 statt
  2026-10-05), damit hängt die Zuordnung zum Kanton vom Zeitpunkt des Klons ab (Review PR #25).

## 2026-11-08 — KI-Einsatz: Issue #22

- **Aufgabe:** Ein Befehl `uv run build`, der `download` und `load` für den Zeitraum der Reihe nach ausführt und
  vorhandene Ergebnisse überspringt, mit Test, Eintrag in `pyproject.toml`, README und Log.
- **Mine:** das Issue (Hn1016); die Vorgaben (schwagia): bestehende Funktionen aufrufen, ihre Logik nicht ändern,
  und im Plan zeigen, wo sie schon überspringen; Zeitraum an genau einer Stelle; pro Schritt genau eine Zeile;
  `--force` baut nur `data/processed` neu; Test ohne echte Daten und ohne Netzwerk, prüft Reihenfolge und
  Überspringen; im Log nur Verweise auf das Issue. Die Entscheide zum Plan (schwagia): Fortschrittsbalken bleiben auf
  stderr, «eine Zeile» gilt für stdout; das Beispiel `--from 2026-09` im README bleibt; `manifest.csv` wird nicht
  committet, der Umgang damit wird ein eigenes Paket; «gebaut/übersprungen» wird vorher an den Zieldateien erkannt,
  weil das direkter und leichter zu erklären ist. Nach Review PR #25 (schwagia, nach Review Hn1016): Zieldateien
  von `load` aus den Tagesdateien im ZIP statt aus allen Kalendertagen, fehlender Kalendertag als Warnung auf stderr,
  mit Test; im README nur noch `uv run build`, ohne Einzelbefehle; beim offenen Punkt zum Manifest die neue
  Haltestellenliste eines frischen Klons ergänzen. Ebenfalls nach Review PR #25 (schwagia): `AGENTS.md` nennt
  `uv run build` als Quelle der Parquet-Dateien, mit Hinweis auf `period.py`, und `notebooks/01_sample.py` nennt
  `uv run build` statt der Einzelbefehle, damit der Agent und das Notebook nicht auf die alten Befehle verweisen.
- **Delegated:** Claude Code hat den Plan mit den Stellen, an denen die Funktionen überspringen
  (`download.py:63`, `download.py:114`, `load.py:91`), `period.py`, `build.py`, `tests/test_build.py`, den Eintrag
  in `pyproject.toml`, die README-Abschnitte und diese Einträge vorgeschlagen und geschrieben; nach Review PR #25
  die Umsetzung der Korrekturen (`archive_days`, `missing_days`, Test mit fehlendem Tag, README, `AGENTS.md`,
  `notebooks/01_sample.py`, Log).
- **Prüfung:** Drei Tests (erster Lauf in Reihenfolge Haltestellen, ZIP, `load`; zweiter Lauf überspringt beide
  Schritte ohne Netzwerkaufruf, ohne neue Manifest-Zeile und ohne neu geschriebene Parquet-Dateien; `--force` baut
  `load` neu und lässt `data/raw` byte-gleich). Nur `requests.get` und die Pfade sind ersetzt, die bestehenden
  Funktionen laufen echt. Ob die Tests scheitern können: mit drei absichtlich eingebauten Fehlern (Prüfung vor `load`
  entfernt, `load` vor `download`, `download` nie übersprungen) schlug je mindestens ein Test fehl. `uv run build`
  auf den lokalen Septemberdaten: zweimal «übersprungen», Manifest unverändert. `--force` auf echten Daten nicht
  ausgeführt (entpackt den ganzen Monat); das deckt der Test ab. Tests und `ruff` laufen durch. Nach Review PR #25:
  vierter Test (Archiv ohne den 15.9.: zweiter Lauf «übersprungen» und eine Warnung); er schlägt mit der alten
  Fassung (Zieldateien aus allen Kalendertagen) fehl und läuft mit der neuen durch. `uv run build` auf den lokalen
  Daten: zweimal «übersprungen», keine Warnung.
- **Übernommen/verworfen:** Übernommen: Aufbau, Test und README. Verworfen: der Vorschlag im Plan, «gebaut» an einer
  neuen Zeile im Manifest bzw. an der Rückgabe von `zip_to_rail_parquet` zu erkennen und beide Schritte immer
  aufzurufen. Ersetzt durch die Prüfung der Zieldateien vor dem Schritt (Entscheid schwagia): Sie ist direkter, und
  ein übersprungener Schritt wird gar nicht aufgerufen. Dafür muss `build` die Dateinamen der Schritte kennen; der
  ZIP-Name wird aus `download.ISTDATEN_URL` abgeleitet, und der Test prüft, dass es dieselbe Datei ist, die
  `fetch_istdaten` schreibt. Die Grenze bei fehlenden Kalendertagen aus der ersten Fassung (`load` meldete bei jedem
  Lauf «gebaut») ist mit Review PR #25 behoben. Dafür liest `build` die Tagesdateien im ZIP mit derselben Regel wie
  `zip_to_rail_parquet` (Endung `.csv`, die ersten zehn Zeichen des Namens); ändert sich die Regel in `load.py`,
  muss `build.py` mitgehen.

## 2026-11-08 — Entscheidung: Haltestellenliste als fester Schnappschuss, Manifest ohne doppelte Zeilen (Issue #26)

- **Ausgangslage:** Der Permalink der Haltestellenliste liefert nur die Fassung des Tages
  (`actual-date-swiss-service-point.csv`); frühere Fassungen bietet der Anbieter nicht an. Ein frischer Klon lud darum
  eine andere Liste als die bisherigen Auswertungen (Review PR #25: 2026-11-08 statt 2026-10-05).
- **Entscheidung:** Der Build verwendet einen festen Schnappschuss. Datum und Prüfsumme stehen nur in
  `src/sbb_delays/period.py` (`SERVICE_POINTS_DATE`, `SERVICE_POINTS_SHA256`). Die Datei ist ein Auszug der Liste vom
  2026-10-05 (Schweizer Halte, `uicCountryCode` 85, nur die Spalten, die der Code liest, nach Nummer sortiert; 33'031
  Zeilen, 2.8 MB), erzeugt mit `download.extract_service_points` und als Release `service-points-2026-10-05` dieses
  Repositorys veröffentlicht. `build` lädt ihn von dort, prüft die Prüfsumme und bricht mit einer Meldung ab, wenn er
  fehlt oder abweicht. Die Prüfsumme steht auch im Manifest; ein Test prüft, dass beide übereinstimmen.
- **Alternativen:**
  - Rohdatei unverändert als Release: verworfen. Grundlage sind die Nutzungsbedingungen Open Data von
    opentransportdata.swiss (abgerufen 2026-11-08), im Wortlaut:
    - §1: «Der Zugang zu den Daten erfolgt über opentransportdata.swiss. Die bezogenen Daten dürfen aufbereitet,
      analysiert und publiziert werden, inkl. Einbezug weiterer Daten.»
    - §5.1: «In Publikationen und Analysen, die auf ODMCH-Daten basieren, ist die URL opentransportdata.swiss als
      Bezugsort der Rohdaten anzugeben.»
    - §5.2: «ODMCH-Daten müssen regelmässig aktualisiert werden, entsprechend dem zugrundeliegenden Aktualisierungstakt
      der Rohdaten.»

    Auslegung (vom Agenten, vom Team übernommen, nicht rechtlich geprüft): Eine unveränderte Kopie ist keine
    Aufbereitung nach §1 und umgeht den Zugang über opentransportdata.swiss; der Auszug ist eine Aufbereitung, mit
    opentransportdata.swiss als Bezugsort (§5.1, im README und im Release).
  - Gemeinsamer Ablageort nur für das Team (Richtlinien v3, Abschnitt 9) statt öffentlichem Release (Review PR #27):
    verworfen (Entscheid Haonan). Ein frischer Klon, auch der des Betreuers, bräuchte dann einen Zugang oder einen
    manuellen Schritt (Richtlinien v3, Abschnitt 6: «Keine manuellen Zwischenschritte»). Das Release lässt sich
    jederzeit löschen, falls die Auslegung nicht hält.
  - Versionsgeschichte des Anbieters (`full-swiss-service-point.csv`, alle Fassungen mit Gültigkeit), je Betriebstag
    die gültige Fassung: verworfen, weil auch sie nicht reproduzierbar ist. Abgerufen am 2026-11-08: 604 Fassungen von
    565 Halten, die vor dem 2026-10-05 gültig wurden, sind nach dem 2026-10-05 bearbeitet worden; für den 2026-10-05
    weicht sie vom Schnappschuss ab (219 Koordinaten, 76 Gültigkeiten, 2 Namen; 261 bzw. 53 Halte nur in einer der
    beiden). Einmalige Abfrage, nicht im Repository.
  - Nur die Prüfsumme der Tagesfassung prüfen: verworfen, weil danach jeder frische Klon abbricht.
- **Was die Wahl für die bisherigen Ergebnisse bedeutet:** nichts. Für die Bahnhalte im September 2026 ergibt die
  Versionsgeschichte keinen anderen Kanton als der Schnappschuss (0 von 48'609 Halt-Tagen); im Zeitraum Juli 2025 bis
  Juni 2026 wechseln nur 25 Halte in Moutier den Kanton (BE → JU), keiner in Zürich. Notebook 04 ergibt mit dem Auszug
  dieselben Zahlen wie im Befund zu #18. Die Koordinaten unterscheiden sich an 2'566 Halt-Tagen; das betrifft die Karte.
- **Annahme:** Ein Schnappschuss genügt für den ganzen Zeitraum ab 2025-07, solange nur der Kanton verwendet wird. Für
  die Karte wird das neu geprüft.
- **Offene Prüfung für das Paket «Zwölf Monate laden» (Review PR #27, schwagia):** Enthält der Schnappschuss vom
  Oktober 2026 alle Halte, die von Juli 2025 bis Juni 2026 bedient wurden, auch inzwischen aufgehobene? Fehlt ein Halt,
  fehlt sein Kanton, und seine Abschnitte fallen still weg. Prüfung auf den echten Daten: jede `BPUIC` der zwölf Monate
  steht im Auszug. Vorab aus der Versionsgeschichte (einmalige Abfrage, nicht im Repository): 229 Schweizer Halte waren
  im Zeitraum gültig und fehlen im Schnappschuss, davon ein Bahnhalt (Aigle-Hôpital, VD, gültig bis 13.12.2025), keiner
  im Kanton Zürich.
- **Grenze:** §5.2 der Nutzungsbedingungen verlangt, Daten «regelmässig» zu aktualisieren. Für eine Auswertung eines
  festen vergangenen Zeitraums halten wir einen festen Schnappschuss für vertretbar; geklärt mit dem Anbieter ist das
  nicht.
- **Manifest (offener Punkt aus Issue #22):** `append_manifest` fügt keine Zeile hinzu, wenn Datei und Prüfsumme schon
  im Manifest stehen. Ein frischer Klon lässt `data/raw/manifest.csv` so unverändert. Committet werden die Zeilen der
  Dateien, die der Build braucht, im Pull Request, der sie einführt; die Zeile der Rohdatei vom 2026-10-05 bleibt als
  Herkunft des Auszugs stehen.

## 2026-11-08 — KI-Einsatz: Issue #26

- **Aufgabe:** Der Build verwendet eine feste Haltestellenliste mit Prüfsumme; Entscheidung zum Manifest.
- **Mine:** das Issue (schwagia); die Entscheide (Haonan): ein eigener fester Schnappschuss statt nur Prüfsumme,
  zuerst als Rohdatei im Release, nach dem Befund zu den Nutzungsbedingungen als Auszug; doppelte Manifest-Zeilen
  überspringen; kein neues Issue, weil die Versionsgeschichte das Problem nicht löst; nach Review PR #27 das
  öffentliche Release behalten statt eines Ablageorts nur für das Team. Die Nutzungsbedingungen hat das Team nur in den
  vom Agenten zitierten Stellen gelesen, nicht die ganze Seite.
- **Delegated:** Claude Code hat die Quellen des Anbieters und die Nutzungsbedingungen gelesen und ausgelegt (Kopie
  keine Aufbereitung nach §1, Auszug schon; darauf baut das öffentliche Release auf), die Versionsgeschichte
  ausgewertet, die drei Wege vorgeschlagen und den Code, die Tests, den Auszug, den README-Abschnitt und diese
  Einträge geschrieben. Entscheide des Agenten: Spalten des Auszugs (die, die `quality.connect` und die Notebooks
  lesen, mit den Namen des Anbieters); Name `service-points-ch_<Datum>.csv`; `latest_service_points` ersetzt durch
  `service_points_snapshot`, auch in `quality.py`, `tests/test_data.py` und den Notebooks 03 und 04, weil sie sonst die
  neueste Datei im Ordner lesen statt den Schnappschuss.
- **Prüfung:** Fünf neue Tests ohne Netzwerk: Download des festen Schnappschusses, auch wenn eine neuere Liste im
  Ordner liegt, und kein zweiter Download und keine zweite Manifest-Zeile beim zweiten Lauf; Abbruch bei anderer
  Prüfsumme (keine Datei, kein `.part`, keine Manifest-Zeile); Abbruch, wenn das Release fehlt; Abbruch bei lokal
  geänderter Datei; Prüfsumme in `period.py` gleich der im Manifest. Die Tests scheitern, wenn die Prüfung der
  Prüfsumme oder das Überspringen doppelter Zeilen entfernt wird. Notebook 04 mit dem Auszug: Klassen, Top 10 und
  beide Erwartungen wie im Befund zu #18. Tests, `ruff` und `marimo check` laufen durch.
- **Übernommen/verworfen:** Verworfen: die Rohdatei als Release (Nutzungsbedingungen §1) und die Versionsgeschichte
  (nachträglich bearbeitet, siehe Entscheidung).

## 2026-11-08 — Entscheidung: Abschnitte als Pipeline-Schritt mit Fixture (Issue #24)

- **Entscheidung:** `sections.sections(con)` (`src/sbb_delays/sections.py`) bildet die Abschnittsfahrten aus der
  View `rail` der Verbindung, wie die Funktionen in `quality.py`, und gibt eine Tabelle zurück. Regeln wie in
  `notebooks/03_erste_rangliste.py` (Issue #14) und Review PR #17: Nachbarn nach `ZEILE` über die ganze Fahrt (alle
  Zeilen, auch ausländische und ausgefallene Halte), Halt A und B aus `quality.delays()`, Abfahrt an A und Ankunft
  an B gemessen (`REAL`), Abschnitte mit rückwärts laufender Soll-Zeit verworfen. Keine Einschränkung auf eine
  Region. Spalten: Betriebstag, Fahrt, Linie, `ZEILE` von A und B, Halt A und B, Abfahrtsverspätung A,
  Ankunftsverspätung B, Streckenverspätung, Soll-Fahrzeit (min), Durchfahrt an A oder B.
- **Durchfahrten zählen als Punkt (Regel a, wie #14):** Eine Durchfahrt (`DURCHFAHRT_TF`) kann Halt A oder B eines
  Abschnitts sein. Festgehalten in Fall 6 der Fixture (`tests/fixtures/sections_cases.csv`).
  - Alternative (b): Durchfahrten auslassen und über sie hinweg einen Abschnitt bilden (in Fall 6 8500120 →
    8500140). Verworfen, weil sonst die Prüfung gegen #14 nicht stimmt; laut Review PR #17 betrifft die Regel nur
    22 von 148'772 Abschnittsfahrten, und ohne sie ändert sich kein Mittel um mehr als 0.006 min.
- **Zeitraum:** `sections` filtert auf die Betriebstage von `START` bis `END` aus `period.py`, nicht auf alles in
  `data/processed/istdaten_rail/`. Sonst nähme der Schritt nach dem Laden der zwölf Monate auch den September 2026
  mit.
- **Build-Schritt:** `uv run build` hat am Ende einen dritten Schritt `sections`; `download` und `load` sind
  unverändert. Ziel ist `data/processed/sections_<Start>_<Ende>_<Prüfsumme>.parquet` (zurzeit
  `sections_2026-09_2026-09_0171af71.parquet`). Der Zeitraum steht im Namen, damit eine Änderung in `period.py` einen
  neuen Build auslöst, statt alte Abschnitte zu überspringen. Die Prüfsumme (die ersten 8 Zeichen von SHA-256 über den
  Inhalt von `src/sbb_delays/sections.py` und `src/sbb_delays/quality.py`) steht im Namen, damit der Build
  Regeländerungen selbst erkennt (Review PR #29); nach einem Neubau werden ältere Abschnittsdateien desselben
  Zeitraums gelöscht. `sections` wird übersprungen, wenn die Datei existiert, ausser bei `--force` oder wenn `load` im
  selben Lauf etwas gebaut hat (sonst blieben die Abschnitte nach neu geladenen Tagen veraltet).
  Grenze der Prüfsumme: Sie erkennt jede Änderung der zwei Dateien, auch Kommentare, und baut dann unnötig neu
  (1.4 s für September); Änderungen in anderen Dateien, die auf die Abschnitte wirken (z. B. die Typisierung in
  `load.py`), erkennt sie nicht.
- **Abweichung vom Issue:** Das Issue nennt `data/processed/sections.parquet`; der Name enthält jetzt den Zeitraum
  (siehe oben). Das README beschreibt den dritten Schritt, weil es sonst «zwei Schritte» nennen würde. `.gitignore`
  enthält neu `.tmp/`: Dorthin lagert DuckDB aus, wenn eine Abfrage den Speicher übersteigt (relativ zum
  Arbeitsverzeichnis). Ein abgebrochener Gegenversuch hatte dort 120 GB hinterlassen, und `git add -A` blieb daran
  hängen (siehe KI-Einsatz).
- **Prüfung gegen #14** (`notebooks/05_abschnitte_pruefung.py`, ausserhalb der Tests): Mo 7.9. bis So 13.9.2026,
  beide Halte im Kanton Zürich (Kanton aus `service_points_snapshot()`, fester Schnappschuss vom 2026-10-05).
  Erwartung vor dem Lauf, aus dem Issue und dem Befund zu #14: 148'772 Abschnittsfahrten auf 400 Abschnitten.
  Ergebnis: 148'772 Abschnittsfahrten, 400 Abschnitte, davon 22 Fahrten mit Durchfahrt (wie Review PR #17). Für den
  ganzen September 2026 und die ganze Schweiz ergibt der Schritt 4'094'329 Abschnittsfahrten an 30 Tagen.
- **Zeilenvergleich mit der Logik aus Notebook 03** (Review PR #29, im selben Notebook): Betriebstag, `ZEILE` von A
  und B, Halt A und B, Streckenverspätung, in beide Richtungen mit `except all`. Erwartung vor dem Lauf: 0
  Abweichungen in beiden Richtungen. Ergebnis: 148'772 Zeilen auf beiden Seiten, 0 nur im neuen Schritt, 0 nur in der
  Logik aus Notebook 03. Der Vergleich kann scheitern: Ohne Durchfahrten auf der Seite von Notebook 03 (Regel b)
  zeigt er 22 Zeilen nur im neuen Schritt.

## 2026-11-08 — KI-Einsatz: Issue #24

- **Aufgabe:** Abschnittsbildung aus Notebook 03 als Funktion in `src/sbb_delays/sections.py` und als Schritt
  `sections` in `uv run build`, mit handgeschriebener Fixture, Test, Prüfung gegen #14 und Log.
- **Mine:** das Issue (Hn1016). Die Vorgaben (schwagia): die sechs Fälle der Fixture; Erwartungswerte der Fixture von
  schwagia nachgerechnet und festgelegt; Regel a für Durchfahrten; Test vor der Funktion, zuerst rot, Erwartungswerte
  nicht ändern; Regeln wie Notebook 03 und Review PR #17, Bereinigung über `quality.delays()`; Funktion nimmt eine
  Tabelle und gibt eine Tabelle zurück; in `build.py` nur am Ende einen Schritt anhängen; Prüfung gegen #14
  ausserhalb der Tests mit dem Kanton aus dem festen Schnappschuss. Die Entscheide zum Plan (schwagia): Eingabe ist
  die View `rail` der Verbindung, wie in `quality.py`; ein Stub, damit der Test an den Erwartungswerten scheitert und
  nicht an einem fehlenden Modul; `sections` filtert auf den Zeitraum aus `period.py`, mit einem Test, dass ein Tag
  ausserhalb keine Abschnitte ergibt; der Zeitraum steht im Dateinamen. Nach der Umsetzung (schwagia): `sections`
  wird auch neu gebaut, wenn `load` im selben Lauf etwas gebaut hat (Vorschlag des Agenten, bewusst übernommen).
  Nach Review PR #29 (schwagia, nach Review Hn1016): eine Prüfsumme (8 Zeichen) über `sections.py` und `quality.py` im
  Dateinamen, damit der Build Regeländerungen selbst erkennt, ältere Dateien desselben Zeitraums werden gelöscht, mit
  Test und angepasstem README; in Notebook 05 der Zeilenvergleich mit der Logik aus Notebook 03, Abweichungen in beide
  Richtungen, Erwartung 0, statt der Grenze «vergleicht nur Anzahlen». Danach (schwagia): `.tmp/` in `.gitignore`
  aufnehmen, Vorschlag des Agenten nach den 120 GB DuckDB-Zwischendateien im Repository.
- **Delegated:** Claude Code hat den Plan, die Fixture-Datei aus den sechs Fällen (Spalten wie in
  `load.SELECT_TYPED`, Füllwerte für Betreiber, Linie und Namen), den Test, den Stub, `sections.py`, den
  Build-Schritt, die Anpassung von `tests/test_build.py`, Notebook 05, den README-Abschnitt und diese Einträge
  geschrieben. Entscheide des Agenten: Ausgabespalten; Fall-Namen als `FAHRT_BEZEICHNER` (z. B.
  `fall6_durchfahrt_zaehlt_als_punkt`) und Kommentarkopf in der Fixture; `sections` wird auch neu gebaut, wenn `load`
  etwas gebaut hat (von schwagia übernommen, siehe «Mine»); die 400 Abschnitte als zweite Zahl in der Prüfung gegen
  #14.
- **Prüfung:** Der Test lief zuerst gegen den Stub (leere Tabelle mit den Ausgabespalten) und schlug in beiden Fällen
  an den Erwartungswerten fehl; mit `sections.py` lief er durch, ohne dass ein Erwartungswert geändert wurde. Ob er
  scheitern kann: mit drei eingebauten Fehlern (Nachbarn aus `delays()` statt aus `rail`, was in Fall 2 und 5
  Abschnitte über den ausgefallenen bzw. ausländischen Halt bildet; Regel zur rückwärts laufenden Soll-Zeit entfernt;
  Filter auf den Zeitraum entfernt) schlug je mindestens ein Test fehl. `tests/test_build.py`: die drei Zeilen auf
  stdout, 30 Abschnittsfahrten im Archiv des Tests, Überspringen beim zweiten Lauf und eine neue Datei bei anderem
  Zeitraum. Prüfung gegen #14 auf den echten Daten: 148'772 und 400 wie erwartet (siehe Entscheidung). Tests, `ruff`
  und `marimo check` laufen durch. Nach Review PR #29: neuer Test (gleiche Regeln: übersprungen; geänderte Kopie von
  `quality.py`: neu gebaut, alte Datei gelöscht, danach wieder übersprungen); er schlägt fehl, wenn die Prüfsumme
  nicht im Namen steht oder die alte Datei nicht gelöscht wird. `uv run build` auf den lokalen Daten hat die Datei
  ohne Prüfsumme durch `sections_2026-09_2026-09_0171af71.parquet` ersetzt. Zeilenvergleich: 0 und 0 wie erwartet,
  Gegenprobe ohne Durchfahrten 22 (siehe Entscheidung). Ein erster Gegenversuch (Notebook 03 ohne die Regel zur
  rückwärts laufenden Soll-Zeit) lief nach über 15 CPU-Minuten nicht durch und wurde abgebrochen.
- **Übernommen/verworfen:** Verworfen im Plan: ein `ModuleNotFoundError` als erstes Scheitern (ersetzt durch den Stub,
  Entscheid schwagia) und `data/processed/sections.parquet` ohne Zeitraum (Entscheid schwagia). Der Vorschlag, die
  Ordnergrenze nur im Log zu nennen, ist durch den Filter auf den Zeitraum ersetzt.

## 2026-11-08 — Hypothese: Zwölf Monate, Annahmen A3 und A4, Halte im Schnappschuss (Issue #30, vor der Analyse notiert)

Anlass: Entscheidung zu Issue #20 (A3 und A4 beim Laden der zwölf Monate prüfen) und offene Prüfung aus PR #27. Daten:
1.7.2025 bis 30.6.2026 (`period.py`), Parquet aus `uv run build`. Fahrplan 2025 bis 13.12.2025, Fahrplan 2026 ab
14.12.2025. Kanton aus dem festen Schnappschuss der Haltestellenliste (2026-10-05).

- **Erwartung (schwagia, im Issue):**
  - (A3) Der `REAL`-Anteil im Kanton Zürich liegt in jedem Monat über 95 % und unterscheidet sich zwischen den beiden
    Fahrplänen um weniger als 1 Prozentpunkt (H1: September 2026 Schweiz 96.2 %, Tage 95.5–96.7 %).
  - (A4) In jedem Monat widerspricht die `ZEILE`-Reihenfolge bei weniger als 0.1 % der Fahrten der Soll-Zeit (H2:
    0 Widersprüche am 8.9.2026).
  - (Halte) Kein im Kanton Zürich bedienter Halt fehlt im Schnappschuss (Vorprüfung mit der Versionsgeschichte in
    PR #27, jetzt auf den echten Daten).
- **Wie gezählt wird (Entscheid des Agenten, im Review zu bestätigen):**
  - (A3) wie H1 (`quality.status_coverage`): je Ankunft und Abfahrt mit Soll-Zeit an einem nicht ausgefallenen Halt
    eine Zeile, Anteil mit Status `REAL`; nur Halte, die im Schnappschuss im Kanton Zürich liegen. Der Vergleich der
    Fahrpläne nimmt alle Ereignisse je Fahrplan zusammen.
  - (A4) Eine Fahrt widerspricht, wenn bei zwei aufeinanderfolgenden Zeilen (nach `ZEILE`) die erste Soll-Zeit der
    späteren Zeile vor der letzten Soll-Zeit der früheren liegt. Gezählt über alle Fahrten des Monats, wie geladen.
  - (Halte) Ob ein Halt, der im Schnappschuss fehlt, in Zürich liegt, steht gerade nicht im Schnappschuss. Darum wird
    geprüft, ob jede Schweizer `BPUIC` (85…) der zwölf Monate im Schnappschuss steht; fehlende Halte stehen mit Anzahl
    Fahrten und Name im Befund, und es wird dort festgestellt, ob einer davon in Zürich liegt.

## 2026-11-08 — Entscheidung: Zeitraum 13.7.2025 bis 30.6.2026 (Issue #30)

- **Entscheidung:** `period.py` setzt die Monate Juli 2025 bis Juni 2026. Die Daten beginnen am 13.7.2025: Das
  Monatsarchiv Juli 2025 enthält nur die Tage 13. bis 31. Juli (Beleg: Dateiliste des ZIPs und die Warnung von
  `uv run build` aus PR #25: «im Archiv fehlen Tage des Zeitraums: 2025-07-01, …, 2025-07-12»). Die Lücke liegt im
  Archiv, nicht beim Laden. Damit 353 Tage, Fahrplan 2025 vom 13.7. bis 13.12.2025 (154 Tage), Fahrplan 2026 vom 14.12.2025 bis
  30.6.2026 (199 Tage). Das Issue nannte 166 Tage für den Fahrplan 2025, ausgehend vom 1.7.
- **Begründung:** Beide Fahrpläne mit dem Fahrplanwechsel vom 14.12.2025 und alle Jahreszeiten, jeder Monat einmal.
- **Alternativen:** Juli bis Juli (Juli doppelt) und Juli bis Mai (nur elf Monate), beide im Issue verworfen.
  August 2025 bis Juli 2026 (zwölf volle Monate, 365 Tage) verworfen (Entscheid Haonan): grössere Abweichung vom
  Issue und ein weiterer Download von 1.4 GB.

## 2026-11-08 — Entscheidung: `load` liest auch Tagesdateien ohne `SLOID` (Issue #30)

- **Befund:** Die Tagesdateien vom 13.7. bis 12.10.2025 haben 21 Spalten, ab dem 13.10.2025 22: Die Spalte `SLOID`
  kam am 13.10.2025 dazu (Beleg: Kopfzeilen aller Tagesdateien der zwölf Archive). `load` brach am ersten Tag ab.
- **Entscheidung:** Fehlt `SLOID`, schreibt `load` die Spalte leer (`NULL`), damit alle Tage dasselbe Schema haben
  (`load.select_typed`, ein Test mit einer Datei ohne `SLOID`). Keine Auswertung verwendet `SLOID`.
- **Abweichung vom Issue:** Das Issue schloss Änderungen an `load` aus. Ohne die Änderung lassen sich die Monate vor
  dem 13.10.2025 nicht laden (Entscheid Haonan: im selben PR statt als eigenes Paket).

## 2026-11-08 — Befund: Zwölf Monate, Annahmen A3 und A4, Halte im Schnappschuss (Issue #30)

Berechnet in `notebooks/06_zwoelf_monate.py` nach der Hypothese oben (Commit `ed40418`, gepusht 2026-11-08 17:55 UTC,
vor dem Laden). Daten aus `uv run build`, 13.7.2025 bis 30.6.2026.

| Monat | Tage | `REAL` Kanton Zürich | Fahrten | Fahrten mit Widerspruch | Anteil |
|---|---|---|---|---|---|
| 2025-07 | 19 | 99.50 % | 303'785 | 257 | 0.085 % |
| 2025-08 | 31 | 99.22 % | 491'961 | 336 | 0.068 % |
| 2025-09 | 30 | 99.62 % | 475'348 | 316 | 0.066 % |
| 2025-10 | 31 | 99.62 % | 475'898 | 469 | 0.099 % |
| 2025-11 | 30 | 99.70 % | 458'800 | 86 | 0.019 % |
| 2025-12 | 31 | 99.72 % | 475'180 | 250 | 0.053 % |
| 2026-01 | 31 | 99.71 % | 484'098 | 237 | 0.049 % |
| 2026-02 | 28 | 99.61 % | 444'274 | 231 | 0.052 % |
| 2026-03 | 31 | 99.56 % | 487'669 | 436 | 0.089 % |
| 2026-04 | 30 | 99.55 % | 468'966 | 309 | 0.066 % |
| 2026-05 | 31 | 99.25 % | 484'176 | 756 | 0.156 % |
| 2026-06 | 30 | 99.48 % | 470'809 | 877 | 0.186 % |

- **(A3) gehalten.** Jeder Monat liegt über 95 % (tiefster Wert 99.22 %, August 2025). Fahrplan 2025: 99.55 % von
  7'027'903 Ereignissen, Fahrplan 2026: 99.55 % von 9'046'132; Unterschied 0.00 Prozentpunkte. Der Kanton Zürich liegt
  damit deutlich über dem Schweizer Wert aus H1 (96.2 %), mit dem die Erwartung begründet war.
- **(A4) nicht gehalten.** Zehn Monate liegen unter 0.1 %, Mai 2026 (0.156 %) und Juni 2026 (0.186 %) darüber. Die
  Erwartung stützte sich auf H2 («0 Widersprüche am 8.9.2026»); H2 hatte nur Halte in derselben Soll-Minute mit den
  Ist-Zeiten verglichen, nicht jede Soll-Zeit, die Zahlen sind also nicht direkt vergleichbar. Was die Widersprüche
  sind (beschreibend, nach dem Befund gerechnet, nicht im Notebook):
  - 4'614 Schritte in 4'560 Fahrten im ganzen Zeitraum, an jedem Tag im Mai und Juni mindestens einer. Etwa die
    Hälfte betrifft Halte im Ausland (SNCF, vor allem RB und TER bei Neuenburg (Baden): 1'974 Fahrten); 2'379 Schritte
    liegen zwischen zwei Schweizer Halten, 1'316 zwischen zwei Halten im Kanton Zürich, davon 1'029 im Mai und Juni,
    am häufigsten S7 bei Zürich Flughafen.
  - Median 2 Minuten rückwärts, 90 % bis 15 Minuten.
  - Bei 186 Schritten sind beide Zeiten gemessen; bei 108 davon laufen auch die Ist-Zeiten rückwärts. Dort stimmt die
    `ZEILE`-Reihenfolge nicht mit der gefahrenen Reihenfolge überein, nicht nur die Soll-Zeit.
  - Der Schritt `sections` verwirft Abschnitte mit rückwärts laufender Soll-Zeit bereits: Im Abschnitts-File des
    Zeitraums hat keine Abschnittsfahrt eine negative Soll-Fahrzeit. Ob eine falsche Reihenfolge andere Abschnitte
    erzeugt, deren Soll-Zeit vorwärts läuft, ist im Review nachgeprüft (Eintrag 2026-11-10).
  - Der Datentest zur Reihenfolge (`tests/test_data.py`, höchstens 1 von 10'000 Schweizer Abschnitten rückwärts)
    zeigt dasselbe Muster: pro Monat 0.05 bis 0.5 von 10'000, im Mai 2026 1.1 und im Juni 2026 1.5. Er läuft jetzt pro
    Monat und führte Mai und Juni zuerst mit einer eigenen Obergrenze von 2 von 10'000 (Entscheid Haonan); im Review
    ersetzt (Eintrag 2026-11-10).
- **(Halte) gehalten.** Jede Schweizer `BPUIC` des Zeitraums steht im Schnappschuss vom 2026-10-05, auch ausserhalb
  von Zürich; es fehlt kein Halt. Die Vorprüfung in PR #27 (Aigle-Hôpital) betraf keinen Halt in den Bahndaten.
- **Status in `docs/assumptions.md`:** A3 «gestützt», Evidenz «hoch» (für den Kanton Zürich); A4 «teilweise»,
  Evidenz «mittel» (10 von 12 Monaten). Die Tabelle ist neu sortiert.
- **Entscheidung (Haonan, 2026-11-08, Vorschlag des Agenten übernommen):** Die Rangliste bleibt auf den Abschnitten
  nach `ZEILE`; Abschnitte mit rückwärts laufender Soll-Zeit verwirft `sections` schon. Die Häufung im Mai und Juni
  2026 (S7 bei Zürich Flughafen) wird bei A5 («Gleicher Weg») geprüft, weil sie nach geänderten Laufwegen aussieht.

## 2026-11-08 — KI-Einsatz: Issue #30

- **Aufgabe:** zwölf Monate laden, A3, A4 und die Halte im Schnappschuss prüfen, Zeitraum festlegen.
- **Mine:** das Issue mit den drei Erwartungen (schwagia); die Entscheide (Haonan): `SLOID`-Korrektur im selben PR;
  Zeitraum als Monate Juli 2025 bis Juni 2026 mit Beginn am 13.7.; Hypothese vor dem Laden gepusht; Platz für den
  Download (ZIP September 2026 gelöscht, Neustart des Rechners); Mai und Juni 2026 im Datentest als bekannter Befund
  mit Obergrenze statt einer Prüfung über den ganzen Zeitraum, die die zwei Monate verdeckt hätte; die Entscheidung im
  Befund (Vorschlag des Agenten übernommen).
- **Delegated:** Claude Code hat den Hypothesen-Eintrag aus dem Issue, `period.py`, die Korrektur in `load.py` mit
  Test, die Anpassung von `tests/test_build.py`, das Notebook 06, die Beschreibung der Widersprüche, die Einträge in
  `assumptions.md` und diese Einträge geschrieben. Entscheide des Agenten: wie gezählt wird (im Hypothesen-Eintrag,
  vor dem Lauf); die Prüfung «Halte» über alle Schweizer `BPUIC`, weil der Kanton eines fehlenden Halts nicht
  bekannt ist; `tests/test_build.py` setzt den Zeitraum auf September 2026, weil die Tests sonst vom Zeitraum in
  `period.py` abhängen; die Datentests prüfen Lücken nur im Zeitraum (im Ordner liegen weiter die Tage vom September
  2026 für die Notebooks 03 bis 05) und die Reihenfolge pro Monat, weil die Abfrage über den ganzen Zeitraum mehr als
  10 GB Platz auf der Festplatte brauchte und mit «No space left on device» abbrach; der Vorschlag zur Entscheidung.
- **Prüfung:** Der neue Test in `tests/test_load.py` schlägt mit dem alten `load` fehl und läuft mit der Korrektur
  durch. Die Tage je Monat stimmen mit den Dateilisten der Archive überein (19 im Juli, sonst Kalendertage). Tests,
  `ruff` und `marimo check` laufen durch.
- **Übernommen/verworfen:** Nicht übernommen: die Widersprüche nach dem Befund nur zwischen Schweizer Halten zu
  zählen; das hätte die Regel an das Ergebnis angepasst. Die Aufteilung steht nur beschreibend im Befund.

## 2026-11-10 — Entscheidung: A4-Widersprüche sind meist Umleitungen, Datentest ohne eigene Obergrenze (Review PR #31)

Anlass: zwei Fragen von schwagia im Review. Gerechnet nach dem Befund, beschreibend, in `notebooks/06_zwoelf_monate.py`
(Abschnitt «A4: Widersprüche und Abschnitte»); keine neue Erwartung, darum keine Hypothese.

- **Befund:** Die Widersprüche sind fast alle Umleitungen. Beispiel S7 Winterthur–Rapperswil am 14.6.2026: Zürich
  Flughafen (Soll 10:27) steht als zusätzlicher Halt in der Fahrt, die ausgelassenen Halte Kloten (10:24) und Kloten
  Balsberg (10:26) bleiben als ausgefallene Zeilen dahinter stehen. Von den 1'316 rückwärts laufenden Schritten
  zwischen zwei Halten im Kanton Zürich haben 1'306 eine ausgefallene Zeile (im ganzen Zeitraum 2'351 von 4'614).
  `sections` bildet über ausgefallene Halte keinen Abschnitt; die übrigen Abschnitte dieser Fahrten folgen dem
  gefahrenen Weg. Von 7'510'318 Zürcher Abschnittsfahrten liegen 1'225 an einem solchen Schritt, davon 22 an einem
  Schritt ohne ausgefallene Zeile (3 von 1 Mio.); nur diese 22 könnten in falscher Reihenfolge gebildet sein.
- **Entscheidung (Haonan, Vorschlag des Agenten übernommen):** `sections` bleibt, wie es ist. Fahrten mit Widerspruch
  auszuschliessen würde 15'383 Zürcher Abschnittsfahrten entfernen, fast nur die umgeleiteten S7-Fahrten im Mai und
  Juni und damit gerade gestörte Fahrten, um 22 möglicherweise falsche zu vermeiden. Die Prüfung bei A5 («Gleicher
  Weg») bleibt.
- **Entscheidung (Haonan, Vorschlag des Agenten übernommen):** Der Datentest zur Reihenfolge hat für jeden Monat
  dieselbe Grenze von 1 von 10'000. Die eigene Obergrenze von 2 von 10'000 für Mai und Juni war erst nach dem Befund
  festgelegt und hätte den Test an das Ergebnis angepasst. Mai und Juni 2026 sind jetzt als erwarteter Fehlschlag
  markiert (`xfail`, `strict`), mit Verweis auf diesen Eintrag. Läuft einer der beiden Monate wieder durch, wird der
  Test rot; liegt ein anderer Monat über der Grenze, ebenfalls. Eine weitere Ausnahme gibt es nur mit Log-Eintrag
  und Review. Die Prüfung «eine Fahrt hat einen Betreiber und eine Linie» ist ein eigener Test, damit die Markierung
  sie nicht verdeckt.
- **Status A4:** bleibt «teilweise», Evidenz «mittel»; ergänzt, dass die Widersprüche meist Umleitungen sind.

## 2026-11-10 — KI-Einsatz: Review PR #31

- **Mine:** die Fragen im Review (schwagia); die beiden Entscheide (Haonan).
- **Delegated:** Claude Code hat die Zählungen, den Abschnitt im Notebook 06, die Änderung in `tests/test_data.py`,
  diese Einträge und die Antworten im Review geschrieben. Entscheid des Agenten: als Grenze für «möglicherweise
  falsch» gilt ein Abschnitt, dessen Halt A oder B an einem rückwärts laufenden Schritt ohne ausgefallene Zeile liegt.
- **Prüfung:** Die Zahlen im Notebook stimmen mit einer getrennten Zählung pro Monat überein. Mit der alten Grenze
  wären Mai und Juni rot; mit `xfail` laufen sie als erwarteter Fehlschlag, alle anderen Monate durch. Tests, `ruff`
  und `marimo check` laufen durch.

## 2026-11-10 — Hypothese: Rangliste mit Referenzwert je Soll-Fahrzeit (Issue #23, vor der Analyse notiert)

Anlass: Entscheidung zu Issue #18 (A7 widerlegt, die rohe Rangliste bevorzugt kurze Abschnitte). Basis: 13.7.2025 bis
30.6.2026 (`period.py`, Beginn laut Eintrag vom 2026-11-08), Abschnittsfahrten aus `uv run build`
(`sections.sections`, Regeln wie #14), beide Halte im Kanton Zürich laut Schnappschuss vom 2026-10-05.

- **Erwartung (schwagia, im Issue):**
  - (a) In der rohen Top 10 haben mindestens 4 Abschnitte eine Soll-Fahrzeit von höchstens 2 Minuten, in der Top 10
    mit Referenzwert höchstens 2.
  - (b) Höchstens 5 der Abschnitte aus der rohen Top 10 stehen auch in der Top 10 mit Referenzwert.
- **Regeln aus dem Issue und aus #14 und #18:**
  - Abschnitt = Paar (Halt A, Halt B), je Richtung getrennt. In die Rangliste kommt ein Abschnitt mit mindestens 20
    gemessenen Fahrten im Zeitraum (vorläufig wie #14, bis «Regeln festlegen» sie neu setzt). Rang nach Mittelwert,
    `rank()`, absteigend.
  - Roh: Mittel der Streckenverspätung je Abschnitt. Mit Referenzwert: von jeder Abschnittsfahrt wird das Mittel
    ihrer Klasse der Soll-Fahrzeit abgezogen, dann gemittelt. Klassen 1, 2, 3, 4, 5 und mehr Minuten; die
    Klassenmittel über alle Zürcher Abschnittsfahrten desselben Zeitraums.
  - Soll-Fahrzeit eines Abschnitts in den Tabellen und für (a): Median über seine Fahrten (wie #18).
- **Ergänzt vom Agenten (im Review zu bestätigen):** Fahrten mit 0 Minuten Soll-Fahrzeit (Ankunft B in derselben
  Minute wie Abfahrt A) kamen in der Woche von #18 nicht vor. Kommen sie im Zeitraum vor, bilden sie eine eigene
  Klasse 0 mit eigenem Mittel, statt mit der Klasse 1 vermischt zu werden; ihre Anzahl steht im Befund. Für (a)
  zählen sie zu «höchstens 2 Minuten».
